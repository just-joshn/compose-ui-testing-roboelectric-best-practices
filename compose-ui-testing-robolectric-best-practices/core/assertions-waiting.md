# Assert UI outcomes and synchronize work

Use this guide for settled-state assertions, pending states, asynchronous results, and clock-controlled transitions in Android local tests. Keep the Compose rule real. Control the boundary that produces nondeterministic work.

## Contents

- [Choose the assertion and work owner](#choose-the-assertion-and-work-owner)
- [Assert observable state](#assert-observable-state)
- [Hold and complete external work](#hold-and-complete-external-work)
- [Use bounded waits](#use-bounded-waits)
- [Control Compose time](#control-compose-time)
- [Keep value assertions and custom matchers narrow](#keep-value-assertions-and-custom-matchers-narrow)
- [Handle failures without hiding them](#handle-failures-without-hiding-them)
- [Troubleshoot timeouts](#troubleshoot-timeouts)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the assertion and work owner

| Claim or work | Use | Do not infer |
| --- | --- | --- |
| A semantic node is present | `assertExists()` | It is displayed or has correct content |
| A node is visible | `assertIsDisplayed()` | A click produced the correct state |
| A node is absent | `assertDoesNotExist()` | A hidden node is necessarily absent |
| A control is disabled | `assertIsNotEnabled()` | Real device touch behavior |
| A toggle is selected | `assertIsOn`, `assertIsSelected`, as appropriate | A callback count establishes visual state |
| A known Compose update settles | Normal action or assertion synchronization | Arbitrary executor or network completion |
| Composition-owned time passes | `mainClock` | Wall clock or unrelated coroutine time |
| A fake request completes | Explicit fake completion | Advancing frames supplies its response |
| External work progresses | Bounded `waitUntil` or registered idling resource | A universal retrying assertion |
| A plain value is correct | JUnit value assertion | UI behavior without a UI assertion |

Compose assertions synchronize known work before examining semantics. They are not Playwright web-first assertions that retry every expected business condition until success.

## Assert observable state

This complete illustrative test uses Material3, JUnit 4, Robolectric, and Compose UI test dependencies from [configuration](configuration.md). It is not part of the compiled canonical fixture.

```kotlin
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class SaveTest {
	@get:Rule val rule = createComposeRule()

	@Test fun saveDisplaysConfirmation() {
		rule.setContent {
			var saved by remember { mutableStateOf(false) }
			Button(onClick = { saved = true }) { Text("Save") }
			if (saved) Text("Saved")
		}
		rule.onNodeWithText("Saved").assertDoesNotExist()
		rule.onNodeWithText("Save").performClick()
		rule.onNodeWithText("Saved").assertIsDisplayed()
	}
}
```

The final assertion fails when the click becomes a no-op. Checking that `Save` still exists would not detect that regression.

Use `assertTextEquals` when the exact semantic text is the contract. A text field can expose both label text and editable text. Inspect the node before assuming that a single string is its entire text collection.

For collections, use `assertCountEquals`, `assertAll`, or `assertAny` when the requirement concerns count or matching properties. A singular finder is appropriate when exactly one result must exist.

## Hold and complete external work

A fresh `CompletableDeferred` creates a deterministic pending interval. This illustrative fake implements the canonical `fixture.Sender` interface:

```kotlin
import fixture.Sender
import kotlinx.coroutines.CompletableDeferred

class PendingSender : Sender {
	private val receipt = CompletableDeferred<String>()

	override suspend fun send(message: String): String = receipt.await()

	fun complete(value: String) {
		check(receipt.complete(value))
	}
}
```

Use it with the canonical `MessagePanel`. The following fragment belongs inside a hosted test method:

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import fixture.MessagePanel

val sender = PendingSender()
rule.setContent { MessagePanel(sender) }
rule.onNodeWithText("Message").performTextInput("Hello")
rule.onNodeWithText("Send").performClick()
rule.onNodeWithText("Sending").assertIsDisplayed()
rule.runOnIdle { sender.complete("Delivered Hello") }
rule.onNodeWithText("Delivered Hello").assertIsDisplayed()
```

Create a new fake for every test. A reused completed deferred skips the pending interval. Supplement the result with a payload assertion when needed, but do not replace the UI result with a callback count.

Do not register this deliberately pending fake as globally busy while you need to assert `Sending`. Synchronized assertions would wait for that busy resource instead of inspecting the pending UI.

## Use bounded waits

For independently progressing work, wait for a concrete observable condition and then make the stronger assertion:

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithText

rule.waitUntil(timeoutMillis = 2_000) {
	rule.onAllNodesWithText("Delivered Hello")
		.fetchSemanticsNodes().size == 1
}
rule.onNodeWithText("Delivered Hello").assertIsDisplayed()
```

The collection naturally represents zero matches. Do not catch every assertion in a retry loop. That can conceal an ambiguous selector or application exception.

The timeout bounds observation in elapsed time. It does not advance every subsystem. Verify that the producer can progress while the test waits. A blocked latch on the same thread needed by Compose cannot solve that dependency.

If an asynchronous subsystem must participate in all synchronized actions, implement Compose `IdlingResource`. Register before starting work, keep its idle query cheap and nonblocking, and unregister during cleanup. The canonical fixture does not validate a custom idling resource.

## Control Compose time

For ordinary final-state tests, leave `mainClock.autoAdvance` enabled. For a timed transition, disable it before starting the action. This test-method fragment assumes an existing `rule`, canonical `MessagePanel`, and the `PendingSender` declared above. Annotate the containing method with `@OptIn(ExperimentalCoroutinesApi::class)` for the scheduler API.

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import fixture.MessagePanel
import kotlinx.coroutines.ExperimentalCoroutinesApi

val sender = PendingSender()
rule.mainClock.autoAdvance = false
rule.setContent { MessagePanel(sender) }
rule.onNodeWithText("Message").performTextInput("Clock")
rule.mainClock.advanceTimeByFrame()
rule.onNodeWithText("Send").performClick()
rule.mainClock.scheduler.runCurrent()
rule.mainClock.advanceTimeByFrame()
rule.onNodeWithText("Still sending").assertDoesNotExist()
rule.mainClock.advanceTimeBy(1_200)
rule.onNodeWithText("Still sending").assertIsDisplayed()
rule.onNodeWithText("Sending").assertIsDisplayed()
```

The sender remains pending while the Compose-owned long-wait label appears. See the compiled `composeClockDoesNotCompleteSender` example for subsequent fake completion and the final receipt assertion.

Establish when the effect starts before calculating its deadline. `advanceTimeBy` normally rounds to frames. Work queued at a deadline can require `runCurrent()` or another frame.

Use `advanceTimeUntil` only for a condition that Compose time can change. Do not call synchronized semantics finders inside that clock predicate. Use a known state value there, or use `waitUntil` for semantics observation.

Keep independent coroutine schedulers explicit. A new `runTest` scope can introduce another scheduler. Its `advanceTimeBy` does not automatically advance the Compose rule's scheduler. Neither scheduler changes `Instant.now()` or supplies a fake response.

## Keep value assertions and custom matchers narrow

Use JUnit assertions for plain values. Read UI-owned mutable state through `runOnIdle` when appropriate. Do not invoke synchronized UI assertions from inside `runOnIdle` in the stable 1.12.1 environment.

For repeated semantics assertions, return a `SemanticsMatcher` rather than a helper that swallows failures. This illustrative declaration needs the UI test artifact:

```kotlin
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.SemanticsMatcher

fun hasUnreadCount(count: Int): SemanticsMatcher =
	SemanticsMatcher.expectValue(
		SemanticsProperties.StateDescription,
		"$count unread",
	)
```

Use it only if the product deliberately exposes that state description. Do not add test-only accessibility wording to make a matcher convenient.

## Handle failures without hiding them

JUnit 4 assertions normally stop at the first failure. Do not imitate soft assertions with `try/catch` and logs. For independent plain-value checks, JUnit's `ErrorCollector` can accumulate failures. For UI journeys, stop when a precondition fails so later actions do not produce misleading errors.

A test timeout, Compose idle timeout, `waitUntil` timeout, and Gradle worker timeout cover different boundaries. Increasing all of them hides the failing owner. Use a local bound with a reason when external work legitimately needs longer.

Anti-patterns include sleeping for two seconds, polling a mutating action, draining every looper, and treating `waitForIdle()` as network completion. Replace each with control or observation of the actual producer.

## Troubleshoot timeouts

| Symptom | Observation | Fix |
| --- | --- | --- |
| Pending forever | Fake is incomplete | Complete or fail that test's fake |
| Timer never starts | Effect remains queued | Start current scheduler work before advancing time |
| Assertion skips loading | Auto-advance or immediate fake completion | Hold external work or control the clock before the action |
| Idle never arrives | Recomposition loop or busy resource | Inspect producer and idle accounting |
| Wait ends but assertion fails | Presence differs from visibility or content | Keep the final precise assertion and inspect semantics |
| Works with v1 but not v2 | Immediate-effect assumption | Follow StandardTestDispatcher scheduling explicitly |

## Review checklist

- The final assertion checks the user's result.
- The test names every clock and asynchronous producer it controls.
- Pending state does not depend on a sleep.
- The wait predicate does not mutate application state.
- Cleanup cancels test-owned jobs and unregisters resources.
- A broken action would fail the behavior assertion.

## Related guides and sources

- [Canonical tests](../examples/FixtureUiTest.kt) contain complete fake and clock examples.
- [Clock control](../advanced/clock-control.md) covers time ownership in more detail.
- [Synchronization](https://developer.android.com/develop/ui/compose/testing/synchronization) documents idle and wait contracts.
- [v2 migration](https://developer.android.com/develop/ui/compose/testing/migrate-v2) describes scheduling changes. Its 1.13 configuration examples are not 1.12.1 APIs.
- [Evidence](../references/evidence.md) records the version boundary.
