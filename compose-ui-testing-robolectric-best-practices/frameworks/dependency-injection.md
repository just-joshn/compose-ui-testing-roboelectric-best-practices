# Test dependency-injected Compose screens

## Table of contents

- [Choose how much graph to test](#choose-how-much-graph-to-test)
- [Start with explicit parameters](#start-with-explicit-parameters)
- [Test the route and screen separately](#test-the-route-and-screen-separately)
- [Use a Hilt host only for graph claims](#use-a-hilt-host-only-for-graph-claims)
- [Replace dependencies before launch](#replace-dependencies-before-launch)
- [Handle flows, validation, and lazy dependencies](#handle-flows-validation-and-lazy-dependencies)
- [Keep variants and test applications explicit](#keep-variants-and-test-applications-explicit)
- [Isolate the graph and synchronize work](#isolate-the-graph-and-synchronize-work)
- [Avoid injection shortcuts](#avoid-injection-shortcuts)
- [Troubleshoot failures](#troubleshoot-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose how much graph to test

Use this guide when a Compose screen receives repositories, use cases, ViewModels, clocks, or platform adapters through injection. The goal is to control nondeterministic boundaries without replacing Compose's state and semantics machinery.

Do not require Hilt for a stateless component test. The smallest useful test usually supplies state and callbacks directly. Add graph integration tests only for claims about the actual graph, entry points, scopes, qualifiers, or activity wiring.

| Claim | Test arrangement | What remains outside the claim |
| --- | --- | --- |
| Screen renders disabled submit | Pass immutable state to the composable | Validation orchestration and DI |
| Clicking submit shows the repository result | Inject a controlled sender into a stateful screen | Production graph and transport |
| ViewModel maps errors correctly | Construct ViewModel with a fake | Activity and graph resolution |
| Route obtains the intended scoped ViewModel | Real route and hosted owner | Backend integration |
| Hilt qualifier resolves the intended repository | Hilt test application and replacement module | Real repository service behavior |
| Release variant contains the right binding | Variant-specific graph or build test | Local debug graph is not release evidence |

Treat the injected object graph and its mutable state as test-owned. A shared singleton fake can make one method's result satisfy another method's assertion.

## Start with explicit parameters

Data shape comes first. In this example the dependency is one suspend function from a message to a receipt. The screen owns its input and sending state. The fake controls only completion.

The [canonical `Sender` and `MessagePanel`](../examples/FixtureUi.kt) already implement this boundary. Reuse the pattern rather than introducing a test service locator.

Illustrative standalone test using those canonical types. It requires their `fixture` package on the test source path, Android resources, the default activity host manifest, Compose UI test JUnit4 1.12.1, JUnit 4, coroutines, and Robolectric. This guide's additional test is not compiled by the canonical fixture.

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import fixture.MessagePanel
import fixture.Sender
import kotlinx.coroutines.CompletableDeferred
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class InjectedSenderTest {
	@get:Rule val rule = createComposeRule()

	@Test fun displaysTheInjectedReceipt() {
		val receipt = CompletableDeferred<String>()
		val requests = mutableListOf<String>()
		val sender = Sender { message ->
			requests.add(message)
			receipt.await()
		}
		rule.setContent { MessagePanel(sender) }
		rule.onNodeWithText("Message").performTextInput("Hello")
		rule.onNodeWithText("Send").performClick()
		rule.onNodeWithText("Sending").assertIsDisplayed()
		rule.runOnIdle {
			assertEquals(listOf("Hello"), requests)
			receipt.complete("Receipt 42")
		}
		rule.onNodeWithText("Receipt 42").assertIsDisplayed()
		rule.onNodeWithText("Sending").assertDoesNotExist()
	}
}
```

A no-op click must fail this test because the receipt never appears. The request assertion supplements the UI result. It is not the only proof.

The deferred creates a real pending interval without an arbitrary delay. An immediately returning fake can hide loading or duplicate-submission bugs.

## Test the route and screen separately

Keep a route composable that obtains the ViewModel and collects its state separate from a screen composable that accepts state and event callbacks. Test each according to its responsibility.

For a screen rendering test, pass a loading, success, or error state. Verify the visible content and available actions. Do not claim the ViewModel produced that state.

For a state-production test, construct the ViewModel with controlled repositories and a known scheduler. Exercise its public action and assert emitted state. Keep pure validation and transformation cases here rather than repeating every permutation through Compose.

For a route integration test, mount the real route under the correct lifecycle, saved-state, and ViewModel owners. Click a real control and verify the rendered state. Add a small number of tests that prove the graph supplies the correct dependency.

When a ViewModel is scoped to a navigation entry, do not replace that owner with an arbitrary global owner. Two destinations can intentionally share a graph-scoped ViewModel, while two separate navigation graphs must not share one accidentally.

For route transitions, see [navigation](navigation.md). For state production and saved state, see [state and ViewModels](state-viewmodels.md).

## Use a Hilt host only for graph claims

Use Hilt's test support when the production wiring is the subject. A Hilt local test needs more than a fake object and a Compose rule.

Configure the following using the consuming project's Hilt and annotation-processing versions:

- `com.google.dagger:hilt-android-testing` on the local test classpath.
- The Hilt compiler on the project's test annotation-processing configuration.
- A Hilt test application, commonly `HiltTestApplication`, selected for the Robolectric test.
- `@HiltAndroidTest` and a `HiltAndroidRule`.
- An appropriate declared activity host when testing Android entry points.
- The same Android resources and Robolectric runner required by other local hosted tests.

Do not add Hilt compiler configuration to a project that does not use Hilt. Do not mix KSP and kapt instructions without checking the project's processing setup.

For a replacement used by a test source set, use `@TestInstallIn` to replace the production module in the intended component. Keep the component and qualifier aligned with production. A fake bound without the production qualifier is a different binding.

For a single test's replacement, use the documented `@UninstallModules` and `@BindValue` approach when appropriate. Follow the Hilt testing guide's restrictions on which modules can be uninstalled. Avoid broad replacement modules when a direct constructor test already answers the question.

The canonical fixture does not include Hilt. A Hilt recipe here is guidance for a Hilt-consuming project, not fixture-validated compatibility evidence.

## Replace dependencies before launch

Activity launch can resolve injected fields and create ViewModels before `@Before` executes. A test that assigns its fake after launch can be testing the real repository.

Establish this order:

1. Configure the test application and replacement modules.
2. Initialize field-bound fakes before any rule that launches an activity.
3. Let the Hilt rule prepare the test component before activity launch.
4. Launch the declared activity or mount the test-owned content.
5. Assert the visible result of an action using that fake.

If the launched activity sets its own content, do not call another `setContent`. Choose the activity-owned route or a test-owned default host, not both.

Assign JUnit rule order explicitly for a Hilt rule and an activity-launching Compose rule. Use the documented order supported by the project's JUnit and Hilt setup. Do not rely on field declaration order.

`hiltRule.inject()` injects the test instance where requested. It is not a replacement for ordering the activity launch correctly. If fake initialization requires data from `@Before`, use a host arrangement that does not launch before that data exists.

## Handle flows, validation, and lazy dependencies

Replacing a repository does not remove synchronization requirements. A fake may return a cold Flow, a hot Flow, a deferred result, or an executor callback. State which one it provides.

For async field validation, keep the result pending, assert the loading or disabled state, then release success or rejection. If typing a new value cancels the old request, complete the older result last and verify it does not overwrite the new value's result.

For lazily created dependencies, drive the feature that first requests them. A start-screen test does not prove a rarely opened settings graph can resolve its bindings.

For optional features or on-demand modules, test local route behavior with a controlled availability boundary. Use an installed application test for actual dynamic-feature installation. There is no Android counterpart to waiting for a browser JavaScript chunk in a Robolectric UI test.

Do not read an internal DI component or service locator solely to assert that it exists. Assert the feature's visible result. Inspect binding identity only when identity or scope is the actual contract.

## Keep variants and test applications explicit

| Setup | Use it for | Do not infer |
| --- | --- | --- |
| Plain Robolectric application and direct constructor fake | Screen or ViewModel behavior | Production application startup |
| Hilt test application with replacement modules | Hilt graph integration | Real service behavior |
| Debug variant graph | Debug configuration | Release-only bindings or shrinker behavior |
| Device application build | Manifest entry points and runtime integration | Every local logic case |

Run the real local test task for the module and variant. For the repository fixture, the task is `:fixture:testDebugUnitTest`. A consuming app may have a different task name. Inspect its tasks instead of copying this name blindly.

Server rendering and hydration from the upstream Angular guide have no direct Android DI equivalent. The useful local checks are correct initial state, interactive behavior after mounting, and application startup wiring. Keep backend rendering or delivery claims in their own tests.

## Isolate the graph and synchronize work

Create fakes per test. Close databases, clients, and test-owned scopes after every method. Restore any global overrides even after a failure. A DI singleton scope does not grant permission to share one mutable fake across test workers.

If a dependency is captured by `remember` or created as a ViewModel, replacing the fake later may not change the captured instance. Install the fake before content and owner creation.

Do not globally replace `Dispatchers.Main` around a Compose rule by guesswork. Keep separate ViewModel unit-test dispatcher rules separate from hosted Compose tests. Identify the actual scheduler before advancing it.

Use a bounded observable wait for genuinely external work. Do not register a pending fake as a permanently busy idling resource if the test must assert the pending UI.

## Avoid injection shortcuts

| Anti-pattern | Failure mechanism | Correction |
| --- | --- | --- |
| Hilt for every stateless test | Graph setup obscures a rendering contract | Pass state and callbacks directly |
| Replace the fake after activity launch | The ViewModel already captured production dependencies | Initialize before launch |
| Share a singleton fake across methods | Requests and completed values leak | Create a fresh fake per test |
| Mock Compose or Android `Context` | Framework behavior is replaced with incomplete objects | Keep framework objects real |
| Assert only a mock invocation | The UI can ignore the returned value | Assert the rendered result |
| Assume debug graph proves release | Variant-specific modules and shrinker behavior differ | Test the required variant separately |

## Troubleshoot failures

| Symptom | Observe | Fix |
| --- | --- | --- |
| Real network call appears | Fake installation and ViewModel creation order | Replace before the host starts |
| Hilt component generation fails | Compiler configuration and source set | Align test processing with project Hilt setup |
| Binding is missing | Component, qualifier, and replacement target | Replace the intended binding, not a similarly named type |
| Fake result is ignored | Captured instance and flow collector | Use one injected instance and the actual state stream |
| Two screens share unexpected state | ViewModel owner and DI scope | Scope to the intended graph or destination |
| Loading never becomes success | Deferred, scheduler, or external callback owner | Complete the responsible work explicitly |

## Review checklist

- Is a DI graph necessary for this claim?
- Are the real framework and semantics APIs preserved?
- Are replacements installed before activity and ViewModel creation?
- Is exactly one owner responsible for content?
- Do asynchronous tests assert pending and final UI?
- Are qualifiers, scopes, and variants tested only where relevant?
- Are test-owned graph resources cleaned up?

## Related guides and sources

- [State and ViewModels](state-viewmodels.md) covers state ownership.
- [Navigation](navigation.md) covers graph-scoped owners.
- [Fixtures and hooks](../core/fixtures-hooks.md) covers test setup lifetime.
- [Hilt testing](https://developer.android.com/training/dependency-injection/hilt-testing) documents local test applications, rules, and replacement modules.
- [Manual dependency injection](https://developer.android.com/training/dependency-injection/manual) describes explicit dependency ownership.
- [Compose testing common patterns](https://developer.android.com/develop/ui/compose/testing/common-patterns) covers isolated composables and host choices.
- [Robolectric best practices](https://robolectric.org/best-practices/) covers Android objects and leaked threads.
