"""
Iterative compile-and-run repair loop for Python source files.

Used when the LLM is unavailable or returns code that still fails. Each round
compiles the code (fixing syntax errors) and then executes it, applying a
targeted fix for the first error found on the reported line. Repeats until the
code runs cleanly, no rule applies, or the round limit is reached.
"""
import difflib
import keyword
import os
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Dict, Any, List, Optional, Tuple

BLOCK_KEYWORDS = ("def", "class", "if", "elif", "else", "for", "while", "try",
                  "except", "finally", "with", "async def", "async for", "async with")


def _is_block_header(stripped: str) -> bool:
    for kw in BLOCK_KEYWORDS:
        if stripped == kw or stripped.startswith(kw + " ") or stripped.startswith(kw + "(") or stripped.startswith(kw + ":"):
            return True
    return False


def _code_part(line: str) -> str:
    """Strip a trailing comment (naive: ignores '#' inside strings)."""
    in_str = None
    for i, ch in enumerate(line):
        if in_str:
            if ch == in_str:
                in_str = None
        elif ch in ("'", '"'):
            in_str = ch
        elif ch == "#":
            return line[:i].rstrip()
    return line.rstrip()


def _fix_syntax(lines: List[str], err: SyntaxError) -> Optional[str]:
    """Apply one syntax fix to `lines` in place. Returns a note, or None if no rule applies."""
    msg = (err.msg or "").lower()
    idx = (err.lineno or 1) - 1
    if idx < 0 or idx >= len(lines):
        return None

    # Missing colon on a block header (check the reported line, then scan nearby headers)
    candidates = [idx] + [i for i in range(max(0, idx - 2), min(len(lines), idx + 2)) if i != idx]
    if "expected ':'" in msg or "invalid syntax" in msg or "expected an indented block" in msg:
        for i in candidates:
            code = _code_part(lines[i])
            stripped = code.strip()
            if stripped and _is_block_header(stripped) and not stripped.endswith(":"):
                comment = lines[i][len(code):]
                lines[i] = code + ":" + comment
                return f"Line {i + 1}: added missing ':' at end of `{stripped}`."

    if "expected an indented block" in msg:
        # Indent the line following the header
        header = idx - 1 if idx > 0 else idx
        base = len(lines[header]) - len(lines[header].lstrip())
        if idx < len(lines):
            lines[idx] = " " * (base + 4) + lines[idx].lstrip()
            return f"Line {idx + 1}: indented block body under line {header + 1}."

    if "unindent does not match" in msg or "unexpected indent" in msg:
        prev = idx - 1
        while prev >= 0 and not lines[prev].strip():
            prev -= 1
        target = len(lines[prev]) - len(lines[prev].lstrip()) if prev >= 0 else 0
        if prev >= 0 and _code_part(lines[prev]).rstrip().endswith(":") and "unexpected indent" not in msg:
            target += 4
        lines[idx] = " " * target + lines[idx].lstrip()
        return f"Line {idx + 1}: corrected indentation."

    m = re.search(r"'([(\[{])' was never closed", err.msg or "")
    if m:
        closer = {"(": ")", "[": "]", "{": "}"}[m.group(1)]
        code = _code_part(lines[idx])
        lines[idx] = code + closer + lines[idx][len(code):]
        return f"Line {idx + 1}: added missing '{closer}'."

    if "unterminated string literal" in msg:
        line = lines[idx]
        for q in ('"', "'"):
            if line.count(q) % 2 == 1:
                lines[idx] = line.rstrip() + q
                return f"Line {idx + 1}: closed unterminated string literal."

    return None


def _identifiers(code: str) -> List[str]:
    names = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", code))
    return [n for n in names if not keyword.iskeyword(n)]


def _enclosing_loop_vars(lines: List[str], idx: int) -> List[str]:
    """Loop variables of `for` headers enclosing line `idx`, innermost first."""
    result = []
    indent = len(lines[idx]) - len(lines[idx].lstrip())
    for i in range(idx - 1, -1, -1):
        stripped = lines[i].strip()
        if not stripped:
            continue
        ind = len(lines[i]) - len(lines[i].lstrip())
        if ind < indent:
            indent = ind
            m = re.match(r"(?:async\s+)?for\s+(.+?)\s+in\s", stripped)
            if m:
                result.extend(re.findall(r"[A-Za-z_]\w*", m.group(1)))
            if stripped.startswith(("def ", "async def ", "class ")):
                break
    return result


