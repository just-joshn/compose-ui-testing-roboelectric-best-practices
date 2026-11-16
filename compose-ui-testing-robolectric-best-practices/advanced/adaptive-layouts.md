# Test adaptive layouts and touch behavior

## Table of contents

- [Choose a layout test layer](#choose-a-layout-test-layer)
- [Build a configuration matrix](#build-a-configuration-matrix)
- [Test layout policy separately from window integration](#test-layout-policy-separately-from-window-integration)
- [Exercise compact navigation and sheets](#exercise-compact-navigation-and-sheets)
- [Drive touch gestures](#drive-touch-gestures)
- [Test size changes without losing state](#test-size-changes-without-losing-state)
- [Synchronize and isolate configurations](#synchronize-and-isolate-configurations)
- [Avoid false device emulation](#avoid-false-device-emulation)
- [Troubleshoot](#troubleshoot)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose a layout test layer

Use this guide for compact and expanded navigation, list-detail layouts, orientation-sensitive behavior, and touch interactions in local Compose tests. Robolectric supplies Android configuration and a hosted Compose tree. It does not emulate a named phone's hardware, real IME, fold posture, or graphics stack.

| Claim | Local approach | Additional layer |
| --- | --- | --- |
| Compact policy shows bottom navigation | Inject compact policy into real UI | Window-policy integration |
| Available width selects two panes | Real constraint or window-size calculation | Device resizing and multi-window |
| Swipe dismisses an item | Compose touch injection and visible result | Device gesture conflicts |
| Font scaling keeps action reachable | Controlled font scale and bounds | Device visual and accessibility review |
| Fold posture avoids hinge | Inject posture model into layout policy | Foldable emulator or device |
| Content avoids system bars and keyboard | Limited local state tests | Device insets and IME checks |
| Layout looks correct in pixels | Dedicated screenshot environment | Device rendering when fidelity matters |

Use Android `src/test`, `testImplementation`, resources, and a Robolectric host as described in [setup](../references/setup.md). Keep the app's dependency versions unless there is a specific compatibility reason to change them.

## Build a configuration matrix

Choose cases from the application's actual adaptation policy. Do not copy web CSS breakpoints or assume dp equals pixels.

| Dimension | Representative cases | Behavior to inspect |
| --- | --- | --- |
| Width | Below, at, and above the actual policy threshold | Navigation and pane changes |
| Height | Short landscape and tall portrait | Actions remain reachable |
| Font scale | Default and a supported larger scale | Text wrapping and scrolling |
| Density | Selected resource densities | dp-to-pixel assumptions |
| Direction | LTR and RTL | Navigation placement and gestures |
| Content | Empty, long text, and populated list | Overflow and duplicate identities |
| Posture | Product-supported flat and separating states | Pane placement |

Keep the matrix bounded. Test the policy around each boundary, then choose representative full-screen cases. A Cartesian product of every configuration usually adds repeated assertions without a new claim.

A Robolectric configuration example is illustrative and uses `org.robolectric.annotation.Config`:

```kotlin
import org.robolectric.annotation.Config

@Config(sdk = [35], qualifiers = "w360dp-h640dp-port")
class CompactInboxTest

@Config(sdk = [35], qualifiers = "w840dp-h600dp-land")
class ExpandedInboxTest
```

These class declarations show qualifier placement, not runnable tests. Add the runner, rule, and methods from the [canonical test](../examples/FixtureUiTest.kt). Inspect the host's actual constraints. Resource qualifiers alone do not prove the available content window has exactly those dimensions after decor, insets, or application constraints.

For resource selection, use real qualifiers. For a component's adaptation policy, pass a small explicit layout model. For a constraints-driven composable, host it under known parent constraints that fit within the actual root.

## Test layout policy separately from window integration

The data shape should describe what the layout needs, such as `Compact` or `Expanded`, rather than a string naming a device. Keep conversion from real window information in an adapter with its own tests.

Illustrative component and test-body fragment. It requires Compose foundation, Material3, runtime, and UI test artifacts. `rule` is the configured v2 rule. This fragment tests injected policy, not real window-size classification.

```kotlin
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick

enum class MailLayout { Compact, Expanded }

@Composable
fun MailNavigation(layout: MailLayout, onInbox: () -> Unit) {
	Column {
		Text(if (layout == MailLayout.Compact) "Bottom navigation" else "Navigation rail")
		Button(onClick = onInbox) { Text("Inbox") }
	}
}

val layout = mutableStateOf(MailLayout.Compact)
val destination = mutableStateOf("Home")
rule.setContent {
	Column {
		MailNavigation(layout.value) { destination.value = "Inbox opened" }
		Text(destination.value)
	}
}
rule.onNodeWithText("Bottom navigation").assertIsDisplayed()
rule.onNodeWithText("Inbox").performClick()
rule.onNodeWithText("Inbox opened").assertIsDisplayed()
rule.runOnIdle { layout.value = MailLayout.Expanded }
rule.onNodeWithText("Navigation rail").assertIsDisplayed()
rule.onNodeWithText("Bottom navigation").assertDoesNotExist()
rule.onNodeWithText("Inbox opened").assertIsDisplayed()
```

In a real app, assert the actual navigation controls instead of adding diagnostic text such as "Navigation rail" for the test. Use meaningful semantics for stable group identity when labels cannot distinguish the alternatives.

Then test the adapter using its real window inputs. Verify threshold-minus-one, threshold, and threshold-plus-one values in the units that adapter accepts. Do not compute the expected branch by calling the same classifier under test.

## Exercise compact navigation and sheets

For a compact navigation drawer, assert it is initially closed. Click the menu action, select a destination within the drawer, and assert both the destination content and drawer dismissal.

Use descendant scoping when a destination label also exists in the main content. Do not repair duplicate **Inbox** matches with `[0]`.

For a modal sheet, open it through the real action. Select an option, confirm, and assert the resulting screen state. Also test cancellation if dismissal is part of the contract.

A sheet is not always a dialog semantics node. Inspect the actual Material component's tree before choosing `isDialog()`. Scope by the sheet's meaningful content or stable group identity when necessary.

For pull to refresh, inject a controlled refresh repository. Keep the result pending so the refreshing state can be asserted. Complete it with changed content and assert the change. A spinner alone cannot prove that refreshed data was displayed.

## Drive touch gestures

Use semantic `performClick()` for activation tests. Use touch injection only when pointer movement, duration, or position is the behavior under test.

Illustrative test-body fragment. It assumes `InboxRoute(repository)` renders a tagged `message-alex` row with swipe-to-reveal and a tagged `feed` container. The repository is test-owned. Required touch APIs come from Compose UI test.

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTouchInput
import androidx.compose.ui.test.swipeLeft

rule.onNodeWithTag("message-alex").performTouchInput { swipeLeft() }
rule.onNodeWithText("Delete Alex's message").assertIsDisplayed()
rule.onNodeWithText("Delete Alex's message").performClick()
rule.onNodeWithTag("message-alex").assertDoesNotExist()
rule.onNodeWithTag("message-bob").assertIsDisplayed()
```

The unchanged Bob row catches wrong-target deletion. If deletion is asynchronous, hold it pending and complete the fake before asserting removal according to the product's optimistic or confirmed behavior.

For long press, use Compose's touch gesture support and assert the contextual actions. For pinch, use multi-pointer injection supported by the resolved test library when the app actually implements pinch. Calling the zoom setter directly tests state rendering, not pinch recognition.

Do not hardcode screen coordinates copied from a screenshot. Inject relative to the intended node's bounds. Use device tests for conflicts with Android edge gestures, physical touch behavior, and accessibility services.

## Test size changes without losing state

A static compact test and static expanded test do not prove adaptation during an active session.

Start on a compact list, select a stable item, enter a draft, and change the layout input. Assert that selection and draft remain correct in the expanded view. Change back and assert the product's expected single-pane destination.

Keep one `setContent` call. Change observable input or drive a real host configuration transition. Replacing the whole composition with another `setContent` is not a resize and can discard the state you intend to test.

Separate three claims:

- Updating an injected layout policy tests UI adaptation to that model.
- Activity recreation tests saved state and host lifecycle behavior.
- Real multi-window resizing tests Android window integration.

If the activity supplies content, let `createAndroidComposeRule` launch it. Install dependencies before launch and do not add a second content owner.

## Synchronize and isolate configurations

Create fresh selection, navigation state, repository, and layout model for each test. Keep qualifier changes local to a test or class. Restore any legacy global density, locale, or time-zone changes.

Allow ordinary navigation animations to settle through default Compose synchronization. Pause the Compose clock only to inspect an intermediate animation state. Completing refresh requires releasing the fake, not advancing animation time.

A layout assertion must check the actual user outcome. If content is offscreen in a scroll container, use the relevant scroll action and assert reachability. `assertExists()` alone does not prove that an action is displayed or usable.

## Avoid false device emulation

Bad practice is to label a `w360dp` Robolectric test "Pixel hardware verified". Qualifiers do not emulate hardware, system UI, IME, or GPU behavior.

Correct it by naming the claim "compact-width navigation" and documenting the input configuration. Run the hardware-dependent behavior on the intended device or emulator.

Another anti-pattern tests only the compact branch and assumes all larger windows behave the same. Add actual policy boundaries and a populated list-detail case. Assert content identity and navigation outcomes, not just the existence of a rail.

## Troubleshoot

| Symptom | Observation | Correction |
| --- | --- | --- |
| Expanded branch never appears | Actual parent constraints and classifier input | Supply the real input or test adapter separately |
| Large text action exists but cannot be used | Display bounds and scroll semantics | Assert reachability and scroll to it |
| Drawer selection is ambiguous | Both main and drawer labels | Scope by actual ancestor identity |
| Gesture hits another row | Selected node bounds and lazy-list identity | Scroll to and match the intended row |
| Resize loses draft | State ownership and recreation path | Test the production retention policy |
| Local layout passes, IME obscures action | Real insets and keyboard behavior | Add a device scenario |

## Review checklist

- Does the matrix follow the app's real policy instead of web breakpoints?
- Are dp, pixels, density, font scale, and available window size distinct?
- Are static rendering, live adaptation, recreation, and device resizing separate claims?
- Do gesture tests assert the changed item and important unchanged items?
- Are sheet and drawer selectors grounded in the actual semantics tree?
- Are system UI, fold hardware, pixels, and performance handed to the right layer?

## Related guides and sources

- [Gestures](../testing-patterns/gestures.md), [multiple roots](multiple-roots.md), and [visual regression](../testing-patterns/visual-regression.md).
- [Semantics selectors](../core/semantics-selectors.md) and [clock control](clock-control.md).
- [Android adaptive layouts](https://developer.android.com/develop/ui/compose/layouts/adaptive) describes adaptive design and window information.
- [Compose testing APIs](https://developer.android.com/develop/ui/compose/testing/apis) describes semantics and input.
- [Robolectric configuration](https://robolectric.org/configuring/) describes qualifiers.
- [Evidence and limits](../references/evidence.md) bounds the validated JVM environment.
