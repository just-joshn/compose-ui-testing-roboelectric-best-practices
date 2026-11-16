#!/usr/bin/env python3

import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
NAME = "compose-ui-testing-robolectric-best-practices"
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
UPSTREAM = "https://github.com/currents-dev/playwright-best-practices-skill"
COMMIT = "0b75b5835a87de1fdd202ba965f3bc5a27738fdf"
SOURCE_INVENTORY_SHA256 = "c1568e2e2e039adaf6337fb677efe1a3090c9ece204cbd4a345119d06c4b8e0e"
CATEGORIES = {
    "core", "advanced", "android-apis", "architecture", "debugging", "frameworks",
    "infrastructure-ci-cd", "testing-patterns",
}
REFERENCES = {
    "behavior.md", "diagnostics.md", "evidence.md", "isolation.md",
    "semantics.md", "setup.md", "synchronization.md",
}


def prose(body):
    return re.sub(r"^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$", "", body,
                  flags=re.MULTILINE | re.DOTALL)


def headings(body):
    return re.findall(r"^ {0,3}(#{1,6})\s+(.+?)(?:\s+#+)?\s*$", prose(body), re.MULTILINE)


def fragments(body):
    anchors = set()
    counts = {}
    for _, title in headings(body):
        title = LINK.sub(lambda match: match[0].split("](", 1)[0][1:], title)
        slug = re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        anchors.add(f"{slug}-{count}" if count else slug)
    return anchors


def check_map(directory):
    manifest = directory / "adaptation-map.json"
    assert manifest.is_file(), "Missing adaptation-map.json"
    try:
        mapping = json.loads(manifest.read_text())
    except ValueError as error:
        raise AssertionError(f"Invalid adaptation-map.json: {error}") from error
    assert isinstance(mapping, dict), "Adaptation map must be an object"
    assert mapping.get("schema_version") == 1, "Adaptation map schema_version must be 1"
    assert mapping.get("upstream") == UPSTREAM, "Adaptation map has wrong upstream"
    assert mapping.get("commit") == COMMIT, "Adaptation map has wrong upstream commit"
    topics = mapping.get("topics")
    assert isinstance(topics, list) and len(topics) == 58, "Adaptation map must cover all 58 source topics"
    sources, targets = set(), set()
    for topic in topics:
        assert isinstance(topic, dict), "Each adaptation topic must be an object"
        source, target = topic.get("source"), topic.get("target")
        assert isinstance(source, str) and source, "Missing adaptation source path"
        assert source not in sources, f"Duplicate adaptation source: {source}"
        sources.add(source)
        assert isinstance(topic.get("source_sha256"), str) and re.fullmatch(
            r"[0-9a-f]{64}", topic["source_sha256"]), f"Invalid source SHA-256: {source}"
        assert topic.get("treatment") in ("adapt", "reframe", "boundary"), f"Invalid treatment: {source}"
        assert isinstance(topic.get("rationale"), str) and topic["rationale"].strip(), \
            f"Missing adaptation rationale: {source}"
        assert isinstance(target, str) and target, f"Missing adaptation target: {source}"
        path = PurePosixPath(target)
        resolved = (directory / target).resolve()
        assert (not path.is_absolute() and ".." not in path.parts
                and resolved.is_relative_to(directory.resolve())), f"Unsafe adaptation target: {target}"
        assert path.parts[0] in CATEGORIES and path.suffix == ".md", f"Invalid guide target: {target}"
        assert resolved.is_file(), f"Missing adaptation target: {target}"
        assert resolved not in targets, f"Duplicate adaptation target: {target}"
        targets.add(resolved)
    inventory_hash = hashlib.sha256("\n".join(sorted(sources)).encode("utf-8")).hexdigest()
    assert inventory_hash == SOURCE_INVENTORY_SHA256, "Adaptation source inventory differs from pinned 58 topics"
    guides = {path.resolve() for category in CATEGORIES for path in (directory / category).rglob("*.md")}
    assert guides == targets, (
        f"Category guides must equal adaptation targets. Unmanifested {sorted(guides - targets)}; "
        f"missing {sorted(targets - guides)}"
    )
    return targets


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
    targets = check_map(directory)
    routed = set()
    for document in directory.rglob("*.md"):
        body = document.read_text()
        assert "\u2014" not in body, f"Long dash in {document}"
        links = LINK.findall(prose(body))
        for target in links:
            if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                continue
            relative, separator, fragment = target.partition("#")
            resolved = (document.parent / unquote(relative)).resolve() if relative else document.resolve()
            assert resolved.is_relative_to(directory.resolve()), f"Install-escaping link in {document}: {target}"
            assert resolved.exists(), f"Broken link in {document}: {target}"
            if separator and fragment and resolved.suffix == ".md":
                assert unquote(fragment) in fragments(resolved.read_text()), \
                    f"Broken fragment in {document}: {target}"
            if document == entry and relative and resolved.suffix == ".md":
                routed.add(resolved)
        if document.resolve() in targets:
            assert sum(level == "#" for level, _ in headings(body)) == 1, f"Guide needs one H1: {document}"
            toc = re.search(r"^## (?:contents|table of contents)\s*\n(.*?)(?=^## |\Z)",
                            prose(body), re.MULTILINE | re.DOTALL | re.IGNORECASE)
            assert toc and any(link.startswith("#") and len(link) > 1
                               for link in LINK.findall(toc[1])), f"Guide needs TOC links: {document}"
            assert re.search(r"^\s*(`{3,}|~{3,})", body, re.MULTILINE), f"Guide needs a code fence: {document}"
            assert any(not re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", link)
                       and link.split("#", 1)[0].endswith(".md") for link in links), \
                f"Guide needs local related links: {document}"
            assert any(re.match(r"https?://", link) for link in links), f"Guide needs external source links: {document}"
    references = {path.resolve() for path in (directory / "references").rglob("*.md")}
    assert all((directory / "references" / name).is_file() for name in REFERENCES), "Missing canonical reference"
    assert references <= routed, "Every reference must have an entry route"
    assert targets <= routed, f"Every adaptation target must have an entry route: {sorted(targets - routed)}"
    examples = list((directory / "examples").glob("*.kt"))
    assert examples, "Missing canonical Kotlin examples"
    for example in examples:
        assert "Thread.sleep(" not in example.read_text(), f"Sleep synchronization in {example}"
    print(f"PASS {len(targets)} routed adaptation guides, {len(references)} references and {len(examples)} Kotlin example files")


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
