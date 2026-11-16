# Compose UI testing with Robolectric

An installable agent skill for writing, reviewing, and debugging Kotlin Jetpack Compose UI tests that run locally on the JVM with Robolectric.

The skill routes each activity to focused guidance on setup, semantics, observable behavior, synchronization, isolation, and diagnosis. Its Kotlin examples compile and run in a small Android library fixture. It does not include screenshot tooling, CI-provider catalogs, or an application framework.

## Install the skill

From the repository checkout, install only the named skill into your current project:

```bash
npx skills add /path/to/compose-ui-testing-roboelectric-best-practices \
  --skill compose-ui-testing-robolectric-best-practices
```

After this change is merged, install from GitHub:

```bash
npx skills add https://github.com/just-joshn/compose-ui-testing-roboelectric-best-practices \
  --skill compose-ui-testing-robolectric-best-practices
```

Choose your agent when prompted. The [skills CLI](https://github.com/vercel-labs/skills) requires Node.js 22.20 or later in the documentation consulted for this release.

For manual installation, copy the entire `compose-ui-testing-robolectric-best-practices/` directory into your agent's skills directory. Preserve its references, examples, license, and attribution files. Pi discovers project skills under `.agents/skills/`.

The declared skill name is `compose-ui-testing-robolectric-best-practices`, as requested. The repository URL retains its existing `roboelectric` spelling.

## Use the skill

Ask your agent to write a Compose UI test, review an unreliable Robolectric test, or diagnose a missing semantics node. The description advertises those tasks to skill-capable agents. Automatic selection depends on the agent. In Pi, explicitly invoke:

```text
/skill:compose-ui-testing-robolectric-best-practices
```

Start at [SKILL.md](compose-ui-testing-robolectric-best-practices/SKILL.md). It links to references by activity. The [evidence reference](compose-ui-testing-robolectric-best-practices/references/evidence.md) states documentation boundaries and device limitations.

## Run the validation fixture

Prerequisites are JDK 17, Python 3.10 or later for the verification scripts, an Android SDK with the Android 37 platform and Build Tools 36.0.0, accepted SDK licenses, and network access for initial dependency downloads. The installed platform on the verification host is `platforms/android-37.0`.

Set `JAVA_HOME` to your JDK 17 installation and `ANDROID_HOME` to your Android SDK. On the tested macOS host:

```bash
export JAVA_HOME="$(/usr/libexec/java_home -v 17)"
export ANDROID_HOME="$HOME/Library/Android/sdk"
./gradlew :fixture:testDebugUnitTest --console=plain --rerun-tasks
```

The wrapper pins Gradle and its distribution checksum. The project compiles against API 37 and runs Robolectric at API 35. Compile SDK and runtime SDK are different choices. API 35 allows this run on JDK 17.

Run the rerunnable checks from the repository root:

```bash
python3 scripts/check_skill.py
python3 scripts/test_check_skill.py
python3 scripts/verify_fixture.py
python3 scripts/compare_setup.py
python3 scripts/verify_agent_outputs.py
```

`verify_fixture.py` builds a disposable project copy, runs the suite, and checks three UI mutations against named test assertions. It restores each mutation and reruns the baseline. `compare_setup.py` changes only Android-resource inclusion in another copy. Neither script edits the canonical example sources. `verify_agent_outputs.py` compiles the saved writing, review, and debugging responses against the UI and checks their assigned mutations. It can also accept new responses through `--responses path/to/responses`.

Run one method when diagnosing a failure:

```bash
./gradlew :fixture:testDebugUnitTest \
  --tests fixture.FixtureUiTest.mergedLabelAndUnmergedChild \
  --console=plain --rerun-tasks
```

The canonical sources are [FixtureUi.kt](compose-ui-testing-robolectric-best-practices/examples/FixtureUi.kt) and [FixtureUiTest.kt](compose-ui-testing-robolectric-best-practices/examples/FixtureUiTest.kt). The fixture compiles those files directly. It has no backend or device dependency.

Gradle's normal reports are under `fixture/build/reports/tests/testDebugUnitTest/`. Verification scripts retain logs, result summaries, and JUnit XML under `.work/fixture-results/`. That directory is ignored by Git.

## Evidence and limitations

Read [the evidence report](evidence/report.md) for the tested versions, actual results, reproduction commands, and remaining limits. [Reference inspection](evidence/reference-inspection.md) explains what was preserved from the Playwright skill. [The design decision](evidence/design.md) explains the fixture's small shape. [The agent-task contract](evidence/agent-task-contract.md) defines writing, review, and debugging acceptance.

Robolectric proves local JVM behavior for the tested configuration. It does not prove real-device rendering, TalkBack navigation, system UI, IME integration, hardware behavior, or performance. Device-dependent claims need device or emulator checks.

## License and attribution

Original content is [MIT licensed](LICENSE). The skill's packaging and routing design is informed by [Currents' Playwright skill](https://github.com/currents-dev/playwright-best-practices-skill). Its [attribution and MIT notice](compose-ui-testing-robolectric-best-practices/ATTRIBUTION.md) ship inside the installable directory. Browser examples are not copied.

The Gradle wrapper includes its own license. Gradle distribution [license](licenses/gradle-LICENSE.txt) and [notice](licenses/gradle-NOTICE.txt) are retained separately from the original-content MIT license.
