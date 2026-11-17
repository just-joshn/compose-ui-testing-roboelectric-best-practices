# Fix a Flaky Test

## When to use

Use this playbook when a Compose UI test passes and fails without code changes.

## Delegate

- Delegate to one read-only subagent: run the test repeatedly with one command and return the pass and fail record with each failure message.
- Delegate to a second read-only subagent: read the test and the code under test for timing, waiting, and shared state, and report each candidate cause with its location.
- Keep for yourself: matching the candidates to the record, naming the cause, and making the fix.
- After verification, delegate the challenge to a fresh reviewer: look for a different explanation that fits the same pass and fail record.

## Investigate and design

### Investigate

1. Run the test repeatedly with the same command and record each pass or fail, with the failure message of each failing run.
2. Compare the output of a failing run with the output of a passing run.
3. Check whether the test uses the methods that synchronize it with the UI. Assertions and actions through the rule synchronize beforehand, and without synchronizing methods no recomposition occurs. See [flaky-tests.md](../references/debugging/flaky-tests.md#compose-synchronization).
4. Check the `autoAdvance` property of the main clock, because `waitForIdle()` depends on it. See [flaky-tests.md](../references/debugging/flaky-tests.md#manual-synchronization).
5. Check whether the test waits for a condition that depends on external work, such as data loading, without `waitUntil`. See [flaky-tests.md](../references/debugging/flaky-tests.md#wait-for-conditions).
6. Check whether the test uses an external mechanism such as `CountDownLatch` instead of the `waitUntil` APIs. In some cases this could behave unexpectedly, since the test clock won't be advanced. See [synchronization.md](../references/core/synchronization.md#warnings).
7. Check whether asynchronous work that is not done through Compose's mechanisms is registered as an `IdlingResource`. See [synchronization.md](../references/core/synchronization.md#idling-resources).
8. Check which API version the test uses. The v1 APIs run a launched coroutine immediately, which could mask real timing issues or race conditions, while the v2 APIs queue it until the test advances the virtual clock. See [flaky-tests.md](../references/debugging/flaky-tests.md#coroutine-timing-v1-vs-v2).
9. Check whether the test combines `createComposeRule` with `runTest`, which creates two separate clocks. See [flaky-tests.md](../references/debugging/flaky-tests.md#migrate-to-runcomposeuitest).
10. Check each timeout: the `waitUntil` timeout on the rule observes wall clock time, while the `advanceTimeUntil` timeout is test clock time. See [synchronization.md](../references/core/synchronization.md#waituntil-behavior).
11. Check the Looper mode. In `LooperMode.PAUSED`, tasks posted to the main Looper are not executed automatically, and tasks posted to background loopers run asynchronously in separate threads. See [flaky-tests.md](../references/debugging/flaky-tests.md#main-looper-and-threads).
12. Check how many threads run during the test, because rogue threads often cause test pollution since they are not automatically cleaned up between tests. See [flaky-tests.md](../references/debugging/flaky-tests.md#limiting-threads).
13. Check whether the test relies on non-touch input modes configured through instrumentation APIs before the test starts, which can make tests fail during migration. See [flaky-tests.md](../references/debugging/flaky-tests.md#input-mode-leakage).

### Design

- Fix the cause the evidence points to, with the smallest change. Each item below applies to one cause from the investigation.
- Condition on external work: use `waitUntil` or one of its helpers. See [synchronization.md](../references/core/synchronization.md#waiting-for-conditions).
- Condition on Compose state: try `MainTestClock.advanceTimeUntil` before `waitUntil`, because `waitUntil` sleeps after every iteration. See [synchronization.md](../references/core/synchronization.md#waituntil-behavior).
- Background work outside Compose: register an `IdlingResource` on the rule. See [synchronization.md](../references/core/synchronization.md#idling-resources).
- Assertions on shared variables: use `runOnIdle`, which waits until the app is idle. See [synchronization.md](../references/core/synchronization.md#runonidle).
- Queued coroutines: use `waitForIdle` or `runOnIdle` before asserting. In scenarios involving manual synchronization, such as when auto-advancing is disabled, use `runCurrent()` to execute queued tasks without advancing the virtual clock. See [flaky-tests.md](../references/debugging/flaky-tests.md#failures-after-upgrading-to-v2) and [flaky-tests.md](../references/debugging/flaky-tests.md#run-queued-coroutines-without-advancing-time).
- Compose test APIs alongside `runTest`: switch to `runComposeUiTest`, which is strongly recommended. See [flaky-tests.md](../references/debugging/flaky-tests.md#migrate-to-runcomposeuitest).
- Unexecuted main Looper tasks: if you see test failures like 'Main looper has queued unexecuted runnables.', insert `shadowOf(getMainLooper()).idle()` calls into your test to drain the main Looper. See [synchronization.md](../references/core/synchronization.md#draining-the-main-looper).
- Extra threads: if necessary to run multiple threads, explicitly stop all threads and `ExecutorServices`. See [flaky-tests.md](../references/debugging/flaky-tests.md#limiting-threads).
- Non-touch input mode: specify the required input mode in `ComposeUiTestConfig`. See [flaky-tests.md](../references/debugging/flaky-tests.md#input-mode-leakage).

## Implement and clean

- Change only what the named cause requires.
- Remove the repeat-run scaffolding and temporary output added while investigating.

## Verify actual behavior

- Rerun the test the same number of times with the same command as the investigation, and compare the pass and fail record with the earlier one.
- Report the result as the record itself, such as the number of failing runs out of the total. A run of passes is not proof that the flakiness is gone; if the record cannot show the cause is removed, mark the check Unresolved.
- Where the failure can be reproduced, reintroduce the cause, confirm the failure returns, then restore the fix.
- Check whether the test waits with an external mechanism such as `CountDownLatch` instead of the `waitUntil` APIs, which in some cases could behave unexpectedly. See [synchronization.md](../references/core/synchronization.md#warnings).
- Ask an independent reviewer for a different explanation that fits the same pass and fail record.

## Deliver artifact and evidence

- State the observed pass and fail pattern, with the commands and the number of runs.
- State the cause that the difference between failing and passing runs supports, with the evidence behind it.
- If no official page covers the behavior, say it is not documented.

## Sources

- https://developer.android.com/develop/ui/compose/testing/synchronization
- https://developer.android.com/develop/ui/compose/testing/migrate-v2
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/junit4/ComposeTestRule
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/MainTestClock
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/IdlingResource
- https://robolectric.org/javadoc/4.18/org/robolectric/annotation/LooperMode.Mode.html
- https://robolectric.org/best-practices
