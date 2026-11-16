# Test third-party service boundaries

## Table of contents

- [Choose the service boundary](#choose-the-service-boundary)
- [Control OAuth and enterprise sign-in](#control-oauth-and-enterprise-sign-in)
- [Test payment outcomes](#test-payment-outcomes)
- [Test email verification and private inboxes](#test-email-verification-and-private-inboxes)
- [Test SMS verification](#test-sms-verification)
- [Record analytics without sending it](#record-analytics-without-sending-it)
- [Isolate SDKs and synchronize callbacks](#isolate-sdks-and-synchronize-callbacks)
- [Avoid provider shortcuts](#avoid-provider-shortcuts)
- [Troubleshoot](#troubleshoot)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the service boundary

Use this guide when Compose screens launch identity, payment, email, SMS, or analytics integrations. Keep the app's UI and state transitions real. Replace the app-owned adapter around the external SDK or service.

Run these local tests in Android `src/test` with the [Robolectric setup](../references/setup.md). Provider SDKs can depend on real services, browsers, hardware, or unsupported framework behavior. A passing fake-based test establishes only the client contract it exercises.

| Service | Local controlled boundary | Observable local result | Separate integration |
| --- | --- | --- | --- |
| OAuth provider | Launcher and exchange adapter | Welcome, cancellation, or retry UI | Provider tenant, browser, redirect, and exchange |
| Enterprise SSO | App's SSO session result | Correct signed-in identity or rejection | Backend assertion validation |
| Payment SDK | Payment launcher plus order repository | Decline, cancel, pending, or confirmed order | Provider test mode and backend reconciliation |
| Email | Registration result and link entry | Inbox prompt and verification result | Actual private inbox delivery |
| SMS | Challenge repository and entered code | Verified, invalid, expired, or resend UI | Delivery, consent, and platform integration |
| Analytics | Recording sink | Screen result plus intended event | SDK payload and ingestion contract |

Prefer existing application adapters. Do not build an elaborate universal SDK abstraction just for one test. Use a focused contract that represents the results the app already handles.

## Control OAuth and enterprise sign-in

Keep launch, provider result, token exchange, and session activation distinct. A provider code is not itself a signed-in session.

Illustrative application-owned adapter shape. It uses Kotlin and `kotlinx-coroutines-core`. No provider SDK API is implied, and this fragment is not fixture-compiled.

```kotlin
import kotlinx.coroutines.CompletableDeferred

sealed interface ProviderResult {
	data class Code(val value: String, val state: String) : ProviderResult
	data object Cancelled : ProviderResult
	data class Failed(val reason: String) : ProviderResult
}

fun interface IdentityLauncher {
	suspend fun launch(provider: String): ProviderResult
}

class ControlledIdentityLauncher : IdentityLauncher {
	val requestedProviders = mutableListOf<String>()
	private val result = CompletableDeferred<ProviderResult>()

	override suspend fun launch(provider: String): ProviderResult {
		requestedProviders.add(provider)
		return result.await()
	}

	fun complete(value: ProviderResult) {
		check(result.complete(value))
	}
}
```

Install the launcher and controlled exchange repository before constructing the real auth screen owner. Then drive **Continue with provider** through Compose.

Illustrative test-body fragment. It assumes a real `ProviderLoginRoute(launcher, exchange)` and a configured v2 `rule`. `ControlledExchangeRepository` is project-specific and holds its result until released.

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick

val launcher = ControlledIdentityLauncher()
val exchange = ControlledExchangeRepository()
rule.setContent { ProviderLoginRoute(launcher, exchange) }
rule.onNodeWithText("Continue with provider").performClick()
rule.onNodeWithText("Connecting").assertIsDisplayed()
rule.runOnIdle {
	launcher.complete(ProviderResult.Code("test-code", "expected-test-state"))
}
rule.onNodeWithText("Welcome, Alex").assertDoesNotExist()
rule.runOnIdle { exchange.acceptUser("alex", "Alex") }
rule.onNodeWithText("Welcome, Alex").assertIsDisplayed()
```

The real callback handler must correlate the response with the outstanding request. Do not hardcode production state or accept arbitrary codes to make this fragment work. The test fixture's expected state must come from its controlled request contract.

Use separate tests for cancellation, provider failure, exchange rejection, mismatched state, and callback replay where the app owns replay prevention. Verify that anonymous UI remains usable after cancellation and that failed exchange does not activate a session.

Test PKCE generation, verifier retention, state matching, and token exchange in the component that implements them, with its real logic and controlled transport. A fake launcher alone proves none of those mechanisms.

For multiple providers, configure provider identity explicitly and verify the selected provider reaches the adapter. Avoid a fake that ignores provider name and always returns the same account.

For SAML SSO, test the app-facing session result locally. If the backend owns assertion validation, test signatures, issuer, audience, and replay rejection there. Do not create a fake SAML assertion parser inside a UI test.

Run a separate device scenario with an authorized provider test tenant. Verify browser launch, cancellation, app return, and the intended account. Keep real credentials out of source and reports.

## Test payment outcomes

Represent SDK outcome and backend order state separately. Provider approval may still leave the order pending confirmation. The app must not display **Order confirmed** merely because a client callback said "success" unless that is the actual, documented architecture.

| Controlled outcome | Expected UI | Further check |
| --- | --- | --- |
| User cancels | Checkout remains usable, no success | No unintended order confirmation |
| Card declined | Useful error and retry path | Retry preserves correct amount and order |
| SDK approved, backend pending | Pending or processing state | No premature fulfillment claim |
| Backend confirms order | Returned order reference visible | Correct cart and amount mapping |
| Backend rejects | Recoverable error according to policy | No duplicate payment on retry |
| Duplicate callback | One stable order result | Repository idempotency contract |

For the local success path:

1. Seed a cart through the real checkout owner.
2. Click the displayed pay action.
3. Hold SDK completion and assert processing UI.
4. Deliver approval through the adapter.
5. Keep backend confirmation pending and assert that confirmed order UI is absent.
6. Complete the order repository with a concrete order ID.
7. Assert the returned order reference and product-defined cart state.

For failure, return a typed declined result, not a generic uncaught exception. Assert that the user can retry without losing the intended order context. Verify cancellation separately from decline.

Keep amount and currency explicit. A request assertion can supplement the final UI when the payment boundary's contract includes them. Do not use a floating-point approximate amount when the app models minor currency units.

Use provider test mode and documented test instruments in integration tests. Never execute real charges from routine tests. Validate webhook signatures, delayed confirmation, refunds, and reconciliation at the backend layer. A local fake cannot prove any of them.

Provider-specific SDK versions and test-mode APIs require current provider documentation. This guide deliberately uses app-owned adapter contracts rather than invented Stripe or PayPal Kotlin calls.

## Test email verification and private inboxes

For local UI tests, return a controlled "verification sent" result, assert **Check your email**, then deliver a synthetic link through the app's link-entry contract. Complete verification separately and assert the verified screen.

Use [authentication flows](authentication-flows.md) for expired, invalid, and already-used token cases. A fake token establishes neither message delivery nor account ownership.

For an email integration job:

1. Provision a private test mailbox or private domain under your control.
2. Use a run-specific recipient or correlation ID.
3. Trigger registration through the supported service path.
4. Poll for the correlated message with a deadline and diagnostic metadata.
5. Parse the expected verification link and validate its scheme and host.
6. Open the link through the intended integration layer.
7. Verify the final account state and clean up the test account.

Do not use a public temporary inbox for credentials, recovery links, or private account data. Do not pick the newest message from a shared inbox. Another worker may own it.

Do not expose a production reset token in the registration API merely to simplify tests. Use controlled fakes locally or approved test-environment mail tooling for integration.

## Test SMS verification

Keep challenge creation, code entry, and verification result distinct. After **Send code**, hold the request, assert pending UI, then release a challenge result. Enter a fixed synthetic code through the field and verify through the controlled repository.

Cover invalid code, expired challenge, resend cooldown, attempt limit, and cancellation where supported. Check the new challenge identity after resend so an old code cannot accidentally satisfy the new attempt in the fake.

Use explicit fixed values rather than random digits in local tests. Randomness adds no phone-ownership proof and makes failures harder to reproduce.

SMS retrieval, user-consent flows, permissions, and delivery need separate device or provider integration. Do not manufacture a real SMS event by directly assigning the expected verified UI state.

Test code autofill through the app-owned autofill result boundary locally, then verify the platform flow on a device. Entered-code tests remain useful even if autofill is unavailable.

## Record analytics without sending it

Default local tests to a no-network analytics implementation. For analytics behavior tests, use a recording sink with fresh per-test state.

Illustrative Kotlin sink, not a provider SDK replacement API:

```kotlin
data class AnalyticsEvent(val name: String, val properties: Map<String, String>)

fun interface AnalyticsSink {
	fun record(event: AnalyticsEvent)
}

class RecordingAnalytics : AnalyticsSink {
	val events = mutableListOf<AnalyticsEvent>()
	override fun record(event: AnalyticsEvent) {
		events.add(event)
	}
}
```

Drive the user action and assert its visible result first. Then inspect the sink for the intended event and public properties, such as order ID or currency. Do not assert incidental SDK batching order unless the product contract requires it.

For duplicate-event prevention, trigger the relevant recomposition or repeated callback and verify the event policy. A rendering effect that records on every recomposition can pollute analytics despite correct UI.

Keep passwords, tokens, raw verification links, and unnecessary personal data out of events. Add focused assertions for prohibited fields when privacy is part of the contract.

A recording sink proves app event emission, not ingestion, attribution, consent enforcement by the SDK, or dashboard processing. Verify SDK mapping and consent behavior separately with authorized test tooling.

If an SDK auto-initializes through an application or manifest component, replacing only the screen's sink may still allow network traffic. Configure the test variant or application initialization deliberately. Confirm the real SDK is not running rather than relying on a URL blacklist.

## Isolate SDKs and synchronize callbacks

Install adapters before activity launch when the activity owns content. Do not call another `setContent` over an already initialized real activity.

Use fresh pending results and listener registrations per test. Unregister SDK listeners, cancel scopes, and close clients in teardown. Late callbacks must not target a disposed owner or resurrect a cleared session.

A fake callback may complete on the test thread, UI thread, or an executor according to its contract. Match the application's boundary expectations. Use thread-safe recording if callbacks run concurrently. The simple recording lists above assume serialized access.

Compose synchronization does not wait for every SDK. Hold and release test results explicitly. For genuine external async progress, use a bounded condition or an appropriate idling resource. Do not sleep after payment or provider return.

Do not mark an entire SDK lifetime busy if the test must inspect its pending state. An idling resource should describe finite work the assertion intends to wait for.

## Avoid provider shortcuts

Bad practice is to bypass OAuth by setting `SignedIn` after the provider button is clicked and call it an OAuth test. That skips launcher result handling, exchange, and failure policy.

Correct it by exercising each app-owned boundary and naming the claim "client handles provider result". Keep real provider authentication in its own integration scenario.

Another anti-pattern treats a payment approval callback as proof that money moved. Assert the app's processing and confirmation behavior locally. Verify actual provider and backend state in test-mode integration.

## Troubleshoot

| Symptom | Observation | Correction |
| --- | --- | --- |
| Real provider launches in local test | Dependency capture and SDK initialization | Replace adapter before owner creation |
| Provider result arrives but UI stays pending | Exchange boundary and scheduler | Release exchange and synchronize its owner |
| Payment success appears too early | SDK approval versus order confirmation | Assert the pending interval before backend result |
| Email job opens another test's link | Mail correlation and mailbox privacy | Unique recipient and bounded correlated polling |
| Analytics still reaches production | Auto-initialization and variant config | Disable real initialization in local tests |
| Callback updates a later test | Listener and scope lifetime | Unregister and cancel on every exit path |

## Review checklist

- Are provider launch, result, exchange, and session activation distinct?
- Are cancellation and rejection tested without success fallbacks?
- Is backend order confirmation separate from payment SDK approval?
- Are mailboxes private and integration messages correlated?
- Are analytics assertions paired with a real visible outcome?
- Are secrets excluded from code, logs, fixtures, and events?
- Are SDK callbacks and resources cleaned up after failed tests too?

## Related guides and sources

- [Authentication](authentication.md), [authentication flows](authentication-flows.md), and [network fakes](network-fakes.md).
- [Multiple roots](multiple-roots.md), [system services](../android-apis/system-services.md), and [security testing](../testing-patterns/security-testing.md).
- [Android identity guidance](https://developer.android.com/identity) describes platform identity options.
- [Activity results](https://developer.android.com/training/basics/intents/result) describes app launch and callback lifecycle.
- [Android App Links](https://developer.android.com/training/app-links) describes verified app routing.
- [Compose synchronization](https://developer.android.com/develop/ui/compose/testing/synchronization) and [test doubles](https://developer.android.com/training/testing/fundamentals/test-doubles) define local boundaries.