def _fix_range_off_by_one(lines: List[str], idx: int, index_var: str) -> Optional[str]:
    """If `index_var` comes from an enclosing `for ... in range(len(X) ...)` that overruns, fix the bounds."""
    indent = len(lines[idx]) - len(lines[idx].lstrip())
    for i in range(idx - 1, -1, -1):
        stripped = lines[i].strip()
        if not stripped:
            continue
        ind = len(lines[i]) - len(lines[i].lstrip())
        if ind >= indent:
            continue
        indent = ind
        if stripped.startswith(("def ", "async def ", "class ")):
            return None
        m = re.match(rf"for\s+{re.escape(index_var)}\s+in\s+range\((.*)\)\s*:", stripped)
        if not m:
            continue
        args, new_args = m.group(1), None
        L = r"len\(([^()]+)\)"
        if re.fullmatch(rf"\s*{L}\s*,\s*0\s*,\s*-1\s*", args):          # range(len(x), 0, -1)
            new_args = re.sub(rf"{L}\s*,\s*0", r"len(\1) - 1, -1", args, count=1)
        elif re.fullmatch(rf"\s*{L}\s*,\s*-1\s*,\s*-1\s*", args):       # range(len(x), -1, -1)
            new_args = re.sub(L, r"len(\1) - 1", args, count=1)
        elif re.fullmatch(rf"\s*(0\s*,\s*)?{L}\s*\+\s*1\s*", args):     # range(len(x) + 1)
            new_args = re.sub(rf"({L})\s*\+\s*1", r"\1", args, count=1)
        if new_args is None:
            return None
        lines[i] = lines[i].replace(f"range({args})", f"range({new_args.strip()})", 1)
        return f"Line {i + 1}: fixed off-by-one loop bounds `range({args.strip()})` -> `range({new_args.strip()})`."
    return None


def _split_top_level_plus(expr: str) -> List[str]:
    parts, depth, quote, cur = [], 0, None, ""
    for ch in expr:
        if quote:
            cur += ch
            if ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "+" and depth == 0:
            parts.append(cur.strip())
            cur = ""
            continue
        cur += ch
    parts.append(cur.strip())
    return parts


def _concat_to_fstring(lines: List[str], idx: int) -> Optional[str]:
    """Rewrite `a + " text " + b` (str + non-str concatenation) on this line as an f-string."""
    line = lines[idx]
    code = _code_part(line)
    m = re.match(r"^(\s*)(return\s+|[\w.\[\]'\"]+\s*=\s*|print\()(.*?)(\)?)$", code)
    if not m:
        return None
    indent, head, expr, tail = m.groups()
    if head != "print(":
        expr, tail = expr + tail, ""
    parts = _split_top_level_plus(expr)
    if len(parts) < 2:
        return None
    out = ""
    for p in parts:
        lit = re.fullmatch(r"(['\"])(.*)\1", p)
        if lit:
            out += lit.group(2).replace("{", "{{").replace("}", "}}")
        elif p and '"' not in p and "'" not in p:
            out += "{" + p + "}"
        else:
            return None
    lines[idx] = f'{indent}{head}f"{out}"{tail}' + line[len(code):]
    return "converted string concatenation with non-string values to an f-string."


