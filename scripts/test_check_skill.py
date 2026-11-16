#!/usr/bin/env python3

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NAME = "compose-ui-testing-robolectric-best-practices"
SOURCES = """advanced/authentication-flows.md
advanced/authentication.md
advanced/clock-mocking.md
advanced/mobile-testing.md
advanced/multi-context.md
advanced/multi-user.md
advanced/network-advanced.md
advanced/third-party.md
architecture/pom-vs-fixtures.md
architecture/test-architecture.md
architecture/when-to-mock.md
browser-apis/browser-apis.md
browser-apis/iframes.md
browser-apis/service-workers.md
browser-apis/websockets.md
core/annotations.md
core/assertions-waiting.md
core/configuration.md
core/fixtures-hooks.md
core/global-setup.md
core/locators.md
core/page-object-model.md
core/projects-dependencies.md
core/test-data.md
core/test-suite-structure.md
core/test-tags.md
debugging/console-errors.md
debugging/debugging.md
debugging/error-testing.md
debugging/flaky-tests.md
frameworks/angular.md
frameworks/nextjs.md
frameworks/react.md
frameworks/vue.md
infrastructure-ci-cd/ci-cd.md
infrastructure-ci-cd/docker.md
infrastructure-ci-cd/github-actions.md
infrastructure-ci-cd/gitlab.md
infrastructure-ci-cd/other-providers.md
infrastructure-ci-cd/parallel-sharding.md
infrastructure-ci-cd/performance.md
infrastructure-ci-cd/reporting.md
infrastructure-ci-cd/test-coverage.md
testing-patterns/accessibility.md
testing-patterns/api-testing.md
testing-patterns/browser-extensions.md
testing-patterns/canvas-webgl.md
testing-patterns/component-testing.md
testing-patterns/drag-drop.md
testing-patterns/electron.md
testing-patterns/file-operations.md
testing-patterns/file-upload-download.md
testing-patterns/forms-validation.md
testing-patterns/graphql-testing.md
testing-patterns/i18n.md
testing-patterns/performance-testing.md
testing-patterns/security-testing.md
testing-patterns/visual-regression.md""".splitlines()
REFERENCES = (
    "behavior", "diagnostics", "evidence", "isolation", "semantics", "setup", "synchronization",
)
GUIDE = """# Example guide

## Table of contents

- [Example section](#example-section)
- [Repeated section](#example-section-1)

## Example section

```kotlin
val heading = "# Not a Markdown heading"
```

## Example section

[Related setup](../references/setup.md#setup)
[Source](https://developer.android.com/develop/ui/compose/testing)
"""


class SkillCheckTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.skill = Path(self.temporary.name) / NAME
        self.skill.mkdir()
        self.mapping = {
            "schema_version": 1,
            "upstream": "https://github.com/currents-dev/playwright-best-practices-skill",
            "commit": "0b75b5835a87de1fdd202ba965f3bc5a27738fdf",
            "topics": [],
        }
        routes = []
        for source in SOURCES:
            target = source.replace("browser-apis/", "android-apis/")
            self.put(target, GUIDE)
            routes.append(f"[Guide]({target})")
            self.mapping["topics"].append({
                "source": source, "source_sha256": "0" * 64, "target": target,
                "treatment": "adapt", "rationale": "Exercise the portable package contract.",
            })
        for name in REFERENCES:
            self.put(f"references/{name}.md", f"# {name.title()}\n")
            routes.append(f"[Reference](references/{name}.md)")
        self.put("SKILL.md", f"""---
name: {NAME}
description: Compose UI testing on the JVM with Robolectric.
license: MIT
---
# Compose testing

""" + "\n".join(routes) + "\n")
        for required in ("LICENSE", "ATTRIBUTION.md", "licenses/currents-MIT.txt"):
            self.put(required, "MIT\n")
        self.put("examples/Example.kt", "val example = true\n")
        self.save_map()

    def put(self, relative, text):
        destination = self.skill / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text)

    def save_map(self):
        self.put("adaptation-map.json", json.dumps(self.mapping))

    def replace(self, relative, before, after):
        path = self.skill / relative
        original = path.read_text()
        self.assertIn(before, original)
        path.write_text(original.replace(before, after))

    def run_check(self):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts/check_skill.py"), str(self.skill)],
            capture_output=True, text=True, timeout=30,
        )

    def assert_rejected(self, message):
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("AssertionError", result.stderr)
        self.assertIn(message, result.stderr)

    def test_complete_standalone_copy(self):
        self.mapping["topics"][0]["treatment"] = "reframe"
        self.mapping["topics"][1]["treatment"] = "boundary"
        self.mapping["topics"][1]["boundary"] = "Device fidelity requires a separate suite."
        self.save_map()
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS 58 routed adaptation guides, 7 references", result.stdout)
        self.assertIn("PASS standalone copied install", result.stdout)

    def test_rejects_packaging_defects(self):
        mutations = {
            "wrong name": ("name: " + NAME, "name: wrong-name", "Skill name"),
            "missing reference": ("references/setup.md", "references/missing.md", "Broken link"),
            "install escape": ("references/setup.md", "../outside.md", "Install-escaping"),
            "disabled activation": ("license: MIT", "license: MIT\ndisable-model-invocation: true", "activation"),
        }
        entry = (self.skill / "SKILL.md").read_text()
        for label, (before, after, message) in mutations.items():
            with self.subTest(label=label):
                self.put("SKILL.md", entry.replace(before, after))
                self.assert_rejected(message)

    def test_missing_map(self):
        (self.skill / "adaptation-map.json").unlink()
        self.assert_rejected("Missing adaptation-map.json")

    def test_deleted_mapping(self):
        self.mapping["topics"].pop()
        self.save_map()
        self.assert_rejected("all 58 source topics")

    def test_duplicate_or_unknown_source_with_58_rows(self):
        for source, message in ((SOURCES[1], "Duplicate adaptation source"),
                                ("core/unknown.md", "source inventory")):
            with self.subTest(source=source):
                self.mapping["topics"][0]["source"] = source
                self.save_map()
                self.assert_rejected(message)

    def test_map_metadata(self):
        for key, value, message in (
            ("commit", "f" * 40, "wrong upstream commit"),
            ("upstream", "https://example.com", "wrong upstream"),
            ("schema_version", 2, "schema_version"),
        ):
            with self.subTest(key=key):
                original = self.mapping[key]
                self.mapping[key] = value
                self.save_map()
                self.assert_rejected(message)
                self.mapping[key] = original

    def test_topic_metadata_and_targets(self):
        for key, value, message in (
            ("source_sha256", "not-a-hash", "Invalid source SHA-256"),
            ("treatment", "direct", "Invalid treatment"),
            ("rationale", "  ", "Missing adaptation rationale"),
            ("target", "core/missing.md", "Missing adaptation target"),
            ("target", "../outside.md", "Unsafe adaptation target"),
            ("target", str(self.skill / "advanced/authentication-flows.md"), "Unsafe adaptation target"),
            ("target", self.mapping["topics"][1]["target"], "Duplicate adaptation target"),
        ):
            with self.subTest(key=key, value=value):
                original = self.mapping["topics"][0][key]
                self.mapping["topics"][0][key] = value
                self.save_map()
                self.assert_rejected(message)
                self.mapping["topics"][0][key] = original

    def test_unrouted_category_guide(self):
        target = self.mapping["topics"][0]["target"]
        self.replace("SKILL.md", f"[Guide]({target})", "")
        self.assert_rejected("Every adaptation target must have an entry route")

    def test_unmanifested_nested_guide(self):
        self.put("core/nested/unmanifested.md", GUIDE)
        self.assert_rejected("Unmanifested")

    def test_reference_routes_are_recursive(self):
        self.put("references/nested/extra.md", "# Extra\n")
        self.assert_rejected("Every reference must have an entry route")
        with (self.skill / "SKILL.md").open("a") as entry:
            entry.write("\n[Extra](references/nested/extra.md)\n")
        self.assertEqual(self.run_check().returncode, 0)

    def test_missing_canonical_reference(self):
        (self.skill / "references/behavior.md").unlink()
        self.replace("SKILL.md", "[Reference](references/behavior.md)", "")
        self.assert_rejected("Missing canonical reference")

    def test_broken_same_page_and_cross_document_fragments(self):
        target = self.mapping["topics"][0]["target"]
        for before, after in (("#example-section)", "#absent)"),
                              ("setup.md#setup", "setup.md#absent")):
            with self.subTest(fragment=after):
                self.put(target, GUIDE.replace(before, after))
                self.assert_rejected("Broken fragment")

    def test_guide_structure(self):
        target = self.mapping["topics"][0]["target"]
        for before, after, message in (
            ("# Example guide", "## Example guide", "one H1"),
            ("# Example guide", "# Example guide\n# Another title", "one H1"),
            ("- [Example section](#example-section)\n- [Repeated section](#example-section-1)", "", "TOC links"),
            ('```kotlin\nval heading = "# Not a Markdown heading"\n```', "", "code fence"),
            ("[Related setup](../references/setup.md#setup)", "", "local related links"),
            ("[Source](https://developer.android.com/develop/ui/compose/testing)", "", "external source links"),
        ):
            with self.subTest(message=message):
                self.put(target, GUIDE.replace(before, after))
                self.assert_rejected(message)

    def test_missing_legal_file_and_sleep_example(self):
        license_file = self.skill / "LICENSE"
        license_file.unlink()
        self.assert_rejected("Missing LICENSE")
        self.put("LICENSE", "MIT\n")
        self.put("examples/Example.kt", "Thread.sleep(100)\n")
        self.assert_rejected("Sleep synchronization")


if __name__ == "__main__":
    unittest.main()
