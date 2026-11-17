# Assertions & Actions

## Table of Contents

1. [Assertions](#assertions)
2. [Collection Assertions](#collection-assertions)
3. [Bounds Assertions](#bounds-assertions)
4. [Actions](#actions)
5. [Touch Input](#touch-input)
6. [Key Input and Focus](#key-input-and-focus)
7. [Text Input](#text-input)
8. [Scrolling](#scrolling)
9. [Chaining and Return Values](#chaining-and-return-values)
10. [Related References](#related-references)
11. [Sources](#sources)

## Assertions

Assertions are used to verify that the elements exist or have certain attributes.

Check assertions by calling `assert()` on the `SemanticsNodeInteraction` returned by a finder with one or multiple matchers:

```kotlin
// Single matcher:
composeTestRule
    .onNode(matcher)
    .assert(hasText("Button")) // hasText is a SemanticsMatcher

// Multiple matchers can use and / or
composeTestRule
    .onNode(matcher).assert(hasText("Button") or hasText("Button2"))
```

`assert` throws `AssertionError` if the matcher does not match or the node can no longer be found.

You can also use convenience functions for the most common assertions, such as `assertExists`, `assertIsDisplayed`, and `assertTextEquals`.

- `assertExists` asserts that the component was found and is part of the component tree.
- `assertDoesNotExist` asserts that no item was found or that the item is no longer in the hierarchy.
- `assertIsEnabled` asserts that the current semantics node is enabled, and `assertIsNotEnabled` asserts that it is not enabled.
- `assertHasClickAction` asserts that the current semantics node has a click action, and `assertHasNoClickAction` asserts that it doesn't have one.
- `assertIsFocused` asserts that the current semantics node has a focus.
- `assertIsSelected` asserts that the current semantics node is selected.
- `assertValueEquals` asserts the node's value equals the given value.

`assertIsDisplayed` asserts that the current semantics node is displayed on screen. Specifically, the node must be composed, placed and at least a portion of its bounds must be visible on screen after clipping is applied. It throws `AssertionError` if the node is not displayed.

`assertTextEquals` asserts that the node's list of text values contains exactly the given values and nothing else. The order of the elements does not matter.

In the merged semantics tree (the default in Compose testing), the `Text` property's list often contains multiple text items merged from child nodes. `assertTextEquals` evaluates the entire list.

To also evaluate `InputText`, which holds the raw user input of fields like passwords, bypassing visual transformations, set `includeInputText` to `true`.

`assertTextContains` asserts that the node's list of text values contains the given value. By default, this requires an exact string match with at least one complete item in the list.

`isDisplayed()` returns true if the matched node is displayed on screen. If no matching node is found, returns false. If multiple nodes match, throws an `AssertionError`.

```kotlin
val interaction = composeTestRule.onNodeWithTag("test")
composeTestRule.waitUntil { interaction.isDisplayed() }
```

`isNotDisplayed()` returns true if the matched node is not displayed on screen, including when the node is not composed, composed but not placed, or when none of its bounds are visible on screen after clipping is applied.

## Collection Assertions

There are also functions to check assertions on a collection of nodes:

```kotlin
// Check number of matched nodes
composeTestRule
    .onAllNodesWithContentDescription("Beatle").assertCountEquals(4)
// At least one matches
composeTestRule
    .onAllNodesWithContentDescription("Beatle").assertAny(hasTestTag("Drummer"))
// All of them match
composeTestRule
    .onAllNodesWithContentDescription("Beatle").assertAll(hasClickAction())
```

`assertAll` passes also for empty collections.

`assertCountEquals` provides a detailed error message on failure.

## Bounds Assertions

`assertHeightIsAtLeast` asserts that the layout of this node has height that is greater than or equal to the expected minimum height.

`assertPositionInRootIsEqualTo` asserts that the layout of this node has position in the root composable that is equal to the expected left and top values. Its `tolerance` parameter is the tolerance within which the values should be treated as equal. It defaults to the tolerance configured in `ComposeUiTestConfig`, or `0.5.dp` if unspecified.

```kotlin
composeTestRule
    .onNodeWithTag("icon", useUnmergedTree = true)
    .assertLeftPositionInRootIsEqualTo(16.dp)
    .assertTopPositionInRootIsEqualTo(16.dp)
```

## Actions

Actions inject simulated user events on the elements, such as clicks or other gestures.

To inject an action on a node, call a `perform...()` function:

```kotlin
composeTestRule.onNode(...).performClick()
```

You cannot chain actions inside a perform function. Instead, make multiple `perform...()` calls.

- `performClick` performs a click action on the element represented by the given semantics node. Depending on the platform this may be implemented by a touch click (tap), a mouse click, or another more appropriate method for that platform.
- `performSemanticsAction(key)` provides support to call custom semantics actions on this node. This method is for calling actions that have no parameters. It throws `AssertionError` if the semantics action is not defined on this node.
- `performKeyPress(keyEvent)` sends the specified `KeyEvent` to the focused component. It returns true if the event was consumed and false otherwise.
- `performGesture` is deprecated: it is replaced by `performTouchInput`.

## Touch Input

`performTouchInput` executes the touch gesture specified in the given block. The gesture doesn't need to be complete and can be resumed in a later invocation of one of the `perform.*Input` methods. The event time is initialized to the current time of the `MainTestClock`.

Be aware that if you split a gesture over multiple invocations of `perform.*Input`, everything that happens in between will run as if the gesture is still ongoing (imagine a finger still touching the screen).

Due to the batching of events, all events in a block are sent together and no recomposition will take place in between events.

Example of performing a swipe up:

```kotlin
composeTestRule.onNodeWithTag("myComponent").performTouchInput { swipeUp() }
```

Example of performing an off-center click:

```kotlin
composeTestRule.onNodeWithTag("myComponent").performTouchInput {
    click(percentOffset(.2f, .5f))
}
```

Example of doing an assertion during a click:

```kotlin
composeTestRule
    .onNodeWithTag("myComponent")
    .performTouchInput { down(topLeft) }
    .assertHasClickAction()
    .performTouchInput { up() }
```

Example of performing a click-and-drag:

```kotlin
composeTestRule.onNodeWithTag("myComponent").performTouchInput {
    click()
    advanceEventTime(100)
    swipeUp()
}
```

## Key Input and Focus

To write focus tests, use `createComposeRule()` from the Compose testing library:

```kotlin
@RunWith(AndroidJUnit4::class)
class FocusNavigationTest {
    @get:Rule
    val composeTestRule = createComposeRule()
```

You can verify whether a UI element can receive focus by performing a click or requesting focus, and then asserting its state using `assertIsFocused()` and `assertIsNotFocused()`.

```kotlin
@Test
fun interactiveElement_isFocusTarget() {
    composeTestRule.setContent {
        AppTheme {
            CardListScreen()
        }
    }

    val firstCard = composeTestRule.onNodeWithTag("card_1")
    val secondCard = composeTestRule.onNodeWithTag("card_2")

    // Focus the first element
    firstCard.performClick()
    firstCard.assertIsFocused()
    secondCard.assertIsNotFocused()
}
```

As a best practice, verify both forward navigation (`Key.Tab`) and reverse navigation (`Key.Tab` with `Key.ShiftLeft` held down) to ensure two-way traversal integrity:

```kotlin
@Test
fun tabKey_navigatesInAppearanceOrder() {
    composeTestRule.setContent {
        AppTheme {
            CardListScreen()
        }
    }

    val firstCard = composeTestRule.onNodeWithTag("card_1")
    val secondCard = composeTestRule.onNodeWithTag("card_2")
    val thirdCard = composeTestRule.onNodeWithTag("card_3")

    firstCard.performClick()
    firstCard.assertIsFocused()

    // Press Tab -> Moves to second card
    firstCard.performKeyInput {
        pressKey(Key.Tab)
    }
    secondCard.assertIsFocused()
    firstCard.assertIsNotFocused()

    // Press Tab -> Moves to third card
    secondCard.performKeyInput {
        pressKey(Key.Tab)
    }
    thirdCard.assertIsFocused()

    // Press Shift + Tab -> Moves backward to second card
    thirdCard.performKeyInput {
        withKeyDown(Key.ShiftLeft) {
            pressKey(Key.Tab)
        }
    }
    secondCard.assertIsFocused()
}
```

Arrow keys or D-pad directional keys are simulated using `Key.DirectionDown`, `Key.DirectionUp`, `Key.DirectionRight`, and `Key.DirectionLeft`.

When migrating to the v2 APIs, tests can fail if they rely on non-touch input modes configured through instrumentation APIs before the test starts. Within the setup functions for tests, the system enforces `InputMode.Touch` by default at the start of each test for more determinism and to prevent state leakage, overriding ambient device state and pre-test setup.

To resolve this, specify the required input mode in `ComposeUiTestConfig`:

```kotlin
class FocusTest {
    @get:Rule
    val rule = createComposeRule(
        config = ComposeUiTestConfig(inputMode = InputMode.Keyboard)
    )

    @Test
    fun testFocus() {}
}
```

The `ComposeUiTestConfig` class is included, starting in version 1.13, in the `junit4` and `ui-test` parts of the `androidx.compose.ui` AndroidX artifact (`androidx.compose.ui:ui-test-junit4:1.13.0-alpha01+` and `androidx.compose.ui:ui-test:1.13.0-alpha01+`).

## Text Input

- `performTextInput(text)` sends the given text to this node in similar way to IME.
- `performTextClearance()` clears the text in this node in similar way to IME.
- `performTextReplacement(text)` replaces existing text with the given text in this node in similar way to IME. This does not reflect text selection. All the text gets cleared out and new inserted.
- `performImeAction()` sends to this node the IME action associated with it in a similar way to the IME. The node needs to define its IME action in semantics via `onImeAction`.

## Scrolling

- `performScrollTo` scrolls the closest enclosing scroll parent by the smallest amount such that this node is fully visible in its viewport. This action should be performed on the `SemanticsNodeInteraction` that is part of the scrollable content, not on the scrollable container.
- `performScrollTo` throws `AssertionError` if there is no scroll parent, or if a scroll is needed but `MainTestClock#autoAdvance()` is set to `false`. Compose scroll actions rely on clock frames to execute scroll animations, so scrolling cannot make progress when clock auto-advancement is disabled.
- `performScrollToIndex(index)` scrolls a scrollable container with items to the item with the given index. This action should be performed on a `SemanticsNodeInteraction` that is a scrollable container, not on a node that is part of the content of that container.
- `performScrollToKey(key)` scrolls a scrollable container with keyed items to the item with the given key.
- `performScrollToNode(matcher)` scrolls a scrollable container to the content that matches the given matcher.

## Chaining and Return Values

Here you can see how you can locate a checkbox, click it and verify that it's checked:

```kotlin
composeTestRule.onNode(isToggleable()).performClick().assertIsOn()
```

`performTextInput` and `performImeAction` return `Unit`.

## Related References

- **Finding nodes**: See [semantics-finders.md](semantics-finders.md)
- **Waiting and clock**: See [synchronization.md](synchronization.md)
- **Clock control for scroll and animation**: See [clock-control.md](../advanced/clock-control.md)
- **Focus and accessibility tests**: See [accessibility.md](../testing-patterns/accessibility.md)

## Sources

- https://developer.android.com/develop/ui/compose/testing/apis
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/SemanticsNodeInteraction
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/SemanticsNodeInteractionCollection
- https://developer.android.com/develop/ui/compose/touch-input/focus/testing-focus
- https://developer.android.com/develop/ui/compose/testing/migrate-v2
