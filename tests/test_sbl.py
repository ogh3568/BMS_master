"""Tests for SBL v1 and the legacy importer (stdlib unittest; run: python -m unittest)."""

from __future__ import annotations

import math
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from bmskit.logs import legacy, sbl  # noqa: E402

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sbl" / "example_l3.sbl.tsv"

try:
    import openpyxl  # noqa: F401
    HAVE_XLSX = True
except ImportError:
    HAVE_XLSX = False


def make_log(n: int = 10) -> sbl.SBLLog:
    log = sbl.SBLLog(meta={"sbl": "1.0", "current_sign": "discharge_positive",
                           "t0": "2026-10-15T09:00:00+09:00", "pack.series": "2"})
    chans = [("t", "s"), ("pack.v", "V"), ("pack.i", "A"), ("cell.v.01", "V"),
             ("cell.v.02", "V"), ("temp.cell.01", "degC"), ("bms.soc", "%"), ("model.v_pred", "V")]
    for name, unit in chans:
        log.channels.append(sbl.Channel(name, unit))
    log.data = {
        "t": [float(i) for i in range(n)],
        "pack.v": [8.2 - 0.01 * i for i in range(n)],
        "pack.i": [10.0] * n,
        "cell.v.01": [4.1 - 0.005 * i for i in range(n)],
        "cell.v.02": [4.1 - 0.005 * i for i in range(n)],
        "temp.cell.01": [25.0] * n,
        "bms.soc": [90.0 - 0.1 * i for i in range(n)],
        "model.v_pred": [4.1 - 0.005 * i for i in range(n)],
    }
    return log


class TestSBL(unittest.TestCase):
    def test_example_file_is_valid(self):
        rep = sbl.validate(sbl.read(EXAMPLE))
        self.assertTrue(rep.ok, [str(i) for i in rep.issues])
        self.assertEqual(rep.conformance, "L3+R")

    def test_text_roundtrip(self):
        log = make_log()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.sbl.tsv"
            sbl.write_text(log, p)
            back = sbl.read(p)
        self.assertEqual(back.names, log.names)
        self.assertAlmostEqual(back.data["pack.v"][3], log.data["pack.v"][3])
        rep = sbl.validate(back)
        self.assertTrue(rep.ok, [str(i) for i in rep.issues])
        self.assertEqual(rep.conformance, "L3")

    @unittest.skipUnless(HAVE_XLSX, "openpyxl not installed")
    def test_xlsx_roundtrip(self):
        log = make_log()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.xlsx"
            sbl.write_xlsx(log, p)
            back = sbl.read(p)
        self.assertEqual(back.names, log.names)
        self.assertEqual(back.meta["current_sign"], "discharge_positive")
        self.assertTrue(sbl.validate(back).ok)

    def test_detects_errors(self):
        log = make_log()
        log.data["t"][5] = 1.0  # time goes backwards
        log.channels.append(sbl.Channel("Cell.V.3", "V"))  # bad name
        log.data["Cell.V.3"] = [1.0] * 10
        del log.meta["current_sign"]
        codes = {i.code for i in sbl.validate(log).issues}
        self.assertTrue({"E031", "E012", "E020"} <= codes, codes)

    def test_unit_incompatible_and_normalize(self):
        log = make_log()
        log.channels[3].unit = "mV"
        log.data["cell.v.01"] = [v * 1000 for v in log.data["cell.v.01"]]
        rep = sbl.validate(log)
        self.assertTrue(rep.ok)
        self.assertIn("I010", {i.code for i in rep.issues})
        sbl.normalize_units(log)
        self.assertAlmostEqual(log.data["cell.v.01"][0], 4.1)
        log.channels[1].unit = "A"  # pack.v in amps
        self.assertIn("E014", {i.code for i in sbl.validate(log).issues})


class TestLegacy(unittest.TestCase):
    def test_cp949_txt_with_korean_headers(self):
        text = (
            "시험명\t주행시험A\n"
            "장비\tCycler-01\n"
            "시간\t팩전압(V)\t전류(A)\t셀전압1\t셀전압2\t온도1\tSOC\n"
            + "".join(
                f"00:00:{i:02d}\t{8.2 - 0.01 * i:.3f}\t-10.0\t{4100 - 5 * i}\t{4100 - 5 * i}\t25.1\t{0.9 - 0.001 * i:.3f}\n"
                for i in range(20)
            )
        )
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "legacy.txt"
            p.write_bytes(text.encode("cp949"))
            plan, _ = legacy.suggest_plan(p)
            self.assertEqual(plan.encoding, "cp949")
            self.assertEqual(plan.header_row, 2)
            self.assertEqual(plan.time_kind, "hms")
            targets = {c.source: c.target for c in plan.columns}
            self.assertEqual(targets["팩전압(V)"], "pack.v")
            self.assertEqual(targets["전류(A)"], "pack.i")
            self.assertEqual(targets["셀전압1"], "cell.v.01")
            self.assertEqual(targets["온도1"], "temp.cell.01")
            units = {c.target: c.unit for c in plan.columns}
            self.assertEqual(units["cell.v.01"], "mV")
            self.assertEqual(units["bms.soc"], "-")
            self.assertEqual(plan.meta.get("legacy.시험명"), "주행시험A")
            log, _ = legacy.convert(p, plan, current_sign="charge_positive")
        self.assertAlmostEqual(log.data["cell.v.01"][0], 4.1)
        self.assertAlmostEqual(log.data["bms.soc"][0], 90.0)
        self.assertEqual(log.data["t"][19], 19.0)
        rep = sbl.validate(log)
        self.assertTrue(rep.ok, [str(i) for i in rep.issues])
        self.assertEqual(rep.conformance, "L2")

    def test_plan_json_roundtrip_and_unknown_columns(self):
        text = "Time,Voltage,Current,MysterySignal\n" + "".join(
            f"{i * 0.5},{3.7},{1.0},{i}\n" for i in range(10)
        )
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.csv"
            p.write_text(text, encoding="utf-8")
            plan, _ = legacy.suggest_plan(p)
            targets = {c.source: c.target for c in plan.columns}
            self.assertEqual(targets["MysterySignal"], "x.mysterysignal")
            plan2 = legacy.ImportPlan.from_json(plan.to_json())
            log, _ = legacy.convert(p, plan2, current_sign="discharge_positive")
        self.assertEqual(log.data["t"][2], 1.0)
        self.assertTrue(sbl.validate(log).ok)

    @unittest.skipUnless(HAVE_XLSX, "openpyxl not installed")
    def test_xlsx_legacy(self):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Test Time (s)", "Pack Voltage (V)", "Pack Current (A)", "Cell_V_01 (mV)"])
        for i in range(10):
            ws.append([i, 400.0 - i * 0.1, 50.0, 3700 - i])
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "old.xlsx"
            wb.save(p)
            log, plan = legacy.convert(p, current_sign="discharge_positive")
        self.assertEqual({c.target for c in plan.columns} >= {"t", "pack.v", "pack.i", "cell.v.01"}, True)
        self.assertAlmostEqual(log.data["cell.v.01"][0], 3.7)
        self.assertFalse(any(math.isnan(v) for v in log.data["pack.v"]))


if __name__ == "__main__":
    unittest.main()