def _lint_logic_bugs(lines: List[str]) -> List[str]:
    """Fix common silent logic bugs that don't raise errors."""
    notes = []
    for i, line in enumerate(lines):
        # `x =+ 1` is almost always a typo for `x += 1`
        m = re.match(r"^(\s*)([A-Za-z_][\w.]*)\s*=\+\s*(.+)$", line)
        if m:
            lines[i] = f"{m.group(1)}{m.group(2)} += {m.group(3)}"
            notes.append(f"Line {i + 1}: `{m.group(2)} =+ ...` -> `{m.group(2)} += ...` (typo reset the value instead of adding).")
            continue
        # Accumulator overwritten in a loop: `total = 0` / `for p in xs:` / `total = p` / `return total`
        m = re.match(r"^(\s*)([A-Za-z_]\w*)\s*=\s*([A-Za-z_]\w*)\s*$", _code_part(line))
        if m:
            acc, var = m.group(2), m.group(3)
            # Only when the assignment sits directly in the loop body (not under an `if`)
            parent = next((lines[j].strip() for j in range(i - 1, -1, -1) if lines[j].strip()
                           and len(lines[j]) - len(lines[j].lstrip()) < len(line) - len(line.lstrip())), "")
            if re.match(rf"for\s+{re.escape(var)}\s+in\s", parent):
                func_start = next((j for j in range(i, -1, -1) if lines[j].strip().startswith("def ")), 0)
                func_end = next((j for j in range(i + 1, len(lines))
                                 if lines[j].strip() and not lines[j].startswith((" ", "\t"))), len(lines))
                body_before = "\n".join(lines[func_start:i])
                body_after = "\n".join(lines[i + 1:func_end])
                if re.search(rf"^\s*{acc}\s*=\s*0\s*$", body_before, re.M) and re.search(rf"^\s*return\s+{acc}\s*$", body_after, re.M):
                    lines[i] = f"{m.group(1)}{acc} += {var}"
                    notes.append(f"Line {i + 1}: `{acc} = {var}` -> `{acc} += {var}` (loop overwrote the running total).")
    return notes


def _parse_runtime_error(output: str, filename: str) -> Optional[Tuple[str, str, int]]:
    """Return (error_type, message, line_number) for the last frame in `filename`."""
    frames = re.findall(r'File "([^"]+)", line (\d+)', output)
    line_no = None
    for path, ln in frames:
        if os.path.basename(path) == filename:
            line_no = int(ln)
    exc = None
    for line in reversed(output.strip().splitlines()):
        m = re.match(r"^([A-Za-z_][\w.]*(?:Error|Exception)):?\s*(.*)$", line.strip())
        if m:
            exc = (m.group(1).split(".")[-1], m.group(2))
            break
    if not exc or line_no is None:
        return None
    return exc[0], exc[1], line_no


