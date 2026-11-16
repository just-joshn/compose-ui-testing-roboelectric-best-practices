# Test multi-user and collaboration behavior

## Table of contents

- [Choose the collaboration claim](#choose-the-collaboration-claim)
- [Create independent client owners](#create-independent-client-owners)
- [Drive a two-user exchange](#drive-a-two-user-exchange)
- [Test document changes and presence](#test-document-changes-and-presence)
- [Cover role-specific behavior](#cover-role-specific-behavior)
- [Schedule conflicts deliberately](#schedule-conflicts-deliberately)
- [Test delivery and reconnect states](#test-delivery-and-reconnect-states)
- [Isolate users and synchronize events](#isolate-users-and-synchronize-events)
- [Avoid collaboration shortcuts](#avoid-collaboration-shortcuts)
- [Troubleshoot](#troubleshoot)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the collaboration claim

Use this guide for messaging, shared documents, support workflows, presence, and role-dependent interactions. Robolectric can test independent client state owners in one JVM. It does not turn those owners into independently authenticated devices.

| Claim | Local arrangement | Integration requirement |
| --- | --- | --- |
| A sent message appears in the conversation | Real screen owner and controlled repository | None for the client contract |
| Two local screens react to delivered events | Independent owners and explicit test event bus | Real transport delivery |
| Stale save displays conflict recovery | Controlled versioned repository response | Server optimistic-lock enforcement |
| Viewer cannot edit in the UI | Viewer capabilities and real screen | Server rejects forged writes |
| Presence expires | Controlled event and time owner | Server presence and disconnect policy |
| Two devices converge on one document | Limited local event-sequence tests | Multi-client service and device scenario |

Use the [local Android setup](../references/setup.md). Do not introduce network access merely to make a UI test appear more realistic. Put the real transport claim in a separately named suite.

## Create independent client owners

Represent a client with explicit identity, session source, repository adapter, ViewModel or state owner, and coroutine lifetime. Do not change a global "current user" between actions. Both owners can capture that global and accidentally act as the same user.

A useful local arrangement has fresh Alice and Bob clients connected to a test-owned delivery controller. The controller accepts commands, records their identity and revision, and delivers events only when the test asks it to.

Keep the controller's limitations explicit. It is a script of client-observable service behavior, not a second implementation of the collaboration server.

For a single-screen claim, prefer one client plus injected remote events. Two visible screens are useful when the relationship between their client states is the actual claim.

For several visible clients under one host, use stable groups such as `alice-client` and `bob-client`. Each group must remain a meaningful ancestor in the selected semantics tree. A test tag does not create a separate authentication context.

## Drive a two-user exchange

Illustrative test-body fragment. It assumes project-defined `ChatClient`, `ControlledDelivery`, and `ChatRoute(client)` types. Each route owns its message entry and send orchestration. The delivery controller has explicit `deliverNextTo(userId)` behavior. This fragment is not fixture-compiled.

Required dependencies are Compose foundation, UI, runtime, Material components used by the routes, and the configured Compose UI test environment.

```kotlin
import androidx.compose.foundation.layout.Column
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasAnyAncestor
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput

val delivery = ControlledDelivery()
val alice = ChatClient(userId = "alice", delivery = delivery)
val bob = ChatClient(userId = "bob", delivery = delivery)
rule.setContent {
	Column {
		Column(Modifier.testTag("alice-client")) { ChatRoute(alice) }
		Column(Modifier.testTag("bob-client")) { ChatRoute(bob) }
	}
}
rule.onNode(hasText("Message") and hasAnyAncestor(hasTestTag("alice-client")))
	.performTextInput("Hi Bob")
rule.onNode(hasText("Send") and hasAnyAncestor(hasTestTag("alice-client")))
	.performClick()
rule.onNode(hasText("Sending") and hasAnyAncestor(hasTestTag("alice-client")))
	.assertIsDisplayed()
rule.runOnIdle { delivery.deliverNextTo("bob") }
rule.onNode(hasText("Alice: Hi Bob") and hasAnyAncestor(hasTestTag("bob-client")))
	.assertIsDisplayed()
```

The controller must distinguish delivery to Bob from acknowledgement to Alice. If the protocol does, acknowledge separately and assert Alice's **Sent** status only after that event.

Then drive Bob's reply through Bob's input, deliver it to Alice, and assert Alice's conversation. Verify that the sender identity is correct. A shared mutable list displayed by both routes cannot test independent delivery or acknowledgement.

Cancel both clients in cleanup, including on assertion failure. The app-specific `ChatClient` in this example must expose a test-owned lifetime or receive a scope that the test can cancel.

For an admin support workflow, use the same sequence. A member submits a ticket, the admin receives it, the admin replies, and the member sees the reply. Keep ticket identity explicit to catch replies routed to the wrong conversation.

## Test document changes and presence

For remote document edits, mount the real editor owner and deliver a remote revision. Assert the resulting editable text and the product's cursor or selection policy. Do not replace the UI state directly and call that collaboration.

Test local edits separately from incoming edits. Hold the local acknowledgement, deliver a concurrent remote revision, then release the acknowledgement in the order the protocol permits.

If the application uses operational transforms or a CRDT, test convergence and merge rules in algorithm-level tests with real implementations. Compose tests should cover a few meaningful client consequences, such as preserving a draft and showing conflict recovery.

Presence and cursor rendering have separate inputs. Deliver an event with user identity, document identity, position, and expiration policy. Assert the remote user's label and the relevant presence indicator. A Canvas cursor may require semantic alternatives or drawing tests rather than a text finder.

Test presence removal on disconnect or expiry using the actual time owner. Do not assume advancing Compose animation time expires a server-owned presence record.

A fake that immediately broadcasts every local edit cannot expose out-of-order, duplicate, delayed, or missing events. Configure those cases deliberately where the client promises to handle them.

## Cover role-specific behavior

Choose a table from the real capability model:

| Role | View | Edit | Delete |
| --- | --- | --- | --- |
| Viewer | Visible | Disabled or absent according to product | Absent |
| Editor | Visible | Enabled | Absent unless explicitly permitted |
| Administrator | Visible | Enabled | Enabled where permitted |

Use fresh state for every row of the matrix. Assert the actual product policy for disabled versus absent controls. Those are not interchangeable observations.

For a denied destination, navigate through the real route entry and assert **Access denied** or sign-in according to the application. Mounting the denial screen directly proves no route guard.

For a permission change while editing, deliver revoked capabilities, attempt the supported next action, and assert that unsaved content is handled according to policy. A server `Forbidden` result should also have a client test even when the UI initially believed editing was allowed.

Never label hidden controls as backend authorization proof. Use a service integration test that authenticates a viewer and attempts the forbidden operation directly.

## Schedule conflicts deliberately

Two calls to `performClick()` run sequentially on the test thread. They do not create a meaningful simultaneous network race. Control command acceptance and response order instead.

For optimistic locking:

1. Seed both independent owners with record `invoice-7`, revision 4.
2. Enter different values through each client's UI.
3. Submit Alice's save and hold its response.
4. Submit Bob's save and hold its response.
5. Accept Alice's command with revision 5.
6. Reject Bob's revision-4 command with a conflict carrying revision 5.
7. Assert Alice sees **Saved**.
8. Assert Bob sees **Someone else modified this** and a recovery action.
9. Drive recovery and assert the server's accepted value appears.

The fake schedules one permitted outcome. A separate reversed-order case catches client assumptions about which user wins.

Assert draft retention if the product promises it. Do not accept either result by catching errors. Each configured schedule must have a precise expected outcome.

For duplicate submit, hold the first result and verify the UI's pending policy prevents or safely handles a second submission. Idempotency key construction belongs in repository or transport contract tests.

## Test delivery and reconnect states

Cover connection loss without conflating it with message rejection. The app may retain an unsent message and display **Reconnecting**, while the server may already have accepted the command.

Deliver a disconnect, enter or send according to supported offline policy, reconnect, and deliver the next revision or acknowledgement. Assert no duplicate visible message when the same event is replayed if deduplication is part of the client contract.

For out-of-order events, specify the protocol sequence or revision. Deliver revision 6 before revision 5 and assert the documented behavior. Do not assume all systems guarantee the same ordering.

Use separate tests for permanent rejection and transient disconnect. A fake success after every reconnect cannot test retry limits or recovery UI.

Real socket handshake, TLS, authentication, server fan-out, and reconnect behavior belong in transport and service integration tests. Device coverage verifies lifecycle changes such as background and foreground transitions.

## Isolate users and synchronize events

Create fresh sessions, owners, event controllers, IDs, and pending responses per test. Share only the test-owned controller when the scenario requires collaboration.

Install subscriptions before delivering events. A zero-replay event stream can lose an event emitted before collection begins. Use an explicit subscriber-ready signal or the relevant scheduler step, not a sleep.

Release commands or events through the controller, then let Compose synchronize. For independent executors, use a bounded wait on observable UI or a correctly registered idling resource.

Do not mark the entire connection permanently busy. A live connection can be idle while still open. Otherwise every synchronized assertion can time out.

Cancel client scopes, close channels, unregister listeners, and shut down executors in teardown. No client should be able to deliver an event into a later test.

## Avoid collaboration shortcuts

Bad practice is to mount both users with the same mutable ViewModel and assert both labels changed. That tests two renderings of one owner, not independent client behavior.

Correct it by giving each client its own owner and explicit delivery events. For a rendering-only test, keep one owner and name the narrower claim honestly.

Another anti-pattern launches two test-thread clicks in parallel and treats any result as proof of race handling. Replace it with held commands and enumerated completion orders. Exercise the actual server concurrency policy separately.

## Troubleshoot

| Symptom | Observation | Correction |
| --- | --- | --- |
| Alice and Bob use the same identity | Session references and captured globals | Independent immutable identities and owners |
| Remote event is lost | Collector registration and replay policy | Establish subscription before emission |
| Send matches twice | Client groups in semantics | Scope to the intended client |
| Every assertion times out | Connection idling status | Idle means no pending transition, not closed socket |
| Conflict test always succeeds | Fake ignores expected revision | Match revision and return configured conflict |
| Later test receives old events | Listener and scope ownership | Cancel and unregister all clients |

## Review checklist

- Are client identity, state, and lifetime independent?
- Is sharing limited to an explicit collaboration boundary?
- Are commands, acknowledgements, and remote events distinct where the protocol requires it?
- Are conflict schedules and expected outcomes deterministic?
- Do tests assert recipient UI and important sender status?
- Are server authorization and real-time transport claims verified separately?

## Related guides and sources

- [Multiple roots](multiple-roots.md), [network fakes](network-fakes.md), and [authentication](authentication.md).
- [Reactive streams](../android-apis/reactive-streams.md) and [repository contracts](../testing-patterns/repository-contracts.md).
- [Android data layer](https://developer.android.com/topic/architecture/data-layer) describes repository ownership.
- [Android coroutine testing](https://developer.android.com/kotlin/coroutines/test) describes explicit test schedulers.
- [Compose synchronization](https://developer.android.com/develop/ui/compose/testing/synchronization) describes local UI synchronization.
- [Robolectric best practices](https://robolectric.org/best-practices/) describes cleanup limits.
