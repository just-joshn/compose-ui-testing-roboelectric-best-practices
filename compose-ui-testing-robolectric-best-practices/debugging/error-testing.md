# Test recoverable errors, loading, and edge cases

Use this guide when a screen must explain a failed operation and let the user recover. It covers local Compose behavior with controlled dependencies. It does not prove real HTTP failures, Android connectivity changes, or backend validation.

## Table of contents

- [Choose a failure at the correct boundary](#choose-a-failure-at-the-correct-boundary)
- [Model recoverable UI states](#model-recoverable-ui-states)
- [Test pending work and retry](#test-pending-work-and-retry)
- [Cover distinct error contracts](#cover-distinct-error-contracts)
- [Test offline and cached behavior](#test-offline-and-cached-behavior)
- [Test validation and correction](#test-validation-and-correction)
- [Keep cancellation and isolation explicit](#keep-cancellation-and-isolation-explicit)
- [Avoid false error coverage](#avoid-false-error-coverage)
- [Troubleshoot error tests](#troubleshoot-error-tests)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose a failure at the correct boundary

| Failure | Local UI stimulus | Separate test needed |
| --- | --- | --- |
| Service unavailable | Repository's defined unavailable result | HTTP status mapping and real service behavior |
| Connection failure | Repository failure or thrown transport exception the state owner handles | Actual transport adapter |
| Request timeout | Defined timeout result, or actual timeout policy under its scheduler | Client timeout configuration |
| Unauthorized session | Session-expired outcome | Token refresh and server authorization |
| Forbidden operation | Permission-denied outcome | Server enforcement |
| Missing item | Not-found outcome | API contract |
| Malformed response | Protocol-error domain result | Serializer and adapter mapping |
| Mid-transfer failure | Progress followed by defined failure | Streaming transport integration |
| Invalid field | User input through the real form | Server validation separately |
| Programmer defect during composition | Let the test fail with original exception | Do not pretend a generic UI error boundary catches it |

Do not test every numeric HTTP status by rendering the same generic banner. Group equivalent domain outcomes for UI coverage. Test the status-to-outcome mapping at the adapter layer.

Compose has no direct equivalent of React error boundaries. Represent recoverable failures as state produced by the screen's owner. Do not wrap arbitrary composable calls in exception handling or swallow programming defects.

## Model recoverable UI states

The data shape below separates idle, loading, content, and recoverable I/O failure. The loader is a suspend boundary. Cancellation remains cancellation.

This complete illustrative UI is not part of the compiled canonical fixture. It needs Compose runtime, foundation, Material3, and coroutines. A production test should mount the real screen rather than copy this implementation into its test.

```kotlin
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import java.io.IOException
import kotlinx.coroutines.launch

sealed interface LoadState {
	data object Idle : LoadState
	data object Loading : LoadState
	data class Content(val title: String) : LoadState
	data object Unavailable : LoadState
}

fun interface TitleLoader {
	suspend fun load(): String
}

@Composable
fun RecoverableTitle(loader: TitleLoader) {
	var state by remember { mutableStateOf<LoadState>(LoadState.Idle) }
	val scope = rememberCoroutineScope()
	Column {
		Button(
			enabled = state != LoadState.Loading,
			onClick = {
				state = LoadState.Loading
				scope.launch {
					state = try {
						LoadState.Content(loader.load())
					} catch (error: IOException) {
						LoadState.Unavailable
					}
				}
			},
		) {
			Text(if (state == LoadState.Unavailable) "Retry" else "Load")
		}
		when (val current = state) {
			LoadState.Idle -> Text("Ready")
			LoadState.Loading -> Text("Loading")
			LoadState.Unavailable -> Text("Could not load title")
			is LoadState.Content -> Text(current.title)
		}
	}
}
```

Only `IOException` maps to unavailable here. In a real application, prefer the repository's explicit domain failures where available. Do not catch `Throwable` and show success or a generic fallback. That would also hide cancellation and programmer defects.

Keep the current content visible during refresh if the product contract requires stale data. That contract needs a richer state shape, such as content plus refresh status. Do not force every feature into the sample's mutually exclusive states.

## Test pending work and retry

A two-request fake can hold the first operation, fail it, and hold the retry independently. It gives the test a reliable loading interval without a delay.

This complete illustrative test file depends on the preceding UI types, Compose UI 1.12.1, Robolectric, JUnit 4, Android resources, and the declared default host. Put it in Android `src/test`.

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import java.io.IOException
import kotlinx.coroutines.CompletableDeferred
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.LooperMode

class TwoAttemptLoader : TitleLoader {
	val attempts = listOf(
		CompletableDeferred<String>(),
		CompletableDeferred<String>(),
	)
	var calls = 0
		private set

	override suspend fun load(): String {
		check(calls < attempts.size) { "Unexpected extra load" }
		val pending = attempts[calls]
		calls += 1
		return pending.await()
	}
}

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
@LooperMode(LooperMode.Mode.PAUSED)
class RecoverableTitleTest {
	@get:Rule val compose = createComposeRule()

	@Test fun retryReplacesErrorWithContent() {
		val loader = TwoAttemptLoader()
		compose.setContent { RecoverableTitle(loader) }

		compose.onNodeWithText("Load").performClick()
		compose.onNodeWithText("Loading").assertIsDisplayed()
		compose.onNodeWithText("Load").assertIsNotEnabled()
		compose.runOnIdle {
			assertEquals(1, loader.calls)
			check(loader.attempts[0].completeExceptionally(IOException("offline")))
		}

		compose.onNodeWithText("Could not load title").assertIsDisplayed()
		compose.onNodeWithText("Loading").assertDoesNotExist()
		compose.onNodeWithText("Retry").performClick()
		compose.onNodeWithText("Loading").assertIsDisplayed()
		compose.onNodeWithText("Could not load title").assertDoesNotExist()
		compose.runOnIdle {
			assertEquals(2, loader.calls)
			check(loader.attempts[1].complete("Inventory overview"))
		}

		compose.onNodeWithText("Inventory overview").assertIsDisplayed()
		compose.onNodeWithText("Loading").assertDoesNotExist()
		compose.onNodeWithText("Could not load title").assertDoesNotExist()
	}
}
```

The call count supplements the visible result. If the UI never renders `Inventory overview`, this test fails even when two repository calls occurred.

Do not import `assertDoesNotExist` as a top-level extension. It is a member of the interaction returned by the finder.

The canonical [message tests](../examples/FixtureUiTest.kt) compile the same controlled-pending technique for success and cancellation. They do not compile this new retry example, and canonical `MessagePanel` itself has no error handling.

## Cover distinct error contracts

Add cases for behavior that changes what the user can do:

| State | Observable assertions |
| --- | --- |
| Retryable failure | Safe message, enabled Retry, no stale spinner |
| Expired session | Sign-in action or route, no sensitive stale content |
| Forbidden action | Permission explanation, no inappropriate Retry loop |
| Not found | Missing-item message and route back |
| Empty success | Empty-state explanation and create action |
| Failed refresh with cached content | Existing rows remain, refresh error appears |
| Transfer fails after progress | Progress ends, failure appears, no false completion receipt |
| Timeout | Timeout message after application deadline, no indefinite loading |

For empty success, return an empty collection from the repository and assert the empty-state UI. Do not use a connection failure to simulate an empty result.

For timeout policy, distinguish testing rendering from testing the timer. A fake timeout result tests the former. To test an actual timeout, hold the operation pending and advance the scheduler that owns the production timeout. An unrelated Compose clock cannot trigger a timeout in an injected IO dispatcher.

For mid-transfer failure, emit a concrete progress event before the error. Assert progress is visible while pending and the completed receipt never appears after failure. Keep the real stream parser in an adapter test if parsing is part of the claim.

## Test offline and cached behavior

A local fake can model an unavailable repository and a connectivity signal. It cannot turn the host or emulator's network off, prove DNS behavior, or verify Android's real connectivity callbacks.

Use an explicit scenario:

1. Load a known item and verify it is displayed.
2. Emit offline state through the application's injected connectivity boundary.
3. Trigger Refresh through the UI.
4. Fail the refresh with the defined unavailable result.
5. Assert the offline indicator and the intended cached-content behavior.
6. Emit online state, retry, and return different content.
7. Assert the new content and removal of the offline indicator.

Do not infer internet reachability from a connectivity flag alone. A connected network can still return transport failures. Cover those outcomes through the repository boundary.

Use device tests for real connectivity transitions and a controlled service for retry integration. Use repository/database tests for cache persistence and reconciliation. A UI fake that remembers rows does not prove durable storage.

## Test validation and correction

Distinguish client validation from a server rejection. The client can reject an empty email before calling the repository. A server can reject a well-formed but already registered email.

An illustrative form test body requires the real form, a recording registration fake, `onNodeWithText`, `performClick`, `performTextReplacement`, and `assertIsDisplayed` from Compose test APIs:

```kotlin
compose.onNodeWithText("Register").performClick()
compose.onNodeWithText("Email is required").assertIsDisplayed()
compose.runOnIdle { assertEquals(0, registration.calls) }

compose.onNodeWithText("Email").performTextReplacement("reader@example.test")
compose.onNodeWithText("Register").performClick()
```

Complete the registration fake with its field-error result and assert `Email already registered` near the intended field. Then correct the input and exercise a successful submission if recovery is the claim.

Do not put invented `registration.calls` or UI labels into a consuming project unchanged. These are surrounding contracts the test must supply. Scope repeated error labels to the intended field or form group.

If validation runs on blur, move focus through the actual supported interaction that triggers it. Do not mutate a `validated` flag from the test and call that user validation coverage.

## Keep cancellation and isolation explicit

Create a fresh fake and pending requests for every test. A retry needs a fresh pending request, not a deferred that has already failed.

Let the rule dispose the composition. Composition-owned work must cancel on disposal. Test-owned scopes, executors, and external streams need their own cleanup. Assert that a late result from a disposed screen does not appear in a new screen if stale delivery is a risk.

Do not register held work as globally busy while asserting its pending UI. Keep fake release explicit, then use Compose synchronization for the resulting state. Use bounded `waitUntil` for external progress only when necessary and follow it with the final UI assertion.

## Avoid false error coverage

Faulty illustrative test:

```kotlin
compose.setContent { ErrorBanner("Could not load title") }
compose.onNodeWithText("Could not load title").assertIsDisplayed()
```

This is a valid banner-rendering test. It does not prove that a repository failure reaches the banner, and it does not prove Retry works.

Correct the recovery claim by pressing Load, failing its pending request, pressing Retry, completing the new request, and asserting content. The worked test above follows that path.

| Anti-pattern | Failure mechanism | Correction |
| --- | --- | --- |
| Sleep before checking loading | Loading may finish before observation | Hold a controlled completion |
| Never complete a fake to test timeout rendering | Test hangs without exercising timeout policy | Use a timeout result or advance the owning scheduler |
| Catch every throwable | Cancellation and bugs become generic UI errors | Map defined failures only |
| Assert only an error log | User may still see a spinner forever | Assert error UI and recovery actions |
| Assert error exists after retry only | Stale error can survive a successful result | Assert its removal and the new content |

## Troubleshoot error tests

| Symptom | Observe | Fix |
| --- | --- | --- |
| Expected error crashes the test | Is this failure part of the state owner's handled contract? | Inject a defined recoverable failure or fix real mapping |
| Spinner vanishes before assertion | Fake completed before test held it | Create fresh pending work |
| Retry instantly fails again | Same failed deferred reused | Allocate one pending result per request |
| Error remains after success | State owner retained stale error | Fix transition and assert error removal |
| Timeout never occurs | Wrong scheduler advanced | Advance the scheduler that owns the timeout |
| Cancellation shows an error | Broad exception mapping catches cancellation | Preserve cancellation semantics |

## Review checklist

- Does each case name a distinct user-visible contract?
- Does the test trigger the real action-to-failure path?
- Is loading observable without a sleep?
- Does retry use a new request and replace the error?
- Are cancellation and programmer defects kept distinct from recoverable failures?
- Are transport, connectivity, validation, and persistence claims tested at their own layers?
- Does cleanup isolate later tests from pending work?

## Related guides and sources

- [When to fake](../architecture/when-to-fake.md) chooses the failure boundary.
- [Network fakes](../advanced/network-fakes.md) controls asynchronous responses.
- [Forms and validation](../testing-patterns/forms-validation.md) covers field interactions.
- [Background work](../android-apis/background-work.md) covers durable work boundaries.
- [Compose state](https://developer.android.com/develop/ui/compose/state) describes observable UI state.
- [Compose side effects](https://developer.android.com/develop/ui/compose/side-effects) describes composition-owned coroutine lifecycles.
- [Compose synchronization](https://developer.android.com/develop/ui/compose/testing/synchronization) describes test work ownership.
