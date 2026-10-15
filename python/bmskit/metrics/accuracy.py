"""Set-level (device-mounted) accuracy of SOC, SOH and ISD across environments.

Inputs are SBL v1 logs (docs/spec/sbl_v1.md). Channel and meta conventions:

* SOC: ``bms.soc`` [%] vs ``ref.soc`` [%]. Without ``ref.soc``, a reference is built by
  coulomb counting ``ref.i`` (or ``pack.i``) from ``meta ref.soc0`` [%] with ``meta ref.capacity_ah``
  (or ``cell.capacity_ah`` x ``pack.parallel``).
* SOH: ``bms.soh`` [%] (last valid value) vs ``meta ref.soh`` [%].
* ISD: BMS outputs ``bms.isd_flag`` (0/1), ``bms.isd_cell`` (index), ``bms.isd_r`` [Ohm];
  labels in meta ``label.isd`` (``none`` or ``yes``), ``label.isd_cell``, ``label.isd_r_ohm``,
  ``label.isd_t_start`` [s].
* Environment: meta ``env`` (free text), ``test.temp_degc``, ``test.type``.

Errors are stratified by temperature, current and SOC bands so accuracy can be compared across
environments.

CLI::

    python -m bmskit.metrics.accuracy soc  <log.sbl.tsv>...   [--json]
    python -m bmskit.metrics.accuracy soh  <log.sbl.tsv>...
    python -m bmskit.metrics.accuracy isd  <log.sbl.tsv>...
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from ..logs import sbl

TEMP_BANDS = ((-np.inf, 0, "<0C"), (0, 10, "0-10C"), (10, 25, "10-25C"), (25, 40, "25-40C"), (40, np.inf, ">40C"))
CRATE_BANDS = ((0, 0.02, "rest"), (0.02, 0.5, "<0.5C"), (0.5, 1.0, "0.5-1C"), (1.0, np.inf, ">1C"))
SOC_BANDS = ((-np.inf, 20, "SOC<20"), (20, 80, "SOC20-80"), (80, np.inf, "SOC>80"))


def _arr(log: sbl.SBLLog, name: str) -> np.ndarray | None:
    v = log.data.get(name)
    if v is None:
        return None
    return np.array([np.nan if x is None else x for x in v], dtype=float)


def _sign(log: sbl.SBLLog) -> float:
    return 1.0 if log.meta.get("current_sign", "discharge_positive") == "discharge_positive" else -1.0


def capacity_ah(log: sbl.SBLLog) -> float | None:
    for key in ("ref.capacity_ah",):
        if key in log.meta:
            return float(log.meta[key])
    if "cell.capacity_ah" in log.meta:
        return float(log.meta["cell.capacity_ah"]) * float(log.meta.get("pack.parallel", 1))
    return None


def reference_soc(log: sbl.SBLLog) -> tuple[np.ndarray | None, str]:
    ref = _arr(log, "ref.soc")
    if ref is not None:
        return ref, "ref.soc"
    cap = capacity_ah(log)
    soc0 = log.meta.get("ref.soc0")
    cur = _arr(log, "ref.i")
    src = "ref.i"
    if cur is None:
        cur, src = _arr(log, "pack.i"), "pack.i"
    t = _arr(log, "t")
    if cap is None or soc0 is None or cur is None or t is None:
        return None, "unavailable (need ref.soc, or ref.soc0 + capacity + current)"
    i = np.nan_to_num(cur) * _sign(log)  # discharge positive
    dt = np.diff(t, prepend=t[0])
    ah = np.cumsum(i * dt) / 3600.0
    return float(soc0) - 100.0 * ah / cap, f"coulomb counting of {src} from ref.soc0"


def _band(values: np.ndarray, bands) -> np.ndarray:
    out = np.full(values.shape, "", dtype=object)
    for lo, hi, name in bands:
        out[(values >= lo) & (values < hi)] = name
    return out


def soc_accuracy(log: sbl.SBLLog) -> dict:
    est = _arr(log, "bms.soc")
    ref, ref_src = reference_soc(log)
    res: dict = {"source": log.meta.get("source", ""), "env": environment(log), "reference": ref_src}
    if est is None or ref is None:
        res["error"] = "need bms.soc and a SOC reference"
        return res
    err = est - ref
    ok = ~np.isnan(err)
    t = _arr(log, "t")
    res.update(_stats(err[ok]))
    span_h = (t[ok][-1] - t[ok][0]) / 3600.0 if ok.sum() > 1 else 0.0
    res["drift_pct_per_h"] = float(np.polyfit(t[ok] / 3600.0, err[ok], 1)[0]) if span_h > 0.1 else None
    res["final_error"] = float(err[ok][-1]) if ok.any() else None
    strata = {}
    temp = _first_temp(log)
    if temp is not None:
        strata["temperature"] = _stratify(err, _band(temp, TEMP_BANDS))
    cap = capacity_ah(log)
    cur = _arr(log, "pack.i")
    if cap and cur is not None:
        strata["c_rate"] = _stratify(err, _band(np.abs(cur) / cap, CRATE_BANDS))
    strata["soc"] = _stratify(err, _band(ref, SOC_BANDS))
    res["strata"] = strata
    return res


def _first_temp(log: sbl.SBLLog) -> np.ndarray | None:
    names = [n for n in log.names if n.startswith("temp.cell.")] or [n for n in log.names if n.startswith("temp.")]
    if not names:
        return None
    arrs = np.vstack([_arr(log, n) for n in names])
    with np.errstate(all="ignore"):
        return np.nanmean(arrs, axis=0)


def _stats(e: np.ndarray) -> dict:
    if e.size == 0:
        return {"n": 0}
    return {"n": int(e.size), "rmse": float(np.sqrt(np.mean(e ** 2))), "mean": float(e.mean()),
            "max_abs": float(np.abs(e).max()), "p95_abs": float(np.percentile(np.abs(e), 95))}


def _stratify(err: np.ndarray, labels: np.ndarray) -> dict:
    out = {}
    for lab in sorted({x for x in labels if x}):
        m = (labels == lab) & ~np.isnan(err)
        if m.any():
            out[lab] = _stats(err[m])
    return out


def environment(log: sbl.SBLLog) -> str:
    parts = [log.meta.get("env", "")]
    if "test.temp_degc" in log.meta:
        parts.append(f"{log.meta['test.temp_degc']}C")
    if "test.type" in log.meta:
        parts.append(log.meta["test.type"])
    return " / ".join(p for p in parts if p) or "unspecified"


def soh_accuracy(logs: Sequence[sbl.SBLLog]) -> dict:
    rows = []
    for log in logs:
        est = _arr(log, "bms.soh")
        ref = log.meta.get("ref.soh")
        if est is None or ref is None or np.all(np.isnan(est)):
            rows.append({"source": log.meta.get("source", ""), "error": "need bms.soh and meta ref.soh"})
            continue
        last = float(est[~np.isnan(est)][-1])
        rows.append({"source": log.meta.get("source", ""), "env": environment(log), "bms_soh": last,
                     "ref_soh": float(ref), "error": last - float(ref)})
    errs = np.array([r["error"] for r in rows if isinstance(r.get("error"), float)])
    by_env = defaultdict(list)
    for r in rows:
        if isinstance(r.get("error"), float):
            by_env[r["env"]].append(r["error"])
    return {"logs": rows, "overall": _stats(errs),
            "by_env": {k: _stats(np.array(v)) for k, v in by_env.items()}}


def isd_evaluation(logs: Sequence[sbl.SBLLog]) -> dict:
    rows = []
    for log in logs:
        label = log.meta.get("label.isd")
        flag = _arr(log, "bms.isd_flag")
        t = _arr(log, "t")
        row: dict = {"source": log.meta.get("source", ""), "env": environment(log)}
        if label is None or flag is None:
            row["error"] = "need meta label.isd and bms.isd_flag"
            rows.append(row)
            continue
        truth = label.strip().lower() not in ("none", "no", "0", "false")
        t_start = float(log.meta.get("label.isd_t_start", t[0]))
        on = np.flatnonzero(np.nan_to_num(flag) > 0.5)
        detected = on.size > 0
        first = float(t[on[0]]) if detected else None
        row.update({"truth": truth, "detected": detected})
        if truth and detected:
            row["outcome"] = "TP" if first >= t_start else "TP_early(false alarm before onset)"
            row["delay_s"] = first - t_start
            cell_est = _arr(log, "bms.isd_cell")
            if cell_est is not None and "label.isd_cell" in log.meta:
                row["cell_correct"] = bool(round(float(cell_est[on[-1]])) == int(float(log.meta["label.isd_cell"])))
            r_est = _arr(log, "bms.isd_r")
            if r_est is not None and "label.isd_r_ohm" in log.meta:
                re_ = float(r_est[on[-1]])
                rt = float(log.meta["label.isd_r_ohm"])
                if re_ > 0 and rt > 0:
                    row["r_log10_error"] = math.log10(re_ / rt)
        elif truth:
            row["outcome"] = "FN"
        elif detected:
            row["outcome"] = "FP"
            row["first_alarm_s"] = first
        else:
            row["outcome"] = "TN"
        rows.append(row)
    return {"logs": rows, "overall": _confusion(rows), "by_env": {
        env: _confusion([r for r in rows if r.get("env") == env]) for env in sorted({r.get("env") for r in rows})}}


def _confusion(rows) -> dict:
    c = defaultdict(int)
    delays, rerr, cells = [], [], []
    for r in rows:
        o = r.get("outcome")
        if o is None:
            continue
        c["TP" if o.startswith("TP") else o] += 1
        if "delay_s" in r and r["delay_s"] >= 0:
            delays.append(r["delay_s"])
        if "r_log10_error" in r:
            rerr.append(abs(r["r_log10_error"]))
        if "cell_correct" in r:
            cells.append(r["cell_correct"])
    tp, fp, fn, tn = c["TP"], c["FP"], c["FN"], c["TN"]
    out = {"TP": tp, "FP": fp, "FN": fn, "TN": tn,
           "recall": tp / (tp + fn) if tp + fn else None,
           "precision": tp / (tp + fp) if tp + fp else None,
           "false_alarm_rate": fp / (fp + tn) if fp + tn else None}
    if delays:
        out["delay_s_median"] = float(np.median(delays))
        out["delay_s_max"] = float(np.max(delays))
    if cells:
        out["cell_localization_accuracy"] = float(np.mean(cells))
    if rerr:
        out["r_abs_log10_error_median"] = float(np.median(rerr))
    return out


# ---------------------------------------------------------------- markdown

def soc_markdown(results: list[dict]) -> str:
    lines = ["# SOC 정확도 (세트)", "", "| 로그 | 환경 | 기준 | RMSE %p | 평균 %p | 최대 %p | 최종 %p | 드리프트 %p/h |",
             "|---|---|---|---|---|---|---|---|"]
    for r in results:
        if "error" in r:
            lines.append(f"| {r['source']} | {r['env']} | {r['reference']} | - | - | - | - | {r['error']} |")
            continue
        d = r.get("drift_pct_per_h")
        lines.append(f"| {r['source']} | {r['env']} | {r['reference']} | {r['rmse']:.2f} | {r['mean']:+.2f} | "
                     f"{r['max_abs']:.2f} | {r['final_error']:+.2f} | {'-' if d is None else f'{d:+.3f}'} |")
    agg: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for r in results:
        for dim, strata in r.get("strata", {}).items():
            for lab, s in strata.items():
                agg[dim][lab].append(s)
    for dim, labs in agg.items():
        lines += ["", f"## 조건별 ({dim})", "", "| 구간 | 로그 수 | 샘플 | RMSE %p | 평균 %p | 최대 %p |", "|---|---|---|---|---|---|"]
        for lab, ss in labs.items():
            n = sum(s["n"] for s in ss)
            rmse = math.sqrt(sum(s["rmse"] ** 2 * s["n"] for s in ss) / n)
            mean = sum(s["mean"] * s["n"] for s in ss) / n
            lines.append(f"| {lab} | {len(ss)} | {n} | {rmse:.2f} | {mean:+.2f} | {max(s['max_abs'] for s in ss):.2f} |")
    return "\n".join(lines) + "\n"


def isd_markdown(res: dict) -> str:
    def row(name, c):
        f = lambda x: "-" if x is None else f"{x:.2f}"  # noqa: E731
        return (f"| {name} | {c['TP']} | {c['FP']} | {c['FN']} | {c['TN']} | {f(c['recall'])} | {f(c['precision'])} | "
                f"{f(c['false_alarm_rate'])} | {c.get('delay_s_median', '-')} | {f(c.get('cell_localization_accuracy'))} |")
    lines = ["# ISD 감지 평가 (세트)", "",
             "| 범위 | TP | FP | FN | TN | 재현율 | 정밀도 | 오경보율 | 지연 중앙값 s | 셀 위치 정확도 |",
             "|---|---|---|---|---|---|---|---|---|---|", row("전체", res["overall"])]
    for env, c in res["by_env"].items():
        lines.append(row(env, c))
    return "\n".join(lines) + "\n"


def _cli(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bmskit.metrics.accuracy")
    ap.add_argument("what", choices=("soc", "soh", "isd"))
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(list(argv) if argv is not None else None)
    logs = [sbl.read(p) for p in args.paths]
    for log, p in zip(logs, args.paths):
        log.meta.setdefault("source", Path(p).name)
    if args.what == "soc":
        res = [soc_accuracy(l) for l in logs]
        print(json.dumps(res, ensure_ascii=False, indent=2) if args.json else soc_markdown(res))
    elif args.what == "soh":
        res = soh_accuracy(logs)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        res = isd_evaluation(logs)
        print(json.dumps(res, ensure_ascii=False, indent=2) if args.json else isd_markdown(res))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
