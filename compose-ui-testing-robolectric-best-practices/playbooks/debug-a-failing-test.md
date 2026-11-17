# Debug a Failing Test

## When to use

Use this playbook when a Compose UI test fails on Robolectric and the cause is not known.

## Investigate and establish evidence

1. Run the failing test and record the exact command, the failure message, and the stack trace.
2. Print the semantics tree at any point in the test, because looking at it is the main way to solve problems in tests. See [debugging.md](../debugging/debugging.md#semantics-tree-printing).
3. Print the semantics tree with `useUnmergedTree` set to true as well as the default tree, because some nodes merge the semantics information of their children. See [semantics-finders.md](../core/semantics-finders.md#merged-and-unmerged-trees).
4. Check whether the UI has identical Compose elements nested inside multiple traditional Android Views, where a standard Compose search might fail with a "Multiple nodes found" error. See [debugging.md](../debugging/debugging.md#multiple-nodes-found-inside-android-views).
5. If an assertion fails right after launching a task and the data is still in a "Loading" state, check whether the test uses the v2 APIs, which queue coroutines instead of executing them immediately. See [debugging.md](../debugging/debugging.md#assertion-fails-after-launching-a-task-v2-apis).
6. If the UI does not update after a state change, check whether the test used the methods that synchronize it, because without them no recomposition occurs. See [debugging.md](../debugging/debugging.md#ui-appears-paused).
7. If the failure mentions unexecuted tasks in the main Looper queue, note that `LooperMode.PAUSED` warns when a test fails with them. See [debugging.md](../debugging/debugging.md#looper-warnings).
8. Check whether the test relies on a non-touch input mode configured through instrumentation APIs before the test starts, which can make tests fail during migration. See [flaky-tests.md](../debugging/flaky-tests.md#input-mode-leakage).
9. You can automatically capture screenshots and UI hierarchies upon test failure, because debugging UI tests often requires inspecting the screen state and composition hierarchy. See [debugging.md](../debugging/debugging.md#failure-artifacts).
10. If it is not clear whether resources are loaded for a library, turn on Robolectric debug logging. See [debugging.md](../debugging/debugging.md#debug-logging).
11. The Robolectric simulator can be a useful way to preview how your UI would look in a Robolectric environment, which can be helpful when debugging failing Robolectric tests. It is highly experimental and still largely in the proof-of-concept stage, and UI rendered in it may not match an Android emulator or device 100%. See [debugging.md](../debugging/debugging.md#robolectric-simulator).
12. Check whether the failure comes from a documented difference between Android libcore and OpenJDK, or from a fidelity limit of Robolectric. See [debugging.md](../debugging/debugging.md#android-libcore-and-openjdk-differences) and [debugging.md](../debugging/debugging.md#fidelity-limits).
13. If a rendering assertion fails after advancing the clock, check whether the test waited for the draw pass to complete. See [debugging.md](../debugging/debugging.md#wait-for-draw-before-capturing).

## Deliver supported findings

- State the cause as the first place the evidence shows the test going wrong, with the command output, file and line, or official page behind it.
- Separate what the evidence shows from what you infer.
- If no official page covers the behavior, say it is not documented.
- List open questions.

## Design and implement

- Fix the cause the evidence points to, with the smallest change. Each item below applies to one cause from the investigation.
- Merged tree hides the node: set `useUnmergedTree` for a special need to inspect implementation detail within children. See [semantics-finders.md](../core/semantics-finders.md#merged-and-unmerged-trees).
- Identical elements inside Android Views: use `onRootWithViewInteraction`, which is experimental and subject to change. See [interoperability.md](../advanced/interoperability.md).
- Queued coroutines: use `waitForIdle` or `runOnIdle` to execute queued tasks before asserting. See [debugging.md](../debugging/debugging.md#assertion-fails-after-launching-a-task-v2-apis).
- Condition that depends on external work: use `waitUntil`. See [synchronization.md](../core/synchronization.md#waiting-for-conditions).
- Unexecuted main Looper tasks: if you see test failures like 'Main looper has queued unexecuted runnables.', you may need to insert `shadowOf(getMainLooper()).idle()` calls to your test to drain the main Looper. See [synchronization.md](../core/synchronization.md#draining-the-main-looper).
- Non-touch input mode: specify the required input mode in `ComposeUiTestConfig`. See [configuration.md](../core/configuration.md#input-mode).
- Rendering assertion after advancing the clock: call `waitForIdle` or `runOnIdle` before asserting. See [debugging.md](../debugging/debugging.md#wait-for-draw-before-capturing).

## Verify behavior and challenge findings

- Rerun the failing test with the same command and record the result.
- Reintroduce the cause, confirm the test fails again, then restore the fix.
- Print the semantics tree again after the fix and compare it with the tree from the investigation. See [debugging.md](../debugging/debugging.md#semantics-tree-printing).
- Remove temporary diagnostic output added during the investigation, and run the rest of the module's tests.
- Ask an independent reviewer for a different explanation that fits the same evidence.

## Sources

- https://developer.android.com/develop/ui/compose/testing
- https://developer.android.com/develop/ui/compose/testing/common-patterns
- https://developer.android.com/develop/ui/compose/testing/migrate-v2
- https://developer.android.com/develop/ui/compose/testing/debug
- https://developer.android.com/develop/ui/compose/testing/apis
- https://developer.android.com/develop/ui/compose/testing/interoperability
- https://developer.android.com/develop/ui/compose/testing/synchronization
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/SemanticsNodeInteraction
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/MainTestClock
- https://robolectric.org/javadoc/4.18/org/robolectric/annotation/LooperMode.Mode.html
- https://developer.android.com/training/testing/local-tests/robolectric
- https://robolectric.org/best-practices
- https://robolectric.org/getting-started
- https://robolectric.org/simulator
