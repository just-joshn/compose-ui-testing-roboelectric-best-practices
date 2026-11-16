# Control network-backed UI with fakes and transport tests

## Table of contents

- [Choose the boundary](#choose-the-boundary)
- [Hold and release a request](#hold-and-release-a-request)
- [Match requests and script retries](#match-requests-and-script-retries)
- [Test headers, bodies, and response mapping](#test-headers-bodies-and-response-mapping)
- [Handle GraphQL operations](#handle-graphql-operations)
- [Use recorded fixtures without live fallback](#use-recorded-fixtures-without-live-fallback)
- [Test latency, offline, and stale results](#test-latency-offline-and-stale-results)
- [Keep real-time boundaries explicit](#keep-real-time-boundaries-explicit)
- [Own synchronization and cleanup](#own-synchronization-and-cleanup)
- [Avoid fake-based false greens](#avoid-fake-based-false-greens)
- [Troubleshoot](#troubleshoot)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the boundary

Use this guide when a screen depends on HTTP, GraphQL, delayed responses, retry, connectivity, or real-time data. Compose has no browser route-interception API. Choose a repository fake, SDK adapter, or controlled transport according to the claim.

| Claim | Boundary to control | Keep real |
| --- | --- | --- |
| Loading changes to content | Repository response | Screen, state owner, Compose interactions |
| Search forwards query and shows results | Repository command and result | Search orchestration |
| Authorization header is constructed | HTTP transport or request recorder | Real request-building code |
| JSON maps to a domain error | Response bytes | Real serializer and repository mapping |
| GraphQL partial errors render correctly | Generated client adapter or transport | Relevant mapping and UI |
| Server enforces authorization | Dedicated service environment | Real authentication and server |
| Slow connection throughput is tolerable | Network shaping on integration environment | Real transport and device |

Install fakes before the ViewModel or activity captures dependencies. Use [dependency injection](../frameworks/dependency-injection.md) for framework-specific replacement. Keep local tests in Android `src/test` with the [declared host setup](../references/setup.md).

## Hold and release a request

Use a pending result instead of a wall-clock delay. A pending fake gives the test a stable interval in which to assert loading, disabled controls, or a cancel action.

Illustrative fake for the canonical `Sender` contract. `Sender` and `MessagePanel` come from [FixtureUi.kt](../examples/FixtureUi.kt). The fake needs `kotlinx-coroutines-core`. This fragment is not added to the compiled fixture.

```kotlin
import fixture.Sender
import kotlinx.coroutines.CompletableDeferred

class PendingSender : Sender {
	val submitted = mutableListOf<String>()
	private val result = CompletableDeferred<String>()

	override suspend fun send(message: String): String {
		submitted.add(message)
		return result.await()
	}

	fun succeed(receipt: String) {
		check(result.complete(receipt))
	}
}
```

Illustrative test body using the configured v2 rule:

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
rule.onNodeWithText("Delivered Hello").assertDoesNotExist()
rule.runOnIdle { sender.succeed("Delivered Hello") }
rule.onNodeWithText("Delivered Hello").assertIsDisplayed()
rule.onNodeWithText("Sending").assertDoesNotExist()
```

Use the [canonical executable test](../examples/FixtureUiTest.kt) for the validated version of this pattern. The receipt assertion catches a no-op state update. The fake alone proves no HTTP request, serialization, TLS, or service behavior.

For failure tests, use the real boundary's failure shape. If it returns a sealed result, return that result. If it documents exceptions, throw the documented type and ensure the app handles it. Do not invent a generic exception path absent from the application.

## Match requests and script retries

A useful fake rejects unexpected commands. Match the identity that matters, such as search query, resource ID, operation, revision, and attempt. Do not return a success fixture for every call.

Prefer keyed response queues when multiple requests can overlap. A single global call counter can assign the wrong response when unrelated background work runs first.

For a retry scenario:

1. Configure the first load for `orders-alex` as a retryable failure.
2. Open the real orders route.
3. Release the failure and assert **Could not load orders**.
4. Click **Retry**.
5. Release a successful order list.
6. Assert the returned order identity and absence of the error.

If retry is automatic with backoff, control the scheduler that owns backoff. Assert the pending or reconnecting UI, advance one intended interval, and release the next response. Do not call `advanceUntilIdle()` on indefinite retry work.

Use a response sequence such as failure, failure, success only when that sequence is the requirement. Keep an exhausted script as a test failure rather than silently repeating the final success.

For pagination, match page key and filters. Return a distinct second page and assert appended content without duplicates. A fake that returns the same list for every page can hide incorrect pagination parameters.

## Test headers, bodies, and response mapping

Do not add an auth header inside a test interceptor and then claim the app constructs auth headers. That tests the interceptor's injection, not production code.

Instead, run the real request builder against a controlled transport or local test server supported by the app's HTTP client. Inspect the recorded request and reply with deterministic bytes. Keep server lifecycle and client base URL test-owned.

Check the method, path, relevant query parameters, content type, and public payload fields. Avoid pinning incidental header ordering or generated trace IDs unless those are contractual.

For request-body modification features, such as adding an idempotency key, call the real repository operation. Assert the emitted request contains the expected stable relationship. Do not mutate the outgoing body in the test to manufacture correctness.

For response transformations, such as discounts, run the real mapper with a fixed response and assert the domain or UI result. Changing the response fixture to already contain the expected discounted value skips the mapping under test.

Keep most request construction tests below Compose. Add one UI smoke case with the real repository and controlled transport when integration between those layers is important. Do not couple every UI test to raw JSON.

## Handle GraphQL operations

Match operation identity and variables, not only the shared `/graphql` URL. Two operations can use the same endpoint while having different behavior.

| Scenario | Controlled input | Expected client observation |
| --- | --- | --- |
| Query success | Data for named operation and variables | Correct content identity |
| Mutation success | Result tied to submitted input | Confirmation with returned record ID |
| GraphQL error | HTTP success with `errors` | Mapped error or recovery UI |
| Partial data | Data plus errors | Product's partial-data policy |
| Transport failure | Timeout, disconnect, or HTTP error | Transport-specific recovery |
| Cache hit | Seeded cache under the real key | Expected data without forced network claim |

A repository fake with a typed domain result does not test GraphQL parsing, generated adapters, cache normalization, or operation serialization. Use the real GraphQL client with its supported test transport for those claims.

Fail on unconfigured operations in hermetic tests. Live fallback can silently contact a real endpoint, return unrelated account data, or make an incomplete fixture appear successful.

For subscriptions, use explicit events and connection states. See [reactive streams](../android-apis/reactive-streams.md). A returned `Flow` is not proof of WebSocket framing or subscription authorization.

## Use recorded fixtures without live fallback

The Android analogue of browser HAR replay is usually sanitized response fixtures served through a controlled transport, or typed factories at a repository boundary. HAR is not a universal Compose test format.

Capture fixtures only from an authorized test environment. Remove credentials, cookies, private user data, and unstable timestamps before committing them. Record the endpoint or operation, schema version, expected method and variables, and purpose alongside the fixture.

Run captured bytes through the real parser when parsing is the claim. For UI-only tests, use a small domain factory so a schema change does not rewrite every screen test.

Treat fixture refresh as a reviewed change. A script that automatically rerecords on test failure can replace the expected result with a regression.

Avoid live fallback for missing recordings. An unexpected request should fail with its safe, redacted identity. Keep intentionally live integration tests in a separate task with explicit environment and credentials.

## Test latency, offline, and stale results

A suspended fake proves the UI remains correct while a result is pending. It does not emulate bandwidth, packet loss, DNS, or radio conditions.

For slow-load UI, hold the request, assert a loading affordance, and verify the user can cancel or navigate according to policy. Then complete or cancel explicitly.

For offline behavior, inject the repository's documented connectivity or transport failure. Assert cached content, offline messaging, and retry behavior. A connectivity boolean alone does not prove requests actually fail or that the cache is populated.

For offline-first logic, use the real local store and a controlled remote source in repository tests. Seed a cached record, fail the remote source, and verify the store-backed UI. Test background synchronization separately.

For stale search results, start query A, then query B. Complete B first, assert B results, then complete A. Assert A cannot overwrite the current results. Also cover cancellation if the implementation promises it.

Use an integration environment for throughput limits, TLS errors, actual timeouts, and connection switching. Do not report "3G verified" from a fake that merely waits two virtual seconds.

## Keep real-time boundaries explicit

Model connection state, event delivery, acknowledgement, and permanent failure separately. An open connection can be idle. It must not keep every Compose assertion waiting forever.

Deliver events after the collector is ready. For zero-replay streams, establish subscription through an explicit signal or the correct scheduler step. Avoid arbitrary sleeps before emission.

Test duplicate and out-of-order events when the client contract handles them. Keep protocol sequence IDs explicit. Use [multi-user testing](multi-user.md) for deterministic conflict and delivery schedules.

A local fake event stream proves client reactions. Real handshake, server fan-out, authentication, and reconnect negotiation need transport or service tests.

## Own synchronization and cleanup

Create fresh scripts, results, request logs, and clients per test. Do not reuse a completed deferred. Close local servers and clients, cancel scopes, and shut down executors even after failures.

`waitForIdle()` does not finish a held response. Release it explicitly. For external async work that must finish, use a bounded `waitUntil` or an appropriate idling resource.

Do not register a busy resource around the pending interval you need to inspect. Synchronized loading assertions would wait for completion and miss the state under test.

Use `mainClock` for Compose-owned timers, a separate scheduler for independent work, and injected time for wall-clock logic. Never drain every scheduler until the test happens to pass.

## Avoid fake-based false greens

Bad practice is to click **Save**, inspect `fake.calls == 1`, and stop. A broken state reducer can still satisfy that assertion.

Correct it by returning a concrete record and asserting the visible saved result. Keep request assertions when they represent the boundary's public contract.

Another anti-pattern returns success for unmatched calls or uses live fallback. Fail unexpected commands instead. Add a distinct wrong-ID or wrong-variable case where it can expose a real regression.

## Troubleshoot

| Symptom | Observation | Correction |
| --- | --- | --- |
| Loading is never visible | Fake completes immediately | Hold the result until after the assertion |
| Success never appears | Fake pending state and actual scheduler | Release result and synchronize its owner |
| Wrong retry response consumed | Global counter and concurrent requests | Key scripts by operation identity |
| UI fake passes, HTTP fails | Boundary removed by fake | Add real parser and transport contract tests |
| Test contacts production | Base URL and fallback behavior | Fail closed and isolate integration tasks |
| Stream events disappear | Subscription readiness and replay | Establish collector before delivery |

## Review checklist

- Is the selected fake below the behavior being claimed?
- Are unexpected commands rejected rather than silently accepted?
- Are loading, success, and relevant failure states observable?
- Are response order, retry time, and stale results controlled explicitly?
- Are parsing, HTTP, GraphQL, and server claims tested with their real implementations?
- Are clients, servers, listeners, and scopes closed after every test?

## Related guides and sources

- [When to fake](../architecture/when-to-fake.md), [repository contracts](../testing-patterns/repository-contracts.md), and [GraphQL](../testing-patterns/graphql.md).
- [Clock control](clock-control.md), [reactive streams](../android-apis/reactive-streams.md), and [error testing](../debugging/error-testing.md).
- [Canonical examples](../examples/FixtureUiTest.kt) validate controlled completion and stale-result isolation in the fixture.
- [Android test doubles](https://developer.android.com/training/testing/fundamentals/test-doubles) describes boundary replacements.
- [Android data layer](https://developer.android.com/topic/architecture/data-layer) describes repository responsibilities.
- [Compose synchronization](https://developer.android.com/develop/ui/compose/testing/synchronization) defines UI waiting limits.
