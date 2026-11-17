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
9. [Chaining Actions and Assertions](#chaining-actions-and-assertions)
10. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
11. [Related References](#related-references)
12. [Sources](#sources)

## Assertions

Assertions are used to verify that the elements exist or have certain attributes.

### Assert with Matchers

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

`assert`: Throws `AssertionError` if the matcher does not match or the node can no longer be found.

### Convenience Assertions

You can also use convenience functions for the most common assertions, such as `assertExists`, `assertIsDisplayed`, and `assertTextEquals`.

| Assertion                | Behavior                                                                    |
| ------------------------ | --------------------------------------------------------------------------- |
| `assertExists`           | Asserts that the component was found and is part of the component tree.     |
| `assertDoesNotExist`     | Asserts that no item was found or that the item is no longer in the hierarchy. |
| `assertIsEnabled`        | Asserts that the current semantics node is enabled.                         |
| `assertIsNotEnabled`     | Asserts that the current semantics node is not enabled.                     |
| `assertHasClickAction`   | Asserts that the current semantics node has a click action.                 |
| `assertHasNoClickAction` | Asserts that the current semantics node has doesn't have a click action.    |
| `assertIsFocused`        | Asserts that the current semantics node has a focus.                        |
| `assertIsNotFocused`     | Asserts that the current semantics node does not have a focus.              |
| `assertIsSelected`       | Asserts that the current semantics node is selected.                        |
| `assertIsOn`             | Asserts that the current semantics node is checked.                         |
| `assertValueEquals`      | Asserts the node's value equals the given value.                            |

### Display State

| Function               | Behavior                                                                                                                                                                                                                                                          |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `assertIsDisplayed`    | Asserts that the current semantics node is displayed on screen. Specifically, the node must be composed, placed and at least a portion of its bounds must be visible on screen after clipping is applied. Throws `AssertionError` if the node is not displayed. |
| `assertIsNotDisplayed` | Asserts that the current semantics node is not displayed on screen, including when the node is not composed, composed but not placed, or when none of its bounds are visible on screen after clipping is applied. Throws `AssertionError` If the node is displayed. |
| `isDisplayed()`        | Returns true if the matched node is displayed on screen. If no matching node is found, returns false. If multiple nodes match, throws an `AssertionError`. Added in 1.6.0.                                                                                       |
| `isNotDisplayed()`     | Returns true if the matched node is not displayed on screen, including when the node is not composed, composed but not placed, or when none of its bounds are visible on screen after clipping is applied. Returns false if a matching node is currently displayed. Added in 1.6.0. |

```kotlin
val interaction = composeTestRule.onNodeWithTag("test")
composeTestRule.waitUntil { interaction.isDisplayed() }
```

### Text Content

| Function            | Behavior                                                                                                                                                                                        |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `assertTextEquals`  | Asserts that the node's list of text values contains exactly the given values and nothing else. Note that the order of the elements does not matter.                                           |
| `assertTextContains` | Asserts that the node's list of text values contains the given value. By default, this requires an exact string match with at least one complete item in the list.                             |

The `Text` property is represented as a list of strings. In the merged semantics tree (the default in Compose testing), this list often contains multiple text items merged from child nodes. `assertTextEquals`: This function evaluates the entire list.

To also evaluate `SemanticsProperties.InputText` (which holds the raw user input of fields like passwords, bypassing visual transformations), set `includeInputText` to `true`.

- `value`: Value to match against the items in the list of text values.
- `substring`: Whether this can be satisfied as a substring match of an item in the list of text. Defaults to `false`.
- `ignoreCase`: Whether case should be ignored. Defaults to `false`.

```kotlin
composeTestRule.setContent {
    // Explicitly merging descendants to demonstrate list semantics
    Row(Modifier.semantics(mergeDescendants = true) { testTag = "textRow" }) {
        Text("Hello")
        Text("World")
    }
}

// The merged text list is: ["Hello", "World"]

// "Hello" is an exact match for one of the items in the list.
composeTestRule.onNodeWithTag("textRow").assertTextContains("Hello")

// "Hel" is a substring of an item in the list, and we explicitly enable substring matching.
composeTestRule.onNodeWithTag("textRow").assertTextContains("Hel", substring = true)
```

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

| Function           | Behavior                                                                                                         |
| ------------------ | ---------------------------------------------------------------------------------------------------------------- |
| `assertCountEquals` | Check number of matched nodes. Provides a detailed error message on failure.                                     |
| `assertAny`        | Asserts that this collection contains at least one element that satisfies the given matcher.                     |
| `assertAll`        | Asserts that all the nodes in this collection satisfy the given matcher. This passes also for empty collections. |

## Bounds Assertions

| Function                         | Behavior                                                                                                                                                                                                                                         |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `assertHeightIsAtLeast`          | Asserts that the layout of this node has height that is greater than or equal to `expectedMinHeight`. Added in 1.10.0.                                                                                                                  |
| `assertPositionInRootIsEqualTo`  | Asserts that the layout of this node has position in the root composable that is equal to the `expectedLeft` and `expectedTop` within the given `tolerance`. `tolerance`: The tolerance within which the values should be treated as equal. Defaults to the tolerance configured in `ComposeUiTestConfig`, or `0.5.dp` if unspecified. |

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

| Action                        | Behavior                                                                                                                                                                                             |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `performClick`                | Performs a click action on the element represented by the given semantics node. Depending on the platform this may be implemented by a touch click (tap), a mouse click, or another more appropriate method for that platform. |
| `performSemanticsAction(key)` | Provides support to call custom semantics actions on this node. This method is for calling actions that have no parameters. Throws `AssertionError` If the semantics action is not defined on this node. |
| `performKeyPress(keyEvent)`   | Send the specified `KeyEvent` to the focused component. Returns `Boolean` `true` if the event was consumed. False otherwise. Added in 1.10.0.                                                                 |

## Touch Input

`performTouchInput`: Executes the touch gesture specified in the given block. The gesture doesn't need to be complete and can be resumed in a later invocation of one of the `perform.*Input` methods. The event time is initialized to the current time of the `MainTestClock`.

Be aware that if you split a gesture over multiple invocations of `perform.*Input`, everything that happens in between will run as if the gesture is still ongoing (imagine a finger still touching the screen).

Due to the batching of events, all events in a block are sent together and no recomposition will take place in between events.

### Swipe Up

```kotlin
composeTestRule.onNodeWithTag("myComponent").performTouchInput { swipeUp() }
```

### Click Off-Center

```kotlin
composeTestRule.onNodeWithTag("myComponent").performTouchInput {
    click(percentOffset(.2f, .5f))
}
```

### Assert During a Click

```kotlin
composeTestRule
    .onNodeWithTag("myComponent")
    .performTouchInput { down(topLeft) }
    .assertHasClickAction()
    .performTouchInput { up() }
```

### Click and Drag

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

### Verify Focus Targets

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

### Verify Tab Traversal

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

### Arrow and D-Pad Keys

Simulate arrow keys or D-pad directional keys using `Key.DirectionDown`, `Key.DirectionUp`, `Key.DirectionRight`, and `Key.DirectionLeft`.

### Input Mode

Tests can fail during migration if they rely on non-touch input modes configured through instrumentation APIs before the test starts. Within the setup functions for tests, the system enforces `InputMode.Touch` by default at the start of each test for more determinism and to prevent state leakage, overriding ambient device state and pre-test setup.

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

To configure the input mode for individual test cases instead of the entire test class, pass `ComposeUiTestConfig` to `runComposeUiTest`:

```kotlin
class FocusTest {
    @Test
    fun testTouchMode() = runComposeUiTest {
        // Runs with the default InputMode.Touch
    }

    @Test
    fun testKeyboardMode() = runComposeUiTest(
        ComposeUiTestConfig(inputMode = InputMode.Keyboard)
    ) {
        // Runs with InputMode.Keyboard
    }
}
```

## Text Input

| Action                       | Behavior                                                                                                                                                           |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `performTextInput`           | Sends the given text to this node in similar way to IME.                                                                                                           |
| `performTextClearance()`     | Clears the text in this node in similar way to IME.                                                                                                                |
| `performTextReplacement`   | Replaces existing text with the given text in this node in similar way to IME. This does not reflect text selection. All the text gets cleared out and new inserted. |
| `performImeAction()`         | Sends to this node the IME action associated with it in a similar way to the IME. The node needs to define its IME action in semantics via `SemanticsPropertyReceiver.onImeAction`.          |

## Scrolling

| Action                       | Behavior                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `performScrollTo`            | Scrolls the closest enclosing scroll parent by the smallest amount such that this node is fully visible in its viewport. This action should be performed on the node that is part of the scrollable content, not on the scrollable container. Throws `AssertionError` if there is no scroll parent, or if a scroll is needed but `mainClock.autoAdvance` is set to `false`. Compose scroll actions rely on clock frames to execute scroll animations, so scrolling cannot make progress when clock auto-advancement is disabled. |
| `performScrollToIndex` | Scrolls a scrollable container with items to the item with the given index. Note that not all scrollable containers have item indices. For example, a scrollable doesn't have items with an index, while `LazyColumn` does. This action should be performed on a node that is a scrollable container, not on a node that is part of the content of that container.                                                                                                                       |
| `performScrollToKey`    | Scrolls a scrollable container with keyed items to the item with the given key, such as `LazyColumn` or `LazyRow`. This action should be performed on a node that is a scrollable container, not on a node that is part of the content of that container.                                                                                                                                                                              |
| `performScrollToNode` | Scrolls a scrollable container to the content that matches the given matcher. If the content isn't yet visible, the scrollable container will be scrolled from the start till the end till it finds the content we're looking for. Added in 1.1.0.                                                                                                                                                                       |

## Chaining Actions and Assertions

Here you can see how you can locate a checkbox, click it and verify that it's checked:

```kotlin
composeTestRule.onNode(isToggleable()).performClick().assertIsOn()
```

## Anti-Patterns to Avoid

- You cannot chain actions inside a perform function. Instead, make multiple `perform...()` calls.
- `performGesture`: This function is deprecated. Replaced by performTouchInput, use this instead: performTouchInput(block)
- `assertExists`: If you are using fetchSemanticsNode you don't need to call this. In fact you would just introduce additional overhead.
- `performScrollTo`: This action should be performed on the node that is part of the scrollable content, not on the scrollable container.
- `performScrollToIndex`: This action should be performed on a node that is a scrollable container, not on a node that is part of the content of that container.
- `performScrollToKey`: This action should be performed on a node that is a scrollable container, not on a node that is part of the content of that container.

## Related References

- **Finding nodes**: See [semantics-finders.md](semantics-finders.md)
- **Waiting and clock**: See [synchronization.md](synchronization.md)
- **Clock control for scroll and animation**: See [clock-control.md](../advanced/clock-control.md)
- **Focus and accessibility tests**: See [accessibility.md](../testing-patterns/accessibility.md)

## Sources

- https://developer.android.com/develop/ui/compose/testing/apis
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/SemanticsNodeInteraction
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/SemanticsNodeInteractionCollection
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/package-summary
- https://developer.android.com/develop/ui/compose/touch-input/focus/testing-focus
- https://developer.android.com/develop/ui/compose/testing/migrate-v2
