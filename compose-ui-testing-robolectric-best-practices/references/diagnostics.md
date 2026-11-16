# Diagnose the first failing boundary

## Continue with the topic guides

Read [debugging](../debugging/debugging.md) for the full failure-classification workflow and artifact contract. Use [flaky tests](../debugging/flaky-tests.md), [logs and exceptions](../debugging/logs-exceptions.md), and [error testing](../debugging/error-testing.md) for their specific failure classes.

## Preserve the failure

Run the narrow test with its current dependencies. Save its full exception, the command, and the JUnit report. Distinguish a Gradle configuration failure, Kotlin compilation failure, Robolectric host failure, synchronization timeout, and behavior assertion failure before editing the test.

For the repository fixture, use the Gradle task and method filter documented in the repository README. In another project, use that project's real module and variant. Do not replace a failing UI assertion with a setup workaround.

## Classify the symptom

| Symptom | First check | Do not do |
| --- | --- | --- |
| `Method ... not mocked` | Does this local test run through a Robolectric-aware runner with the right dependencies? | Enable `returnDefaultValues` |
| Activity cannot launch or resources are absent | Debug merged manifest, `ui-test-manifest` or real host declaration, Android resource inclusion, selected variant | Add arbitrary waits |
| Unsupported SDK or class-file version | Explicit `@Config` SDK, Robolectric compatibility table, actual test-worker JDK | Downgrade dependencies blindly |
| Expected one node but found zero | Actual text, selected tree, clearing/merging, content mounted, and work ownership | Broaden text matching until green |
| Expected one node but found multiple | Dump matching nodes and scope by meaningful identity | Select the first match without an order contract |
| Pending UI never becomes a result | Which fake, dispatcher, clock, or external job can produce the result? | Advance the Compose clock for unrelated work |
| UI stays busy | Recomposition loop, pending animation, registered busy resource, work that never completes | Increase every timeout |
| Test passes alone but fails in a class | Shared fake/state, leaked threads, globals, cleanup | Force method order |

## Inspect the tree, not the composable source alone

Print both roots using `onRoot().printToString()` and `onRoot(useUnmergedTree = true).printToString()`. Keep the selector and its cardinality next to the dumps. Inspect the relevant node's text, tag, actions, and merge boundary.

A child folded into its parent may be absent as a distinct merged node while its text is still searchable on the parent. Correct the test to the intended group or intentionally query the unmerged child. Do not add production semantics solely to expose an implementation detail.

Compose 1.12.1 source contains a misleading hint that spells the option `useUnmergedNode`. The public finder parameter is `useUnmergedTree`. Treat framework error text as evidence, not compilable Kotlin.

## Diagnose time in separate steps

1. Establish whether the transition started through the intended user action.
2. Identify which actor owns each pending operation.
3. If Compose time owns it, establish the start frame and advance that clock.
4. If an external fake owns it, release or fail the fake explicitly.
5. If external production work owns it, observe a bounded condition or register its idling resource.
6. Assert the resulting user-visible state after synchronization.

Do not call a test-side blocking latch while the UI needs Compose progress. Do not invoke synchronized assertions from `runOnIdle` or from a UI-thread callback that they need to synchronize. Stable 1.12.1 and the 1.13 pre-release differ in main-thread synchronization support. Check the actual artifact instead of copying current online examples.

## Confirm the correction

Rerun the test and its containing class. Introduce the relevant wrong action or missing semantics and confirm the corrected test fails at the intended assertion. Preserve the original failure and the corrected result in the report.

The [canonical examples](../examples/) include intentional ambiguity and timeout diagnostics. They catch only the expected failure type. Production behavior tests must not swallow their own assertion failures.

See [setup.md](setup.md), [semantics.md](semantics.md), and [synchronization.md](synchronization.md) for the corresponding repair path. The [evidence reference](evidence.md) separates observed messages from version-sensitive documentation.
