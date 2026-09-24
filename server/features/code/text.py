"""Source text: lines in and out, where functions and classes are, how a line
range moves when the file around it changes, and diffs.

Everything here is pure (no database, no git), so it's tested on its own."""
from __future__ import annotations

import ast
import difflib
import re


class NotText(Exception):
    """Binary, or not UTF-8: shown in the map, never opened or edited here."""


# ── lines ─────────────────────────────────────────────────────────────────────

class Text:
    """A file as a list of lines, remembering its line ending, BOM and whether
    it ended with a newline, so writing it back changes nothing else."""

    def __init__(self, data: bytes):
        if b"\0" in data[:8000]:
            raise NotText()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise NotText() from None
        self.bom = text.startswith("﻿")
        if self.bom:
            text = text[1:]
        self.eol = "\r\n" if text.count("\r\n") * 2 > text.count("\n") else "\n"
        self.final_nl = text.endswith("\n")
        body = text[:-1] if self.final_nl else text
        self.lines = [ln[:-1] if ln.endswith("\r") else ln for ln in body.split("\n")] if body else []

    def to_bytes(self, lines: list[str] | None = None) -> bytes:
        lines = self.lines if lines is None else lines
        text = self.eol.join(lines) + (self.eol if (self.final_nl or not lines) and lines else "")
        return (("﻿" if self.bom else "") + text).encode("utf-8")


