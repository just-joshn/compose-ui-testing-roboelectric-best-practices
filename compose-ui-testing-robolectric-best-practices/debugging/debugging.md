# Diagnose a failing Compose Robolectric test

Use this guide when a local Android UI test fails during setup, selection, synchronization, or an outcome assertion. Preserve the first failure before changing code. This workflow uses JUnit, Gradle output, a JVM debugger, and semantics dumps. Robolectric has no headed browser or Playwright trace viewer.

## Table of contents

- [Classify the first failed boundary](#classify-the-first-failed-boundary)
- [Reproduce the named test](#reproduce-the-named-test)
- [Inspect semantics and cardinality](#inspect-semantics-and-cardinality)
- [Diagnose work and clock ownership](#diagnose-work-and-clock-ownership)
- [Inspect dependencies and host setup](#inspect-dependencies-and-host-setup)
- [Debug authentication and data](#debug-authentication-and-data)
- [Collect CI evidence](#collect-ci-evidence)
- [Confirm the correction](#confirm-the-correction)
- [Troubleshooting table](#troubleshooting-table)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Classify the first failed boundary

| First failure | Inspect first | Do not repair with |
| --- | --- | --- |
| Gradle configuration | Plugin versions, wrapper, variant, JDK | Semantics changes |
| Unresolved Kotlin import | Resolved artifact and published API | Random extra dependencies |
| `Method ... not mocked` | Robolectric runner and source set | `returnDefaultValues` |
| Activity cannot launch | Resources, merged manifest, host declaration | A longer wait |
| No matching node | Mounted content, actual tree, exact text | Index selection |
| Several matching nodes | Identity and ancestor scope | `[0]` |
| Compose stays busy | Recomposition loop, animation, idling resource | Global timeout increase |
| Loading never resolves | Pending fake or external scheduler | Advancing unrelated Compose time |
| Wrong visible result | Action target and state transition | Replacing the result assertion with a callback count |

A dependency download failure can prevent execution without saying anything about UI correctness. A sandbox-only permission error is an environment suspect until reproduced outside that sandbox. Keep the exact error and affected command.

## Reproduce the named test

For this repository's fixture, run:

```bash
./gradlew :fixture:testDebugUnitTest \
  --tests 'fixture.FixtureUiTest.selectorFailureIncludesTreeDiagnostics' \
  --console=plain --no-daemon --rerun-tasks --stacktrace
```

In another project, substitute its actual module, local-unit-test variant, class, and method. Do not switch to `connectedAndroidTest` and call it the same reproduction.

Save the command, full output, process exit code, selected SDK, JDK, resolved dependencies, and JUnit XML. The usual report locations for this task are:

```text
fixture/build/test-results/testDebugUnitTest/TEST-*.xml
fixture/build/reports/tests/testDebugUnitTest/index.html
```

Check that the intended method executed without a skip. `UP-TO-DATE`, `NO-SOURCE`, or an empty report cannot establish a fresh pass. Preserve the old report before rerunning because the task can overwrite it.

Use Android Studio's debugger on the local JUnit test to inspect application state and coroutine ownership. Place breakpoints at the action handler, repository boundary, and state emission. Breakpoints can change race timing, so confirm the repair without the debugger too.

Do not add sleeps to slow the test visually. There is no real device window to watch in this local setup. Use action-boundary semantics snapshots instead.

## Inspect semantics and cardinality

The data shape to inspect is the semantics tree, not the composable call tree. Capture both merged and unmerged roots while the environment can still synchronize.

This illustrative fragment needs a configured rule named `compose` and these imports:

```kotlin
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.printToString

println("MERGED\n${compose.onRoot().printToString()}")
println("UNMERGED\n${compose.onRoot(useUnmergedTree = true).printToString()}")
```

Do not invoke synchronized tree queries from `runOnIdle` or a UI callback. Run them on the test side. If synchronization itself is stuck, a synchronized dump may also time out. Preserve the original timeout rather than allowing a secondary diagnostic failure to replace it.

### Missing child in the merged tree

The canonical JUnit output contains this real failure excerpt:

```text
Failed: assertExists.
Reason: Expected exactly '1' node but could not find any node that satisfies: (TestTag = 'summary-child')
However, the unmerged tree contains '1' node that matches. Are you missing `useUnmergedNode = true` in your finder?
```

Its recorded tree includes the following excerpt. Node identifiers and bounds belong to this run, not stable test expectations.

```text
MERGED
Printing with useUnmergedTree = 'false'
Node #5 at (l=0.0, t=0.0, r=5.0, b=70.0)px
 |-Node #6 at (l=0.0, t=0.0, r=5.0, b=70.0)px, Tag: 'summary'
   Text = '[Draft, Ready]'
   Actions = [ClearTextSubstitution, GetTextLayoutResult, SetTextSubstitution, ShowTextSubstitution]
   MergeDescendants = 'true'
UNMERGED
Printing with useUnmergedTree = 'true'
Node #5 at (l=0.0, t=0.0, r=5.0, b=70.0)px
 |-Node #6 at (l=0.0, t=0.0, r=5.0, b=70.0)px, Tag: 'summary'
   MergeDescendants = 'true'
    |-Node #7 at (l=0.0, t=0.0, r=5.0, b=35.0)px, Tag: 'summary-child'
    | Text = '[Draft]'
```

The unmerged excerpt stops at the first child's text. The full output also contains its actions and the second child. The observation establishes that the child exists but is merged into the user-facing group.

Faulty finder for a child-specific assertion:

```kotlin
compose.onNodeWithTag("summary-child").assertExists()
```

Corrected finder:

```kotlin
compose.onNodeWithTag("summary-child", useUnmergedTree = true).assertIsDisplayed()
```

These fragments use `onNodeWithTag` and `assertIsDisplayed` from `androidx.compose.ui.test`. `assertExists` is an interaction member, not a top-level import. The public parameter is `useUnmergedTree`, despite the error message's `useUnmergedNode` spelling.

If the claim concerns the group instead, assert its merged text and identity. Do not switch every finder to the unmerged tree. `clearAndSetSemantics` replaces descendant information in the merged tree. The unmerged tree can still expose children for test inspection. Their presence there does not establish that accessibility services receive those original child semantics.

### Duplicate action labels

The recorded `scopedOpenSelectsDraft` diagnostic contains:

```text
Failed to inject touch input.
Reason: Expected exactly '1' node but found '2' nodes that satisfy: (Text + InputText + EditableText contains 'Open' (ignoreCase: false))
```

This is a target-selection failure before the intended user action. Increasing a timeout cannot choose the correct button.

Use meaningful identity. This illustrative correction assumes the canonical `DraftActions` tree:

```kotlin
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasAnyAncestor
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick

compose.onAllNodesWithText("Open").assertCountEquals(2)
compose.onNode(hasText("Open") and hasAnyAncestor(hasTestTag("draft")))
	.performClick()
compose.onNodeWithText("Draft opened").assertIsDisplayed()
compose.onNodeWithText("Archive opened").assertDoesNotExist()
```

If the clickable node itself owns both tag and merged text, combine `hasText` and `hasTestTag` on that node instead of searching ancestors. Inspect the selected tree to decide.

## Diagnose work and clock ownership

Identify the first missing transition rather than draining every scheduler:

1. Confirm the action selected and activated the intended node.
2. Observe whether the real state owner began the operation.
3. Identify the dependency that can produce the next state.
4. Control or observe that dependency.
5. Assert the resulting visible state.

| Work owner | Evidence to inspect | Correct control |
| --- | --- | --- |
| Composition timer or animation | Timer started, current Compose virtual time | `mainClock` |
| Queued composition coroutine | Effect or resumed task queued at current time | `mainClock.scheduler.runCurrent()` when needed |
| Separate coroutine test scheduler | Dispatcher supplied to repository or ViewModel | That scheduler, not an unrelated `runTest` scope |
| Pending fake | Completion belongs to this test's instance | Complete or fail the fake |
| Android looper task | Which looper owns the callback | A targeted looper action only when that is the actual boundary |
| External work | Completion signal and executor lifecycle | Bounded observation or registered idling resource |
| Business date or expiration | Injected application time source | Advance that source |

Compose assertions synchronize known work. They are not browser-style retrying assertions for arbitrary business state. A bounded `waitUntil` can observe external progress, but the operation must be capable of finishing.

The canonical `composeClockDoesNotCompleteSender` test advances a composition-owned delay and observes `Still sending`. It then completes the sender separately. That separation is the repair when time advances but no receipt appears.

## Inspect dependencies and host setup

Inspect resolved dependencies rather than guessing from declared versions:

```bash
./gradlew :fixture:dependencies --configuration debugUnitTestRuntimeClasspath
./gradlew --version
```

Use the configuration exposed by your project's plugin and variant. Confirm the actual test-worker JDK as well as the Gradle launcher JDK. Kotlin bytecode target is not the worker's Java version.

The pinned fixture uses Compose UI 1.12.1 and `androidx.compose.ui.test.junit4.v2.createComposeRule`. Current online 1.13 configuration examples can use APIs absent from 1.12.1. Do not add `ComposeUiTestConfig` merely because a newer guide mentions it.

Check `src/test`, `testImplementation`, resource inclusion, Robolectric runner, explicit supported SDK, and activity declaration. For the default host, check `ui-test-manifest`. For a custom host, check its actual manifest declaration.

The recorded resource-disabled comparison failed before UI execution with:

```text
java.lang.RuntimeException: Unable to resolve activity for Intent { act=android.intent.action.MAIN cat=[android.intent.category.LAUNCHER] cmp=org.robolectric.default/androidx.activity.ComponentActivity } -- see https://github.com/robolectric/robolectric/pull/4736 for details
```

Restoring Android resource inclusion restored the selected test's pass in that experiment. This observation does not mean every activity-resolution failure has that cause. Inspect the selected variant and manifest first.

Do not downgrade a project's dependencies to fit whatever artifacts happen to be cached. Choose the intended versions, then resolve their required artifacts. A blocked download is not a UI regression.

## Debug authentication and data

For fake-backed UI tests, inspect the session state supplied to the real state owner. Verify that the dependency override was installed before the activity or ViewModel was created.

Log session category and sanitized account identity, not tokens. Check whether the screen starts signed out, refreshes, receives unauthorized status, or routes away. A fake signed-in session cannot prove OAuth redirects, credential storage security, or backend authorization.

For stale content, inspect repository instance identity, cache lifetime, stream replay, and record namespace. Do not repair leaked data by forcing test method order.

For device-only authentication failures, retain the device and provider evidence in that suite. Do not invent a Robolectric browser callback as proof of the real flow.

## Collect CI evidence

Keep the first failing attempt, not only a successful retry. Archive:

- Exact command, commit, module, variant, and test filter.
- Wrapper, AGP, Kotlin compiler plugin, Compose, Robolectric, SDK, and worker JDK versions.
- Process output, JUnit XML, and HTML report.
- Merged and unmerged semantics dumps where synchronization permits them.
- Sanitized fake request and completion events.
- Relevant configuration such as locale, density, font scale, and clock mode.

A JVM drawing capture can aid a local diagnosis, but it does not prove device pixels. Use semantics for semantic regressions and a separate device screenshot workflow for rendering claims.

Match CI's versions and test configuration before comparing results. Reduce concurrency as an experiment to expose shared-state or resource contention. Do not make serial execution the permanent fix without understanding the dependency.

## Confirm the correction

Rerun the named test, its containing class, and the relevant suite. For an intermittent failure, repeat forced executions and preserve every result.

Apply a narrow negative control such as a no-op action or wrong-item callback. The corrected test must fail at its behavior assertion, not during compilation or host startup. Restore the behavior and rerun.

The repository's recorded wrong-item mutation failed on `Draft opened` not being displayed. Its restoration passed. That evidence supports the outcome assertion, not device fidelity or every possible interleaving.

## Troubleshooting table

| Symptom | Observation | Repair path |
| --- | --- | --- |
| Zero matches in merged tree | Child exists only unmerged | Query the intended group or deliberate child |
| Repeated label matches twice | Both nodes expose the same action text | Scope by item identity |
| Infinite loading | Fake is pending or state collection did not resume | Release the right boundary and scheduler |
| Timeout after global Main replacement | Compose and application scheduling no longer agree | Remove speculative replacement and inspect ownership |
| Failure only after another method | Mutable fake, preference, stream, or thread survives | Fix ownership and cleanup |
| CI-only class-version failure | SDK requires a newer worker JVM | Select a supported SDK and JDK combination |
| Test passes with broken action | Test supplied final state or asserted only existence | Exercise action-to-outcome path |

## Review checklist

- Is the first failing boundary identified?
- Are the command and original JUnit failure preserved?
- Does the tree support the chosen matcher and cardinality?
- Is each asynchronous operation assigned to its actual owner?
- Does the fix address the first incorrect transition?
- Did the intended negative control fail at a behavior assertion?
- Are local and device claims kept separate?

## Related guides and sources

- [Flaky tests](flaky-tests.md) covers repeated-run experiments.
- [Logs and exceptions](logs-exceptions.md) preserves diagnostic causes.
- [Semantics selectors](../core/semantics-selectors.md) covers identity and merging.
- [Assertions and waiting](../core/assertions-waiting.md) chooses synchronization.
- [Evidence and limits](../references/evidence.md) records the fixture's version boundaries.
- [Compose testing APIs](https://developer.android.com/develop/ui/compose/testing/apis) documents tree inspection.
- [Compose synchronization](https://developer.android.com/develop/ui/compose/testing/synchronization) documents clocks and external work.
- [Robolectric configuration](https://robolectric.org/configuring/) documents SDK and environment settings.
