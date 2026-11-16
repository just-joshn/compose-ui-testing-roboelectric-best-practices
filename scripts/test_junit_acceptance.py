#!/usr/bin/env python3
"""Regressions for JUnit acceptance and mutation evidence without Gradle."""

from contextlib import ExitStack
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import compare_setup
import verify_agent_outputs
import verify_fixture


class JunitAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        verify_fixture.copy_project(self.root)
        (self.root / ".work").mkdir()
        self.results = self.root / ".work/results"
        for module in (verify_fixture, verify_agent_outputs, compare_setup):
            self.stack.enter_context(patch.object(module, "ROOT", self.root))
            self.stack.enter_context(patch.object(module, "RESULTS", self.results))
        self.stack.enter_context(patch.dict("os.environ", {"JAVA_HOME": "/unused"}))
        self.stack.enter_context(patch.object(verify_fixture.subprocess, "run", self.produce))
        self.bad_label = "bad"
        self.terminals = ("<failure/>",)
        self.exit_code = 0
        self.default_methods = (compare_setup.METHOD,)

    def produce(self, command, *, cwd, stdout, **kwargs):
        label = Path(stdout.name).parent.name
        bad = label == self.bad_label
        methods = self.default_methods
        if "--tests" in command:
            methods = (command[-1].rsplit(".", 1)[-1],)
        suite = ET.Element("testsuite")
        for method in methods:
            ET.SubElement(suite, "testcase", name=method, classname="fixture.FixtureUiTest")
        if bad:
            for index, terminal in enumerate(self.terminals):
                if index == 0:
                    case = suite[0]
                else:
                    case = ET.SubElement(suite, "testcase", name=f"other{index}", classname="fixture.FixtureUiTest")
                case.append(ET.fromstring(terminal))
        xml_dir = Path(cwd) / "fixture/build/test-results/testDebugUnitTest"
        xml_dir.mkdir(parents=True)
        ET.ElementTree(suite).write(xml_dir / "TEST-fixture.xml")
        return subprocess.CompletedProcess(command, self.exit_code if bad else 0)

    def test_clean_report_passes(self):
        verify_fixture.require_pass(verify_fixture.run(self.root, "clean"), self.default_methods)

    def test_terminal_elements_reject_exit_zero(self):
        for terminal in ("<failure/>", "<error/>", '<error type="java.lang.IllegalStateException"/>'):
            with self.subTest(terminal=terminal):
                self.terminals = (terminal,)
                result = verify_fixture.run(self.root, "bad")
                with self.assertRaises(AssertionError):
                    verify_fixture.require_pass(result, self.default_methods)

    def test_saved_response_rejects_mixed_mutation_evidence(self):
        case = verify_agent_outputs.CASES[0]
        responses = self.root / "responses"
        responses.mkdir()
        (responses / case[1]).write_text("class SavedResponse\n")
        self.bad_label = "agent-writing-wrong-item"
        self.exit_code = 1
        assertion = '<failure type="java.lang.AssertionError"/>'
        for terminal in ("<error/>", '<error type="java.lang.IllegalStateException"/>', "<failure/>"):
            with self.subTest(terminal=terminal):
                self.terminals = (assertion, terminal)
                with self.assertRaises(AssertionError):
                    verify_agent_outputs.verify(case, responses)

    def test_setup_comparison_does_not_call_terminal_report_passed(self):
        self.bad_label = "resources-disabled"
        for terminal in ("<failure/>", '<failure type="java.lang.AssertionError"/>', "<error/>", '<error type="java.lang.IllegalStateException"/>'):
            with self.subTest(terminal=terminal):
                self.terminals = (terminal,)
                report = self.results / "setup-comparison.md"
                report.unlink(missing_ok=True)
                try:
                    compare_setup.main()
                except AssertionError:
                    pass
                if report.exists():
                    self.assertNotIn("passed with resources disabled", report.read_text())

    def test_fixture_mutation_rejects_error_alongside_named_assertion(self):
        self.default_methods = verify_fixture.TEST_METHODS + ("effectStartOrder", "effectStartOrder")
        self.bad_label = verify_fixture.MUTATIONS[0][0]
        self.exit_code = 1
        self.terminals = ('<failure type="java.lang.AssertionError"/>', "<error/>")
        self.stack.enter_context(patch.object(verify_fixture, "MUTATIONS", verify_fixture.MUTATIONS[:1]))
        self.stack.enter_context(patch("sys.argv", ["verify_fixture.py"]))
        with self.assertRaises(AssertionError):
            verify_fixture.main()


if __name__ == "__main__":
    unittest.main()
