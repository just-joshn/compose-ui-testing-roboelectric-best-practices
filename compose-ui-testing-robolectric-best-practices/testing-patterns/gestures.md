# Test gestures and drag operations

Use this guide for swipe actions, reorderable lists, board movement, custom drag handles, and pinch zoom in Compose. Test pointer recognition and resulting UI locally with Robolectric. Use device integration tests for Android cross-window drag-and-drop, external content permissions, and hardware input behavior.

## Table of contents

- [Choose an interaction method](#choose-an-interaction-method)
- [Establish the gesture contract](#establish-the-gesture-contract)
- [Inject a local drag](#inject-a-local-drag)
- [Move cards between columns](#move-cards-between-columns)
- [Verify list order](#verify-list-order)
- [Test previews and cancellation](#test-previews-and-cancellation)
- [Test custom drawing and resize handles](#test-custom-drawing-and-resize-handles)
- [Inject a two-pointer pinch](#inject-a-two-pointer-pinch)
- [Cover keyboard and accessibility alternatives](#cover-keyboard-and-accessibility-alternatives)
- [Separate native drag-and-drop](#separate-native-drag-and-drop)
- [Check persistence and undo](#check-persistence-and-undo)
- [Synchronize and isolate gesture tests](#synchronize-and-isolate-gesture-tests)
- [Avoid brittle gestures](#avoid-brittle-gestures)
- [Troubleshoot failures](#troubleshoot-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose an interaction method

| Claim | Method | Required result |
| --- | --- | --- |
| A semantic button activates an action | `performClick` | New content or state |
| A swipe dismisses an item | `performTouchInput` with a swipe | Intended item disappears and undo appears |
| Long-press drag reorders an item | Down, hold, incremental move, up | Full expected order |
| A board card moves to a column | Root-relative touch sequence | Destination contains the same card, source does not |
| Keyboard users can reorder | Focus and supported key events | Same order change as touch |
| Accessibility users can move an item | Exposed custom semantics action | Same result as the gesture |
| A file arrives from another app | Device drag-and-drop or picker integration | URI access and imported content |
| A shape snaps to a grid | Pointer sequence plus model or geometry checks | Correct logical position and visible result |
| A pinch changes zoom | Two pointer IDs with shared move events | Displayed zoom changes, then both pointers release or cancel |

A semantic click does not prove hit testing or touch slop. A touch gesture does not prove an accessibility alternative exists. Keep tests for both when both are product requirements.

## Establish the gesture contract

Before injecting events, record:

- The actual pointer target, such as a dedicated reorder handle.
- Whether recognition starts immediately or after a long press.
- The movement threshold and allowed axis.
- The target region and the expected final identity or order.
- Whether committing occurs during movement or on release.
- What cancellation and rejection do to visible state.

Mount the smallest real UI that owns this contract with fresh items and stable IDs. Set a deterministic size when geometry is material to the test. Do not rely on one developer's monitor dimensions or density.

The examples below are illustrative fragments for a hosted Compose UI 1.12.1 rule named `compose`. They require Android local-test setup from [the setup reference](../references/setup.md). They are not compiled fixture examples.

## Inject a local drag

`performTouchInput` coordinates are local to the selected node. Query bounds in the root coordinate system, subtract the gesture host's origin, and inject all events through the same host.

This fragment assumes `board`, `card-42-handle`, and `column-active` are unique test tags on laid-out nodes. The board covers the complete path. The app uses a 500 ms long-press policy, so the test holds for 600 ms before moving. Use the actual product policy rather than copying that duration blindly.

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performTouchInput

val board = compose.onNodeWithTag("board")
val handle = compose.onNodeWithTag("card-42-handle")
val target = compose.onNodeWithTag("column-active")
handle.assertIsDisplayed()
target.assertIsDisplayed()

val boardBounds = board.fetchSemanticsNode().boundsInRoot
val start = handle.fetchSemanticsNode().boundsInRoot.center - boardBounds.topLeft
val end = target.fetchSemanticsNode().boundsInRoot.center - boardBounds.topLeft

board.performTouchInput {
	down(start)
	advanceEventTime(600)
	for (step in 1..12) {
		moveTo(start + (end - start) * (step / 12f), delayMillis = 16)
	}
	up()
}
```

The loop supplies intermediate motion events. A single teleport may skip the recognizer's threshold or the app's intermediate hit regions. The event timestamps establish the input sequence. They are not sleeps and do not measure latency.

If the component starts dragging immediately, omit the long-press hold. If the behavior is only horizontal dismissal, use the appropriate swipe helper instead of manually reproducing every move.

Do not fetch geometry while a layout transition is still moving the target. Settle the layout first or explicitly control the animation to a known frame.

## Move cards between columns

After the gesture, verify identity and membership rather than only a drop callback. This fragment assumes card nodes retain `card-42`, column groups remain ancestors in the selected tree, and their semantics do not merge away the card identity.

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasAnyAncestor
import androidx.compose.ui.test.hasTestTag

compose.onNode(
	hasTestTag("card-42") and hasAnyAncestor(hasTestTag("column-active"))
).assertIsDisplayed()
compose.onNode(
	hasTestTag("card-42") and hasAnyAncestor(hasTestTag("column-backlog"))
).assertDoesNotExist()
```

If the card itself owns a merged column label, select that actual structure instead. Inspect the tree before writing an ancestor matcher.

For a workflow board, test one valid transition and one rejected transition independently. A single test that drags through every column can fail early and leave later rules untested.

If column counts are part of the UI, assert the changed counts and an unaffected card. A test that only sees the destination label can pass even if the app duplicates the card instead of moving it.

## Verify list order

Use stable IDs for gesture targets. Use index assertions only when order is itself the contract.

For a fully materialized vertical three-row list, assert the visible labels in top-to-bottom order after moving C before A. This fragment assumes the three queried nodes each expose one text entry and occupy distinct vertical positions.

```kotlin
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.hasAnyAncestor
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.hasText
import org.junit.Assert.assertEquals

val labels = compose.onAllNodes(
	hasAnyAncestor(hasTestTag("priorities")) and
		(hasText("Priority A") or hasText("Priority B") or hasText("Priority C"))
).fetchSemanticsNodes().sortedBy { it.boundsInRoot.top }.map { node ->
	node.config[SemanticsProperties.Text].single().text
}
assertEquals(listOf("Priority C", "Priority A", "Priority B"), labels)
```

Do not apply that collection pattern to an entire lazy list. Offscreen items may not be composed. For a large list, assert the affected visible positions and verify the repository's complete persisted order in a separate contract test.

A dedicated handle needs its own case. Dragging anywhere on a row can pass even when the handle is broken or scrolling is unintentionally intercepted.

Cover edge placement, moving to the same position, moving to the end, and dragging across an auto-scroll boundary when the app implements those behaviors. For auto-scroll, explicitly progress the work owner between movement steps. Do not replace the scenario with an unbounded drag duration.

## Test previews and cancellation

To observe in-progress feedback, split the sequence across `performTouchInput` calls on the same host.

1. Send down, hold if required, and move into the active drag region.
2. Assert the preview text or placeholder state outside the injection lambda.
3. Send the remaining move and up events.
4. Assert the preview is gone and the final arrangement is correct.

Input state can continue across calls. Every successful test path must release or cancel the pointer. If the first assertion fails, ensure cleanup cancels an active sequence rather than leaving later actions in a pressed state.

For cancellation, begin a real drag, send `cancel()`, and assert that the item returns to its original position. Verify that no committed repository change appears. Pair that negative case with a successful drop that does commit.

For a multiselect drag, select the items through the real selection UI. Assert the preview's item count, release into the destination, and check all selected identities moved while an unselected item stayed behind.

Do not perform synchronized assertions inside the `performTouchInput` lambda. Events are batched, and the UI may not have received the sequence yet.

## Test custom drawing and resize handles

For a drawing editor, distinguish logical coordinates from physical pixels. A grid cell of 20 logical units is not necessarily 20 root pixels at every density or zoom.

Capture the editor transform and derive the expected root-space target. Inject through the editor node. Assert the model-facing position exposed by the UI contract, such as a coordinates panel, and optionally compare final bounds with a defined pixel tolerance.

For snapping, choose a point away from a tie boundary and assert the exact snapped logical coordinate. For constraints, drag beyond each boundary and assert the shape remains inside. For resizing, drag the actual handle and check both dimensions and any minimum-size rule.

A Canvas may expose no semantics for individual shapes. Add meaningful user-facing semantics or a separate coordinate display if the product needs accessible manipulation. Do not infer which shape moved from a callback count alone.

Use a dedicated rendering or device suite for drag shadows, clipping, and GPU effects. A local bounds assertion cannot establish the preview's visual fidelity.

## Inject a two-pointer pinch

Use two pointer identities and move both positions before emitting each shared move event. Two independent swipes are not a pinch. `updatePointerTo` changes a pointer's pending position without sending an event. `move` sends the positions together.

This standalone illustrative test mounts a real Foundation `transformable` recognizer. It uses Compose Foundation and UI test 1.12.1, Material3, and the Robolectric host from [setup](../references/setup.md). The test is not part of the canonical fixture. `ZoomState.factor` is the domain state. The recognizer applies live zoom, clamped from 1 to 3, to both the drawing and a visible percentage. This centered-circle component ignores pan, rotation, and gesture centroid. An editor that zooms around a touched point must retain and test those transforms too. Cancellation keeps the already applied zoom, ends the input sequence, and does not promise rollback.

```kotlin
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.rememberTransformableState
import androidx.compose.foundation.gestures.transformable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.SemanticsNodeInteraction
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertTextEquals
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performTouchInput
import androidx.compose.ui.unit.dp
import kotlin.math.roundToInt
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

private data class ZoomState(val factor: Float = 1f)

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class PinchZoomTest {
	@get:Rule val compose = createComposeRule()

	private fun mountEditor() {
		compose.setContent {
			var zoom by remember { mutableStateOf(ZoomState()) }
			val transform = rememberTransformableState { _, zoomChange, _, _ ->
				zoom = zoom.copy(factor = (zoom.factor * zoomChange).coerceIn(1f, 3f))
			}
			Column {
				Canvas(Modifier.size(240.dp).testTag("zoom-canvas").transformable(transform)) {
					drawCircle(Color.Blue, radius = size.minDimension * 0.1f * zoom.factor)
				}
				Text("${(zoom.factor * 100).roundToInt()}%", Modifier.testTag("zoom-value"))
			}
		}
	}

	private fun SemanticsNodeInteraction.pinchOut(release: Boolean) {
		performTouchInput {
			val y = height * 0.5f
			down(pointerId = 0, position = Offset(width * 0.35f, y))
			down(pointerId = 1, position = Offset(width * 0.65f, y))
			for (step in 1..10) {
				val spread = 0.15f + 0.02f * step
				updatePointerTo(0, Offset(width * (0.5f - spread), y))
				updatePointerTo(1, Offset(width * (0.5f + spread), y))
				move(delayMillis = 16)
			}
			if (release) {
				up(pointerId = 0)
				up(pointerId = 1)
			} else {
				cancel()
			}
		}
	}

	private fun visibleZoomPercent(): Int {
		val label = compose.onNodeWithTag("zoom-value").assertIsDisplayed()
			.fetchSemanticsNode().config[SemanticsProperties.Text].single().text
		return label.removeSuffix("%").toInt()
	}

	private fun SemanticsNodeInteraction.cancelRemainingPointers() {
		performTouchInput {
			if (currentPosition(0) != null || currentPosition(1) != null) cancel()
		}
	}

	@Test fun pinchOutChangesDisplayedZoom() {
		mountEditor()
		val canvas = compose.onNodeWithTag("zoom-canvas")
		compose.onNodeWithTag("zoom-value").assertTextEquals("100%")
		try {
			canvas.pinchOut(release = true)
			assertTrue("A pinch must visibly zoom in", visibleZoomPercent() in 126..300)
		} finally {
			canvas.cancelRemainingPointers()
		}
	}

	@Test fun cancellationRetainsLiveZoomAndAllowsAnotherGesture() {
		mountEditor()
		val canvas = compose.onNodeWithTag("zoom-canvas")
		try {
			canvas.pinchOut(release = false)
			val afterCancel = visibleZoomPercent()
			assertTrue("Live zoom survives cancellation", afterCancel in 126..299)
			canvas.pinchOut(release = true)
			assertTrue("A new pinch is recognized", visibleZoomPercent() > afterCancel)
		} finally {
			canvas.cancelRemainingPointers()
		}
	}
}
```

All pointer positions use canvas-local pixels. The first movements cross the recognizer's touch slop, so the test checks a meaningful zoom range rather than claiming an exact geometric ratio. Event-time increments do not advance wall time. Assertions occur after event delivery, outside the injection block. The `finally` cleanup cancels any pointer left down if injection or an assertion fails.

Add separate inward and outward cases at the product's minimum and maximum zoom. A production editor that commits only on release needs a different cancellation assertion. Check its visible committed value and persistence boundary, not this sample's live-update policy. This example proves pointer recognition and visible state, not rendered pixels or hardware multitouch fidelity.

The multi-pointer signatures above were checked against the pinned `ui-test-android:1.12.1` AAR's `TouchInjectionScope` interface, including `down`, `updatePointerTo`, `move`, `up`, `currentPosition`, and `cancel`. Consult the [touch API reference](https://developer.android.com/reference/kotlin/androidx/compose/ui/test/TouchInjectionScope) when adapting to another version.

## Cover keyboard and accessibility alternatives

If the product supports keyboard reordering, focus the named handle and inject its actual activation and arrow-key sequence. Assert the same complete order as the touch case.

For accessibility custom actions, invoke the action by its meaningful label through the semantics action API for your installed Compose version. Assert the resulting order or column. This tests the exposed action handler, not TalkBack's action menu.

Keep focus and selection setup explicit. Do not invent Space-to-grab behavior because a browser drag library uses it. Native apps choose their own supported keyboard contract.

## Separate native drag-and-drop

Compose pointer dragging is different from Android platform drag-and-drop. A local touch sequence does not create a `ClipData` transfer from another application.

For incoming documents, locally test your URI-processing boundary with controlled MIME type, filename, bytes, cancellation, and rejection. Assert the imported item or error text. Use a device test to establish drag event delivery, URI grants, source-app interaction, and permission lifetime.

For Android View interop or cross-window dragging, use [View interop](../android-apis/view-interop.md) and a device integration case. There is no native equivalent of dispatching HTML `DataTransfer` to an iframe.

## Check persistence and undo

A successful reorder UI test proves only the mounted UI path when the repository is fake. To prove persistence, test the real repository against an isolated store, write the new order, construct a new reader, and verify the saved order.

For an end-to-end device case, perform the gesture, wait for the actual save boundary, relaunch or recreate through the supported lifecycle, and verify the arrangement. State exactly which lifecycle was exercised. Remounting a composable does not prove process-death recovery.

If undo exists, assert the post-drag arrangement, activate **Undo**, and verify the original order and repository state. A callback named `undo` is not sufficient evidence.

## Synchronize and isolate gesture tests

Create fresh item lists, selection state, repository fakes, and geometry per test. Never reuse a pressed pointer sequence or a shared mutable board.

Use event time for input recognition. Use `mainClock` for Compose animation and recomposition. Use a controlled fake or bounded wait for external persistence. These controls are not interchangeable.

Keep auto-advance enabled for ordinary final-state checks. When observing a transient preview animation, disable it deliberately and advance to the frame you intend to inspect.

## Avoid brittle gestures

| Anti-pattern | Failure mechanism | Correction |
| --- | --- | --- |
| Hardcode screen coordinates | Density and layout changes hit another item | Derive local coordinates from measured bounds |
| Call a move callback directly | Pointer recognition can be broken | Inject touch through the real handle |
| Assert only a save call | UI can duplicate or lose the item | Assert identity, membership, and order |
| Use index zero for a repeated label | A different item can move | Select stable identity |
| Sleep for long-press recognition | Wall-clock delay is unrelated to injected event timestamps | Advance event time in the gesture |
| Claim native file drop from a fake URI | Platform delivery and grants were bypassed | Add device integration evidence |

## Troubleshoot failures

| Symptom | Observe | Fix |
| --- | --- | --- |
| Drag becomes a scroll | Handle target, hold duration, touch slop | Match the real recognizer and use incremental movement |
| Item jumps to the wrong location | Root bounds, host origin, density | Convert into one host's local coordinates |
| Preview never appears | Event batching and recognizer state | Split injection calls and inspect after delivery |
| Result disappears after refresh | Actual repository save and read | Test persistence separately from optimistic UI |
| Collection omits rows | Lazy composition and viewport | Assert visible positions and repository order separately |
| Test hangs after an assertion | Unreleased pointer or busy work | Cancel input and clean up owned work |

## Review checklist

- [ ] The test targets the intended handle by identity.
- [ ] Coordinates share one explicit coordinate system.
- [ ] Recognition thresholds and event time are deliberate.
- [ ] Final membership or order is asserted.
- [ ] Cancellation, rejection, and undo match product requirements.
- [ ] Pointer input ends with release or cancellation.
- [ ] A pinch uses two pointer identities and checks visible zoom, including cancellation behavior.
- [ ] Platform drag-and-drop claims have device evidence.

## Related guides and sources

- [Custom drawing](custom-drawing.md) covers Canvas testing boundaries.
- [Repository contracts](repository-contracts.md) covers persistence and request behavior.
- [Accessibility](accessibility.md) covers alternative actions and focus.
- [TouchInjectionScope](https://developer.android.com/reference/kotlin/androidx/compose/ui/test/TouchInjectionScope) documents event timing and local coordinates.
- [Compose drag, swipe, and fling](https://developer.android.com/develop/ui/compose/touch-input/pointer-input/drag-swipe-fling) describes gesture recognition.
- [Compose drag-and-drop](https://developer.android.com/develop/ui/compose/touch-input/user-interactions/drag-and-drop) describes Android transfer integration.
