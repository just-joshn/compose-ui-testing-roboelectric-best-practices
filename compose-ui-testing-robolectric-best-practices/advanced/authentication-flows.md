# Test verification, recovery, expiry, and logout

## Table of contents

- [Choose a flow and its boundary](#choose-a-flow-and-its-boundary)
- [Verify an email address](#verify-an-email-address)
- [Reset a password](#reset-a-password)
- [Warn about session expiry](#warn-about-session-expiry)
- [Restore remembered sessions](#restore-remembered-sessions)
- [Log out and reject late results](#log-out-and-reject-late-results)
- [Synchronize and isolate the flow](#synchronize-and-isolate-the-flow)
- [Avoid shortcut assertions](#avoid-shortcut-assertions)
- [Troubleshoot](#troubleshoot)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose a flow and its boundary

Use this guide when authentication spans several screens or events. Run the local client tests in Android `src/test` with the [Robolectric host setup](../references/setup.md). Start with [authentication](authentication.md) for login and seeded sessions.

A recovery test has several owners. The app owns forms and navigation. A backend owns token issuance and invalidation. Email and SMS providers own delivery. Android owns verified links and activity routing. Assign assertions accordingly.

| Flow | Local controlled input | Local observable result | Integration handoff |
| --- | --- | --- | --- |
| Email verification | Registration result and app callback | Inbox prompt, then verified screen | Delivered message and verified App Link |
| Password reset | Reset-link token and repository response | Validation, pending, success, or expiry UI | Old password rejected, new password accepted |
| Session expiry | Application time and session result | Warning, extension, then sign-in if expired | Server token rejection |
| Remember me | Real test-owned session store | Restoration by a new owner | Process restart and secure storage behavior |
| Logout everywhere | Revocation result | Local session cleared and protected UI absent | Other authenticated clients revoked |

Use synthetic tokens such as `reset-alex-1` only in fakes. Do not expose production verification tokens in API responses to make UI tests convenient.

## Verify an email address

Keep registration and verification as separate transitions. Registration success usually displays **Check your inbox**. It does not mean the account is verified.

Illustrative test-body fragment. It assumes a v2 Compose `rule`, a real `RegistrationRoute(repository, links)` composable, a controlled repository with typed results, and an app-owned `links.deliverVerification(token)` entry point. These project-specific types are not fixture APIs. Imports for actions and assertions are shown.

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput

val repository = ControlledRegistrationRepository()
val links = TestAuthLinks()
rule.setContent { RegistrationRoute(repository, links) }
rule.onNodeWithText("Email").performTextInput("alex@example.test")
rule.onNodeWithText("Password").performTextInput("test-only-password")
rule.onNodeWithText("Create account").performClick()
rule.runOnIdle { repository.registrationSent() }
rule.onNodeWithText("Check your inbox").assertIsDisplayed()
rule.onNodeWithText("Email confirmed").assertDoesNotExist()
rule.runOnIdle { links.deliverVerification("verify-alex-1") }
rule.onNodeWithText("Verifying email").assertIsDisplayed()
rule.runOnIdle { repository.verificationAccepted("verify-alex-1") }
rule.onNodeWithText("Email confirmed").assertIsDisplayed()
```

The fake must verify that the submitted token matches its configured case. A fake that returns success for every token cannot exercise invalid-token handling.

Add separate tests for malformed input rejected before the repository, expired token, already-used token, and verification rejected by the service. Assert the retry or resend action when supported.

For resend, hold the request pending and click again only if the UI allows it. Check duplicate submission policy through visible enabled state and the boundary request record. If the product has a cooldown, control its scheduler rather than waiting in real time.

Test the real URI parser separately with scheme, host, path, missing token, duplicated parameters, and invalid encoding. Delivering a token directly to the route proves no URI parsing. Launching a Robolectric activity with an intent can test local intent handling, but not Android's domain verification or email-app behavior.

For delivery integration, provision a private test inbox, correlate a unique registration attempt, poll with a deadline, parse the expected link, and fail if no matching message exists. Do not select the newest message from a shared inbox.

## Reset a password

Start anonymous. Submit an email through the recovery screen and assert the product's non-enumerating acknowledgement. Do not change the expected copy to reveal whether an account exists.

Use this sequence for the local success path:

1. Enter the email and request a reset link.
2. Complete the request and assert **Reset email sent**.
3. Deliver a synthetic link through the app's callback entry point.
4. Enter a new password and confirmation.
5. Submit and assert a pending state.
6. Complete the reset result and assert **Password updated**.
7. Follow the app's sign-in action and assert the login screen.

A reset result does not establish that a real password changed. Run a service integration test that logs in with the new password, rejects the old one, and verifies token reuse is rejected.

| Case | Setup | Expected local observation |
| --- | --- | --- |
| Weak password | Valid token, invalid password | Field error, no reset request |
| Mismatched confirmation | Valid token, two different values | Confirmation error |
| Expired link | Repository returns expiry | Request-new-link action |
| Used token | Repository returns already used | No success screen |
| Network failure | Typed retryable failure | Values retained according to policy, retry available |
| Back while pending | Controlled request still suspended | Navigation remains stable after a late result |

Scope repeated **Password** and **Confirm password** labels exactly. Do not use substring matching that finds both fields. Inspect merged semantics when editable text and label share a node.

## Warn about session expiry

Treat wall time and the timer that schedules checks as different dependencies. Advancing `mainClock` does not change `Instant.now()`.

For example, an app session expires at a fixed instant and a coroutine checks every minute. Install the fake clock before constructing the session owner. Start its checker, advance the owned scheduler, and update the application clock to the intended instant.

Test the boundary on both sides. Before the warning threshold, no warning exists. At the warning threshold, **Stay signed in** appears. After expiry, protected content disappears and sign-in is available.

For extension, keep the refresh response pending after clicking **Stay signed in**. Assert **Extending session** if the product displays it. Complete a new expiry result and assert that the warning disappears while the protected screen remains usable.

Also reject extension and assert sign-in. A call-count assertion such as `refreshCalls == 1` cannot replace the visible session result.

Use [clock control](clock-control.md) to choose the right scheduler. Keep timer behavior tests separate from server-side expiry enforcement.

## Restore remembered sessions

"Remember me" is an application policy, not a browser cookie category in Compose.

For a persistent-session test, use the real session store against a test-owned file or preferences name. Sign in through the owner that writes that store. Close the owner. Construct a new owner from the same store and assert its restored state through the screen.

For session-only login, reconstruct from the persisted store without copying in-memory session state. Assert anonymous behavior after restoration. If the product intentionally persists all sessions, do not invent a session-only policy for the test.

Do not call `setContent` twice. If one test needs a new owner within a single rule host, switch the owner through a keyed subtree and document that the test exercises reconstruction, not process death. Prefer repository-level persistence tests plus one UI restoration case.

Activity recreation has a different purpose. It tests configuration and saved-state behavior. Process restart and platform-backed secure storage need separate device coverage. Disposing a composable is neither activity recreation nor process death.

## Log out and reject late results

Drive logout through the account menu and confirmation when present. Assert the sign-in screen, absence of sensitive content, and rejection of subsequent protected navigation.

Supplement UI assertions with store checks when clearing persisted credentials is part of the logout contract. Do not search arbitrary preference names for strings containing "token". Query the real session store's public read contract.

Cover this late-result sequence:

1. Start a protected request or refresh and hold it pending.
2. Perform logout.
3. Assert anonymous UI.
4. Complete the older request with a successful authenticated result.
5. Assert that private content does not reappear.

For **Sign out everywhere**, verify confirmation and the client result separately from remote revocation. A fake `revokeAll()` response can prove local transition to anonymous. It cannot prove another device lost authorization.

The integration case needs two independently authenticated clients. Revoke from the first, then make a protected request from the second. Check the documented revocation timing with bounded observation, not a fixed sleep.

## Synchronize and isolate the flow

Create fresh token fixtures, session stores, fakes, and deferred results per test. Install callbacks and DI replacements before the relevant screen or activity starts. Cancel pending jobs and remove listeners in teardown.

Use a controllable fake to preserve intermediate states. A busy idling resource that covers the entire pending registration can prevent synchronized assertions from observing **Sending**. Register idling resources only when waiting for completion is the intended test contract.

Keep assertions outside `runOnIdle`. Use that block only to release a fake or change app-owned observable input on the UI thread. Compose actions and assertions synchronize known work, not arbitrary transport completion.

## Avoid shortcut assertions

Bad practice is to invoke a verification callback and check only that the fake recorded the token. Navigation could remain broken while the test passes.

Correct it by asserting the screen before delivery, the verification pending state, and the final result after the repository accepts the token. Keep token forwarding as a supplementary boundary assertion.

Another anti-pattern shortens production token expiry to a few milliseconds so tests finish sooner. Scheduling noise then determines the result. Inject a fixed clock and explicitly controlled checker instead.

## Troubleshoot

| Symptom | Observation | Fix |
| --- | --- | --- |
| Verification succeeds with any token | Fake's matching behavior | Reject unexpected tokens and add an invalid case |
| Warning skips straight to expired | Auto-advancement or uncontrolled wall time | Pause the owning scheduler and inject time |
| Remember-me test always restores | Same in-memory owner reused | Reconstruct from the real store |
| Logout passes but private content returns | Late request or refresh result | Test cancellation or session-generation policy |
| Deep link works locally but not from email | Intent filters and domain verification | Run App Link integration on a device |
| Reset email test finds another run's link | Shared inbox selection | Correlate by run and request identity |

## Review checklist

- Are registration, verification, reset, and login separate transitions?
- Does the test cover an invalid or expired token?
- Is time controlled before the owner captures it?
- Is persistence verified through reconstruction rather than memory reuse?
- Does logout prevent late authenticated results from restoring content?
- Are email delivery, App Links, password changes, and remote revocation verified outside the fake-based UI layer?

## Related guides and sources

- [Authentication](authentication.md), [clock control](clock-control.md), and [third-party services](third-party.md).
- [Navigation](../frameworks/navigation.md) and [semantics selectors](../core/semantics-selectors.md).
- [Canonical cancellation example](../examples/FixtureUiTest.kt) covers disposal and stale results without claiming process death.
- [Android App Links](https://developer.android.com/training/app-links) describes verified routing.
- [Compose synchronization](https://developer.android.com/develop/ui/compose/testing/synchronization) describes test clocks and external work.
- [Android data layer](https://developer.android.com/topic/architecture/data-layer) describes repository boundaries.
