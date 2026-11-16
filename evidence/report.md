# Evidence report

The goal is an installable skill that helps agents write, review, and debug trustworthy Kotlin Compose UI tests on JVM Robolectric. The fixture substantiates the guidance rather than providing an application framework.

Verification date is 2026-11-16. Results below distinguish documentation, local observations, and limits. Machine-readable fixture outcomes are in [results/fixture.json](results/fixture.json). The scripts regenerate detailed logs and JUnit XML under `.work/fixture-results/`.

## Versions actually executed

| Component | Executed version or configuration |
| --- | --- |
| Host | macOS 27.2.1, Darwin arm64 |
| Java | OpenJDK 17.0.21.0.3 |
| Gradle | 9.4.1, official distribution checksum pinned |
| Android Gradle Plugin | 9.2.0 |
| Android Kotlin and Compose compiler plugin | 2.2.10, AGP built-in Kotlin |
| Compose BOM | 2026.09.00 |
| Compose UI and UI testing | 1.12.1 |
| Material3 | 1.4.0 |
| Robolectric | 4.18 |
| JUnit | 4.13.2 |
| Compile SDK and Build Tools | API 37, Build Tools 36.0.0 |
| Robolectric runtime | API 35, PAUSED looper |
| Python | 3.15.2 |
| Agent loader and installer | Pi 1.5.2, skills CLI 1.9.0 |

Gradle's version command reports embedded Kotlin 2.3.0. That is not the Android compilation plugin. API 35 was deliberately pinned for the Java 17 run. Compiling against API 37 does not mean Robolectric ran API 37.

## Executable fixture

The first hosted semantics test passed before the fixture expanded. The full suite then passed with eight tests, zero failures, and zero skips. Six tests cover semantics, ambiguity, input/action/result behavior, manual Compose time, deferred completion, disposal and fresh-state isolation, and diagnostics. Two isolated probes compare v1/v2 effect-start ordering.

Each of the six fixture methods also passed alone. Initial and final full mutation baselines passed. A [fresh coordinator run of the canonical project](results/canonical-final.json) also passed all eight tests after aggregation. These runs are evidence for this configuration, not proof of every possible test order.

| Compiled UI regression | Named test that failed | Observed failure |
| --- | --- | --- |
| Make Send a no-op | `sendShowsReceiptAfterCompletion` | Sending is not displayed |
| Route Draft to the Archive result | `scopedOpenSelectsDraft` | Draft opened is not displayed |
| Remove descendant merging | `mergedLabelAndUnmergedChild` | Summary no longer exposes Draft text |

All three failures are `java.lang.AssertionError` from the named tests. The script rejects compilation or setup failure as mutation detection. Each restored named test passed, followed by the passing eight-test baseline.

## Targeted comparisons

### Android resource inclusion

Hypothesis. With the default activity host supplied by `ui-test-manifest`, excluding Android resources prevents the merged debug manifest from providing that host.

Command. `python3 scripts/compare_setup.py` runs the same `mergedLabelAndUnmergedChild` test with only `unitTests.isIncludeAndroidResources` varied.

Observation. Enabled passed. Disabled reached JUnit but failed with `RuntimeException: Unable to resolve activity ... org.robolectric.default/androidx.activity.ComponentActivity`. Restored passed.

Recommendation. Keep resources enabled for this hosted setup. The experiment did not separately remove the manifest dependency and does not prove that every Robolectric test needs Android resources.

### v1 versus v2 effect startup

Hypothesis. The documented dispatcher change can alter immediate effect-start ordering.

Command. Run the fixture suite, or filter `fixture.V1EffectOrderTest` and `fixture.V2EffectOrderTest`. Both register a `LaunchedEffect` before a `DisposableEffect` and then wait for idle.

Observation. The v1 probe printed `[effect, apply]`. The v2 probe printed `[apply, effect]`. Both displayed Probe and ran both callbacks. This is a callback-order observation, not a timing benchmark or a universal effect-order contract.

Recommendation. Use the non-deprecated stable v2 rule factory and explicit synchronization. Do not rely on the deprecated factory's immediate coroutine startup.

## Setup findings and diagnostics

Compose 1.12.1 dependency metadata rejected compile SDK 35. Raising only compile SDK to 37 allowed that gate to proceed. The runtime remains API 35. AGP's legacy source-set accessor produced a cast failure. Explicit `LibraryExtension` configuration compiled the canonical example directory. A `NO-SOURCE` build was rejected as evidence, not counted as a pass.