def split_lines(text: str) -> list[str]:
    """What someone typed into an editor, as lines (any line ending)."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text.endswith("\n"):
        text = text[:-1]
    return text.split("\n") if text else []


# ── ranges ────────────────────────────────────────────────────────────────────

def _ops(old: list[str], new: list[str]):
    return difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes()


def map_range(old: list[str], new: list[str], start: int, end: int) -> tuple[int, int] | None:
    """Where lines start..end (1-based, inclusive) of `old` are in `new`.

    The range follows its own code: lines added or removed above it shift it,
    lines added inside it make it longer, and if every line of it is gone the
    answer is None. Lines added right at its edges are not claimed."""
    s0, e0 = start - 1, end - 1
    ns = ne = None
    for tag, i1, i2, j1, j2 in _ops(old, new):
        if ns is None and i1 <= s0 < i2:
            ns = j1 + (s0 - i1) if tag == "equal" else j1
        if i1 <= e0 < i2:
            ne = j1 + (e0 - i1) if tag == "equal" else j2 - 1
            break
    if ns is None or ne is None or ne < ns:
        return None
    return ns + 1, ne + 1


def merge_ranges(ranges):
    """[(start, end, editable)] → sorted, non-overlapping; editable wins where they overlap."""
    points = sorted({p for s, e, _ in ranges for p in (s, e + 1)})
    out = []
    for a, b in zip(points, points[1:]):
        covering = [ed for s, e, ed in ranges if s <= a and b - 1 <= e]
        if not covering:
            continue
        ed = any(covering)
        if out and out[-1][1] == a - 1 and out[-1][2] == ed:
            out[-1] = (out[-1][0], b - 1, ed)
        else:
            out.append((a, b - 1, ed))
    return out


# ── functions and classes ─────────────────────────────────────────────────────

PY = (".py", ".pyw")
JS = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx")
PROSE = (".txt", ".md", ".prompt")
_CONSTANT = re.compile(r"^_?[A-Z][A-Z0-9_]*$")


def symbols(path: str, lines: list[str]) -> list[dict]:
    """Every named part of a file: [{name, kind, start, end}].

    kind: function | class (names qualified by their parents,
    "LocalBackend.build_prompt"), setting (a module-level CONSTANT: the
    numbers and lists an algorithm is tuned by), or section (a prompt or
    document section under its heading)."""
    low = path.lower()
    try:
        if low.endswith(PY):
            return _py_symbols("\n".join(lines))
        if low.endswith(JS):
            return _js_symbols(lines)
        if low.endswith(PROSE):
            return _sections(lines, markdown=low.endswith(".md"))
    except (SyntaxError, ValueError, RecursionError):
        return []
    return []


def _py_symbols(source: str) -> list[dict]:
    out = []
    tree = ast.parse(source)
    for node in tree.body:                     # settings: module-level CONSTANTS only
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        names = [t.id for t in targets if isinstance(t, ast.Name) and _CONSTANT.match(t.id)]
        if names:
            out.append({"name": names[0], "kind": "setting", "start": node.lineno, "end": node.end_lineno})

    def walk(node, prefix):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = f"{prefix}{child.name}"
                start = min([child.lineno] + [d.lineno for d in child.decorator_list])
                out.append({"name": name, "kind": "class" if isinstance(child, ast.ClassDef) else "function",
                            "start": start, "end": child.end_lineno})
                walk(child, name + ".")
    walk(tree, "")
    return sorted(out, key=lambda s: s["start"])


# A prompt heading: at least two capitalised words opening an unindented line
# ("CRITICAL IDENTITY FACTS (…):", "THE TEST. …", "YOU CAN SHOW THINGS VISUALLY:").
_HEADING = re.compile(r"^([A-Z][A-Z0-9'’&/]*(?: [A-Z][A-Z0-9'’&/]*)+)(?=$|[\s.:(,—–-])")


def _sections(lines: list[str], markdown: bool) -> list[dict]:
    heads = []
    for i, ln in enumerate(lines):
        if markdown:
            m = re.match(r"^#{1,6}\s+(.+?)\s*#*$", ln)
            name = m.group(1).strip() if m else None
        else:
            m = _HEADING.match(ln)
            name = m.group(1) if m and sum(c.isalpha() for c in m.group(1)) >= 6 else None
        if name:
            heads.append((i, name[:80]))
    out, seen = [], {}
    for k, (i, name) in enumerate(heads):
        end = heads[k + 1][0] - 1 if k + 1 < len(heads) else len(lines) - 1
        while end > i and not lines[end].strip():
            end -= 1
        seen[name] = seen.get(name, 0) + 1
        label = name if seen[name] == 1 else f"{name} ({seen[name]})"
        out.append({"name": label, "kind": "section", "start": i + 1, "end": end + 1})
    return out


_JS_DECL = [
    (re.compile(r"^\s*(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)\s*\("), "function"),
    (re.compile(r"^\s*(?:export\s+(?:default\s+)?)?class\s+([A-Za-z_$][\w$]*)"), "class"),
    (re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?"
                r"(?:function\b|\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>|\(\s*$)"), "function"),
    (re.compile(r"^(?:export\s+)?const\s+([A-Z][A-Z0-9_]*)\s*="), "setting"),
]
_JS_METHOD = re.compile(r"^\s*(?:static\s+)?(?:async\s+)?(?:get\s+|set\s+)?(?!if\b|for\b|while\b|switch\b|catch\b|return\b)"
                        r"([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{")


def _js_end(lines: list[str], start: int) -> int:
    """Last line (0-based) of the declaration starting at `start`: where its
    brackets balance again at a line end. Skips strings, template literals and
    comments; a line ending in `=>` or an operator carries on."""
    depth, i = 0, start
    in_block_comment = False
    stack: list[str] = []     # quote chars; '}' marks a ${ } inside a template
    while i < len(lines):
        line, j = lines[i], 0
        while j < len(line):
            c = line[j]
            if in_block_comment:
                if line.startswith("*/", j):
                    in_block_comment, j = False, j + 2
                    continue
                j += 1
                continue
            if stack and stack[-1] in "'\"`":
                q = stack[-1]
                if c == "\\":
                    j += 2
                    continue
                if q == "`" and line.startswith("${", j):
                    stack.append("}")
                    j += 2
                    continue
                if c == q:
                    stack.pop()
                j += 1
                continue
            if line.startswith("//", j):
                break
            if line.startswith("/*", j):
                in_block_comment, j = True, j + 2
                continue
            if c in "'\"`":
                stack.append(c)
            elif c in "([{":
                depth += 1
            elif c in ")]}":
                if c == "}" and stack and stack[-1] == "}":
                    stack.pop()
                else:
                    depth -= 1
            j += 1
        tail = line.split("//")[0].rstrip()
        if depth <= 0 and not stack and not in_block_comment and not tail.endswith(("=>", "=", "(", ",", "?", ":", "&&", "||", "+")):
            return i
        i += 1
    return len(lines) - 1


def _js_symbols(lines: list[str]) -> list[dict]:
    out, i = [], 0
    while i < len(lines):
        for rx, kind in _JS_DECL:
            m = rx.match(lines[i])
            if m:
                end = _js_end(lines, i)
                out.append({"name": m.group(1), "kind": kind, "start": i + 1, "end": end + 1})
                if kind == "class":
                    k = i + 1
                    while k < end:
                        mm = _JS_METHOD.match(lines[k])
                        if mm:
                            mend = _js_end(lines, k)
                            out.append({"name": f"{m.group(1)}.{mm.group(1)}", "kind": "function",
                                        "start": k + 1, "end": mend + 1})
                            k = mend
                        k += 1
                i = end
                break
        i += 1
    return out


def find_symbol(path: str, lines: list[str], name: str) -> tuple[int, int] | None:
    for s in symbols(path, lines):
        if s["name"] == name:
            return s["start"], s["end"]
    return None


# ── diffs ─────────────────────────────────────────────────────────────────────

def hunks(old: list[str], new: list[str], context: int = 3, see_old=None, see_new=None) -> list[list[dict]]:
    """Unified-diff hunks as rows {t: ' '|'-'|'+', a: old no, b: new no, text}.
    `see_old` / `see_new` (sets of line numbers, or None for everything) decide
    what the viewer may read; the rest collapses into {t: 'hidden', n}."""
    out = []
    for group in difflib.SequenceMatcher(None, old, new, autojunk=False).get_grouped_opcodes(context):
        rows = []
        for tag, i1, i2, j1, j2 in group:
            if tag == "equal":
                rows += [{"t": " ", "a": i1 + k + 1, "b": j1 + k + 1, "text": old[i1 + k]} for k in range(i2 - i1)]
            else:
                rows += [{"t": "-", "a": k + 1, "b": None, "text": old[k]} for k in range(i1, i2)]
                rows += [{"t": "+", "a": None, "b": k + 1, "text": new[k]} for k in range(j1, j2)]
        shown = []
        for r in rows:
            if r["t"] == "+":
                ok = see_new is None or r["b"] in see_new
            else:
                ok = see_old is None or r["a"] in see_old
            if ok:
                shown.append(r)
            elif shown and shown[-1]["t"] == "hidden":
                shown[-1]["n"] += 1
            else:
                shown.append({"t": "hidden", "n": 1})
        out.append(shown)
    return out


def stats(old: list[str], new: list[str]) -> tuple[int, int]:
    added = removed = 0
    for tag, i1, i2, j1, j2 in _ops(old, new):
        if tag != "equal":
            removed += i2 - i1
            added += j2 - j1
    return added, removed