def _fix_runtime(lines: List[str], err_type: str, message: str, line_no: int) -> Optional[str]:
    idx = line_no - 1
    if idx < 0 or idx >= len(lines):
        return None
    line = lines[idx]
    code = "\n".join(lines)

    if err_type in ("NameError", "UnboundLocalError"):
        m = re.search(r"name '([^']+)' is not defined", message) or re.search(r"'([^']+)'", message)
        if not m:
            return None
        bad = m.group(1)
        pool = [n for n in _identifiers(code) if n != bad]
        match = difflib.get_close_matches(bad, pool, n=1, cutoff=0.75)
        # Prefer a loop variable of an enclosing `for` that resembles the bad name
        # (e.g. `number` inside `for num in numbers:` means `num`, not `numbers`).
        for loop_var in _enclosing_loop_vars(lines, idx):
            if loop_var != bad and (bad.startswith(loop_var) or loop_var.startswith(bad)
                                    or difflib.SequenceMatcher(None, bad, loop_var).ratio() >= 0.6):
                match = [loop_var]
                break
        if match:
            lines[idx] = re.sub(rf"\b{re.escape(bad)}\b", match[0], line)
            return f"Line {line_no}: fixed undefined name `{bad}` -> `{match[0]}` (likely typo)."
        indent = line[:len(line) - len(line.lstrip())]
        # Used in arithmetic -> neutral numeric default; otherwise None
        numeric = re.search(rf"[-+*/%]\s*\b{re.escape(bad)}\b|\b{re.escape(bad)}\b\s*[-+*/%]", line)
        default = "0" if numeric else "None"
        lines.insert(idx, f"{indent}{bad} = {default}  # auto-defined to resolve NameError")
        return f"Line {line_no}: defined missing variable `{bad}` = {default}."

    if err_type == "TypeError" and "can only concatenate str" in message:
        note = _concat_to_fstring(lines, idx)
        if note:
            return f"Line {line_no}: {note}"

    if err_type == "TypeError":
        m = re.search(r"unsupported operand type\(s\) for ([^:]+): '(\w+)' and '(\w+)'", message)
        if m:
            op, left_t, right_t = m.group(1).strip(), m.group(2), m.group(3)
            numeric = ("int", "float")
            side = "left" if left_t == "str" and right_t in numeric else \
                   "right" if right_t == "str" and left_t in numeric else None
            if side:
                operand = r"([A-Za-z_][\w.]*)"
                pat = rf"{operand}(\s*{re.escape(op)}\s*)" if side == "left" else rf"(\s*{re.escape(op)}\s*){operand}"
                mm = re.search(pat, line)
                if mm:
                    if side == "left":
                        name, rest = mm.group(1), mm.group(2)
                        lines[idx] = line[:mm.start()] + f"float({name}){rest}" + line[mm.end():]
                    else:
                        rest, name = mm.group(1), mm.group(2)
                        lines[idx] = line[:mm.start()] + f"{rest}float({name})" + line[mm.end():]
                    return f"Line {line_no}: converted `{name}` to a number before `{op}`."
        return None

    if err_type == "KeyError":
        m = re.search(r"^['\"](.+)['\"]$", message.strip())
        key = m.group(1) if m else message.strip()
        pattern = re.compile(r"(\b[\w.]+)\[\s*(['\"])" + re.escape(key) + r"\2\s*\]")
        if pattern.search(line):
            lines[idx] = pattern.sub(lambda mm: f'{mm.group(1)}.get({mm.group(2)}{key}{mm.group(2)}, "Unknown")', line)
            return f"Line {line_no}: replaced direct key lookup ['{key}'] with .get('{key}', \"Unknown\")."
        return None

    if err_type == "ZeroDivisionError":
        m = re.search(r"(?:/|//|%)\s*([A-Za-z_][\w.]*(?:\([^()]*\))?|\([^()]*\))", line)
        if not m:
            return None
        denom = m.group(1)
        stripped = line.strip()
        indent = line[:len(line) - len(line.lstrip())]
        assign = re.match(r"^(return\s+|[\w.\[\]'\" ,]+\s*=\s*)(.+)$", stripped)
        if assign and "==" not in assign.group(1):
            lhs, expr = assign.group(1), _code_part(assign.group(2))
            lines[idx] = f"{indent}{lhs}({expr}) if {denom} != 0 else 0"
            return f"Line {line_no}: guarded division by `{denom}` against zero."
        lines.insert(idx, f"{indent}if {denom} == 0:")
        lines.insert(idx + 1, f"{indent}    return 0")
        return f"Line {line_no}: added zero-denominator guard before division."

    if err_type == "AttributeError":
        m = re.search(r"'(\w+)' object has no attribute '(\w+)'", message)
        if m:
            obj_type, attr = m.groups()
            str_methods = {n for n in dir(str) if not n.startswith("_")}
            list_aliases = {"push": "append", "add": "append", "remove_at": "pop", "length": None}
            if obj_type in ("int", "float") and attr in str_methods:
                mm = re.search(rf"([A-Za-z_][\w.]*)\.{attr}\b", line)
                if mm:
                    lines[idx] = line.replace(mm.group(0), f"str({mm.group(1)}).{attr}", 1)
                    return f"Line {line_no}: `{mm.group(1)}` is a number; converted to str before calling .{attr}()."
            if obj_type == "list" and list_aliases.get(attr):
                lines[idx] = re.sub(rf"\.{attr}\(", f".{list_aliases[attr]}(", line)
                return f"Line {line_no}: lists have no .{attr}(); used .{list_aliases[attr]}()."
        return None

    if err_type == "ModuleNotFoundError":
        m = re.search(r"No module named '([\w.]+)'", message)
        if m:
            mod = m.group(1)
            other_code = "\n".join(l for i, l in enumerate(lines) if i != idx)
            if re.fullmatch(rf"\s*(import\s+{re.escape(mod)}(\s+as\s+\w+)?|from\s+{re.escape(mod)}\s+import\s+.+)\s*", line) \
                    and not re.search(rf"\b{re.escape(mod.split('.')[0])}\b", other_code):
                lines.pop(idx)
                return f"Line {line_no}: removed import of missing, unused module `{mod}`."
        return None

    if err_type == "FileNotFoundError":
        m = re.match(r"^(\s*)with\s+open\((.+?)(,.*)?\)\s+as\s+\w+\s*:", line)
        if m:
            indent, path = m.group(1), m.group(2).strip()
            end = idx + 1
            while end < len(lines) and (not lines[end].strip() or len(lines[end]) - len(lines[end].lstrip()) > len(indent)):
                end += 1
            block = ["    " + l if l.strip() else l for l in lines[idx:end]]
            lines[idx:end] = [f"{indent}if os.path.exists({path}):"] + block + \
                             [f"{indent}else:", f"{indent}    print(f\"File not found: {{{path}}}\")"]
            if not re.search(r"^\s*import\s+os\b", "\n".join(lines), re.M):
                lines.insert(0, "import os")
            return f"Line {line_no}: check that {path} exists before opening it."
        return None

    if err_type == "IndexError":
        # Off-by-one loop bounds: fix the enclosing `for i in range(len(x)...)` header
        for m in re.finditer(r"\b[\w.]+\[\s*([A-Za-z_]\w*)\s*\]", line):
            note = _fix_range_off_by_one(lines, idx, m.group(1))
            if note:
                return note
        m = re.search(r"(\b[\w.]+)\[\s*(-?\d+|[\w.]+)\s*\]", line)
        if m:
            seq, ix = m.group(1), m.group(2)
            lines[idx] = line.replace(m.group(0), f"({seq}[{ix}] if -len({seq}) <= {ix} < len({seq}) else None)", 1)
            return f"Line {line_no}: added bounds check for `{seq}[{ix}]`."
        return None

    return None


