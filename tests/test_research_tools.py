"""Tests for C parameter extraction, SIL adapter, inference engine and set-level accuracy.

The C model used here is a tiny test fixture (tests/fixtures/sil_toy) that stands in for the
user's model so the tool chain can be tested in CI.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None
try:
    import tree_sitter  # noqa: F401
    import tree_sitter_c  # noqa: F401
    HAVE_TS = True
except ImportError:
    HAVE_TS = False
HAVE_CC = shutil.which("cc") is not None or shutil.which("gcc") is not None

FIX = ROOT / "tests" / "fixtures"


@unittest.skipUnless(HAVE_TS, "tree-sitter not installed")
class TestCParams(unittest.TestCase):
    def test_extract(self):
        from bmskit.codeintel import cparams
        cands = {c.name_in_code: c for c in cparams.scan([FIX / "c_sample"])}
        self.assertEqual(cands["DS_NEG_REF"].kind, "define")
        self.assertEqual(cands["DS_NEG_REF"].group, "diffusion")
        self.assertAlmostEqual(cands["DS_NEG_REF"].value, 3.3e-14)
        self.assertEqual(cands["CELL_CAP_AH"].value, 5.0)
        self.assertEqual(cands["OCV_TBL"].shape, [3, 2])
        self.assertEqual(cands["g_param.R0"].kind, "struct_field")
        self.assertEqual(cands["g_param.R0"].ctype, "const float")
        self.assertIn("model_voltage", cands["g_param.R0"].used_by)
        self.assertEqual(cands["g_param.Ds_p"].used_by, [])
        self.assertEqual(cands["g_param.k_n"].group, "kinetics")
        self.assertEqual(cands["g_soc_gain"].kind, "variable")
        magic = [c for c in cands.values() if c.kind == "magic_number"]
        self.assertTrue(any(abs(c.value - 0.0123) < 1e-9 for c in magic))
        md = cparams.summary_markdown(list(cands.values()))
        self.assertIn("매직 넘버", md)


@unittest.skipUnless(HAVE_TS and HAVE_CC and np is not None, "needs tree-sitter, a C compiler and numpy")
class TestSilAndInference(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bmskit.codeintel import cparams
        from bmskit.sil import wrapgen
        from bmskit.sil.runner import SilModel, build_shared
        cls.tmp = tempfile.TemporaryDirectory()
        d = Path(cls.tmp.name)
        cls.registry = cparams.to_registry(cparams.scan([FIX / "sil_toy" / "toy_model.c"], include_magic=False))
        entries, skipped, files = wrapgen.plan(cls.registry)
        (d / "bms_sil_params.c").write_text(wrapgen.render(entries, files, ROOT), encoding="utf-8")
        lib = build_shared([d / "bms_sil_params.c", FIX / "sil_toy" / "toy_glue.c"], d / "libtoy.so",
                           include_dirs=[ROOT])
        cls.model = SilModel(lib)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def profile(self):
        t, i, tt = [], [], 0.0
        for _ in range(4):
            for dur, cur in ((10, 15.0), (120, 0.0), (10, -10.0), (120, 0.0), (600, 5.0), (300, 0.0)):
                for _ in range(dur):
                    t.append(tt)
                    i.append(cur)
                    tt += 1.0
        t = np.array(t)
        return t, np.array(i), np.where(t < len(t) / 2, 25.0, 5.0)

    def test_parameter_table(self):
        names = self.model.param_names
        self.assertIn("g_toy.r1", names)
        self.assertIn("ocv_tbl[3]", names)  # file-scope static reached through unity build
        self.assertAlmostEqual(self.model.defaults["g_toy.tau1"], 30.0)

    def test_recovery(self):
        from bmskit.optim import infer
        t, i, temp = self.profile()
        truth = {"g_toy.r1": 0.015 * 1.6, "g_toy.tau1": 60.0, "ocv_tbl[3]": 3.815, "g_toy.ea_r": 26000.0}
        meas = self.model.run(t, i, temp, 0.95, truth)["v"] + np.random.default_rng(0).normal(0, 5e-4, len(t))
        params = infer.params_from_registry(self.registry)
        sim = self.model.simulator(t, i, temp, 0.95)
        masks = infer.regimes(t, i, 5.0, temp, self.model.run(t, i, temp, 0.95)["soc"])
        res = infer.pipeline(sim, params, meas, masks, noise=5e-4)
        self.assertTrue(set(truth) <= set(res.selection.subset))
        self.assertIn("unused_gain", res.selection.rejected)
        self.assertEqual(set(res.final.values), set(truth))  # spurious picks are pruned after fitting
        self.assertLess(res.final.rmse, 1e-3)
        for k, v in truth.items():
            self.assertAlmostEqual(res.final.values[k] / v, 1.0, delta=0.02)
        md = infer.pipeline_markdown(res)
        self.assertIn("선택 순서", md)
        self.assertIn("검증", md)

    def test_collinearity_flags_redundant_pair(self):
        from bmskit.optim import infer
        t, i, _ = self.profile()
        params = infer.params_from_registry(self.registry, names=["g_toy.r0", "r_contact"])
        sim = self.model.simulator(t, i, 25.0, 0.95)  # constant temperature: r0 and r_contact act identically
        J = infer.jacobian(sim, params)
        self.assertGreater(infer.collinearity(J, [0, 1]), 100.0)


@unittest.skipUnless(np is not None, "numpy not installed")
class TestAccuracy(unittest.TestCase):
    def make_log(self, bias=1.0, temp=25.0, isd=None, flag_at=None, env="lab"):
        from bmskit.logs import sbl
        n = 3600
        t = [float(k) for k in range(n)]
        cur = [5.0 if k < 1800 else 0.0 for k in range(n)]
        ref_soc = [90.0 - 100.0 * min(k, 1800) * 5.0 / 3600.0 / 50.0 for k in range(n)]
        log = sbl.SBLLog(meta={"sbl": "1.0", "current_sign": "discharge_positive", "cell.capacity_ah": "50",
                               "env": env, "ref.soh": "95"})
        cols = {"t": t, "pack.v": [3.7] * n, "pack.i": cur, "temp.cell.01": [temp] * n,
                "bms.soc": [r + bias for r in ref_soc], "ref.soc": ref_soc, "bms.soh": [96.5] * n,
                "bms.isd_flag": [1.0 if flag_at is not None and k >= flag_at else 0.0 for k in range(n)],
                "bms.isd_cell": [3.0] * n, "bms.isd_r": [120.0] * n}
        units = {"t": "s", "pack.v": "V", "pack.i": "A", "temp.cell.01": "degC", "bms.soc": "%", "ref.soc": "%",
                 "bms.soh": "%", "bms.isd_flag": "-", "bms.isd_cell": "-", "bms.isd_r": "Ohm"}
        for k, v in cols.items():
            log.channels.append(sbl.Channel(k, units[k]))
            log.data[k] = v
        if isd is not None:
            log.meta.update({"label.isd": "yes", "label.isd_cell": "3", "label.isd_r_ohm": str(isd),
                             "label.isd_t_start": "600"})
        else:
            log.meta["label.isd"] = "none"
        return log

    def test_soc(self):
        from bmskit.metrics import accuracy
        r = accuracy.soc_accuracy(self.make_log(bias=1.0, temp=5.0))
        self.assertAlmostEqual(r["rmse"], 1.0, places=6)
        self.assertIn("0-10C", r["strata"]["temperature"])
        self.assertIn("rest", r["strata"]["c_rate"])
        self.assertIn("SOC>80", accuracy.soc_markdown([r]))

    def test_soc_coulomb_reference(self):
        from bmskit.metrics import accuracy
        log = self.make_log(bias=0.0)
        del log.data["ref.soc"]
        log.channels = [c for c in log.channels if c.name != "ref.soc"]
        log.meta["ref.soc0"] = "90"
        r = accuracy.soc_accuracy(log)
        self.assertIn("coulomb", r["reference"])
        self.assertLess(r["rmse"], 0.05)

    def test_soh_and_isd(self):
        from bmskit.metrics import accuracy
        logs = [self.make_log(isd=100.0, flag_at=900, env="cold"), self.make_log(isd=None, flag_at=None),
                self.make_log(isd=None, flag_at=2000), self.make_log(isd=50.0, flag_at=None)]
        soh = accuracy.soh_accuracy(logs)
        self.assertAlmostEqual(soh["overall"]["mean"], 1.5)
        res = accuracy.isd_evaluation(logs)
        o = res["overall"]
        self.assertEqual((o["TP"], o["FP"], o["FN"], o["TN"]), (1, 1, 1, 1))
        self.assertEqual(o["delay_s_median"], 300.0)
        self.assertEqual(o["cell_localization_accuracy"], 1.0)
        self.assertIn("cold", res["by_env"])
        self.assertIn("재현율", accuracy.isd_markdown(res))


if __name__ == "__main__":
    unittest.main()
