# Test Compose components in isolation

Use this guide for reusable controls, cards, dialogs, and small stateful panels. Mount the real composable under Robolectric and test its public inputs, rendered semantics, and interactions. Move repository orchestration and full navigation journeys to tests that own those behaviors.

## Table of contents

- [Choose the component boundary](#choose-the-component-boundary)
- [Set up the host](#set-up-the-host)
- [Mount with a theme and inputs](#mount-with-a-theme-and-inputs)
- [Update controlled state](#update-controlled-state)
- [Test events and payloads](#test-events-and-payloads)
- [Exercise slots and composition locals](#exercise-slots-and-composition-locals)
- [Replace external dependencies](#replace-external-dependencies)
- [Test removal and restoration](#test-removal-and-restoration)
- [Keep synchronization and isolation explicit](#keep-synchronization-and-isolation-explicit)
- [Avoid implementation assertions](#avoid-implementation-assertions)
- [Troubleshoot component tests](#troubleshoot-component-tests)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the component boundary

| Behavior | Mount | Assert |
| --- | --- | --- |
| Disabled button cannot submit | Real button with disabled input | Disabled semantics and an enabled comparison case |
| Controlled input accepts edits | Component plus a state-owning wrapper | Updated editable text and dependent UI |
| Stateful toggle updates itself | Stateful component | Exposed on or off state |
| Slot content is rendered and usable | Component with representative composable slots | Slot label and resulting action |
| Theme or feature flag changes behavior | Component with its real provider | Public behavior, not provider internals |
| Async request shows a result | Small panel with controlled boundary fake | Pending and final UI |
| Screen loads data and navigates | Real screen with test dependencies | Destination content and request result |
| Pixel spacing matches a design | Dedicated rendering test | Approved rendering evidence, not semantics alone |

Do not mock the component's own state transitions. A test that supplies `Success` and checks a success label is a rendering test. It does not prove that clicking **Submit** produces success.

## Set up the host

Put Android local tests in `src/test`. Enable Android resources and use `testImplementation` for JUnit, Robolectric, and `ui-test-junit4`. The default Compose rule needs the activity declared by `ui-test-manifest` in the selected debug variant.

Use the [setup reference](../references/setup.md) for dependency wiring. The validated fixture uses Compose UI 1.12.1 and `androidx.compose.ui.test.junit4.v2.createComposeRule`. Do not copy newer 1.13-only environment configuration into that setup.

Keep tests beside the component's owning module, for example:

```text
feature/profile/src/main/kotlin/example/ProfileCard.kt
feature/profile/src/test/kotlin/example/ProfileCardTest.kt
```

A component test still has an Android activity host. It is not a Desktop Compose test or an activity-free function call.

## Mount with a theme and inputs

This illustrative complete test uses Material3, Compose UI test 1.12.1, JUnit 4, and Robolectric with the default host. It defines its own component and does not claim fixture compilation.

```kotlin
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
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
import org.robolectric.annotation.LooperMode

@Composable
private fun QuantityPicker(quantity: Int, onIncrease: () -> Unit) {
	Column {
		Text("Quantity: $quantity")
		Button(enabled = quantity < 3, onClick = onIncrease) {
			Text("Add one")
		}
	}
}

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
@LooperMode(LooperMode.Mode.PAUSED)
class QuantityPickerTest {
	@get:Rule val compose = createComposeRule()

	@Test fun increaseUpdatesQuantityAndStopsAtLimit() {
		compose.setContent {
			var quantity by remember { mutableStateOf(2) }
			MaterialTheme {
				QuantityPicker(quantity, onIncrease = { quantity += 1 })
			}
		}
		compose.onNodeWithText("Quantity: 2").assertIsDisplayed()
		compose.onNodeWithText("Add one").performClick()
		compose.onNodeWithText("Quantity: 3").assertIsDisplayed()
		compose.onNodeWithText("Add one").assertIsNotEnabled()
	}
}
```

Wrap production controls in the real app theme when typography, colors, or component defaults matter. Prefer a small test wrapper to mounting the entire application. Provide only the dependencies that this component needs.

Cover meaningful input variations with separate cases. For the picker, zero, a normal value, and the limit describe behavior. Testing every color token through a semantics tag does not establish visual correctness.

## Update controlled state

A controlled composable reads a value and reports an event. Its owner must feed the next value back. A plain Kotlin variable is not observable Compose state.

For a real interaction test, use `remember { mutableStateOf(...) }` in a wrapper as above. For an external-input rendering test, create observable state before `setContent`, then update it with `runOnIdle`.

This illustrative fragment assumes `QuantityPicker` and the rule above. It needs `mutableStateOf`, `assertIsDisplayed`, `onNodeWithText`, and `assertIsNotEnabled` imports from the complete example.

```kotlin
val quantity = mutableStateOf(1)
compose.setContent {
	QuantityPicker(quantity.value, onIncrease = { quantity.value += 1 })
}
compose.onNodeWithText("Quantity: 1").assertIsDisplayed()
compose.runOnIdle { quantity.value = 3 }
compose.onNodeWithText("Quantity: 3").assertIsDisplayed()
compose.onNodeWithText("Add one").assertIsNotEnabled()
```

Call `setContent` once. Do not remount the component to simulate every prop update. Remounting destroys remembered state and can conceal a stale-input bug.

Test the distinction between an initial value and a controlled value. A parameter named `initialQuantity` may intentionally initialize `remember` once. Do not demand that later changes reset it unless that is the component's contract.

## Test events and payloads

Drive events through the control's public UI. For a selection component, open its menu, choose a named option, and assert the selected label. Record the selected ID only if the callback payload is part of the public contract.

A wrapper can display callback output as a receipt. This lets the test prove both callback delivery and the value a caller receives. For a pure callback-only button, a callback assertion is valid, but pair broader screen tests with a user-visible result.

For text inputs, use `performTextInput` to insert text or `performTextReplacement` to replace the whole value. Assert editable semantics, including label text if the component merges that text into the node. Do not inspect private `TextFieldState` fields instead of what the field displays.

For keyboard interactions, establish focus, inject the supported key through `performKeyInput`, and assert the same outcome as the corresponding touch action. A direct callback invocation proves neither focus handling nor key routing.

For disabled controls, assert disabled semantics. Add an enabled case that exercises the action so a disconnected callback cannot pass the entire suite.

## Exercise slots and composition locals

Compose slots are composable lambdas, not HTML children or framework-specific named slots. Pass real representative content into `title`, `content`, and `actions` slots.

For a dialog component with an actions slot:

1. Mount the real dialog with a title, body, and **Close** action.
2. Assert all three appear in the correct user-facing grouping.
3. Click **Close**.
4. Assert the dialog disappears and its owning screen remains usable.

Do not assert the composable call order or the number of layout wrappers. Those details can change without changing the slot contract.

For a composition local, use `CompositionLocalProvider` around the component. Prefer the real provider when its behavior is relevant. A fake analytics or feature-flag dependency can be provided when its external behavior is outside the test claim.

If a slot receives state, test at least the pending and populated branches. A slot test that always receives populated data can miss a loading branch that never renders.

## Replace external dependencies

Inject small boundary interfaces or immutable state. Keep Compose runtime, semantics, and interaction code real.

| Dependency | Useful replacement | What remains unproven |
| --- | --- | --- |
| Repository request | Fresh controlled repository fake | HTTP, serialization, server policy |
| Analytics | Recording event sink | SDK delivery and remote processing |
| Feature flags | Immutable per-test flag values | Remote configuration fetching |
| Current user | Test session provider | OAuth and backend authorization |
| Business time | Explicit clock or instant | Device clock integration |

Configure dependencies before mounting. If an effect starts immediately, replacing a singleton afterward can leave the first request using production dependencies.

Use [the canonical message panel tests](../examples/FixtureUiTest.kt) for a compiled controlled-sender pattern. `sendShowsReceiptAfterCompletion` holds the request pending, enters a real message, clicks **Send**, completes the sender, and asserts the returned receipt.

Do not make all component tests depend on the real service. Keep a smaller integration suite for that boundary.

## Test removal and restoration

Remove content through state inside the single mounted composition when disposal is the behavior under test. Assert the user-visible removal and, where contractual, cancellation of owned work.

A `key` change can intentionally replace a component instance. Use it to test whether stale results from an old request contaminate a fresh component. The canonical fixture's disposal case demonstrates that distinction.

State restoration is a different claim. If the component promises saveable state, use the appropriate state-restoration test facility for the project's version. Do not call disposal and remounting "process death" or assume `remember` survives recreation.

## Keep synchronization and isolation explicit

Create state holders, callback recordings, fakes, and providers per test. Never share a mutable query cache or completed deferred between methods.

Default clock advancement suits settled-state assertions. Hold external requests pending to observe loading. Disable automatic Compose clock advancement only when testing a specific timed transition.

If a ViewModel uses a separate test scheduler, advance that scheduler deliberately. A new `runTest` scope does not automatically share the Compose clock. See [synchronization](../references/synchronization.md).

Let the rule dispose the composition. Cancel test-owned scopes and restore overridden globals even after a failure. If the real activity already calls `setContent`, do not mount a second content owner through an activity rule.

## Avoid implementation assertions

| Anti-pattern | Why it fails | Replacement |
| --- | --- | --- |
| Assert a private state variable changed | State can change while rendering is broken | Assert the displayed quantity or selection |
| Update a plain local variable in `onValueChange` | No observable state triggers recomposition | Use a state-owning wrapper |
| Call `setContent` repeatedly | State resets can hide update defects | Change observable input state |
| Snapshot every component state | Large baselines obscure the behavior | Use semantics for behavior and targeted rendering checks |
| Mock Compose internals | The tested path differs from production | Fake only external boundaries |
| Assert only a callback count for a complete form | The UI can remain stuck in loading | Assert success or error content too |

## Troubleshoot component tests

| Symptom | Check | Correction |
| --- | --- | --- |
| Text never updates | Is the wrapper's value observable? | Feed events back through Compose state |
| Provider lookup fails | Which local or theme does the component read? | Supply the smallest real provider |
| Menu item is ambiguous | Popup root and repeated labels | Scope to menu identity, not index zero |
| Loading is never visible | Fake completion and auto-advancing timers | Keep a fresh fake pending |
| Failure occurs before content mounts | Resources, activity declaration, runner | Repair the host, not selectors |
| Test passes only alone | Singleton flags, caches, scopes | Use per-test dependencies and cleanup |

## Review checklist

- [ ] The mounted boundary owns the claimed behavior.
- [ ] Controlled state is fed back through an observable owner.
- [ ] Each test calls `setContent` once.
- [ ] Actions lead to observable assertions.
- [ ] Slots and providers use representative content.
- [ ] External fakes do not become integration claims.
- [ ] Accessibility and lifecycle contracts have focused cases.

## Related guides and sources

- [Accessibility](accessibility.md) covers labels, state, and keyboard behavior.
- [Fixtures and hooks](../core/fixtures-hooks.md) covers lifecycle ownership.
- [State and ViewModels](../frameworks/state-viewmodels.md) covers screen orchestration.
- [Common Compose test patterns](https://developer.android.com/develop/ui/compose/testing/common-patterns) describes isolated composables and state restoration.
- [Compose testing APIs](https://developer.android.com/develop/ui/compose/testing/apis) documents actions and assertions.
- [State in Compose](https://developer.android.com/develop/ui/compose/state) explains observable state and state hoisting.
