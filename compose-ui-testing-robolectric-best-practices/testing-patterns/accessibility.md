# Test accessibility contracts

Use this guide to test the semantics, keyboard actions, and focus behavior that your Compose UI exposes. Run these checks as Android local tests under Robolectric. Pair them with device accessibility checks and TalkBack sessions before claiming an accessible user journey.

## Table of contents

- [Choose the test layer](#choose-the-test-layer)
- [Set up a semantics check](#set-up-a-semantics-check)
- [Check roles, labels, and state](#check-roles-labels-and-state)
- [Exercise keyboard navigation](#exercise-keyboard-navigation)
- [Check dialogs and focus restoration](#check-dialogs-and-focus-restoration)
- [Check dynamic announcements](#check-dynamic-announcements)
- [Cover contrast and motion](#cover-contrast-and-motion)
- [Keep checks isolated and actionable](#keep-checks-isolated-and-actionable)
- [Avoid misleading checks](#avoid-misleading-checks)
- [Troubleshoot failures](#troubleshoot-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the test layer

| Question | Local check | Separate evidence |
| --- | --- | --- |
| Does an icon action have a meaningful label? | Content-description matcher and click outcome | TalkBack pronunciation and context |
| Is a switch announced with the right state? | Role, toggle state, and state description | Spoken output on a device |
| Can a keyboard user finish the flow? | Inject key events and assert focus and result | Hardware keyboard and IME integration |
| Does a dialog return focus? | Assert the named trigger regains input focus | Accessibility focus and traversal on a device |
| Does a status change expose announcement metadata? | Live-region property and updated text | Actual announcement timing with TalkBack |
| Is text readable with high contrast or large fonts? | Theme and configuration cases | Device rendering, contrast analysis, and visual inspection |
| Are all accessibility requirements satisfied? | No single local assertion establishes this | Automated device checks plus manual review |

There is no axe-core equivalent to install into the Compose semantics tree. Android's Accessibility Test Framework integration is a separate facility with its own dependency and runtime requirements. Do not assume that enabling it works in every Robolectric environment.

Keep explicit semantics assertions in the local suite. Add the checks described by the official accessibility testing guide to a supported device test configuration. The pinned fixture does not validate `ui-test-junit4-accessibility` or `enableAccessibilityChecks()` under Robolectric.

## Set up a semantics check

Use `src/test`, `testImplementation`, Android resources, and a declared activity host. See [local setup](../references/setup.md) for dependencies. This illustrative complete test uses Compose UI 1.12.1, Material3, JUnit 4, and Robolectric. It is not an additional compiled fixture example.

```kotlin
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.assertIsOff
import androidx.compose.ui.test.assertIsOn
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.performClick
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.LooperMode

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
@LooperMode(LooperMode.Mode.PAUSED)
class NotificationAccessibilityTest {
	@get:Rule val compose = createComposeRule()

	@Test fun switchExposesAndChangesItsState() {
		compose.setContent {
			var enabled by remember { mutableStateOf(false) }
			MaterialTheme {
				Switch(
					checked = enabled,
					onCheckedChange = { enabled = it },
					modifier = Modifier.semantics {
						contentDescription = "Email notifications"
					},
				)
			}
		}
		val notifications = compose.onNodeWithContentDescription("Email notifications")
		notifications.assert(
			SemanticsMatcher.expectValue(SemanticsProperties.Role, Role.Switch)
		)
		notifications.assertIsOff()
		notifications.performClick()
		notifications.assertIsOn()
	}
}
```

The test drives the actual toggle and verifies its exposed state. It does not prove that TalkBack announces the switch correctly on every Android version.

## Check roles, labels, and state

Prefer Material and Foundation controls that supply appropriate semantics. For custom controls, expose the role, state, and action that match their behavior. Do not repair a missing production role by finding the control through a test tag alone.

For an icon-only **Delete draft** action, find the content description, perform the action, and assert that the draft is removed or that the confirmation appears. A nonempty description is not enough. "Icon" is nonempty but does not describe the action.

For expandable content, verify both the exposed state and the panel content. Compose has no general ARIA `expanded` attribute. Use the semantics that your component actually promises, such as a localized state description and a click action.

This illustrative fragment assumes `compose` is the hosted rule and the FAQ control exposes `stateDescription`. It needs the listed imports in the test module.

```kotlin
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick

val shipping = compose.onNodeWithText("Shipping")
shipping.assert(
	SemanticsMatcher.expectValue(SemanticsProperties.StateDescription, "Collapsed")
)
shipping.performClick()
shipping.assert(
	SemanticsMatcher.expectValue(SemanticsProperties.StateDescription, "Expanded")
)
compose.onNodeWithText("Delivery takes three working days").assertIsDisplayed()
```

Inspect the merged tree first. A clickable row may merge its label and icon into one accessible control. Test the group rather than requiring every child to remain separately discoverable. Use the unmerged tree only for a deliberate child-level contract.

Decorative images should not add redundant spoken labels. Do not give every icon a description if adjacent text already describes the action. Conversely, do not clear a meaningful label with `clearAndSetSemantics` merely to simplify a test.

## Exercise keyboard navigation

Test a meaningful path rather than counting arbitrary Tab presses through the entire app.

1. Establish the intended initial focus using the app's real focus policy.
2. Send Tab or directional keys through the Compose root.
3. Assert the next named control has input focus.
4. Activate the control with the supported key.
5. Assert the resulting content.

This illustrative fragment assumes a screen whose first field is already focused. It requires Compose test APIs and `androidx.compose.ui.input.key.Key`.

```kotlin
import androidx.compose.ui.input.key.Key
import androidx.compose.ui.test.assertIsFocused
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performKeyInput

compose.onNodeWithText("Email").assertIsFocused()
compose.onRoot().performKeyInput {
	keyDown(Key.Tab)
	keyUp(Key.Tab)
}
compose.onNodeWithText("Password").assertIsFocused()
```

Do not click the destination control before testing a startup shortcut. That click can hide the missing-initial-focus defect. If the app is embedded in an Android View host, add a host-level device test where key events begin at that host.

Input focus and accessibility focus are different. `assertIsFocused()` establishes Compose input focus, not TalkBack focus. A skip-to-content action can be tested locally if your app implements one, but web landmark roles and skip links have no automatic native equivalent.

## Check dialogs and focus restoration

Open the dialog through its trigger. Assert the dialog's content, move focus through the intended actions, dismiss it through the supported action, and assert that focus returns to the named trigger.

Use separate cases for **Cancel**, confirmation, and Back or Escape if the product supports those dismissal paths. Do not assume Escape and Android Back have identical handlers.

A useful dialog test verifies that background controls cannot be activated while the dialog is open. Scope selectors to the dialog when background labels repeat. Do not select the first **Cancel** match.

For a focus cycle, list the expected controls explicitly. Checking that a focused control's text happens to occur somewhere in the dialog can pass when the wrong control is focused. Device testing remains necessary for accessibility traversal and system window behavior.

## Check dynamic announcements

For a noncritical status update, inspect the `LiveRegion` semantics property and the new visible text. For a form error, verify that the error is associated with the intended field when your component exposes that relationship.

A local live-region test can establish that the property is `LiveRegionMode.Polite`. It cannot establish that a service spoke the message exactly once or interrupted at the right time. Avoid continuously announcing rapidly changing values such as a countdown.

Capture failures with the selector, selected tree, expected property, and the relevant semantics dump. Those observations are more actionable than an undifferentiated "accessibility failed" report.

## Cover contrast and motion

Add cases for light and dark themes, large font scale, and any app-owned high-contrast setting. Assert that essential labels and actions remain available. A semantics node can exist even if its text is visually clipped or low contrast.

For reduced motion, test the app's actual motion policy. Inject that policy if the component accepts one, trigger the transition, and assert its final usable state. Do not translate browser `prefers-reduced-motion` into an invented Android system flag.

Use device screenshots or an established rendering suite for text clipping, contrast, and font fallback. Keep locale, theme, font scale, density, and OS version in the evidence. JVM rendering is not evidence of device pixels.

## Keep checks isolated and actionable

Create fresh state and focus requesters per test. Dispose test content through the rule. Restore any accessibility-manager or configuration overrides in cleanup.

Compose assertions synchronize known work. Hold asynchronous status updates with a controllable fake, release it, and then assert the updated semantics. If external work is involved, use a bounded condition or a registered idling resource. Never wait with an arbitrary sleep for an announcement.

Run local accessibility-contract classes in CI using the module's local test task. In an `app` module, a class named `NotificationAccessibilityTest` can be selected with:

```shell
./gradlew :app:testDebugUnitTest --tests '*NotificationAccessibilityTest'
```

Use the actual module and class name. Keep device accessibility checks as a separately visible CI job, not an implied consequence of the local job passing.

## Avoid misleading checks

| Anti-pattern | Failure mechanism | Correct approach |
| --- | --- | --- |
| Assert only that a test tag exists | The control can have no accessible label | Assert meaningful label, role, state, and outcome |
| Require all icon children in the merged tree | Merging represents one user-facing control | Test the group and inspect both trees when needed |
| Suppress every automated violation | New defects disappear with old ones | Use narrow, owned, time-bounded exclusions in the supported checker |
| Test only the initial screen | Errors and dialogs can expose different defects | Exercise critical flows and dynamic states |
| Claim TalkBack support from `assertIsFocused()` | Input focus is not accessibility focus | Add device traversal evidence |

## Troubleshoot failures

| Symptom | Observation to collect | Fix |
| --- | --- | --- |
| Label matcher finds two nodes | Merged and unmerged dumps | Scope by meaningful group and remove unintended duplicate labeling |
| Role assertion fails | Actual role and actions | Use a semantic control or repair the custom control contract |
| Tab does nothing | Initial focus, input mode, event target | Exercise the real focus setup and check the host |
| Error text updates but no speech occurs | Device service state and live-region metadata | Fix semantics or service integration at the layer that fails |
| Accessibility checker cannot initialize locally | Dependency, SDK, runtime exception | Run it in a supported device environment rather than disabling checks globally |

## Review checklist

- [ ] Critical controls expose meaningful labels and appropriate actions.
- [ ] State changes are checked after real user actions.
- [ ] Keyboard focus and accessibility focus are not conflated.
- [ ] Dialog dismissal and focus restoration have explicit cases.
- [ ] Dynamic errors and pending states are covered.
- [ ] Device accessibility and visual checks remain separate evidence.

## Related guides and sources

- [Semantics selectors](../core/semantics-selectors.md) explains identity and merging.
- [Forms and validation](forms-validation.md) covers field errors and submission.
- [Internationalization](i18n.md) covers translated labels and RTL.
- [Accessibility testing](https://developer.android.com/develop/ui/compose/accessibility/testing) describes Android automated and manual checks.
- [Semantics](https://developer.android.com/develop/ui/compose/accessibility/semantics) documents roles, state descriptions, and live regions.
- [Merging and clearing](https://developer.android.com/develop/ui/compose/accessibility/merging-clearing) explains custom control semantics.
- [Compose focus](https://developer.android.com/develop/ui/compose/touch-input/focus) covers keyboard focus behavior.
