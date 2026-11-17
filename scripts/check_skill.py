#!/usr/bin/env python3
"""Validate the skill: frontmatter, links, anchors, required sections, and official-only sources."""
import re
import sys
from pathlib import Path

from official import is_allowed

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "compose-ui-testing-robolectric-best-practices"
REQUIRED = ["## Table of Contents", "## Related References", "## Sources"]
# The workflow's flow chart: SKILL.md has one "## " heading per node, in this order.
FLOW = [
    "Goal, constraints, and success check",
    "Select a playbook",
    "Investigate and establish evidence",
    "Requested outcome",
    "Deliver supported findings",
    "Design and implement",
    "Verify behavior and challenge findings",
    "Acceptance checks satisfied?",
    "Deliver the change and evidence",
    "Shipping authorized?",
    "Manage review and land verified work",
    "Hand back for review",
    "Capture useful lessons",
]
# Each playbook supplies the task-specific part of these workflow stages.
PLAYBOOK_REQUIRED = [
    "## When to use",
    "## Investigate and establish evidence",
    "## Deliver supported findings",
    "## Design and implement",
    "## Verify behavior and challenge findings",
    "## Sources",
]

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
URL = re.compile(r"https?://[^\s)>`\"']+")
FENCE = re.compile(r"^(```|~~~).*?^\1", re.M | re.S)


def slug(heading):
    s = heading.strip().lower()
    s = re.sub(r"[^\w\- ]", "", s)
    return s.replace(" ", "-")


def anchors(path):
    text = FENCE.sub("", path.read_text())
    return {slug(m.group(1)) for m in re.finditer(r"^#{1,6} (.+)$", text, re.M)}


def main():
    errors = []
    skill_md = SKILL / "SKILL.md"
    head = re.match(r"---\n(.*?)\n---\n", skill_md.read_text(), re.S)
    if not head:
        errors.append("SKILL.md: missing frontmatter")
    else:
        fm = head.group(1)
        name = re.search(r"^name: (.+)$", fm, re.M)
        if not name or name.group(1).strip() != SKILL.name:
            errors.append(f"SKILL.md: name must be {SKILL.name}")
        if not re.search(r"^description: .+", fm, re.M):
            errors.append("SKILL.md: missing description")

    headings = re.findall(r"^## (.+)$", FENCE.sub("", skill_md.read_text()), re.M)
    flow = [h for h in headings if h in FLOW]
    if flow != FLOW:
        errors.append(f"SKILL.md: flow chart headings missing or out of order: {[h for h in FLOW if h not in flow] or flow}")
    entry_points = skill_md.read_text() + "".join(p.read_text() for p in (SKILL / "playbooks").glob("*.md"))

    for md in sorted(SKILL.rglob("*.md")):
        rel = md.relative_to(SKILL)
        text = md.read_text()
        prose = FENCE.sub("", text)
        if md != skill_md:
            required = PLAYBOOK_REQUIRED if rel.parts[0] == "playbooks" else REQUIRED
            for section in required:
                if section not in text:
                    errors.append(f"{rel}: missing '{section}'")
            if not re.search(r"^## Sources\n(?:\s*\n)*- https?://", text, re.M):
                errors.append(f"{rel}: Sources section lists no URLs")
        for target in LINK.findall(prose):
            if target.startswith(("http://", "https://")):
                continue
            file_part, _, frag = target.partition("#")
            dest = (md.parent / file_part).resolve() if file_part else md
            if not dest.exists():
                errors.append(f"{rel}: broken link {target}")
            elif frag and dest.suffix == ".md" and frag not in anchors(dest):
                errors.append(f"{rel}: missing anchor {target}")
        for url in URL.findall(re.sub(r"`[^`\n]*`", "", prose)):
            if not is_allowed(url):
                errors.append(f"{rel}: URL is not an official source (sources.txt): {url}")
        if md != skill_md and rel.name not in entry_points:
            errors.append(f"{rel}: not linked from SKILL.md or any playbook")

    for e in errors:
        print(e)
    print(f"{len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