def run_python_file(code: str, filename: str, project_path: Optional[str]) -> subprocess.CompletedProcess:
    """Run code as ilename inside a temporary copy of the project."""
    work = tempfile.mkdtemp(prefix="repair_")
    try:
        if project_path and os.path.isdir(project_path):
            shutil.copytree(project_path, work, dirs_exist_ok=True)
        target = os.path.join(work, filename)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(code)
        return subprocess.run([sys.executable, target], cwd=work, capture_output=True,
                              text=True, timeout=10, stdin=subprocess.DEVNULL)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def repair_python_code(source_code: str, filename: str = "main.py",
                       project_path: Optional[str] = None, max_rounds: int = 25) -> Dict[str, Any]:
    """
    Repeatedly compile + run `source_code`, fixing one error per round.
    Returns {"fixed_code", "notes", "compiles", "runs_clean", "last_error"}.
    """
    lines = source_code.splitlines()
    notes: List[str] = []
    last_error = ""
    compiles = runs_clean = False

    for _ in range(max_rounds):
        code = "\n".join(lines) + "\n"
        try:
            compile(code, filename, "exec")
            compiles = True
        except SyntaxError as e:
            compiles = False
            last_error = f"{type(e).__name__}: {e.msg} (line {e.lineno})"
            note = _fix_syntax(lines, e)
            if not note:
                break
            notes.append(note)
            continue

        try:
            proc = run_python_file(code, os.path.basename(filename), project_path)
        except subprocess.TimeoutExpired:
            last_error = "Execution timed out"
            break
        if proc.returncode == 0:
            runs_clean = True
            last_error = ""
            break

        output = proc.stdout + "\n" + proc.stderr
        parsed = _parse_runtime_error(output, os.path.basename(filename))
        last_error = output.strip().splitlines()[-1] if output.strip() else "Execution failed"
        if not parsed:
            break
        note = _fix_runtime(lines, *parsed)
        if not note or note in notes:
            break
        notes.append(note)

    # Once the code runs, fix silent logic bugs too, keeping them only if it still runs cleanly
    if runs_clean:
        linted = list(lines)
        lint_notes = _lint_logic_bugs(linted)
        if lint_notes:
            try:
                if run_python_file("\n".join(linted) + "\n", os.path.basename(filename), project_path).returncode == 0:
                    lines = linted
                    notes.extend(lint_notes)
            except subprocess.TimeoutExpired:
                pass

    return {
        "fixed_code": "\n".join(lines) + "\n",
        "notes": notes,
        "compiles": compiles,
        "runs_clean": runs_clean,
        "last_error": last_error,
    }
