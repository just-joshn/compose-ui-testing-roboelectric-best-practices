# Test custom drawing and interactive charts

Use this guide for Compose `Canvas`, custom drawing modifiers, charts, diagrams, and app controls around GPU-backed content. Test data transformations and interactions locally. Add screenshot checks when pixels are part of the contract, and device tests when the claim depends on graphics hardware.

## Table of contents

- [Choose the evidence](#choose-the-evidence)
- [Expose meaningful semantics](#expose-meaningful-semantics)
- [Test a selectable chart](#test-a-selectable-chart)
- [Test drawing and gestures](#test-drawing-and-gestures)
- [Control animation and simulation](#control-animation-and-simulation)
- [Add visual checks](#add-visual-checks)
- [Test GPU and library integration](#test-gpu-and-library-integration)
- [Avoid brittle checks](#avoid-brittle-checks)
- [Isolate and synchronize](#isolate-and-synchronize)
- [Troubleshoot failures](#troubleshoot-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the evidence

| Question | Best first test | What it does not prove |
| --- | --- | --- |
| Are points scaled correctly? | Pure geometry test with fixed input and bounds | Rendering |
| Does selecting a chart show the right value? | Compose interaction and visible detail assertion | Exact chart pixels |
| Is the chart accessible by meaning? | Semantics assertions and actions | TalkBack traversal |
| Does a stroke become an editable object? | Gesture test followed by object count or selection UI | Stylus hardware behavior |
| Did colors or spacing change? | Optional screenshot comparison in a pinned renderer | Device fidelity |
| Does an OpenGL scene render correctly? | Instrumented graphics test on representative devices | All GPU drivers |
| Does a game advance correctly? | Pure simulation step tests and UI result tests | Frame rate |

A `Canvas` does not create one semantics node per shape. Its composable existence is not evidence that a bar, label, or selected point is visible. Give interactive drawing useful semantics as a product requirement, not a private backdoor into draw commands.

## Expose meaningful semantics

Expose a chart summary and its selected value. For charts with many data points, provide an accessible alternative such as a table or next-point action. A single giant content description is rarely a usable interaction model.

Separate the data shape from rendering:

- Domain data contains point identity, label, and value.
- Geometry maps the data to positions within supplied bounds.
- Interaction selects domain identity from a position or semantic action.
- UI state shows the selected label and value.

Test the mapping independently at empty data, equal values, negative values, and resized bounds. Use deterministic data. Do not make the UI test derive expected results with the same production scaling function because both paths could share the same defect.

## Test a selectable chart

This illustrative example uses one selectable chart region. A production chart with multiple points needs point-specific selection or equivalent accessible actions. The example is not compiled by the fixture.

It requires Compose Foundation, Material3, UI testing, JUnit 4, Robolectric, Android resources, and the default activity host from [setup](../references/setup.md).

```kotlin
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.unit.dp
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class ChartSelectionTest {
	@get:Rule val compose = createComposeRule()

	@Test fun selectingChartShowsValue() {
		compose.setContent {
			var selected by remember { mutableStateOf(false) }
			Column {
				Canvas(
					Modifier.size(160.dp)
						.semantics { contentDescription = "January sales chart" }
						.clickable { selected = true }
				) {
					drawRect(Color.Blue)
				}
				if (selected) Text("January sales: 12")
			}
		}
		compose.onNodeWithContentDescription("January sales chart")
			.performClick()
		compose.onNodeWithText("January sales: 12").assertIsDisplayed()
	}
}
```

The expected observable result is the detail text after selection. A no-op selection must fail the final assertion. The test does not prove that the blue rectangle rendered, or that a coordinate hit-test selects the correct point.

For a real chart library, mount the app's actual chart wrapper with fixed series data. Assert loading, empty, populated, and selected states. Reading the library's internal data array can supplement this check but cannot replace the visible selected result.

## Test drawing and gestures

Use semantic actions when the claim is selecting a data item. Use touch input when the claim is coordinate routing, drag recognition, or stroke creation.

The following illustrative fragment belongs inside a rule test with an already mounted `drawing-board`. It requires `Offset`, `onNodeWithTag`, `performTouchInput`, and `onNodeWithText` imports. Import `assertIsDisplayed` for the final assertion.

```kotlin
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performTouchInput

compose.onNodeWithTag("drawing-board").performTouchInput {
	down(Offset(width * 0.2f, height * 0.2f))
	moveTo(Offset(width * 0.8f, height * 0.8f))
	up()
}
compose.onNodeWithText("1 stroke").assertIsDisplayed()
```

Coordinates are local pixels in the selected node. Derive them from node dimensions rather than screen constants. Specify a duration and intermediate moves when velocity or sampling is part of the behavior.

For object dragging, assert the moved object's coordinates through user-visible properties or a selection inspector, and assert that another object is unchanged. A generic "something was drawn" check can pass if the wrong object moves.

For zoom, test the mathematical transform separately, then inject a supported multi-pointer gesture for the UI recognizer and assert the displayed zoom value. The complete [two-pointer pinch example](gestures.md#inject-a-two-pointer-pinch) mounts a real `transformable` canvas, moves pointer IDs 0 and 1 together, releases or cancels them, and checks the visible zoom percentage. It also verifies that a new gesture works after cancellation. Include minimum and maximum zoom cases for your editor. A single tap is not a pinch test.

## Control animation and simulation

Disable automatic clock advancement before triggering a transition when an intermediate frame is the target. Establish the transition's start, advance to the chosen frame, and assert the associated state. Use the canonical [clock test](../examples/FixtureUiTest.kt) for stable 1.12.1 scheduling patterns.

Keep separate clocks separate. `mainClock` drives Compose frames. A chart library's executor, a simulation timestep, and a wall-clock timestamp do not necessarily use it.

For a simulation, inject a deterministic step source. Test the same input sequence against initial state and assert the resulting score or scene state. Then render a selected state in Compose. This allows a frame-11 screenshot without depending on the machine rendering eleven frames at real-time speed.

A virtual one-second animation completing in a local test says nothing about frames per second. Use [performance testing](performance-testing.md) for device timing.

## Add visual checks

Use a screenshot tool compatible with the project's Android test environment when shape, color, or placement matters. Robolectric screenshot integrations are optional additions to the semantic suite. This fixture does not validate a screenshot plugin or baseline comparator.

Follow this sequence:

1. Freeze chart data, locale, fonts, theme, density, dimensions, and time.
2. Hold external loading until deterministic data is available.
3. Settle the chosen animation state and synchronize pending drawing.
4. Capture the smallest region that includes the drawing and relevant labels.
5. Compare against a reviewed baseline from the same renderer configuration.
6. Retain expected, actual, and diff images on failure.

A non-empty image or one non-white pixel is weak evidence. The chart could contain only a background or an unrelated icon. Use region comparison or focused pixel properties only when those properties express a real visual contract.

Thresholds belong to the selected comparison tool. Do not copy browser screenshot option names into Compose code. Inspect a diff before increasing tolerance, especially for thin lines or small selection markers.

## Test GPU and library integration

For OpenGL, Vulkan, `SurfaceView`, video, maps, or external renderer content, test the surrounding app locally with a deterministic renderer adapter. Cover ready, loading, unavailable, and error states. Verify that user commands contain the intended scene or camera identity.

Then test the real renderer on Android:

1. Load a fixed scene and wait for the renderer's ready signal.
2. Assert actual scene output using its supported capture mechanism.
3. Rotate or zoom through input and verify the camera or visible result.
4. Exercise pause, resume, and resource release.
5. Record device, API, GPU, driver where available, and renderer version.

A successful EGL context creation does not prove correct shading or texture upload. A semantic placeholder around a surface does not prove that surface contains pixels.

For a third-party chart wrapper, keep adapter tests against its supported public API. Avoid inspecting private view fields that change across library versions.

## Avoid brittle checks

Bad practice is hardcoding screen coordinates and asserting only that the canvas still exists. The test can tap the wrong region and pass.

Correct it by selecting the intended drawing node, computing local coordinates, and asserting the selected item's visible detail. Add a separate visual assertion if geometry is the promise.

Do not repair a blank screenshot with a sleep. Check data readiness, frame ownership, drawing synchronization, capture support, and clipping in that order.

## Isolate and synchronize

Create fresh scene models and deterministic random seeds per test. Dispose renderers and cancel animation loops in cleanup. Restore clock settings if a shared helper changes them within a test.

Do not register an idling resource that stays busy forever for a deliberately continuous animation. Expose a finite readiness condition or control the animation state for capture.

## Troubleshoot failures

| Symptom | Observe | Correction |
| --- | --- | --- |
| Canvas exists but no point is found | Actual semantics tree | Add meaningful accessible selection, not draw-command tags |
| Tap selects the wrong point | Bounds, density, transform, and hit-test input | Use node-local coordinates and test transform edges |
| Screenshot is blank | Renderer readiness and capture support | Synchronize drawing or use the renderer's capture path |
| Random chart diffs | Seed, data order, fonts, and animation state | Pin inputs before changing tolerance |
| Test never becomes idle | Infinite work and registered resources | Control the finite state being tested |
| Local pass but device corruption | GPU-specific output and lifecycle | Add a real-renderer device regression |

## Review checklist

- [ ] The test separates geometry, interaction, and visual claims.
- [ ] Coordinate input uses bounds in the correct coordinate system.
- [ ] A user-visible result follows each interaction.
- [ ] Animation and external renderer clocks have explicit owners.
- [ ] Screenshots name their renderer, baseline configuration, and limits.
- [ ] GPU behavior has separate Android evidence.

## Related guides and sources

- [Visual regression](visual-regression.md) covers baseline review.
- [Accessibility](accessibility.md) covers semantics contracts.
- [Compose graphics](https://developer.android.com/develop/ui/compose/graphics/draw/overview) describes drawing APIs.
- [Compose semantics](https://developer.android.com/develop/ui/compose/accessibility/semantics) describes custom-component meaning.
- [Test synchronization](https://developer.android.com/develop/ui/compose/testing/synchronization) describes frame and external-work controls.
- [Evidence limits](../references/evidence.md) states what the canonical fixture does not establish.
