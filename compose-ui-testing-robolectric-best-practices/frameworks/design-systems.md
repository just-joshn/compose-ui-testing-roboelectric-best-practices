# Test Compose design-system components

## Table of contents

- [Choose component and application coverage](#choose-component-and-application-coverage)
- [Provide the real component environment](#provide-the-real-component-environment)
- [Test controlled components and slots](#test-controlled-components-and-slots)
- [Select semantic behavior](#select-semantic-behavior)
- [Test menus, dialogs, and transient content](#test-menus-dialogs-and-transient-content)
- [Test transitions and adaptive variants](#test-transitions-and-adaptive-variants)
- [Test theme and shared configuration](#test-theme-and-shared-configuration)
- [Keep visual and service claims separate](#keep-visual-and-service-claims-separate)
- [Synchronize and isolate component tests](#synchronize-and-isolate-component-tests)
- [Avoid design-system shortcuts](#avoid-design-system-shortcuts)
- [Troubleshoot failures](#troubleshoot-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose component and application coverage

Use this guide for Material components, custom design-system widgets, controlled values, slots, themes, overlays, and adaptive variants. Compose components can be mounted directly in a local Android host. There is no separate experimental browser-component compiler to install.

Keep component tests focused on the component's public contract. A component that needs a repository or navigation controller can still be tested with explicit owners, but repeated graph setup often means the reusable visual component and the route adapter need separate coverage.

| Goal | Test arrangement | Additional evidence |
| --- | --- | --- |
| Switch exposes checked state | Real component and stateful parent | Device accessibility traversal |
| Slot content remains usable | Real component with representative slot | Consumer integration for unusual content |
| Menu selection updates a field | Real menu and controlled value | Device popup behavior where relevant |
| Form shows validation | Real fields with controlled validation result | Repository validation contract |
| Theme tokens produce exact appearance | Screenshot test in a defined environment | Device rendering for fidelity claims |
| Tab updates shared screen state | Application or route integration | Backend and persistence tests |
| Component survives size or locale change | Configuration-focused local test | Device window and IME behavior |

Do not copy Vue or Nuxt setup steps into Android. Their useful principles are controlled values, provided dependencies, semantic selectors, transitions, and application-versus-component coverage.

## Provide the real component environment

Use `src/test`, `testImplementation`, Android resources, a Robolectric runner, and a declared Compose host. Follow [setup](../references/setup.md). Align test Compose artifacts with the project's BOM rather than forcing the fixture's versions onto every consumer.

Mount components under the application's theme. Include required `CompositionLocal` providers, density, locale, and any component-specific owner. Supply deterministic alternatives for time, image loading, or external services only when the component depends on them.

Do not create a giant universal test wrapper that installs navigation, DI, repositories, and every theme for all components. Name the providers the current component actually needs.

A theme can provide defaults that affect interaction. For example, text styles, content colors, and motion configuration may differ. Keep those real when their behavior is part of the contract. A fake theme can hide integration defects.

If a component depends on a ViewModel, first decide whether the claim is about the component or the route that obtains the ViewModel. A stateless component test does not need Hilt.

## Test controlled components and slots

A controlled component receives its value and emits a value change. The parent must feed the new value back for a full interaction test. Recording a callback while passing the same fixed value proves only callback delivery.

Illustrative complete test. It needs Material3, Compose UI test JUnit4 1.12.1, JUnit 4, Robolectric, Android resources, and the default host manifest. It is not compiled in the canonical fixture.

```kotlin
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsOff
import androidx.compose.ui.test.assertIsOn
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@Composable
private fun NotificationPreference(
	checked: Boolean,
	onCheckedChange: (Boolean) -> Unit,
	supportingContent: @Composable () -> Unit,
) {
	Column {
		Text("Notifications")
		Switch(
			checked = checked,
			onCheckedChange = onCheckedChange,
			modifier = Modifier.semantics {
				contentDescription = "Enable notifications"
			},
		)
		supportingContent()
		Text(if (checked) "Notifications enabled" else "Notifications disabled")
	}
}

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class NotificationPreferenceTest {
	@get:Rule val rule = createComposeRule()

	@Test fun updatesControlledValueAndRendersSlot() {
		rule.setContent {
			MaterialTheme {
				var checked by remember { mutableStateOf(false) }
				NotificationPreference(
					checked = checked,
					onCheckedChange = { checked = it },
					supportingContent = { Text("Only order updates") },
				)
			}
		}
		rule.onNodeWithText("Only order updates").assertIsDisplayed()
		val toggle = rule.onNodeWithContentDescription("Enable notifications")
		toggle.assertIsOff()
		toggle.performClick()
		toggle.assertIsOn()
		rule.onNodeWithText("Notifications enabled").assertIsDisplayed()
	}
}
```

This example tests an application preference widget. It does not request Android notification permission or enable real notifications. See [system services](../android-apis/system-services.md) for that separate boundary.

For slots, use representative content with its own interaction if interaction is allowed. Verify that the component neither clears required semantics nor intercepts the slot's action. A static label checks placement in semantics, not every possible consumer slot.

Test empty, long, multiline, and disabled content when those are supported contracts. Keep the matrix based on real component decisions rather than every theoretical combination.

## Select semantic behavior

Prefer text, content descriptions, role, toggle state, selection state, and enabled state. Do not select Material implementation node positions or internal layout structure.

For repeated component instances, scope by stable domain identity. If two cards both have **Edit**, identify the intended card before clicking. A test tag is appropriate for identity not otherwise expressible, but it does not replace accessible labels.

Merged semantics can move a child's text to its clickable parent. Inspect both trees before changing a selector. Use `useUnmergedTree = true` only when the child-specific contract needs it. `clearAndSetSemantics` replaces descendant information in the merged tree, while unmerged inspection can still expose children. That diagnostic visibility is not an accessibility-service guarantee.

For a custom switch-like row, expose one coherent toggle action and state. Avoid two independent clickable nodes for one conceptual setting unless the interaction design intentionally has two actions.

Keyboard and accessibility checks depend on the claim. Local semantics tests can prove actions and states are exposed. Device tests must establish real focus traversal, TalkBack announcements, and IME behavior.

## Test menus, dialogs, and transient content

Compose dialogs and popups can create separate roots. They are not guaranteed descendants of the button that opened them. Scope the target with dialog semantics or a meaningful popup identity.

Use task-specific observable sequences:

| Component | Action | Required result |
| --- | --- | --- |
| Dropdown | Open, select Spanish | Menu closes and selected language becomes Spanish |
| Autocomplete | Enter a prefix, choose Developer | Chosen value replaces query and suggestions close |
| Confirmation dialog | Open, cancel | Original record remains and dialog closes |
| Confirmation dialog | Open, confirm | Intended record changes and dialog closes |
| Snackbar with undo | Trigger deletion, click Undo | Record returns and action feedback changes |
| Paginator | Go to next page | Visible range and records both change |
| Sort control | Select ascending | State description and record order agree |
| Wizard | Complete fields and advance | Next step and preserved values appear |

These sequences preserve the practical component coverage in the upstream guides without assuming browser ARIA roles map exactly to Compose roles.

For auto-dismissal, determine who owns the timeout. A snackbar timer may depend on accessibility timeout recommendations and coroutine scheduling. Do not hard-code a device-independent duration unless the component's contract guarantees it.

Prefer an explicit dismiss action in ordinary behavior tests. Keep timeout-policy tests separate and control the actual scheduler or injected policy. Never use `Thread.sleep` to wait for a toast or snackbar to disappear.

For outside-click or Back dismissal, test the mechanism the component actually supports. A local call to `onDismissRequest` verifies host handling only, not pointer hit testing or system Back dispatch.

## Test transitions and adaptive variants

For settled-state tests, leave `mainClock.autoAdvance` enabled. Trigger add, remove, expand, or collapse, then assert the final content and available actions.

For an animation-specific test, disable auto-advance before the action. Establish the animation's starting frame, advance Compose time, and assert the intended intermediate or final state. Keep semantics assertions outside UI-thread callbacks.

Do not disable every animation globally and then claim transition behavior is covered. A no-motion configuration is a valid separate configuration test when the product supports reduced motion.

Test adaptive behavior with explicit constraints or supported test configuration. Assert which controls and content are available at each supported width. Keep real window insets, fold posture, edge-to-edge behavior, and device IME resizing in device coverage.

For lazy content, scroll to the item by stable identity. An item not composed yet is not necessarily absent from the data. For removal, assert the intended item's absence and another item's continued presence.

## Test theme and shared configuration

Provide the application's theme and configuration at the composition boundary. For dark-mode selection, drive the preference and assert the selected control and any meaningful text change. Use a defined screenshot test to prove colors or typography.

For locale, render fixed known data under the chosen resources and locale. Assert localized labels, number formatting, and layout availability. Restore locale after tests that mutate process-global configuration.

For a shared setting, change it through one consumer and observe another consumer under the production state owner. A test that directly replaces a `CompositionLocal` value proves rendering under that value, not preference persistence or cross-screen wiring.

Do not add DI and navigation only to provide a theme. Conversely, do not replace the real application state owner with a test singleton and claim integration coverage.

## Keep visual and service claims separate

A successful semantics assertion does not establish exact pixels, contrast, touch-target geometry, TalkBack traversal, or overall accessibility compliance. Keep these as explicit additional checks.

A screenshot test needs a defined renderer, device configuration, fonts, baseline policy, and review process. JVM drawing is not proof of device rendering. Use [visual regression guidance](../testing-patterns/visual-regression.md) for that boundary.

Server-rendered markup, metadata, server routes, and Nuxt hydration have no direct design-system equivalent in a native app. Test initial content and interaction locally. Test backend responses and external delivery separately.

Do not assert that no logs appeared as the only sign of correctness. A silent component can still ignore every action. Assert user-facing behavior first, then inspect relevant failures or warnings as supplementary evidence.

## Synchronize and isolate component tests

Create fresh controlled values, remembered state owners, popup state, and fake image loaders per test. Mount once and let the rule dispose content. Restore any modified theme, locale, accessibility, or global configuration.

If slot content owns a coroutine or listener, its cleanup must follow its actual lifetime. Remove the slot through a controlled parent state and verify stale callbacks cannot update the next instance when that behavior matters.

Hold external work to observe transient loading. Advance Compose time only for Compose-owned work. Keep idling resources accurate and nonblocking. A permanently busy resource prevents assertions from observing the pending state.

For a component that is reused in a lazy container, verify that new item identity resets item-specific state according to the contract. Do not retain a previous item's selected value through an accidental missing key.

## Avoid design-system shortcuts

| Anti-pattern | Failure mechanism | Correction |
| --- | --- | --- |
| Record `onValueChange` with fixed input | The component never receives updated state | Feed the result back through a stateful parent |
| Match internal Material node positions | Library implementation changes break selectors | Use public semantics and meaningful identity |
| Test only a label in a slot | Interactive slot wiring remains untested | Supply and exercise representative interactive content |
| Assert an overlay under its opener | The overlay may have another root | Query the actual dialog or popup semantics |
| Turn off all motion to fix timing | Broken transitions are no longer exercised | Separate settled-state and motion tests |
| Treat semantics as pixel proof | No actual color or device rendering assertion exists | Add a defined visual or device test |

## Troubleshoot failures

| Symptom | Observe | Fix |
| --- | --- | --- |
| Callback fires but switch remains off | Controlled value feedback | Update the parent's observed value |
| Text exists only in unmerged tree | Merge boundary and intended contract | Query the appropriate group or child |
| Dialog is invisible to scoped finder | Separate roots and dialog semantics | Scope by the dialog, not the opener's ancestor |
| Snackbar disappears before assertion | Timer owner and auto-advance | Hold or control the relevant timeout policy |
| Test lacks expected typography or defaults | Theme and required locals | Provide the real component environment |
| Reused row has another item's selection | Keys and remembered state | Test and repair item identity ownership |
| Locale test affects another class | Global locale or resources mutation | Restore configuration and isolate tests |

## Review checklist

- Does the component run under its real required providers?
- Does controlled state feed back after actions?
- Are slot content and repeated identities tested meaningfully?
- Are overlays queried in their actual roots?
- Are settled-state, animation, visual, and accessibility claims separate?
- Are shared preferences tested through the production owner?
- Does cleanup restore configuration and release owned work?

## Related guides and sources

- [State and ViewModels](state-viewmodels.md) covers hoisted and durable state.
- [Component testing](../testing-patterns/component-testing.md) covers test scope.
- [Accessibility](../testing-patterns/accessibility.md) covers semantics limits.
- [Adaptive layouts](../advanced/adaptive-layouts.md) covers configuration coverage.
- [Compose testing APIs](https://developer.android.com/develop/ui/compose/testing/apis) documents semantics queries and actions.
- [Compose semantics](https://developer.android.com/develop/ui/compose/accessibility/semantics) documents roles, merging, and custom components.
- [Material3 in Compose](https://developer.android.com/develop/ui/compose/designsystems/material3) documents the component theme environment.
- [Compose component API guidelines](https://github.com/androidx/androidx/blob/androidx-main/compose/docs/compose-component-api-guidelines.md) discusses state and slot contracts.
- [Compose synchronization](https://developer.android.com/develop/ui/compose/testing/synchronization) documents clock ownership.
