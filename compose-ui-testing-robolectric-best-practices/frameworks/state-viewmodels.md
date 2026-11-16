# Test Compose state and ViewModel behavior

## Table of contents

- [Choose the state owner and test layer](#choose-the-state-owner-and-test-layer)
- [Test state through observable UI](#test-state-through-observable-ui)
- [Test ViewModel-driven loading and recovery](#test-viewmodel-driven-loading-and-recovery)
- [Test derived state and forms](#test-derived-state-and-forms)
- [Test effects and cancellation](#test-effects-and-cancellation)
- [Test shared state across screens](#test-shared-state-across-screens)
- [Distinguish restoration and persistence](#distinguish-restoration-and-persistence)
- [Handle overlays and failures honestly](#handle-overlays-and-failures-honestly)
- [Synchronize and isolate state](#synchronize-and-isolate-state)
- [Avoid state-test shortcuts](#avoid-state-test-shortcuts)
- [Troubleshoot failures](#troubleshoot-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the state owner and test layer

Use this guide for local state, hoisted state, state holders, ViewModels, reactive repositories, forms, and shared application state. Test what the user can observe without treating private runtime objects as a public contract.

Compose state is not React state. Recomposition does not provide React Strict Mode's double-effect contract, and Compose has no automatic equivalent of a React render error boundary. Use Compose's actual ownership and scheduling rules.

| State or behavior | Useful test layer | What to control |
| --- | --- | --- |
| Disabled button for invalid input | Stateless screen test | Immutable input state |
| Click updates a counter | Stateful component test | Real local state |
| Repository result becomes a loaded screen | ViewModel plus screen integration | Held repository result |
| Complex validation or reduction | Plain unit test | Inputs and expected domain result |
| `LaunchedEffect` restarts on key change | Hosted Compose test | Key and controlled suspend work |
| ViewModel survives host recreation | Lifecycle host test | Actual owner and repository |
| `rememberSaveable` restoration | Saveable-state test | State restoration mechanism |
| Durable data survives app restart | Storage integration test | Real test storage |

Choose the smallest layer that exercises the promised path. A rendering test that supplies success state does not prove loading orchestration.

## Test state through observable UI

The data shape in this example is an integer quantity with a lower bound of zero. The parent owns the value and passes it into a stateless component. That arrangement tests both the callback and the visible update.

Illustrative complete local test. It needs Material3, Compose UI test JUnit4 1.12.1, JUnit 4, Robolectric, Android resources, and the default host manifest. It is not an additional compiled fixture test.

```kotlin
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@Composable
private fun QuantityPicker(value: Int, onValueChange: (Int) -> Unit) {
	Column {
		Text("Quantity: $value")
		Button(enabled = value > 0, onClick = { onValueChange(value - 1) }) {
			Text("Decrease")
		}
		Button(onClick = { onValueChange(value + 1) }) {
			Text("Increase")
		}
	}
}

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class QuantityPickerTest {
	@get:Rule val rule = createComposeRule()

	@Test fun updatesHoistedStateAndRespectsMinimum() {
		rule.setContent {
			var value by remember { mutableStateOf(0) }
			QuantityPicker(value) { value = it }
		}
		rule.onNodeWithText("Quantity: 0").assertIsDisplayed()
		rule.onNodeWithText("Decrease").assertIsNotEnabled()
		rule.onNodeWithText("Increase").performClick()
		rule.onNodeWithText("Quantity: 1").assertIsDisplayed()
		rule.onNodeWithText("Decrease").performClick()
		rule.onNodeWithText("Quantity: 0").assertIsDisplayed()
		rule.onNodeWithText("Decrease").assertIsNotEnabled()
	}
}
```

A callback-only test could pass even if the label never changes. A fixed `value = 0` with a recording callback proves callback delivery only. Keep the parent state update when the test claims interactive controlled-state behavior.

## Test ViewModel-driven loading and recovery

Keep the production route's state collection real in integration tests. Android screens commonly use `collectAsStateWithLifecycle` and a ViewModel obtained from the appropriate owner. A pure rendering test can bypass both, but must label its narrower claim.

For a ViewModel unit test, construct the ViewModel with a fresh fake repository and a controlled coroutine environment. Exercise its public action. Assert loading, result, and error states according to the public state contract. Do not inspect private jobs, mutable backing flows, or implementation-only caches.

Illustrative standalone ViewModel unit test. It needs `androidx.lifecycle:lifecycle-viewmodel-ktx`, coroutines core, `kotlinx-coroutines-test`, and JUnit 4. It has no Compose rule and does not replace Main around a hosted UI test. The public state is a read-only flow. The sender is the controlled suspend boundary.

```kotlin
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.Assert.assertEquals
import org.junit.Test

private class ReceiptViewModel(private val send: suspend () -> String) : ViewModel() {
	private val mutableStatus = MutableStateFlow("Ready")
	val status: StateFlow<String> = mutableStatus.asStateFlow()

	fun submit() {
		viewModelScope.launch {
			mutableStatus.value = "Sending"
			mutableStatus.value = send()
		}
	}
}

@OptIn(ExperimentalCoroutinesApi::class)
class ReceiptViewModelTest {
	@Test fun publishesPendingThenReceipt() = runTest {
		Dispatchers.setMain(StandardTestDispatcher(testScheduler))
		val receipt = CompletableDeferred<String>()
		val model = ReceiptViewModel { receipt.await() }
		try {
			assertEquals("Ready", model.status.value)
			model.submit()
			runCurrent()
			assertEquals("Sending", model.status.value)
			receipt.complete("Receipt 42")
			runCurrent()
			assertEquals("Receipt 42", model.status.value)
		} finally {
			model.viewModelScope.cancel()
			Dispatchers.resetMain()
		}
	}
}
```

This test proves public state production, not visible screen behavior. It deliberately omits error and duplicate-submit policy because those belong to the consuming application's contract. Add explicit error states and failure cases when that policy exists.

For a UI integration test, inject the same boundary before ViewModel creation. Then:

1. Mount the route once under its real owners.
2. Trigger refresh or submission through the UI.
3. Keep the repository result pending.
4. Assert the loading indicator and any disabled action.
5. Release a success result.
6. Assert the returned content and removal of loading UI.

For recovery, supply an app-defined recoverable error, assert its explanation, click **Retry**, and complete the next request. Do not trigger an unrelated render exception and expect Compose to catch it as a recoverable repository error.

Use the canonical [message sender tests](../examples/FixtureUiTest.kt) for a compiled held-result pattern. A production ViewModel integration needs its own lifecycle and injection setup beyond that example.

## Test derived state and forms

Assert the displayed consequence of derived state. For a cart, add the identified item and verify both the item count and total. A private state-store snapshot alone cannot prove the badge or price formatting.

For forms, exercise input and focus changes through semantics actions. Keep labels and editable values distinct when a merged text-field node exposes both.

| Scenario | Action | Observable assertion |
| --- | --- | --- |
| Empty required field | Submit or move focus according to policy | Required-field explanation |
| Invalid email | Enter malformed text and trigger validation | Format explanation and disabled submit |
| Corrected input | Replace with valid text | Error removed and submit enabled |
| Cross-field mismatch | Enter different confirmation | Mismatch explanation |
| Async validation | Hold repository response | Loading state, then accepted or rejected result |
| Submit pending | Hold submission result | Duplicate submission unavailable if required |
| Submit failure | Fail the controlled boundary | Preserved input and recovery action |

Debounce logic belongs to the scheduler that runs the debouncing coroutine. Test before and after its deadline in a state-holder test. In a UI test, rapid input followed by a held result can verify the visible latest-query behavior without relying on a real-time typing delay.

For stale responses, request A, then request B. Complete B first and A last. Assert that B remains visible if the screen promises latest-query-wins behavior. A request-count assertion alone cannot establish that result ordering is correct.

## Test effects and cancellation

`LaunchedEffect` follows composition lifetime and keys. `rememberCoroutineScope` work follows its composition owner. A ViewModel's scope follows the ViewModel owner. Repository sharing may outlive either one.

Test effects by changing the input that legitimately restarts them. Do not call effect internals directly and claim the key wiring works.

A useful cancellation case starts held work, removes or replaces the owner, completes the old result, and verifies that stale content never appears. The canonical `disposalCancelsPendingSendAndFreshPanelIsIsolated` test demonstrates local composition cancellation.

That local cancellation does not establish ViewModel clearing or process death. For a ViewModel, create and clear a test-owned `ViewModelStore`, or use the real destination owner in a navigation integration test. Cancel any test-owned collection scopes after the test.

Do not infer a leak from an exact recomposition count. Recomposition can occur for reasons unrelated to a resource leak. Inspect the resource ownership contract, active subscriptions, and user-visible stale updates.

If work starts directly in a composable body, recomposition can repeat it. Move lifecycle-sensitive work to an appropriate effect or owner in production code. The test should detect the repeated visible request or stale result, not rely on a private composition counter.

## Test shared state across screens

For cart, account, theme, or locale state, drive one screen and observe another consumer. Add an item through the catalog, navigate to the cart, and assert the identified item and total. This tests the shared-state contract rather than a store field.

For authentication, submit through the app-owned boundary and assert that the header changes to the signed-in identity. Test sign-out clearing user-specific content. Use service integration tests for actual credential verification.

For theme or locale, assert meaningful user-observable changes such as the selected theme option, localized labels, or resource-dependent content. Semantics cannot prove exact colors, typography, or device pixels. Add screenshot or device checks for those claims.

Do not hoist a singleton test state object only to make two screens share state. Use the production owner and scope that the test claims to exercise.

## Distinguish restoration and persistence

| Mechanism | What it can retain | Appropriate proof |
| --- | --- | --- |
| `remember` | State while the composition identity remains | Recomposition or local interaction test |
| `rememberSaveable` | Saveable state through supported restoration | `StateRestorationTester` |
| ViewModel | State while its owner survives | Owner recreation or lifecycle test |
| `SavedStateHandle` | Supported saved state for a ViewModel | Saved-state owner and restoration test |
| Database or preferences | Durable application data | Close and reopen real test storage |

Illustrative fragment for a saveable counter. It requires `StateRestorationTester` from Compose UI testing, `rememberSaveable`, `mutableStateOf`, the delegated-state imports, and the `QuantityPicker` above. It runs inside a hosted test with `rule`.

```kotlin
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.StateRestorationTester
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick

val restoration = StateRestorationTester(rule)
restoration.setContent {
	var value by rememberSaveable { mutableStateOf(0) }
	QuantityPicker(value) { value = it }
}
rule.onNodeWithText("Increase").performClick()
rule.onNodeWithText("Quantity: 1").assertIsDisplayed()
restoration.emulateSavedInstanceStateRestore()
rule.onNodeWithText("Quantity: 1").assertIsDisplayed()
```

This tests saveable-state restoration through that helper. It does not kill an Android process. Do not add a second `rule.setContent` around it. The restoration tester owns content for this test.

## Handle overlays and failures honestly

Dialogs and popups can live in separate roots. Query the appropriate root or scope by dialog semantics rather than assuming the dialog is a descendant of its opener. Test cancel and confirm outcomes, not merely presence.

A repository failure should become an explicit error state when that is the product design. An uncaught render exception should fail the test. Do not add a test-side exception catcher that displays fallback UI and then claim the application recovered.

For lazy content, assert the loading or unavailable state, then the loaded destination. Actual dynamic-feature delivery remains outside a fake availability boundary.

## Synchronize and isolate state

Use fresh state, ViewModels, fakes, stores, and saved-state owners per method. Create state before mounting and call `setContent` once. Mutate controlled state with `runOnIdle`, then assert outside that block.

Keep ordinary clock auto-advance enabled for settled UI. To inspect a transient composition-owned delay, disable it before triggering the transition and establish the timer start. To inspect pending repository work, hold the repository fake instead.

Do not wrap every hosted test in an unrelated `runTest`. It can introduce a separate scheduler. Follow [synchronization](../references/synchronization.md) for v2 scheduling and external work.

## Avoid state-test shortcuts

| Anti-pattern | Failure mechanism | Correction |
| --- | --- | --- |
| Read a private store and stop | UI may not observe or render the state | Assert the visible consequence |
| Supply success state and claim orchestration | The loading path never ran | Use a held repository result |
| Record callbacks without feeding back state | Controlled UI never actually changes | Use a stateful parent for interaction tests |
| Catch render exceptions as expected error UI | The test invents recovery behavior | Assert real app-defined error states |
| Remount and claim persistence | In-memory objects may still be alive | Test the actual restoration or storage mechanism |
| Assert exact recomposition counts | Runtime scheduling becomes the contract | Assert behavior and resource ownership |

## Troubleshoot failures

| Symptom | Observe | Fix |
| --- | --- | --- |
| Click records a callback but label stays old | Parent state feedback | Update observed state through the real owner |
| Flow state never appears | Collector lifecycle and scheduler | Mount the right owner and progress that collector |
| Old search overwrites new results | Cancellation and request identity | Test latest-query policy below and through UI |
| Restored value resets | Saver, keys, and owner | Exercise the actual saveable mechanism |
| Work survives local removal | Composition versus ViewModel ownership | Assert cancellation at the correct lifetime |
| Tests share old data | Singleton state or retained store | Create and clear owners per method |

## Review checklist

- Is the state owner named?
- Does the test exercise the claimed path rather than inject its final result?
- Would a no-op action fail the visible assertion?
- Are loading, errors, and stale responses controlled?
- Are restoration, lifecycle survival, and durable persistence separate claims?
- Are coroutine and Compose schedulers kept explicit?

## Related guides and sources

- [Reactive streams](../android-apis/reactive-streams.md) covers Flow and subscription behavior.
- [Design systems](design-systems.md) covers controlled components and slots.
- [Dependency injection](dependency-injection.md) covers route setup.
- [Compose state](https://developer.android.com/develop/ui/compose/state) documents state and collection.
- [Compose side effects](https://developer.android.com/develop/ui/compose/side-effects) documents effect ownership.
- [ViewModel testing](https://developer.android.com/topic/libraries/architecture/viewmodel/viewmodel-testing) documents ViewModel test boundaries.
- [State restoration testing](https://developer.android.com/develop/ui/compose/testing/common-patterns) documents `StateRestorationTester`.
- [Saved state for Compose](https://developer.android.com/develop/ui/compose/state-saving) distinguishes state-saving mechanisms.
