# Choose when and where to fake dependencies

Use this guide when a Compose UI test needs controlled data, timing, or failures. It covers local Android tests with Robolectric and the separate contract tests that keep fakes honest.

A fake replaces a dependency with a working test implementation. A stub returns predetermined values. A mock usually verifies configured interactions. Choose by the behavior you need, not by a blanket rule that every owned service must remain real.

## Table of contents

- [Choose the boundary by claim](#choose-the-boundary-by-claim)
- [Build a controllable fake](#build-a-controllable-fake)
- [Exercise the UI through the fake](#exercise-the-ui-through-the-fake)
- [Choose alternatives to a repository fake](#choose-alternatives-to-a-repository-fake)
- [Keep real integration coverage](#keep-real-integration-coverage)
- [Prevent fake drift](#prevent-fake-drift)
- [Avoid misleading tests](#avoid-misleading-tests)
- [Troubleshoot fake behavior](#troubleshoot-fake-behavior)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the boundary by claim

| Dependency or behavior | Local UI choice | Separate coverage |
| --- | --- | --- |
| Owned backend data | Fake repository for controlled UI states | Real client adapter and service integration |
| Serialization and HTTP status mapping | Keep adapter real with controlled transport | Service contract verification |
| Compose state and semantics | Keep real | Do not mock the test rule or semantics APIs |
| Android framework object | Prefer actual Robolectric-supported object | Device tests for unsupported behavior |
| Payment provider | Fake application-facing payment interface | Provider SDK sandbox on device |
| OAuth provider | Fake session outcome for UI states | Browser callback and token exchange integration |
| Analytics | No-op or recording fake | Adapter payload tests if analytics is contractual |
| Feature flags | Inject a fixed configuration | Provider integration separately |
| Business time | Inject an application clock | Time-source adapter tests |
| Local database | In-memory real database when persistence is the claim | On-device behavior where required |
| Image or map service | Deterministic loader result for UI behavior | Real loader or map integration at the correct layer |

Start with the question the test must answer:

1. If it concerns rendering or user interaction, keep Compose real and control the data boundary.
2. If it concerns mapping transport data, fake below the mapper, not above it.
3. If it concerns service authorization or persistence, exercise the real service in a controlled environment.
4. If it concerns Android system behavior, decide whether Robolectric implements enough of that behavior. Otherwise use a device.

The upstream browser guide recommends keeping owned frontend-to-backend traffic real in end-to-end tests. Preserve that integration goal, but do not apply it to every local Compose test. Repository fakes are appropriate when the declared claim is client behavior.

## Build a controllable fake

The data shape is one outgoing message and one pending receipt. The fake models only one request. That is sufficient for a single-send test and deliberately rejects accidental reuse.

This complete illustrative fake implements `Sender` from the [canonical UI](../examples/FixtureUi.kt). It needs `kotlinx-coroutines-core`, supplied in the fixture's dependency graph. Place these imports at the top of its test source file. This variation is not compiled by the canonical fixture.

```kotlin
import fixture.Sender
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CompletableDeferred

class PendingSender : Sender {
	private val receipt = CompletableDeferred<String>()
	val messages = mutableListOf<String>()
	var cancelled = false
		private set

	override suspend fun send(message: String): String {
		check(messages.isEmpty()) { "This fake supports one request" }
		messages.add(message)
		return try {
			receipt.await()
		} catch (error: CancellationException) {
			cancelled = true
			throw error
		}
	}

	fun succeed(value: String) {
		check(receipt.complete(value)) { "Receipt already completed" }
	}

	fun fail(error: Throwable) {
		check(receipt.completeExceptionally(error)) { "Receipt already completed" }
	}
}
```

The list and cancellation flag assume calls and observations occur under the test's controlled single-thread usage. Use a thread-safe recorder if production work calls the fake concurrently. Do not silently apply this fake to a multi-request or concurrent sender contract.

A fresh deferred gives the test a pending interval without a sleep. A completed deferred cannot become pending again. Construct a new fake per test.

The fake's `fail` method does not give `MessagePanel` an error state. The canonical panel has no recovery implementation. Use failure completion only with a production screen that maps the error into a defined UI result.

## Exercise the UI through the fake

This illustrative test body assumes a configured Robolectric Compose test, the fake above, and canonical `MessagePanel`. The required UI imports are:

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import fixture.MessagePanel
import org.junit.Assert.assertEquals
```

The body drives the real action path:

```kotlin
val sender = PendingSender()
compose.setContent { MessagePanel(sender) }

compose.onNodeWithText("Message").performTextInput("Hello")
compose.onNodeWithText("Send").performClick()
compose.onNodeWithText("Sending").assertIsDisplayed()
compose.onNodeWithText("Delivered Hello").assertDoesNotExist()

compose.runOnIdle {
	assertEquals(listOf("Hello"), sender.messages)
	sender.succeed("Delivered Hello")
}
compose.onNodeWithText("Delivered Hello").assertIsDisplayed()
compose.onNodeWithText("Sending").assertDoesNotExist()
```

The payload check proves which input crossed the boundary. The receipt assertion proves the UI consumed the result. Neither proves a network delivery occurred.

Keep automatic clock advancement enabled for a settled-state scenario. For a timed pending indicator, disable automatic advancement before triggering the action and use the Compose clock for the composition-owned timer. Completing the fake remains a separate operation.

Do not register an idling resource that stays busy for this pending request if the test must assert the loading UI while the request is held. Synchronized assertions would wait for the very completion the test has not released.

## Choose alternatives to a repository fake

### Keep the adapter real

To test response mapping, use the production repository and serializer with a controlled transport implementation or local HTTP test server appropriate to the project's client. Configure the real client to use that endpoint before constructing the repository.

For each case, assert the domain result, not just that a request was made:

| Controlled response | Expected adapter result |
| --- | --- |
| Valid receipt JSON | Receipt with the expected identifier |
| Conflict response | Domain conflict with safe display information |
| Invalid JSON | Defined protocol failure, not fabricated success |
| Transport timeout | Defined retryable failure |
| Unauthorized response | Session or authorization outcome defined by the client contract |

A fake repository skips all these mappings. A test server proves client transport behavior against the supplied response, not the live server contract.

### Use an explicit decorator

A decorator can alter one result from a real repository, such as setting stock to one for a low-inventory rendering case. Label that as a hybrid test. The real call can still fail or mutate state before the decorator changes the response.

Prefer a fixed fake for deterministic UI coverage. Use a decorator only when the real integration is part of the claim and the environment owns cleanup.

### Replay recorded data carefully

Android does not provide a direct equivalent of Playwright HAR routing through Compose semantics. Store sanitized response bodies or domain fixtures at the boundary your test owns.

Record provenance and schema version. Remove tokens, account details, and personal data. Refresh fixtures when the API changes. A replay file is evidence of a captured response shape, not proof that the current service still behaves that way.

## Keep real integration coverage

Separate fast local and integrated suites by source set, module, category, or task. Do not make the same test silently change its meaning based on whether `CI` is set.

| Suite | Real code | Controlled boundary |
| --- | --- | --- |
| Local UI | Compose and screen state owner | Repository or platform-facing interface |
| Adapter contract | Repository, serializer, transport client | Test server or transport response |
| Service integration | Client and owned test backend | Third-party service sandbox or test double |
| Device journey | Application host and system behavior | Dedicated test accounts and provider sandbox |

A local server gives repeatable setup. A staging server exposes deployed integration but needs isolated data and availability management. A disposable service environment needs an explicit owner for startup, readiness, cleanup, and failure logs.

Do not put service startup in a robot constructor. Do not share production credentials. Keep integration failures visible rather than replacing a failing real dependency with a fake during the run.

## Prevent fake drift

Share a bounded set of contract cases between fake and real implementations when their semantics must agree. For example, both can reject a blank message, preserve its exact text, and expose cancellation as cancellation rather than success.

Do not compare only JSON key names. Contracts include value meaning, missing versus null fields, ordering guarantees, error categories, retryability, and authorization behavior.

Use these checks:

1. Define domain outcomes independently of the fake.
2. Test the real adapter against representative transport responses.
3. Test fake outcomes against the same domain expectations where applicable.
4. Run selected service integration cases against the owned test environment.
5. Update recorded fixtures and consumers together when the contract changes.

A stateful fake needs realistic enough transitions to exercise the UI contract. It does not need an entire backend implementation. Add request sequencing only when a test needs retry, pagination, or concurrent operations.

## Avoid misleading tests

Faulty illustrative test:

```kotlin
compose.onNodeWithText("Send").performClick()
compose.runOnIdle { assertEquals(1, sender.messages.size) }
```

This passes when the screen records the request but never renders its result. Correct it by holding the request, asserting loading, completing the fake, and asserting the receipt, as in the worked example.

| Anti-pattern | Failure mechanism | Correction |
| --- | --- | --- |
| Mock `ComposeContentTestRule` | No real semantics or recomposition runs | Use the actual test environment |
| Mock Android `Context` deeply | Framework assumptions fail outside the configured stubs | Use Robolectric-supported framework objects |
| Fake every internal collaborator | Tests depend on call topology rather than behavior | Fake one meaningful external boundary |
| Use live payment calls in local tests | Cost, nondeterminism, unsafe side effects | Fake UI boundary and use sandbox integration |
| Catch every exception as a success result | Cancellation and programming errors disappear | Map defined failures and rethrow cancellation |
| Share one pending fake across methods | Completion and request history leak | Create fresh state per test |

## Troubleshoot fake behavior

| Symptom | Observe | Correction |
| --- | --- | --- |
| Loading never ends | Was this exact fake completed? | Release its pending request |
| Loading is never observable | Was the deferred already completed? | Hold a fresh completion until after the assertion |
| Compose time advances but no receipt appears | Which subsystem owns the receipt? | Complete the fake instead of advancing unrelated time |
| Retry reuses the first failure | Does the fake support another request? | Use a per-request queue for that contract |
| Device works but fake-based UI test fails | Compare fake contract and adapter outcomes | Repair the fake or the declared test claim |

## Review checklist

- Is the tested claim explicit about what remains fake?
- Does real UI code run through user actions?
- Does the fake expose only the control the scenario needs?
- Is every completion fresh and owned by one test?
- Is cancellation preserved?
- Are adapter and service contracts covered separately?
- Does the final assertion prove a visible result?

## Related guides and sources

- [Test architecture](test-architecture.md) assigns claims to layers.
- [Network fakes](../advanced/network-fakes.md) covers asynchronous response control.
- [Repository contracts](../testing-patterns/repository-contracts.md) covers real adapter behavior.
- [Synchronization](../references/synchronization.md) separates clocks and external completion.
- [Android test doubles](https://developer.android.com/training/testing/fundamentals/test-doubles) describes fakes, stubs, and mocks.
- [Robolectric best practices](https://robolectric.org/best-practices/) recommends using supported Android objects instead of mocking them.
