#!/usr/bin/env python3

import re
import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NAME = "compose-ui-testing-robolectric-best-practices"
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def check(directory):
    entry = directory / "SKILL.md"
    text = entry.read_text()
    parts = text.split("---", 2)
    assert len(parts) == 3 and parts[0] == "", "SKILL.md must begin with frontmatter"
    fields = dict(re.findall(r"^([a-z-]+):\s*(.+)$", parts[1], re.MULTILINE))
    assert fields.get("name") == directory.name == NAME, "Skill name must match its directory"
    assert len(NAME) <= 64 and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", NAME)
    assert 1 <= len(fields.get("description", "")) <= 1024, "Missing or oversized description"
    assert "disable-model-invocation" not in fields, "This skill must support task-based activation"
    assert fields.get("license") == "MIT"
    for required in ("LICENSE", "ATTRIBUTION.md", "licenses/currents-MIT.txt"):
        assert (directory / required).is_file(), f"Missing {required}"
    routed = set()
    for document in directory.rglob("*.md"):
        body = document.read_text()
        assert "\u2014" not in body, f"Long dash in {document}"
        for target in LINK.findall(body):
            if re.match(r"[a-z]+://", target) or target.startswith("#"):
                continue
            relative = target.split("#", 1)[0]
            resolved = (document.parent / relative).resolve()
            assert resolved.is_relative_to(directory.resolve()), f"Install-escaping link in {document}: {target}"
            assert resolved.exists(), f"Broken link in {document}: {target}"
            if document == entry and resolved.suffix == ".md":
                routed.add(resolved)
    references = {path.resolve() for path in (directory / "references").glob("*.md")}
    assert references and references <= routed, "Every reference must have an entry route"
    examples = list((directory / "examples").glob("*.kt"))
    assert examples, "Missing canonical Kotlin examples"
    for example in examples:
        assert "Thread.sleep(" not in example.read_text(), f"Sleep synchronization in {example}"
    print(f"PASS {len(references)} routed references and {len(examples)} Kotlin example files")


def main():
    source = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / NAME
    check(source)
    with tempfile.TemporaryDirectory(prefix="compose-skill-install-") as temporary:
        installed = Path(temporary) / NAME
        shutil.copytree(source, installed)
        check(installed)
    print("PASS standalone copied install")


if __name__ == "__main__":
    main()
