---
name: verify-compose-robolectric
description: Verify the Compose UI testing with Robolectric agent skill and its JVM Compose fixture. Use after changing guidance, packaging, Kotlin examples, or saved writing/review/debugging responses; drive existing Python/Gradle harnesses and preserve mutation evidence. Not device or screenshot verification.
---

# Verify Compose UI testing with Robolectric

Run commands from the repository root. First read [the feature map](features/README.md) and the matching feature file. The shipped product is `compose-ui-testing-robolectric-best-practices/`, an installable agent skill. Its executable surface is an Android **library test fixture**, not an APK, server, CLI prompt, or mobile app. Do not invent an Activity, install it on a device, or claim JVM evidence proves device behavior.

## Launch

Prerequisites: Python 3.10+, JDK 17, an Android SDK with compile platform API 37 (on the verified host: `platforms/android-37.0`), Build Tools 36.0.0, accepted SDK licenses, and network access for uncached dependencies. Robolectric runs API 35. There are no ports, credentials, database migrations, or external service seeds. Each test mounts its own UI and creates fresh state/fakes.

On macOS:

```bash
export JAVA_HOME="$(/usr/libexec/java_home -v 17)"
export ANDROID_HOME="$HOME/Library/Android/sdk"
mkdir -p .work
RUN="$(mktemp -d "$PWD/.work/verify-compose-robolectric.XXXXXX")"
printf '%s\n' "$RUN"
```

On other hosts explicitly export `JAVA_HOME` pointing to JDK 17 and `ANDROID_HOME` pointing to the installed SDK, then run the same `mkdir`/`RUN` commands. Tool calls do not share shell variables: repeat the JDK/SDK exports and restore the printed absolute `RUN` path in subsequent calls. For sandboxed tmux commands also explicitly export `GRADLE_USER_HOME="$PWD/.work/gradle-home"` to reuse the checkout's writable cache rather than a per-job cache.

Build once in a disposable project copy:

```bash
.pi/skills/verify-compose-robolectric/verify.py launch "$RUN"
```

Run launch and Gradle/Python drives using `tmux_run` when they may outlast a tool call. Set its command to the line above with the **printed absolute run path** in place of `$RUN`; use the repository as `cwd`. Record the returned job ID and wait for exit. `READY <run path>` plus exit 0 means the fixture test classes compiled. `BUILD SUCCESSFUL` with `NO-SOURCE` alone is insufficient. Launch is preparation, not a passing behavior test. The helper's read-only doctor checks actual compiled classes. Test methods supply the usable UI when the drive starts.

The helper copies the current working tree's build files, full installable skill, validation scripts, and saved agent responses, including uncommitted changes. It archives sources and SHA-256 hashes before building. It uses `--no-daemon`; Gradle's single-use daemon exits with the command. There is no persistent server to keep alive.

The helper defaults Gradle's writable cache to `.work/gradle-home` (an explicitly set `GRADLE_USER_HOME` wins), Robolectric's Maven cache to `.work/m2`, and JVM temporary storage to the disposable workspace. These are verification scaffolding, not product setup changes. Dependencies may download, and SDK analytics may warn about a read-only home. A warning alone is not a failed test; inspect actual exit codes and JUnit results.

Use one driver at a time. Each run has separate project state, but caches and the Android SDK are shared. Concurrent driving is not supported by this recipe. Never drive a developer's existing Gradle workspace or overwrite `.work/fixture-results/` in the original checkout. An empty workspace is exercised; a cold SDK installation and empty dependency caches are not automatically proven.

## Doctor

Run this read-only check after launch, before each drive, and first whenever results look suspicious:

```bash
.pi/skills/verify-compose-robolectric/verify.py doctor "$RUN"
```

Require `HEALTHY`, the expected checkout/workspace, and exit 0. It checks run ownership, successful launch, compiled `FixtureUiTest.class`, and source hashes against both the snapshot and current checkout. Build/version identity is retained in `evidence/launch/command-1.log` and the archived Gradle files. No server, auth, or port check applies. If the checkout changed, launch a new run; do not bypass a failed doctor. Doctor does not rerun tests or promise dependencies are cached.

## Drive

Use the existing harness rather than calling composable callbacks or changing UI state to manufacture the result:

```bash
.pi/skills/verify-compose-robolectric/verify.py drive "$RUN" writing
```

`writing` compiles the saved writing response, clicks the scoped Draft `Open`, verifies `Draft opened` and absence of `Archive opened`, then proves a wrong-target mutation fails and restoration passes. It is a replay of saved agent output, not a fresh agent activation. Follow the writing feature for fresh-response/routing acceptance.

Other literal journey arguments:

| Journey | Existing harness / result |
| --- | --- |
| `package` | `check_skill.py` and `test_check_skill.py`: portable copied package and rejection of malformed packages |
| `review` / `debugging` | `verify_agent_outputs.py --case review` / `--case debugging`: baseline, assigned mutations, restoration |
| `suite` | `verify_fixture.py --baseline-only`: all 8 tests, no skips |
| `mutations` | `verify_fixture.py`: baseline, 3 named assertion failures, restorations, isolated tests, final baseline |
| `setup` | `compare_setup.py`: Android resource inclusion comparison; inspect its recorded outcomes, not just its PASS banner |
| Any of the 6 `FixtureUiTest` method names in the map | Gradle `:fixture:testDebugUnitTest --tests fixture.FixtureUiTest.<method> --console=plain --no-daemon --rerun-tasks`; require exactly that one passing JUnit test |

Each journey gets a new evidence directory. Do not rerun the same journey in the same run: start a new run instead of reusing stale artifacts. Every command must exit successfully except negative tests **inside** the mutation harness, whose logs must show the intended named assertion failure. A compile/setup failure is not successful mutation detection. The helper retains failed output before reporting an error.

## Evidence

Evidence lives at `$RUN/evidence/`, inside ignored `.work/` but outside the disposable `project/`. Keep the printed absolute path in the task report. Copy it elsewhere before removing the entire `.work/` directory or discarding the checkout.

Capture:

- `manifest.json` and `source/`: exact guidance, UI, action/assertion sources, saved responses, scripts, and build configuration exercised.
- `launch/`: Gradle/JVM versions, build log, commands, and exit codes.
- `<journey>/commands.json` and `command-*.log`: the outer command and combined stdout/stderr, including failures.
- `<journey>/fixture-results/`: existing harness `gradle.log`, `result.json`, and JUnit XML for baseline, negative, and restored runs. Direct method drives instead retain `junit/` and `html/`.
- `doctor.log` and a short `proof.md` written by the driving agent: feature ID, entry point, actions, expected and observed states, negative control outcome, limitations, and paths to the artifacts.

A proof must exercise the actual user path: text input/click through Compose semantics, then visible outcomes. Preserve the executed test source alongside its result so both the action and resulting assertion are evidenced, not just a final status. For message delivery, verify the fake's received payload **and** `Sending`/receipt transitions; a mock call alone is insufficient. The controlled `Sender` is the existing external-system boundary. It is not a real transport: no delivery over a network is claimed. Do not add test-only endpoints or set `Delivery.Sent` internally to fake a pass.

These are real builds/tests, not an offline mode or a dry-run. They write build outputs and caches and may fetch dependencies. Never infer "no network" from the word fixture. No DB/file persistence or actual outbound delivery is implemented in the sample; no such side effects can be certified. For a future dry-run feature, compare files, network activity, and git refs rather than trusting its name.

Report skips, missing seed/preconditions, and unmapped/unimplemented journeys as failures or NOT VERIFIED with the attempted command. Never weaken the assertion or swap entry points to obtain green. A single-feature proof does not certify the whole map. No JVM run establishes screenshots, pixels, TalkBack, IME, system UI, activity recreation, process death, hardware, or performance.

## Cleanup

After success **or any failed iteration**, wait for the tmux job to exit. If it is still running, stop only its recorded job ID using `tmux_jobs` with `action: stop`, then ensure it has exited before deleting its workspace. Never kill Java/Gradle/Python by process name or run a global Gradle stop. No app instance remains after a normal short-lived command exits.

```bash
.pi/skills/verify-compose-robolectric/verify.py cleanup "$RUN"
test ! -d "$RUN/project"
test -s "$RUN/evidence/manifest.json"
find "$RUN/evidence" -type f
```

Cleanup verifies the run's ownership marker, deletes only `project/` and its readiness marker, and leaves evidence plus `owner.json`. It is repeatable. Retain shared dependency caches and the user's SDK. If launch failed before creating an ownership marker, inspect the empty directory manually; never guess which existing directory to remove.

## Helpers

The executable [verify.py](verify.py) has four actions shown above: `launch`, `doctor`, `drive`, `cleanup`. Run `./.pi/skills/verify-compose-robolectric/verify.py --help` for its exact journey list. It wraps the repository scripts, does not replace them, and snapshots the current checkout rather than HEAD alone.

For fresh agent runs, [the writing](features/writing.md), [review](features/review.md), and [debugging](features/debugging.md) maps explain how to use the existing `--responses` and transcript-audit interfaces. Those paths need new responses/transcripts and are not certified by saved-output replay.

After adding or editing this skill run `/reload` in Pi, then invoke `/skill:verify-compose-robolectric`. Maintain the map with `/skill:maintain-verification-skill` when behavior changes.
