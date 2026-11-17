#!/usr/bin/env python3
"""Verify every claim in the skill against the cached text of official pages.

Each prose unit (paragraph, list item, table row) and each code block of a reference file must have
an entry in verification/<file>.json whose quotes appear word for word in an allowed official page.
SKILL.md units that only describe the skill itself may be marked "meta": true instead.
Every API-shaped identifier in code must appear in those pages or be declared in the same code block.
Run scripts/fetch_sources.py first.

Usage: verify_claims.py [skill-relative file ...]
"""
import json
import re
import sys

from official import LEDGER, SKILL, cache_file, canonical, is_allowed, normalize, page_text

EXEMPT_SECTIONS = {"Table of Contents", "Related References", "Sources"}
MIN_QUOTE = 15
IDENT = re.compile(r"(?<![\w@])@?[A-Za-z_][A-Za-z0-9_]*")
DECL = re.compile(r"\b(?:fun|val|var|class|object|interface|typealias)\s+(?:<[^>]*>\s*)?(?:[A-Za-z_][\w.]*\.)?([A-Za-z_]\w*)")
PARAM = re.compile(r"[({,]\s*([a-z_]\w*)\s*(?::|->)")


def units(rel, text):
    """Split a markdown file into claim units: (kind, text)."""
    out = []
    lines = text.splitlines()
    i, section = 0, ""
    is_skill = rel == "SKILL.md"
    if lines and lines[0] == "---":
        end = lines.index("---", 1)
        for line in lines[1:end]:
            if is_skill and re.match(r"\s*(description|compatibility):", line):
                out.append(("prose", line.split(":", 1)[1]))
        i = end + 1
    para = []

    def flush():
        if para:
            out.append(("prose", " ".join(para)))
            para.clear()

    while i < len(lines):
        line = lines[i]
        if line.startswith("#"):
            flush()
            if line.startswith("## "):
                section = line[3:].strip()
            i += 1
            continue
        exempt = section in EXEMPT_SECTIONS
        if line.lstrip().startswith(("```", "~~~")):
            flush()
            fence = line.lstrip()[:3]
            j = i + 1
            while j < len(lines) and not lines[j].lstrip().startswith(fence):
                j += 1
            if not exempt and not (is_skill and section == "Quick Decision Tree"):
                out.append(("code", "\n".join(lines[i + 1 : j])))
            i = j + 1
            continue
        if not line.strip():
            flush()
        elif exempt:
            pass
        elif line.lstrip().startswith("|"):
            flush()
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            is_sep = re.fullmatch(r"\s*\|[\s|:-]+\|\s*", line)
            is_header = re.fullmatch(r"\s*\|[\s|:-]+\|\s*", nxt)
            if not (is_sep or is_header or is_skill):
                out.append(("prose", line))
        elif re.match(r"\s*([-*]|\d+\.)\s", line):
            flush()
            item = [line]
            while i + 1 < len(lines) and lines[i + 1].startswith("  ") and lines[i + 1].strip() \
                    and not re.match(r"\s*([-*]|\d+\.)\s", lines[i + 1]):
                i += 1
                item.append(lines[i])
            out.append(("prose", " ".join(item)))
        else:
            para.append(line)
        i += 1
    flush()
    return [(k, t) for k, t in out if normalize(t)]


def api_tokens(code):
    code = re.sub(r"(?s)/\*.*?\*/", " ", code)
    code = re.sub(r"//[^\n]*", " ", code)
    declared = set(DECL.findall(code)) | set(PARAM.findall(code))
    declared |= set(re.findall(r"\b(\w+)\s*->", code))
    found = set()
    for tok in IDENT.findall(code):
        name = tok.lstrip("@")
        if name in declared or len(name) < 4:
            continue
        if tok.startswith("@") or re.search(r"[a-z][A-Z]", name) or re.match(r"[A-Z][a-z]", name):
            found.add(tok)
    return found


def check_file(rel, corpus):
    problems = []
    md = (SKILL / rel).read_text()
    led_path = LEDGER / (rel + ".json")
    ledger = json.loads(led_path.read_text())["units"] if led_path.exists() else []
    by_text = {normalize(u["text"]): u for u in ledger}
    seen = set()
    for kind, text in units(rel, md):
        key = normalize(text)
        seen.add(key)
        entry = by_text.get(key)
        short = key[:90]
        code = text if kind == "code" else " ".join(re.findall(r"`([^`]+)`", text))
        for tok in sorted(api_tokens(code)):
            if not re.search(r"(?<![\w@])" + re.escape(tok) + r"(?!\w)", corpus):
                problems.append(f"{rel}: identifier not in official pages: {tok} (in: {short[:50]})")
        if entry and entry.get("meta") and rel == "SKILL.md":
            continue
        if not entry or not entry.get("quotes"):
            problems.append(f"{rel}: unsupported {kind}: {short}")
            continue
        for q in entry["quotes"]:
            url, quote = canonical(q["url"]), normalize(q["quote"])
            if not is_allowed(url):
                problems.append(f"{rel}: quote from non-official URL {url}")
            elif page_text(url) is None:
                problems.append(f"{rel}: page not fetched {url}")
            elif len(quote) < MIN_QUOTE or quote not in normalize(page_text(url)):
                problems.append(f"{rel}: quote not on page {url}: {quote[:90]}")
    for key in by_text.keys() - seen:
        problems.append(f"{rel}: stale ledger entry: {key[:90]}")
    return problems


def main(argv):
    files = argv or sorted(str(p.relative_to(SKILL)) for p in SKILL.rglob("*.md"))
    corpus = "\n".join(p.read_text() for p in cache_file("x").parent.glob("*.txt"))
    problems = []
    for rel in files:
        problems += check_file(rel, corpus)
    for p in problems:
        print(p)
    print(f"{len(problems)} problem(s) in {len(files)} file(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
