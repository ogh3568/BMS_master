"""Extract parameter candidates from C sources (the user's BMS / SPM code).

Finds
* numeric ``#define`` constants,
* global/static scalar and array declarations with initializers (const or not),
* struct initializers (designated ``.field = v`` or positional, field names resolved
  from struct definitions found in the same source set),
* "magic numbers" used directly inside function bodies (hidden parameters),
and records where each parameter is used (functions and lines). Each candidate gets a
heuristic physical group with a confidence and reason; the agent refines low-confidence
ones. Needs the optional packages ``tree-sitter`` and ``tree-sitter-c`` (both MIT).

CLI::

    python -m bmskit.codeintel.cparams <src_dir_or_files> [-o registry.json] [--md report.md]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

C_SUFFIXES = (".c", ".h")
NUM_RE = re.compile(r"^[+-]?(0[xX][0-9a-fA-F]+|(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?)[uUlLfF]*$")
TRIVIAL = {0.0, 1.0, -1.0, 2.0, 0.5, 100.0, 1000.0, 10.0}

# Heuristic name rules -> physical group. Order matters (first match wins).
GROUP_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(^|_)(ea|eact|act(iv)?)(_|$)|activation", re.I), "temperature"),
    (re.compile(r"diff|(^|_)d_?s(_|$)|(^|_)ds[np]?(_|$)", re.I), "diffusion"),
    (re.compile(r"radius|(^|_)r_?p(_|$)|(^|_)rp[np]?(_|$)|particle", re.I), "diffusion"),
    (re.compile(r"(^|_)k_?[np]?(_|$)|rate_?const|i0|exch", re.I), "kinetics"),
    (re.compile(r"ocp|ocv|(^|_)u_?[np](_|$)|potential", re.I), "ocp"),
    (re.compile(r"sto|theta|(^|_)x_?(0|100)|(^|_)y_?(0|100)|stoich", re.I), "stoichiometry"),
    (re.compile(r"cs_?max|c_?max|cmax", re.I), "capacity"),
    (re.compile(r"cap|(^|_)q_?(nom|max|full)?(_|$)|ah(_|$)", re.I), "capacity"),
    (re.compile(r"(^|_)r_?0|ohm|resist|(^|_)r_?(ser|int|ct|sei|film)", re.I), "resistance"),
    (re.compile(r"(^|_)ce(_|$)|elec(trolyte)?|kappa|t_?plus", re.I), "electrolyte"),
    (re.compile(r"(^|_)(eps|porosity|thick|(^|_)l_?[np](_|$)|area)", re.I), "geometry"),
    (re.compile(r"temp|therm|heat|(^|_)cp(_|$)|(^|_)h_?(conv|a)?(_|$)", re.I), "thermal"),
    (re.compile(r"hyst", re.I), "hysteresis"),
    (re.compile(r"kalman|ekf|ukf|(^|_)q_?(proc|noise)|(^|_)r_?(meas|noise)|gain|cov", re.I), "estimator"),
    (re.compile(r"thr|thresh|limit|lim(_|$)|max_|min_|_max|_min", re.I), "threshold"),
    (re.compile(r"time|period|dt(_|$)|delay|timeout|cnt|count", re.I), "timing"),
    (re.compile(r"tbl|table|lut|map(_|$)|axis|bp_", re.I), "table"),
]


@dataclass
class Usage:
    function: str
    file: str
    line: int


@dataclass
class ParamCandidate:
    id: str
    name_in_code: str
    kind: str  # define | const | variable | struct_field | array | magic_number
    ctype: str
    value: float | list | None
    shape: list[int]
    source: str  # file#Lline
    group: str = "unknown"
    group_confidence: float = 0.0
    group_reason: str = ""
    used_by: list[str] = field(default_factory=list)
    usages: list[Usage] = field(default_factory=list)
    comment: str = ""


def _parser():
    try:
        import tree_sitter_c as tsc
        from tree_sitter import Language, Parser
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("needs optional packages 'tree-sitter' and 'tree-sitter-c' (pip install .[code])") from e
    return Parser(Language(tsc.language()))


def _text(node, src: bytes) -> str:
    return src[node.start_byte:node.end_byte].decode("utf-8", "replace")


def _num(text: str) -> float | None:
    s = text.strip()
    while s.startswith("(") and s.endswith(")"):
        s = s[1:-1].strip()
    s = re.sub(r"^\((float|double|int|unsigned|long|short|u?int\d+_t|float32|float64|real\w*)\)\s*", "", s)
    if not NUM_RE.match(s):
        return None
    core = s.rstrip("uUlLfF") if not s.lower().startswith(("0x", "-0x", "+0x")) else s.rstrip("uUlL")
    try:
        return float(int(core, 16)) if "x" in core.lower() else float(core)
    except ValueError:
        return None


def _value(node, src: bytes):
    """Numeric scalar, nested list for initializer lists, or None."""
    if node is None:
        return None
    if node.type == "initializer_list":
        vals = [_value(c, src) for c in node.named_children if c.type != "comment"]
        return vals
    if node.type == "unary_expression" and _text(node, src).startswith("-"):
        v = _value(node.named_children[-1], src)
        return -v if isinstance(v, float) else None
    return _num(_text(node, src))


def _shape(v) -> list[int]:
    if isinstance(v, list):
        inner = _shape(v[0]) if v else []
        return [len(v), *inner]
    return []


def _comment_before(node, src: bytes) -> str:
    prev = node.prev_sibling
    if prev is not None and prev.type == "comment" and node.start_point[0] - prev.end_point[0] <= 1:
        return _text(prev, src).strip("/* \t\n")
    # trailing comment on the same line
    nxt = node.next_sibling
    if nxt is not None and nxt.type == "comment" and nxt.start_point[0] == node.end_point[0]:
        return _text(nxt, src).strip("/* \t\n")
    return ""


def classify(name: str, comment: str = "") -> tuple[str, float, str]:
    name = name.split(".")[-1]  # struct fields: classify by the field name
    for pat, group in GROUP_RULES:
        if pat.search(name):
            return group, 0.6, f"name matches /{pat.pattern}/"
    for pat, group in GROUP_RULES:
        if comment and pat.search(comment):
            return group, 0.4, f"comment matches /{pat.pattern}/"
    return "unknown", 0.0, "no rule matched"


def _declarator_name(decl, src: bytes) -> str | None:
    node = decl
    while node is not None and node.type not in ("identifier", "field_identifier"):
        node = node.child_by_field_name("declarator")
    return _text(node, src) if node is not None else None


FIELD_COMMENTS: dict[str, str] = {}
FIELD_TYPES: dict[tuple[str, str], str] = {}
STRUCT_FIELD_TYPES: dict[tuple[str, str], str] = {}


def _struct_fields(root, src: bytes) -> dict[str, list[str]]:
    """Map struct tag / typedef name -> ordered field names (field comments go to FIELD_COMMENTS)."""
    out: dict[str, list[str]] = {}

    def fields_of(spec) -> list[str]:
        body = spec.child_by_field_name("body")
        names: list[str] = []
        if body is None:
            return names
        for fd in body.named_children:
            if fd.type != "field_declaration":
                continue
            ftype = fd.child_by_field_name("type")
            for d in fd.children_by_field_name("declarator"):
                n = _declarator_name(d, src)
                if n:
                    names.append(n)
                    if ftype is not None:
                        FIELD_TYPES[(id(spec), n)] = _text(ftype, src)
                    note = _comment_before(fd, src)
                    if note:
                        FIELD_COMMENTS.setdefault(n, note)
        return names

    def walk(n):
        if n.type == "struct_specifier" and n.child_by_field_name("body") is not None:
            names = fields_of(n)
            keys = []
            tag = n.child_by_field_name("name")
            if tag is not None:
                keys.append(_text(tag, src))
            parent = n.parent
            if parent is not None and parent.type == "type_definition":
                keys += [_text(d, src) for d in parent.children_by_field_name("declarator")]
            for key in keys:
                out[key] = names
                for fn in names:
                    if (id(n), fn) in FIELD_TYPES:
                        STRUCT_FIELD_TYPES[(key, fn)] = FIELD_TYPES[(id(n), fn)]
        for c in n.children:
            walk(c)

    walk(root)
    return out


def scan(paths: Iterable[str | Path], include_magic: bool = True) -> list[ParamCandidate]:
    parser = _parser()
    FIELD_COMMENTS.clear()
    FIELD_TYPES.clear()
    STRUCT_FIELD_TYPES.clear()
    files: list[Path] = []
    for p in map(Path, paths):
        if p.is_dir():
            files += sorted(f for f in p.rglob("*") if f.suffix in C_SUFFIXES)
        elif p.suffix in C_SUFFIXES:
            files.append(p)
    trees = []
    structs: dict[str, list[str]] = {}
    for f in files:
        src = f.read_bytes()
        tree = parser.parse(src)
        trees.append((f, src, tree))
        structs.update(_struct_fields(tree.root_node, src))

    cands: dict[str, ParamCandidate] = {}
    magic: list[ParamCandidate] = []
    root_dir = Path(*Path(files[0]).parts[:1]) if files else Path(".")

    def add(c: ParamCandidate):
        c.group, c.group_confidence, c.group_reason = classify(c.name_in_code, c.comment)
        cands.setdefault(c.id, c)

    for f, src, tree in trees:
        rel = str(f)
        # 1) #define NAME number
        for node in _iter(tree.root_node, {"preproc_def"}):
            name = node.child_by_field_name("name")
            val = node.child_by_field_name("value")
            if name is None or val is None:
                continue
            v = _num(_text(val, src))
            if v is None:
                continue
            nm = _text(name, src)
            add(ParamCandidate(nm, nm, "define", "macro", v, [], f"{rel}#L{node.start_point[0] + 1}",
                               comment=_comment_before(node, src)))
        # 2) file-scope declarations with initializers
        for decl in tree.root_node.named_children:
            for d in _file_scope_decls(decl):
                _collect_decl(d, src, rel, structs, add)
        # 3) magic numbers in function bodies
        if include_magic:
            for fn in _iter(tree.root_node, {"function_definition"}):
                fname = _declarator_name(fn.child_by_field_name("declarator"), src) or "?"
                body = fn.child_by_field_name("body")
                for lit in _iter(body, {"number_literal"}):
                    v = _num(_text(lit, src))
                    if v is None or v in TRIVIAL or _in_index(lit):
                        continue
                    line = lit.start_point[0] + 1
                    magic.append(ParamCandidate(
                        f"{fname}@L{line}:{_text(lit, src)}", _text(lit, src), "magic_number", "literal", v, [],
                        f"{rel}#L{line}", "unknown", 0.0, "literal inside function body",
                        used_by=[fname], usages=[Usage(fname, rel, line)],
                        comment=_text(lit.parent, src)[:80]))

    # usages: identifiers and field accesses inside function bodies
    by_name: dict[str, list[ParamCandidate]] = {}
    for c in cands.values():
        by_name.setdefault(c.name_in_code.split(".")[-1], []).append(c)
    for f, src, tree in trees:
        for fn in _iter(tree.root_node, {"function_definition"}):
            fname = _declarator_name(fn.child_by_field_name("declarator"), src) or "?"
            for ident in _iter(fn.child_by_field_name("body"), {"identifier", "field_identifier"}):
                for c in by_name.get(_text(ident, src), []):
                    if c.kind == "struct_field" and ident.type != "field_identifier":
                        continue
                    if c.kind != "struct_field" and ident.type == "field_identifier":
                        continue
                    if fname not in c.used_by:
                        c.used_by.append(fname)
                    c.usages.append(Usage(fname, str(f), ident.start_point[0] + 1))
    return list(cands.values()) + magic


def _iter(node, types: set[str]):
    if node is None:
        return
    stack = [node]
    while stack:
        n = stack.pop()
        if n.type in types:
            yield n
        stack.extend(reversed(n.children))


def _in_index(lit) -> bool:
    p = lit.parent
    return p is not None and p.type in ("subscript_expression", "array_declarator", "case_statement")


def _file_scope_decls(node):
    if node.type == "declaration":
        yield node
    elif node.type in ("preproc_ifdef", "preproc_if", "preproc_else", "preproc_elif", "linkage_specification",
                       "declaration_list"):
        for c in node.named_children:
            yield from _file_scope_decls(c)


def _collect_decl(decl, src: bytes, rel: str, structs, add) -> None:
    quals = [_text(c, src) for c in decl.children if c.type in ("type_qualifier", "storage_class_specifier")]
    is_const = "const" in quals
    tnode = decl.child_by_field_name("type")
    ctype = _text(tnode, src) if tnode is not None else "?"
    for d in decl.children_by_field_name("declarator"):
        if d.type != "init_declarator":
            continue
        name = _declarator_name(d, src)
        init = d.child_by_field_name("value")
        if not name or init is None:
            continue
        line = decl.start_point[0] + 1
        comment = _comment_before(decl, src)
        struct_name = ctype.replace("struct", "").strip()
        if init.type == "initializer_list" and struct_name in structs:
            fields = structs[struct_name]
            pos = 0
            for item in init.named_children:
                if item.type == "comment":
                    continue
                if item.type == "initializer_pair":
                    fd = item.child_by_field_name("designator") or item.named_children[0]
                    fname = _text(fd, src).lstrip(".")
                    val = _value(item.child_by_field_name("value") or item.named_children[-1], src)
                else:
                    fname = fields[pos] if pos < len(fields) else f"_{pos}"
                    val = _value(item, src)
                    pos += 1
                if val is None:
                    continue
                ftype = STRUCT_FIELD_TYPES.get((struct_name, fname), "?")
                add(ParamCandidate(f"{name}.{fname}", f"{name}.{fname}", "struct_field",
                                   ("const " if is_const else "") + ftype, val,
                                   _shape(val), f"{rel}#L{item.start_point[0] + 1}",
                                   comment=_comment_before(item, src) or FIELD_COMMENTS.get(fname, "") or comment))
            continue
        val = _value(init, src)
        if val is None or (isinstance(val, list) and not _all_numeric(val)):
            continue
        kind = "array" if isinstance(val, list) else ("const" if is_const else "variable")
        add(ParamCandidate(name, name, kind, ("const " if is_const else "") + ctype, val, _shape(val),
                           f"{rel}#L{line}", comment=comment))


def _all_numeric(v) -> bool:
    if isinstance(v, list):
        return bool(v) and all(_all_numeric(x) for x in v)
    return isinstance(v, float)


# ---------------------------------------------------------------- output

def to_registry(cands: list[ParamCandidate]) -> list[dict]:
    out = []
    for c in cands:
        d = asdict(c)
        d["n_values"] = _count(c.value)
        out.append(d)
    return out


def _count(v) -> int:
    if isinstance(v, list):
        return sum(_count(x) for x in v)
    return 0 if v is None else 1


def summary_markdown(cands: list[ParamCandidate], top_magic: int = 30) -> str:
    named = [c for c in cands if c.kind != "magic_number"]
    magic = [c for c in cands if c.kind == "magic_number"]
    total_values = sum(_count(c.value) for c in named)
    lines = ["# C 파라미터 후보 리포트", "",
             f"- 이름 있는 후보: {len(named)}개 (스칼라·테이블 값 합계 {total_values}개)",
             f"- 함수 안 매직 넘버: {len(magic)}개", ""]
    groups: dict[str, list[ParamCandidate]] = {}
    for c in named:
        groups.setdefault(c.group, []).append(c)
    lines += ["## 물리 묶음별 개수", "", "| 묶음 | 후보 수 | 값 개수 |", "|---|---|---|"]
    for g, cs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"| {g} | {len(cs)} | {sum(_count(c.value) for c in cs)} |")
    lines += ["", "## 후보 목록", "", "| 이름 | 종류 | 묶음(신뢰도) | 값/형상 | 사용 함수 | 위치 |", "|---|---|---|---|---|---|"]
    for c in sorted(named, key=lambda c: (c.group, c.name_in_code)):
        val = c.value if not isinstance(c.value, list) else f"table {'x'.join(map(str, c.shape))}"
        used = ", ".join(c.used_by[:4]) + (" …" if len(c.used_by) > 4 else "")
        lines.append(f"| `{c.name_in_code}` | {c.kind} | {c.group} ({c.group_confidence}) | {val} | {used or '-'} | {c.source} |")
    if magic:
        lines += ["", f"## 매직 넘버 (상위 {top_magic})", "", "| 값 | 함수 | 위치 | 문맥 |", "|---|---|---|---|"]
        for c in magic[:top_magic]:
            ctx = c.comment.replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {c.name_in_code} | {c.used_by[0]} | {c.source} | `{ctx}` |")
    unused = [c.name_in_code for c in named if not c.used_by]
    if unused:
        lines += ["", f"## 함수에서 직접 참조되지 않은 후보 ({len(unused)})", "",
                  ", ".join(f"`{u}`" for u in unused[:60])]
    return "\n".join(lines) + "\n"


def _cli(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m bmskit.codeintel.cparams",
                                 description="extract parameter candidates from C sources")
    ap.add_argument("paths", nargs="+")
    ap.add_argument("-o", "--output", help="registry JSON path")
    ap.add_argument("--md", help="markdown summary path")
    ap.add_argument("--no-magic", action="store_true")
    args = ap.parse_args(list(argv) if argv is not None else None)
    cands = scan(args.paths, include_magic=not args.no_magic)
    if args.output:
        Path(args.output).write_text(json.dumps(to_registry(cands), ensure_ascii=False, indent=2), encoding="utf-8")
    md = summary_markdown(cands)
    if args.md:
        Path(args.md).write_text(md, encoding="utf-8")
    if not args.output and not args.md:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