The sandbox denied shared compiler temporary storage and Robolectric's default Maven download lock. Writable JVM temp and Maven-cache locations allowed execution. These are sandbox settings, not product defects. The sandbox run exported:

```bash
export JAVA_HOME="$(/usr/libexec/java_home -v 17)"
export ANDROID_HOME="$HOME/Library/Android/sdk"
export GRADLE_USER_HOME="$PWD/.work/gradle-home"
export JAVA_TOOL_OPTIONS="-Dmaven.repo.local=$PWD/.work/m2"
```

The verification scripts append `-Djava.io.tmpdir=$TMPDIR` when `TMPDIR` exists. Ordinary checkout execution uses the README commands without requiring those sandbox redirects.

Actual tree diagnostics show merged `summary` text `[Draft, Ready]` and an unmerged `summary-child` with `[Draft]`. The 1.12.1 error hint says `useUnmergedNode`; the real parameter is `useUnmergedTree`. The [saved failure and trees](agent-inputs/failure.txt) are direct fixture output.

## Skill and agent acceptance

Structural checks pass for frontmatter, directory naming, all seven routed references, local links, attribution, and a standalone copied installation. Four deliberately broken packages are rejected. The skills CLI discovered one skill and installed a copy into an isolated project. Explicit `/skill:compose-ui-testing-robolectric-best-practices` invocation expanded the entry skill in Pi and routed an ambiguous-node request to semantics.

The [frozen task contract](agent-task-contract.md), [organic prompts](agent-prompts/), [inputs](agent-inputs/), and [saved responses](agent-responses/) support writing, review, and debugging checks. Initial writing and debugging responses compiled and detected their assigned mutations. The initial review response failed compilation on an invalid top-level `onNode` import. That failure is preserved in [the initial compile log](results/initial/review-compile.log). A static independent judge accepted its behavioral intent but missed that import. The executable gate overruled the static verdict.

A fresh follow-up review response removed the invalid import. It compiled and passed both original-behavior tests. Wrong-target and no-op Send mutations each caused an assertion failure, and each restored response passed. The final writing and debugging responses also passed baseline, mutation, and restored runs. [Machine-readable task outcomes](results/agent-tasks.json) preserve the commands and named failures.

Writing used `openai/gpt-6.1-sol`. Review and its follow-up used `spacex-grok/grok-4.7-build-fast`. Debugging used `spacex-cursor/grok-4.7-fast`. All ran at low thinking in Pi 1.5.2. The independent static judge used `spacex-cursor/grok-4.7-fast`. These are task checks, not a comparison of models.

Successful transcript file reads establish routing. The initial review missed the isolation reference. Tightening the entry instruction to read every reference in the activity row was followed by a fresh review that read behavior, synchronization, and isolation. Writing read behavior and semantics. Debugging read diagnostics and semantics. [Routing results](results/routing.json) and the [initial routing gap](results/initial/routing.json) preserve that distinction. `scripts/check_agent_routing.py` can audit new Pi transcripts with `writing=path`, `review=path`, and `debugging=path` arguments.

Tasks explicitly pointed agents to the installed skill. This does not establish unaided automatic discovery, a causal effect versus no skill, or general agent reliability. The follow-up also received the actual compiler error. It is a repair check, not an independent first-pass success.

## Primary evidence and remaining limits

The [retained AGP compatibility excerpt](results/agp-compatibility.txt) confirms the build-tool defaults cited in setup guidance. The installed [evidence reference](../compose-ui-testing-robolectric-best-practices/references/evidence.md) links the official Compose guides, release notes, versioned source JARs and manifest AAR, Robolectric documentation and 4.18 release notes, and AGP release notes. It records documentation conflicts rather than silently combining incompatible claims. [Reference inspection](reference-inspection.md) records the Playwright repository commit, conventions, and license treatment.

Documented options such as a custom idling resource, an unrelated coroutine scheduler, and `runComposeUiTest` are not executable fixture coverage. The fake is a controlled suspended sender, not a real backend or executor integration. Disposal/remount coverage does not prove process death or activity recreation.

Independent final review passed. It requested a retained AGP citation and tracked replacements for scratch-only trail pointers. Those artifacts and append-only corrections are now in [decisions.tsv](decisions.tsv). Historical placeholder timestamps remain visible with their correction.

This run covers one host, one version combination, and one runtime API. It does not establish device rendering, TalkBack traversal, real IME or system UI behavior, hardware behavior, WebView support, performance, prerelease APIs, or a compatibility matrix. Device-dependent claims still require device or emulator tests.
