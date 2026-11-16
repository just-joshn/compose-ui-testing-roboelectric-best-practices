# Synchronize the work that changes the UI

## Identify the owner

Compose actions and assertions synchronize with Compose and registered idling resources. They do not repeatedly evaluate an arbitrary business assertion until it succeeds. `waitForIdle()` can return while a fake, executor, network request, or unrelated dispatcher still has unfinished work.

| Work | Control or observation |
| --- | --- |
| Recomposition, Compose frames, animation, composition-owned delay | `rule.mainClock` |
| Queued composition coroutine tasks at the current virtual time | `rule.mainClock.scheduler.runCurrent()` |
| A separate coroutine test scheduler | Advance that scheduler explicitly, or deliberately share the Compose scheduler |
| A controllable fake awaiting completion | Complete the fake, then synchronize and assert the UI |
| External async work | A bounded `waitUntil` on an observable condition, or a correctly registered idling resource |
| Android draw work | Allow the Compose test framework to synchronize pending work. Clock advancement alone does not establish drawing |
| Wall-clock or business time | Inject the application's time source. Do not assume `mainClock` changes `Instant.now()` |

Do not solve every row with `Thread.sleep`, `advanceUntilIdle`, or `ShadowLooper.idleFor`. Those act on different systems.

## Let the default clock finish ordinary interactions

Keep `autoAdvance` enabled for ordinary settled-state tests. Action and assertion synchronization can advance the clock until Compose is idle. This can skip transient states. If a test must observe a pending state, hold external work with a controllable fake or disable automatic clock advancement before starting the transition.

A fake that suspends on a fresh `CompletableDeferred` gives the test a deterministic pending interval. Assert the pending UI, complete the deferred, then assert the result. Do not make an idling resource report busy for the very work you need to inspect while pending. Synchronized assertions would wait for it.

## Control Compose time deliberately

For a delayed UI transition, set `rule.mainClock.autoAdvance = false` before triggering it. Start queued effects with `rule.mainClock.scheduler.runCurrent()` when needed. Advance frames or virtual time, and then assert an observable state. Establish the timer's start before calculating its deadline.

`advanceTimeBy` rounds to frame boundaries unless you request otherwise. Advancing to a coroutine deadline can leave work queued at that exact time. A current-task or frame step may still be required. Prefer assertions before and after the intended transition over an unexplained large duration.

Use `advanceTimeUntil` only for conditions this clock can change. Do not put a synchronized finder inside an `advanceTimeUntil` predicate. Poll a known Compose state value instead. Use `waitUntil` for a condition that needs external progress or semantics queries.

The [canonical examples](../examples/) keep Compose delay and fake completion separate. Advancing the Compose clock cannot supply a receipt that the test has not completed.

## Wait for external progress without hiding a failure

Use a bounded condition and a final behavior assertion:

```kotlin
rule.waitUntil(timeoutMillis = 2_000) {
    rule.onAllNodesWithText("Delivered").fetchSemanticsNodes().size == 1
}
rule.onNodeWithText("Delivered").assertIsDisplayed()
```

This fragment assumes the app can actually make progress and exposes exactly that text. Supply its real condition. The wait observes presence. The final assertion proves the expected display state.

Do not catch every assertion inside a wait loop. A collection query naturally represents zero matches without swallowing a programming error. Do not use a `CountDownLatch.await()` on the test thread while Compose needs that thread or its clock to progress.

If an asynchronous subsystem must participate in all Compose synchronization, implement the Compose `IdlingResource` contract. Keep `isIdleNow` cheap and nonblocking. Register before work starts and unregister in cleanup. The fixture does not validate a custom idling-resource implementation.

## Keep coroutine schedulers explicit

For Compose 1.12.1, use the `androidx.compose.ui.test.junit4.v2` rule factory. The deprecated v1 factories use `UnconfinedTestDispatcher`. v2 uses `StandardTestDispatcher`, so code that relied on immediate effect execution needs explicit synchronization.

Wrapping a rule test in a new `runTest` introduces another scheduler unless you pass `rule.mainClock.scheduler`. Calling `advanceTimeBy` on that unrelated scope does not advance Compose. Do not replace `Dispatchers.Main` globally around a Compose rule to fix this by guesswork. Inspect the existing effect context and scheduling contract first.

`runComposeUiTest` in the v2 package is another documented environment API. This fixture uses the JUnit rule. It does not establish that the environments are interchangeable for every project's lifecycle.

## Evidence and version boundary

The [official synchronization guide](https://developer.android.com/develop/ui/compose/testing/synchronization), [v2 migration guide](https://developer.android.com/develop/ui/compose/testing/migrate-v2), and published `MainTestClock` KDoc describe these controls. The KDoc is more specific than the guide about Android measure/layout and Choreographer-driven drawing. Do not turn either into a claim that virtual time proves real rendering.

`ComposeUiTestConfig` and main-thread synchronization appear in the 1.13 pre-release documentation. They are not the tested 1.12.1 API. Check [evidence.md](evidence.md) before copying current online examples into an older dependency set.
