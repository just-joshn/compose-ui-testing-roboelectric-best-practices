#!/usr/bin/env python3
"""Check successful skill-reference reads in named Pi session transcripts."""

import argparse
import json
import re
from pathlib import Path


EXPECTED = {
    "writing": {"SKILL.md", "references/behavior.md", "references/semantics.md"},
    "review": {"SKILL.md", "references/behavior.md", "references/synchronization.md", "references/isolation.md"},
    "debugging": {"SKILL.md", "references/diagnostics.md", "references/semantics.md"},
}
PATH = re.compile(r"compose-ui-testing-robolectric-best-practices/(SKILL\.md|references/[a-z-]+\.md)")


def reads(transcript):
    pending = {}
    successful = set()
    for line in transcript.read_text().splitlines():
        row = json.loads(line)
        message = row.get("message", {})
        for content in message.get("content", []):
            if content.get("type") == "toolCall" and content.get("name") in ("read", "codemode"):
                arguments = content.get("arguments", {})
                source = arguments.get("path", "") if content["name"] == "read" else arguments.get("code", "")
                pending[content["id"]] = set(PATH.findall(source))
        if message.get("role") == "toolResult" and not message.get("isError", False):
            successful.update(pending.get(message.get("toolCallId"), set()))
    return successful


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sessions", nargs="+", help="writing=path, review=path, or debugging=path")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    results = []
    for entry in args.sessions:
        label, path = entry.split("=", 1)
        assert label in EXPECTED, label
        observed = reads(Path(path))
        missing = EXPECTED[label] - observed
        results.append({"case": label, "references_read": sorted(observed), "missing": sorted(missing)})
    serialized = json.dumps(results, indent=2) + "\n"
    if args.output:
        args.output.write_text(serialized)
    print(serialized, end="")
    assert all(not result["missing"] for result in results), results


if __name__ == "__main__":
    main()
