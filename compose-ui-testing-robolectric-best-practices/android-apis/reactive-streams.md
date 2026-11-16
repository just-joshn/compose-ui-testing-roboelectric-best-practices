# Test reactive streams and real-time UI

## Table of contents

- [Choose the stream boundary](#choose-the-stream-boundary)
- [Render controlled stream state](#render-controlled-stream-state)
- [Test incoming and outgoing messages](#test-incoming-and-outgoing-messages)
- [Test ordered updates and conflation](#test-ordered-updates-and-conflation)
- [Test reconnect and recovery](#test-reconnect-and-recovery)
- [Test lifecycle and cancellation](#test-lifecycle-and-cancellation)
- [Separate transport contracts](#separate-transport-contracts)
- [Synchronize stream work](#synchronize-stream-work)
- [Avoid stream-test shortcuts](#avoid-stream-test-shortcuts)
- [Troubleshoot failures](#troubleshoot-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the stream boundary

Use this guide for Flow-backed screens, live chat, stock updates, notifications, collaborative presence, and connection status. A Flow fake controls what the application observes. It does not emulate WebSocket framing, server-sent-event parsing, or real network reconnect behavior.

| Goal | Test | Boundary |
| --- | --- | --- |
| Latest quote appears | Compose UI test | Controlled `StateFlow` of screen state |
| Incoming chat becomes a visible message | Screen or ViewModel integration test | Controlled repository event stream |
| Send shows pending then acknowledgement | UI test with held send result | Sender plus observed message state |
| Event ordering and deduplication | Repository or reducer unit test | Ordered domain events |
| WebSocket frames serialize correctly | Transport contract test | Real client and controlled server |
| SSE resumes with the right event ID | Transport integration test | Real parser and reconnect policy |
| Live multi-user collaboration | Service integration test | Multiple real sessions |

State and events have different contracts. `StateFlow` represents the latest state and conflates equal values. `SharedFlow` replay and buffer settings determine which events a subscriber receives. Choose deliberately rather than using whichever fake makes the test pass.

## Render controlled stream state

A state-rendering test supplies immutable state and verifies the visible result. It is useful for connection indicators, quote formatting, and empty states. It does not prove how a ViewModel creates those states.

Illustrative complete test. It needs the hosted Robolectric Compose setup, Material3, Compose UI test JUnit4 1.12.1, coroutines core, and JUnit 4. It is not compiled by the canonical fixture.

```kotlin
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

data class QuoteState(val price: String, val connection: String)

@Composable
private fun QuotePanel(quotes: StateFlow<QuoteState>) {
	val state by quotes.collectAsState()
	Column {
		Text(state.price)
		Text(state.connection)
	}
}

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class QuotePanelTest {
	@get:Rule val rule = createComposeRule()

	@Test fun rendersLatestQuoteAndConnection() {
		val quotes = MutableStateFlow(QuoteState("$149.00", "Connected"))
		rule.setContent { QuotePanel(quotes) }
		rule.onNodeWithText("$149.00").assertIsDisplayed()
		rule.runOnIdle {
			quotes.value = QuoteState("$150.25", "Connected")
		}
		rule.onNodeWithText("$150.25").assertIsDisplayed()
		rule.onNodeWithText("$149.00").assertDoesNotExist()
		rule.runOnIdle {
			quotes.value = QuoteState("$150.25", "Reconnecting")
		}
		rule.onNodeWithText("Reconnecting").assertIsDisplayed()
		rule.onNodeWithText("$150.25").assertIsDisplayed()
	}
}
```

The final assertion checks that disconnecting preserves the last known price in this example's contract. Change that expectation if the product deliberately hides stale data.

Production Android screens commonly use `collectAsStateWithLifecycle` from `androidx.lifecycle:lifecycle-runtime-compose`. Keep the production collection behavior in screen-integration tests. The smaller example uses `collectAsState` to isolate rendering and does not establish lifecycle gating.

## Test incoming and outgoing messages

Install the fake before mounting the screen. A non-replayed event emitted before collection can disappear. For a real-time screen, expose a deterministic subscription-ready signal in the fake or wait for an observable ready state before emitting an event.

For an incoming message:

1. Start from a known conversation and connection state.
2. Confirm the screen is subscribed.
3. Emit a domain message with a stable message ID and sender.
4. Assert the message text and sender in the correct conversation.
5. Emit a message for another conversation and assert it does not appear.

Use meaningful message identity to scope duplicate text. A list can contain several **Hello** messages. Selecting the first text match can exercise the wrong sender or conversation.

For outgoing messages, hold acknowledgement separately from submission. Click **Send**, assert the pending message, complete the controlled sender, then assert the delivered state. Inspect the sent payload as a supplementary contract assertion. A payload-only check can pass when the UI never leaves pending.

Use the canonical [held sender test](../examples/FixtureUiTest.kt) for this synchronization pattern. It proves a fake-backed UI transition, not a live socket.

For a live notification, emit an app-facing event with a specific order ID, then assert the visible notification text and the destination after opening it. Do not infer user-visible delivery from a fake event counter.

## Test ordered updates and conflation

Do not expect the UI to render every intermediate `StateFlow` value. A rapid sequence of prices may result in only the latest price being drawn. Test the latest-state contract in Compose and the ordered reducer contract in a unit test.

If the product must acknowledge each event, model events or durable records rather than depending on transient rendering. Test that no event is lost at the repository boundary.

| Scenario | Required observation |
| --- | --- |
| Same message delivered twice | One visible message with that identity |
| Older quote arrives after a newer quote | Newer version remains visible if version ordering is required |
| Several updates before recomposition | Final state matches the latest accepted update |
| Collaborator leaves | Their presence label or cursor disappears |
| Update for another document | Current document remains unchanged |
| Malformed payload | Transport reports a controlled failure without crashing the screen |

For collaborative editing, inject participant identity, document identity, and position through the repository. Assert participant labels and intended document state locally. Real conflict resolution, ordering across clients, and access enforcement need multi-session service tests.

For SSE-backed counters, provide domain updates locally and assert the final count. Test `data:` parsing, blank-line framing, event IDs, and reconnect headers in transport tests. A prebuilt list of domain events bypasses those protocol rules.

## Test reconnect and recovery

Model connection state independently from content. A reconnecting banner with an empty list can hide accidental loss of the last known content.

Use this sequence for a screen-level test:

1. Publish connected state and one known record.
2. Publish connection loss.
3. Assert the designed reconnecting or offline indication.
4. Assert whether the known record remains according to the product contract.
5. Publish reconnected state and a new record.
6. Assert the banner clears and the new record appears exactly once.

Test explicit retry if the UI provides it. Hold the fake reconnect result so a transient pending indication remains observable. Do not let an immediate success fake skip the state the test intends to inspect.

Backoff and jitter belong to connection-policy tests. Inject the retry time source and deterministic randomness there. Advance the retry policy's coroutine scheduler, not an unrelated Compose clock.

Test authentication expiry separately from transient disconnects. Repeated reconnect attempts must not substitute for the application's reauthentication behavior.

## Test lifecycle and cancellation

A stream subscription can belong to a composition, a lifecycle, a ViewModel, or a repository. Leaving a composition does not necessarily stop a ViewModel-owned shared stream immediately.

State the owner before asserting cancellation. If the repository uses `stateIn` with a stop timeout, subscriber disappearance and upstream cancellation happen at different times. Test the timeout on its owning scheduler in a repository or ViewModel test.

For a screen-owned subscription, remove the screen through a real navigation action or a controlled host state. Assert the next screen. Supplement with fake subscription accounting if listener cleanup is part of the contract.

Deliver an old result after the screen leaves and verify that it cannot appear in the new conversation. Test one subscription on re-entry when duplicate listeners would duplicate messages.

Do not call a cold flow collector in the test and accidentally keep production sharing active while trying to prove that the UI unsubscribed.

## Separate transport contracts

Use a controlled server with the production WebSocket or SSE client for protocol tests. Register listeners before connecting. Wait for a specific connection or handshake condition, not a fixed interval.

Verify serialization, incoming parsing, connection closure, error propagation, and reconnect behavior. Close the client and server in cleanup and use an allocated port rather than a shared hard-coded port.

Local UI fakes do not prove TLS, proxy behavior, authentication, server routing, or delivery ordering. Keep a smaller integration suite against the actual service contract for those claims.

## Synchronize stream work

Compose actions and assertions synchronize Compose work. They do not retry arbitrary business state until a network event arrives.

For controlled state updates, publish the value on the expected thread, then assert through semantics. For separately scheduled collectors, run their scheduler's current tasks before synchronizing Compose. For external work, use a bounded observable wait.

Do not place a suspending `emit` in `runOnIdle` or block the test thread while a collector needs Compose progress. Use `tryEmit` only when the fake checks its result and its buffering contract permits delivery. A successful `tryEmit` with no subscribers does not necessarily mean an event was retained.

Create fresh flows, replay buffers, jobs, channels, and fake connection sessions per test. Cancel owned scopes and close clients. Do not leave an infinite receive loop on a real executor after the test finishes.

## Avoid stream-test shortcuts

| Anti-pattern | Failure mechanism | Correction |
| --- | --- | --- |
| Emit before subscription to a zero-replay flow | The event can be lost | Establish readiness before emitting |
| Mutate a list inside the same state object | Equality and observation may suppress updates | Publish a new immutable state value |
| Assert only the fake's sent frame | The visible message may never update | Assert pending and acknowledged UI |
| Advance Compose time for real reconnect | The client uses another scheduler or wall time | Control the retry policy at its boundary |
| Use a live server in every UI test | Tests depend on service timing and availability | Use local fakes plus separate transport tests |
| Ignore disconnect content | A banner can pass while all data disappears | Assert the content retention contract |

## Troubleshoot failures

| Symptom | Observe | Fix |
| --- | --- | --- |
| First event is missing | Subscriber count and replay policy | Subscribe before emit or use a state contract |
| Latest value never appears | Equality, collector lifecycle, scheduler | Publish a distinct state and progress the actual collector |
| Intermediate value is skipped | Whether the source is conflated state | Assert final state or test ordered events below UI |
| Duplicate messages on re-entry | Active subscriptions and deduplication IDs | Remove old listeners and test domain deduplication |
| UI hangs on disconnect | Busy idling resource or infinite work | Do not register a permanently connected stream as busy |
| Test passes only alone | Replay buffer, shared scope, or client singleton | Create a fresh session and cancel owned work |

## Review checklist

- Does the test distinguish state from events?
- Is subscription readiness established before a non-replayed event?
- Are message and conversation identities explicit?
- Does disconnect coverage include content and recovery?
- Is cancellation asserted against the correct owner?
- Are protocol and service claims tested outside the UI fake?

## Related guides and sources

- [State and ViewModels](../frameworks/state-viewmodels.md) covers state production.
- [Multi-user testing](../advanced/multi-user.md) covers collaboration boundaries.
- [Background work](background-work.md) covers durable queues.
- [Android Flow testing](https://developer.android.com/kotlin/flow/test) documents fakes and collection in tests.
- [StateFlow and SharedFlow](https://developer.android.com/kotlin/flow/stateflow-and-sharedflow) describes state, replay, and lifecycle collection.
- [Compose state](https://developer.android.com/develop/ui/compose/state) documents state observation.
- [Compose synchronization](https://developer.android.com/develop/ui/compose/testing/synchronization) documents clock and external-work boundaries.
