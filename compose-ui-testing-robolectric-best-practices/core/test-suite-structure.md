# Structure a local Compose UI suite

Use this guide to place tests, split behavior by layer, organize reusable helpers, and choose CI entry points. A Robolectric-hosted journey can exercise several screens locally. It is not a full end-to-end test when a fake removes transport, authentication, or platform behavior.

## Contents

- [Choose the layer for each claim](#choose-the-layer-for-each-claim)
- [Organize source sets and packages](#organize-source-sets-and-packages)
- [Write a focused local journey](#write-a-focused-local-journey)
- [Separate component and orchestration tests](#separate-component-and-orchestration-tests)
- [Separate repository and service contracts](#separate-repository-and-service-contracts)
- [Give visual and device checks their own lane](#give-visual-and-device-checks-their-own-lane)
- [Share helpers at the right boundary](#share-helpers-at-the-right-boundary)
- [Run and review the suite](#run-and-review-the-suite)
- [Troubleshoot suite organization](#troubleshoot-suite-organization)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the layer for each claim

| Claim | Best starting layer | What remains unproved |
| --- | --- | --- |
| Price calculation or validation rule | Pure Kotlin unit test | UI presentation |
| Given state renders correctly | Local Compose component test | Event-to-state orchestration |
| User action starts loading and shows a response | Local Compose screen test with a controlled fake | Real transport and server correctness |
| Navigation shows the intended destination | Local hosted journey | OS task and deep-link integration unless separately exercised |
| Real adapter serializes a request correctly | Repository or transport contract test | Production service behavior |
| Backend rejects unauthorized access | Service integration test | Client usability |
| Device IME, system UI, or TalkBack works | Device or emulator instrumentation | Coverage on every physical device |
| Pixels or frame timing are correct | Dedicated visual or device performance suite | General correctness from semantics alone |

Choose the smallest layer that includes the behavior. Do not force a pricing table through Compose or replace a UI interaction test with assertions on a fake's private fields.

## Organize source sets and packages

This illustrative layout assumes the project's Kotlin source directories are configured:

```text
app/
  src/
    main/kotlin/example/messages/
      MessageScreen.kt
      MessageViewModel.kt
    test/kotlin/example/messages/
      MessageRenderingTest.kt
      MessageFlowTest.kt
      MessageRepositoryContractTest.kt
      robots/MessageRobot.kt
      fixtures/MessageScenario.kt
    test/kotlin/example/testcategories/
      Smoke.kt
    test/resources/cases/
      message-results.json
    androidTest/kotlin/example/messages/
      MessageImeTest.kt
```

Local Robolectric tests belong in `src/test` with `testImplementation`. Device tests belong in `src/androidTest` with their own instrumentation dependencies and runner.

Group by feature first when feature ownership helps readers find behavior. Split large classes by a meaningful contract, such as rendering, submission, recovery, or navigation. Do not create a separate class merely for every assertion.

Keep a central configuration guide or convention plugin for shared build settings. Test classes should declare narrow SDK or qualifier needs without copying the entire dependency setup.

A helper module can share test builders and robots across feature modules. It must not share live mutable repositories, Android contexts, or Compose rules.

## Write a focused local journey

This complete illustrative test uses the canonical `MessagePanel` and `Sender` from the package examples. It needs the dependencies and host from [configuration](configuration.md). It is not an additional compiled fixture test.

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import fixture.MessagePanel
import fixture.Sender
import kotlinx.coroutines.CompletableDeferred
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class MessageFlowTest {
	@get:Rule val rule = createComposeRule()

	@Test fun sendShowsReturnedReceipt() {
		val receipt = CompletableDeferred<String>()
		val sender = Sender { receipt.await() }
		rule.setContent { MessagePanel(sender) }

		rule.onNodeWithText("Message").performTextInput("Hello")
		rule.onNodeWithText("Send").performClick()
		rule.onNodeWithText("Sending").assertIsDisplayed()
		rule.onNodeWithText("Delivered Hello").assertDoesNotExist()

		rule.runOnIdle { check(receipt.complete("Delivered Hello")) }
		rule.onNodeWithText("Delivered Hello").assertIsDisplayed()
		rule.onNodeWithText("Sending").assertDoesNotExist()
	}
}
```

The fake deliberately holds the request. No sleep creates the loading interval. The final assertion checks the user-visible result, not merely that the action callback ran.

Keep one coherent journey per test. A checkout journey may need several actions to reach confirmation. Adding unrelated profile editing afterward makes failure ownership unclear and forces repetition of unrelated setup.

For repeated labels, scope by identity before clicking. Do not carry a browser recipe's `.first()` into `onAllNodesWithText(...)[0]` unless order itself is the requirement.

## Separate component and orchestration tests

A component test supplies immutable state and checks text, selection, enabled state, or an emitted callback. If it supplies `Sent("Delivered")` directly, it proves rendering of that state only.

An orchestration test mounts the real state owner, drives the real user action, controls a fake boundary, and observes the transition. It can prove editing to loading to result without a real service.

Keep rendering tables broad and orchestration cases focused. Do not repeat every label assertion in every journey. Retain important preconditions and the result that would fail if the action were a no-op.

Use failure cases when the application defines them. Supply a controlled repository failure, assert the error UI, perform retry when supported, and assert recovery. Do not invent production error handling just to fill a testing example.

Test transient UI through explicit control. Compose auto-advance can skip time-dependent intermediate states. A pending deferred or controlled main clock gives those states a deterministic observation interval.

## Separate repository and service contracts

A fake repository removes serialization, HTTP behavior, endpoint availability, and server authorization from the claim. Local UI tests must not be labeled API coverage merely because the fake records a payload.

Organize contract tests around the adapter that really performs serialization and transport. Use a controlled server or equivalent boundary when appropriate. Verify request shape, response mapping, error mapping, and cancellation there.

Use a real service environment only for the smaller set of claims that requires it. Validate credentials and readiness before running. Namespace data by run and clean up only owned records.

Keep feature UI tests independent of those service tests. A migration or authentication test must not leave global state for another test method to consume.

## Give visual and device checks their own lane

Semantics assertions do not prove pixels, font rasterization, GPU behavior, or animation frame performance. Robolectric drawing can support a separately configured JVM image workflow, but it is not general device fidelity.

For a visual regression lane, define renderer, density, font scale, locale, theme, image-loading behavior, and baseline review policy. Freeze business time and deterministic data instead of broadly hiding content that might contain a regression. See [visual regression](../testing-patterns/visual-regression.md).

For device tests, select concrete platform claims such as IME actions, permission dialogs, system task behavior, TalkBack traversal, and actual frame timing. Keep their reports and execution environment separate from local tests.

Disposing and remounting a composition proves neither activity recreation nor process death. Write a lifecycle or persistence test with the actual required transition if that is the claim.

## Share helpers at the right boundary

| Helper | Owns | Does not own |
| --- | --- | --- |
| Robot | Selectors, user actions, named assertions | Activity creation or repository lifecycle |
| Scenario builder | Immutable inputs and fresh fake construction | Global account or worker session |
| Resource rule | Setup and matching teardown | Business success assertions |
| Matcher | One meaningful semantics condition | Broad retries or exception swallowing |
| Convention plugin | Build configuration | Mutable state across tests |

Keep inline code when a helper has no repeated use. Extract a helper when it reduces repeated decisions without hiding important inputs or results.

Avoid a base test class that silently installs dispatchers, mounts content, logs in, drains loopers, and retries assertions. That inheritance makes work ownership hard to inspect and can install dependencies after an activity has already started.

## Run and review the suite

Illustrative commands for the `app` module:

```bash
./gradlew :app:testDebugUnitTest \
  --tests 'example.messages.MessageFlowTest.sendShowsReturnedReceipt' \
  --console=plain --rerun-tasks
./gradlew :app:testDebugUnitTest --tests 'example.messages.MessageFlowTest'
./gradlew :app:testDebugUnitTest
```

Read the named JUnit results. A green process with zero tests, skips, or only a cached report is insufficient evidence for a fresh behavior run.

Use a small explicit smoke category for PR feedback only when a broader required lane also exists according to pipeline policy. Keep quarantine visible and accountable. See [test filtering](test-filtering.md).

Check isolation by running a method alone, then its class, then the required suite. Diagnose shared fake state, clock settings, database paths, threads, and globals before forcing execution order.

For a new important behavior test, temporarily break the promised action or route it to the wrong item. Require the intended result assertion to fail. Restore the change and rerun. A compilation or host failure is not a successful behavior mutation check.

## Troubleshoot suite organization

| Symptom | Observe | Fix |
| --- | --- | --- |
| Every UI test needs credentials | Boundary chosen too broadly | Fake the nondeterministic repository in local UI tests |
| Component test claimed as flow coverage | Test injects final state | Mount real orchestration and drive actions |
| One class is hard to navigate | Several unrelated contracts | Split by behavior and share only repeated helpers |
| Tests depend on order | Shared state or setup test | Fresh per-method construction |
| Local pass disagrees with device | Claim depends on platform fidelity | Add the correct device-layer check |
| Filtered lane hides failures | Expected method set and quarantine policy | Report scope honestly and run required coverage |

## Review checklist

- Each test name states a behavior rather than an internal function.
- The layer includes the behavior and excludes unrelated infrastructure.
- Source sets, dependencies, and tasks agree.
- Each method has fresh mutable state and one content owner.
- Final assertions detect a broken action.
- Service, device, and visual claims have separate evidence.
- Required lanes execute their expected methods without skips.

## Related guides and sources

- [Test architecture](../architecture/test-architecture.md) describes layer tradeoffs.
- [Component testing](../testing-patterns/component-testing.md) covers rendering and interaction contracts.
- [Test data](test-data.md) covers deterministic scenario inputs.
- [Android testing fundamentals](https://developer.android.com/training/testing/fundamentals) describes testing scopes.
- [Compose testing](https://developer.android.com/develop/ui/compose/testing) describes actions and assertions.
- [Robolectric local tests](https://developer.android.com/training/testing/local-tests/robolectric) describes the local Android layer.
