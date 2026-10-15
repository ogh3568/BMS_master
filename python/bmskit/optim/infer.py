"""Model-agnostic parameter inference: which parameters to optimize, and how much it should help.

Works with any simulator ``f(params: dict[str, float]) -> np.ndarray`` (normally the user's
C model through ``bmskit.sil.runner.SilModel.simulator``). Steps (docs/plan/09_param_inference.md):

1. ``regimes``      split the log into operating regimes (step response, relaxation, high rate, SOC ends, ...)
2. ``signature``    residual statistics per regime
3. ``jacobian``     finite-difference sensitivities in transformed coordinates (log or linear)
4. ``predict``      linearized, prior-regularized improvement for a parameter subset
5. ``collinearity`` identifiability of a subset (collinearity index of normalized sensitivities)
6. ``select``       greedy forward selection: largest predicted gain under an identifiability limit
7. ``fit``          Levenberg-Marquardt on the chosen subset (to verify the prediction)

Only numpy is required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

import numpy as np

Simulator = Callable[[dict[str, float]], np.ndarray]


@dataclass
class Param:
    name: str
    value: float
    scale: str = "log"  # "log": value * exp(u); "lin": value + u * unit
    unit: float = 1.0   # lin only: size of one transformed unit
    prior_sigma: float = 1.0  # in transformed units
    step: float = 0.05  # finite-difference step in transformed units
    lower: float = -np.inf  # bounds on transformed u
    upper: float = np.inf
    group: str = ""

    def apply(self, u: float) -> float:
        return self.value * float(np.exp(u)) if self.scale == "log" else self.value + u * self.unit


def params_from_registry(registry: Sequence[dict], names: Sequence[str] | None = None,
                         log_sigma: float = 0.7, expand_arrays: bool = True,
                         table_sigma: float = 0.05) -> list[Param]:
    """Build Params from cparams registry entries.

    Positive scalars use a log scale. Array (table) elements are expanded to ``name[i][j]``
    (the names used by the SIL parameter table) with a tighter prior ``table_sigma``.
    Use ``names`` to restrict the candidate set (exact names, or array base names).
    """
    def make(name: str, v: float, sigma: float, group: str) -> Param:
        if v > 0:
            return Param(name, v, "log", prior_sigma=sigma, group=group)
        unit = max(abs(v) * 0.05, 1e-3)
        return Param(name, v, "lin", unit=unit, prior_sigma=1.0, step=0.5, group=group)

    def flat(name, v, prefix=""):
        if isinstance(v, list):
            for i, x in enumerate(v):
                yield from flat(name, x, f"{prefix}[{i}]")
        elif v is not None:
            yield f"{name}{prefix}", float(v)

    out = []
    wanted = None if names is None else set(names)
    for r in registry:
        kind, base, value = r.get("kind"), r["name_in_code"], r.get("value")
        if kind in ("magic_number", "define") or value is None:
            continue
        if isinstance(value, list):
            if not expand_arrays:
                continue
            for n, v in flat(base, value):
                if wanted is None or base in wanted or n in wanted:
                    out.append(make(n, v, table_sigma, r.get("group", "")))
        elif wanted is None or base in wanted:
            out.append(make(base, float(value), log_sigma, r.get("group", "")))
    return out


# ---------------------------------------------------------------- regimes and signatures

def regimes(t: np.ndarray, current: np.ndarray, capacity_ah: float, temp_c: np.ndarray | None = None,
            soc: np.ndarray | None = None, step_threshold_c: float = 0.2) -> dict[str, np.ndarray]:
    """Boolean masks of operating regimes. C-rates use ``capacity_ah``."""
    t = np.asarray(t, float)
    i = np.asarray(current, float)
    c_rate = np.abs(i) / capacity_ah
    di = np.abs(np.diff(i, prepend=i[0])) / capacity_ah
    step_idx = np.flatnonzero(di > step_threshold_c)
    since = np.full(len(t), np.inf)
    j = 0
    last = -np.inf
    for k in range(len(t)):
        while j < len(step_idx) and step_idx[j] <= k:
            last = t[step_idx[j]]
            j += 1
        since[k] = t[k] - last
    rest = c_rate < 0.02
    m = {
        "all": np.ones(len(t), bool),
        "step_0_2s": since <= 2.0,
        "dynamic_2_60s": (since > 2.0) & (since <= 60.0) & ~rest,
        "relax_60s_plus": rest & (since > 60.0),
        "relax_first_60s": rest & (since <= 60.0) & (since > 2.0),
        "high_rate": c_rate > 1.0,
        "discharge": i > 0.02 * capacity_ah,
        "charge": i < -0.02 * capacity_ah,
    }
    if soc is not None:
        s = np.asarray(soc, float)
        s = s / 100.0 if np.nanmax(s) > 1.5 else s
        m.update({"soc_low": s < 0.15, "soc_mid": (s >= 0.15) & (s <= 0.85), "soc_high": s > 0.85})
    if temp_c is not None:
        tc = np.broadcast_to(np.asarray(temp_c, float), t.shape)
        m.update({"cold": tc < 10.0, "room": (tc >= 10.0) & (tc <= 35.0), "hot": tc > 35.0})
    return {k: v for k, v in m.items() if v.any()}


def signature(residual: np.ndarray, masks: dict[str, np.ndarray]) -> dict[str, dict[str, float]]:
    r = np.asarray(residual, float)
    out = {}
    for name, m in masks.items():
        rr = r[m]
        out[name] = {"n": int(m.sum()), "rmse": float(np.sqrt(np.mean(rr ** 2))),
                     "mean": float(rr.mean()), "max_abs": float(np.abs(rr).max())}
    return out


# ---------------------------------------------------------------- sensitivities and prediction

def evaluate(sim: Simulator, params: Sequence[Param], u: np.ndarray | None = None) -> np.ndarray:
    u = np.zeros(len(params)) if u is None else u
    return np.asarray(sim({p.name: p.apply(ui) for p, ui in zip(params, u)}), float)


def jacobian(sim: Simulator, params: Sequence[Param], u0: np.ndarray | None = None,
             base: np.ndarray | None = None) -> np.ndarray:
    """d(model output)/du, forward differences. Columns of insensitive parameters are ~0."""
    u0 = np.zeros(len(params)) if u0 is None else np.asarray(u0, float)
    y0 = evaluate(sim, params, u0) if base is None else base
    cols = []
    for k, p in enumerate(params):
        u = u0.copy()
        u[k] += p.step
        cols.append((evaluate(sim, params, u) - y0) / p.step)
    return np.column_stack(cols) if cols else np.zeros((len(y0), 0))


def predict(J: np.ndarray, residual: np.ndarray, subset: Sequence[int], sigma: np.ndarray,
            noise: float = 1e-3) -> tuple[np.ndarray, np.ndarray]:
    """Prior-regularized Gauss-Newton step on ``subset``. Returns (du_subset, predicted residual).

    Minimizes ||r - J_S du||^2 / noise^2 + ||du / sigma_S||^2, where r = measured - model.
    """
    S = list(subset)
    if not S:
        return np.zeros(0), residual.copy()
    js = J[:, S]
    a = js.T @ js / noise ** 2 + np.diag(1.0 / sigma[S] ** 2)
    b = js.T @ residual / noise ** 2
    du = np.linalg.solve(a, b)
    return du, residual - js @ du


def collinearity(J: np.ndarray, subset: Sequence[int]) -> float:
    """Collinearity index (Brun et al.): 1/sqrt(min eigenvalue) of normalized J_S^T J_S."""
    S = list(subset)
    if len(S) <= 1:
        return 1.0
    js = J[:, S]
    norms = np.linalg.norm(js, axis=0)
    if np.any(norms == 0):
        return np.inf
    jn = js / norms
    lam = np.linalg.eigvalsh(jn.T @ jn)
    return float(1.0 / np.sqrt(max(lam[0], 1e-300)))


def _rmse(x: np.ndarray, w: np.ndarray | None = None) -> float:
    return float(np.sqrt(np.mean(x ** 2))) if w is None else float(np.sqrt(np.sum(w * x ** 2) / np.sum(w)))


@dataclass
class SelectionStep:
    added: str
    rmse_pred: float
    gain: float
    collinearity: float


@dataclass
class Selection:
    subset: list[str]
    rmse_before: float
    rmse_pred: float
    steps: list[SelectionStep] = field(default_factory=list)
    rejected: dict[str, str] = field(default_factory=dict)
    single_gain: dict[str, float] = field(default_factory=dict)
    regime_gain: dict[str, dict[str, float]] = field(default_factory=dict)
    du: dict[str, float] = field(default_factory=dict)


def select(J: np.ndarray, residual: np.ndarray, params: Sequence[Param], *, k_max: int = 12,
           gamma_max: float = 15.0, min_gain: float = 0.01, noise: float = 1e-3,
           masks: dict[str, np.ndarray] | None = None, weights: np.ndarray | None = None) -> Selection:
    """Greedy forward selection maximizing predicted RMSE reduction under ``gamma_max``.

    ``min_gain`` is the minimum relative improvement (fraction of the starting RMSE) per added parameter.
    ``weights`` (per sample, >= 0) emphasize regimes when computing RMSE.
    """
    r = np.asarray(residual, float)
    w = None if weights is None else np.asarray(weights, float)
    sw = np.ones_like(r) if w is None else np.sqrt(w)
    Jw, rw = J * sw[:, None], r * sw
    sigma = np.array([p.prior_sigma for p in params])
    names = [p.name for p in params]
    rmse0 = _rmse(r, w)
    sel = Selection([], rmse0, rmse0)
    col_norm = np.linalg.norm(J, axis=0)
    insensitive = col_norm < 1e-9 * max(col_norm.max(), 1e-300)
    for k in np.flatnonzero(insensitive):
        sel.rejected[names[k]] = "insensitive (no effect on output)"
    for k in range(len(params)):
        if not insensitive[k]:
            _, rp = predict(Jw, rw, [k], sigma, noise)
            sel.single_gain[names[k]] = rmse0 - _rmse(rp / sw, w)
    S: list[int] = []
    cur = rmse0
    while len(S) < k_max:
        best = None
        for k in range(len(params)):
            if k in S or insensitive[k]:
                continue
            g = collinearity(J, S + [k])
            if g > gamma_max:
                continue
            _, rp = predict(Jw, rw, S + [k], sigma, noise)
            val = _rmse(rp / sw, w)
            if best is None or val < best[1]:
                best = (k, val, g)
        if best is None or cur - best[1] < min_gain * rmse0:
            break
        S.append(best[0])
        sel.steps.append(SelectionStep(names[best[0]], best[1], cur - best[1], best[2]))
        cur = best[1]
    for k in range(len(params)):
        if k not in S and not insensitive[k] and names[k] not in sel.rejected:
            g = collinearity(J, S + [k]) if S else 1.0
            if g > gamma_max:
                partner = max(S, key=lambda s: abs(np.corrcoef(J[:, s], J[:, k])[0, 1])) if S else None
                sel.rejected[names[k]] = (f"not identifiable together with selected set (collinearity {g:.1f}"
                                          + (f", most correlated with {names[partner]})" if partner is not None else ")"))
            else:
                sel.rejected[names[k]] = "gain below threshold"
    sel.subset = [names[k] for k in S]
    sel.rmse_pred = cur
    du, rp = predict(Jw, rw, S, sigma, noise)
    sel.du = {names[k]: float(d) for k, d in zip(S, du)}
    if masks:
        for k in S:
            _, r1 = predict(J, r, [k], sigma, noise)
            sel.regime_gain[names[k]] = {
                m: float(_rmse(r[mask]) - _rmse(r1[mask])) for m, mask in masks.items() if m != "all"}
    return sel


# ---------------------------------------------------------------- fitting

@dataclass
class FitResult:
    u: dict[str, float]
    values: dict[str, float]
    rmse_history: list[float]
    rmse: float


def fit(sim: Simulator, params: Sequence[Param], measured: np.ndarray, subset: Sequence[str],
        iters: int = 15, noise: float = 1e-3, weights: np.ndarray | None = None, tol: float = 1e-4) -> FitResult:
    """Levenberg-Marquardt with prior regularization on ``subset`` (other params fixed)."""
    idx = [i for i, p in enumerate(params) if p.name in set(subset)]
    sub = [params[i] for i in idx]
    sigma = np.array([p.prior_sigma for p in sub])
    lo = np.array([p.lower for p in sub])
    hi = np.array([p.upper for p in sub])
    meas = np.asarray(measured, float)
    w = np.ones_like(meas) if weights is None else np.asarray(weights, float)
    sw = np.sqrt(w)

    def full_u(us):
        u = np.zeros(len(params))
        u[idx] = us
        return u

    def cost(us, y):
        return float(np.sum(w * (meas - y) ** 2) / noise ** 2 + np.sum((us / sigma) ** 2))

    us = np.zeros(len(sub))
    y = evaluate(sim, params, full_u(us))
    c = cost(us, y)
    lam = 1e-2
    hist = [_rmse(meas - y, w)]
    for _ in range(iters):
        J = jacobian(sim, sub, us, y) if sub else np.zeros((len(meas), 0))
        Jw = J * sw[:, None]
        r = (meas - y) * sw
        a = Jw.T @ Jw / noise ** 2 + np.diag(1.0 / sigma ** 2)
        g = Jw.T @ r / noise ** 2 - us / sigma ** 2
        improved = False
        for _ in range(8):
            step = np.linalg.solve(a + lam * np.diag(np.diag(a)), g)
            un = np.clip(us + step, lo, hi)
            yn = evaluate(sim, params, full_u(un))
            cn = cost(un, yn)
            if cn < c:
                us, y, lam = un, yn, max(lam / 3.0, 1e-6)
                improved = c - cn > tol * c
                c = cn
                break
            lam *= 4.0
        hist.append(_rmse(meas - y, w))
        if not improved:
            break
    return FitResult({p.name: float(v) for p, v in zip(sub, us)},
                     {p.name: p.apply(v) for p, v in zip(sub, us)}, hist, hist[-1])


def report_markdown(sel: Selection, sig_before: dict, fit_res: FitResult | None = None,
                    sig_after: dict | None = None, unit: str = "V", scale: float = 1000.0,
                    unit_label: str = "mV") -> str:
    f = lambda x: f"{x * scale:.2f}"  # noqa: E731
    lines = ["# 파라미터 추론 리포트", "",
             f"- 현재 RMSE: **{f(sel.rmse_before)} {unit_label}**",
             f"- 선택한 {len(sel.subset)}개를 최적화했을 때 예측 RMSE: **{f(sel.rmse_pred)} {unit_label}**"]
    if fit_res is not None:
        lines.append(f"- 실제 최적화 후 RMSE: **{f(fit_res.rmse)} {unit_label}** (예측 대비 {f(fit_res.rmse - sel.rmse_pred)} {unit_label})")
    lines += ["", "## 선택 순서", "", f"| 순서 | 파라미터 | 예측 RMSE ({unit_label}) | 추가 이득 | 공선성 지수 | 예측 변화 |",
              "|---|---|---|---|---|---|"]
    for i, s in enumerate(sel.steps, 1):
        du = sel.du.get(s.added, 0.0)
        lines.append(f"| {i} | `{s.added}` | {f(s.rmse_pred)} | {f(s.gain)} | {s.collinearity:.1f} | {du:+.3f} |")
    if sel.regime_gain:
        regs = sorted({r for g in sel.regime_gain.values() for r in g})
        lines += ["", f"## 파라미터별 운전 영역 기여 (단독 조정 시 RMSE 감소, {unit_label})", "",
                  "| 파라미터 | " + " | ".join(regs) + " |", "|---|" + "---|" * len(regs)]
        for name, g in sel.regime_gain.items():
            lines.append(f"| `{name}` | " + " | ".join(f(g.get(r, 0.0)) for r in regs) + " |")
    lines += ["", f"## 운전 영역별 잔차 ({unit_label})", "", "| 영역 | 샘플 | 현재 RMSE | 평균(편향) |"
              + (" 최적화 후 RMSE |" if sig_after else ""), "|---|---|---|---|" + ("---|" if sig_after else "")]
    for name, s in sig_before.items():
        row = f"| {name} | {s['n']} | {f(s['rmse'])} | {f(s['mean'])} |"
        if sig_after:
            row += f" {f(sig_after[name]['rmse'])} |"
        lines.append(row)
    if sel.rejected:
        lines += ["", "## 제외된 후보", "", "| 파라미터 | 이유 |", "|---|---|"]
        for n, why in sel.rejected.items():
            lines.append(f"| `{n}` | {why} |")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- verification loop

def prune(sim: Simulator, params: Sequence[Param], measured: np.ndarray, fitted: FitResult,
          rel_tol: float = 0.05, weights: np.ndarray | None = None) -> tuple[list[str], dict[str, float]]:
    """Drop fitted parameters that do not matter once the others are fitted.

    Each parameter is reset to its original value (others kept at fitted values); if the RMSE rises by
    less than ``rel_tol`` x fitted RMSE, it is dropped. Returns (kept names, RMSE increase per name).
    """
    meas = np.asarray(measured, float)
    base_vals = {p.name: p.value for p in params}
    fitted_vals = {**base_vals, **fitted.values}
    kept, delta = [], {}
    for name in fitted.values:
        trial = dict(fitted_vals)
        trial[name] = base_vals[name]
        rm = _rmse(meas - np.asarray(sim(trial), float), weights)
        delta[name] = rm - fitted.rmse
        if delta[name] >= rel_tol * fitted.rmse:
            kept.append(name)
    return kept, delta


@dataclass
class PipelineResult:
    selection: Selection
    fit: FitResult
    pruned: list[str]
    delta_on_reset: dict[str, float]
    final: FitResult
    signature_before: dict
    signature_after: dict


def pipeline(sim: Simulator, params: Sequence[Param], measured: np.ndarray, masks: dict[str, np.ndarray],
             noise: float = 1e-3, k_max: int = 12, gamma_max: float = 15.0, min_gain: float = 0.01,
             prune_tol: float = 0.05, weights: np.ndarray | None = None) -> PipelineResult:
    """Select -> fit -> prune -> refit, i.e. predict, then verify against the real model."""
    meas = np.asarray(measured, float)
    base = evaluate(sim, params)
    r = meas - base
    J = jacobian(sim, params, base=base)
    sel = select(J, r, params, k_max=k_max, gamma_max=gamma_max, min_gain=min_gain, noise=noise,
                 masks=masks, weights=weights)
    first = fit(sim, params, meas, sel.subset, noise=noise, weights=weights)
    kept, delta = prune(sim, params, meas, first, prune_tol, weights)
    final = fit(sim, params, meas, kept, noise=noise, weights=weights) if set(kept) != set(sel.subset) else first
    after = meas - np.asarray(sim({**{p.name: p.value for p in params}, **final.values}), float)
    return PipelineResult(sel, first, [n for n in sel.subset if n not in kept], delta, final,
                          signature(r, masks), signature(after, masks))


def pipeline_markdown(res: PipelineResult, scale: float = 1000.0, unit_label: str = "mV") -> str:
    md = report_markdown(res.selection, res.signature_before, res.final, res.signature_after, scale=scale,
                         unit_label=unit_label)
    f = lambda x: f"{x * scale:.3f}"  # noqa: E731
    lines = ["", "## 검증 (최적화 후 각 파라미터를 원래 값으로 되돌렸을 때 RMSE 증가)", "",
             f"| 파라미터 | RMSE 증가 ({unit_label}) | 판정 | 최종값 |", "|---|---|---|---|"]
    for n, d in res.delta_on_reset.items():
        verdict = "제외 (기여 없음)" if n in res.pruned else "유지"
        val = res.final.values.get(n, res.fit.values.get(n))
        lines.append(f"| `{n}` | {f(d)} | {verdict} | {val:.6g} |")
    return md + "\n".join(lines) + "\n"
