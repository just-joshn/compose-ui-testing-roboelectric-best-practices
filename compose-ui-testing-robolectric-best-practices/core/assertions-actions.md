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
10. [Common Issues & Solutions](#common-issues--solutions)
11. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
12. [Related References](#related-references)
13. [Sources](#sources)

## Assertions

Call `assert(matcher)` on the `SemanticsNodeInteraction` a finder returns, or use a convenience assertion. Each assertion synchronizes with the UI first, so there is no manual waiting for recomposition; see [synchronization.md](synchronization.md).

```kotlin
// Generic: any SemanticsMatcher
composeTestRule.onNode(matcher).assert(hasText("Button"))
composeTestRule.onNode(matcher).assert(hasText("Button") or hasText("Button2"))

// Convenience
composeTestRule.onNodeWithText("Welcome").assertIsDisplayed()
composeTestRule.onNodeWithTag("title").assertExists()
composeTestRule.onNodeWithTag("spinner").assertDoesNotExist()
composeTestRule.onNodeWithTag("cart-count").assertTextEquals("1")
composeTestRule.onNodeWithTag("note").assertTextContains("draft")
composeTestRule.onNodeWithTag("icon").assertContentDescriptionEquals("Add to favorites")
composeTestRule.onNodeWithText("Save").assertIsEnabled()
composeTestRule.onNodeWithText("Save").assertHasClickAction()
composeTestRule.onNodeWithTag("switch").assertIsOn()
composeTestRule.onNodeWithTag("tab").assertIsSelected()
composeTestRule.onNodeWithTag("email").assertIsFocused()
```

Related families on `SemanticsNodeInteraction`: `assertIsNotDisplayed`, `assertIsNotEnabled`, `assertIsOff`, `assertIsNotSelected`, `assertIsNotFocused`, `assertIsSelectable`, `assertIsToggleable`, `assertHasNoClickAction`, `assertValueEquals`, `assertRangeInfoEquals`.

`assertTextEquals(vararg values)` asserts the node's text list contains exactly those values and nothing else; order does not matter. In the merged tree that list can hold text from several children.

`isDisplayed()` and `isNotDisplayed()` return a Boolean and do not assert. Use them inside `waitUntil`, never instead of `assertIsDisplayed()`.

```kotlin
// Good: waiting on a Boolean
val interaction = composeTestRule.onNodeWithTag("test")
composeTestRule.waitUntil { interaction.isDisplayed() }

// Bad: the Boolean is dropped, the test cannot fail
composeTestRule.onNodeWithTag("test").isDisplayed()
```

"Displayed" means composed, placed, and at least part of the bounds visible after clipping. `isDisplayed()` returns false when no node matches, and throws `AssertionError` when several do.

## Collection Assertions

```kotlin
// Exact count
composeTestRule.onAllNodesWithContentDescription("Beatle").assertCountEquals(4)
// At least one matches
composeTestRule.onAllNodesWithContentDescription("Beatle").assertAny(hasTestTag("Drummer"))
// Every one matches
composeTestRule.onAllNodesWithContentDescription("Beatle").assertAll(hasClickAction())
```

Filter a collection first with `filter(matcher)`, or reduce it to one node with `filterToOne(matcher)`, `onFirst()`, or `onLast()`.

## Bounds Assertions

Layout assertions take `Dp`:

```kotlin
composeTestRule.onNodeWithTag("card")
    .assertWidthIsEqualTo(200.dp)
    .assertHeightIsAtLeast(48.dp)
    .assertPositionInRootIsEqualTo(expectedLeft = 16.dp, expectedTop = 8.dp)
```

`assertWidthIsEqualTo` and similar also accept a `tolerance: Dp`. The `ComposeUiTestConfig(boundsAssertionTolerance = ...)` setting is a 1.13.0-rc01 API that sets a default tolerance.

## Actions

Inject events with `perform...()`:

```kotlin
composeTestRule.onNodeWithText("Continue").performClick()
composeTestRule.onNode(...).performSemanticsAction(key)            // key: a semantics action property key
composeTestRule.onNodeWithTag("field").performKeyPress(keyEvent)   // sends to the focused component
```

`performClick` is the convenience. `performSemanticsAction(key)` calls a semantics action that takes no parameters and fails with a clear `AssertionError` if the node does not define it. The docs list `performGesture { swipeLeft() }` in the APIs overview, but `performGesture` is deprecated in the API reference in favor of `performTouchInput`.

## Touch Input

`performTouchInput { }` takes a `TouchInjectionScope` block. Events in one block are batched and sent together, so no recomposition happens between events.

```kotlin
import androidx.compose.ui.test.click
import androidx.compose.ui.test.swipeUp

// Swipe
composeTestRule.onNodeWithTag("myComponent").performTouchInput { swipeUp() }

// Off-center click
composeTestRule.onNodeWithTag("myComponent").performTouchInput {
    click(percentOffset(.2f, .5f))
}

// Click, wait 100 ms of event time, then swipe
composeTestRule.onNodeWithTag("myComponent").performTouchInput {
    click()
    advanceEventTime(100)
    swipeUp()
}
```

A gesture can be split across invocations. Everything between runs as if the finger is still down:

```kotlin
composeTestRule
    .onNodeWithTag("myComponent")
    .performTouchInput { down(topLeft) }
    .assertHasClickAction()   // assertion while pressed
    .performTouchInput { up() }
```

Event time starts at the current `MainTestClock` time. Also available: `performMouseInput`, `performRotaryScrollInput`, `performTrackpadInput`, `performMultiModalInput`.

## Key Input and Focus

```kotlin
// Forward and reverse traversal
firstCard.performKeyInput { pressKey(Key.Tab) }
secondCard.performKeyInput {
    withKeyDown(Key.ShiftLeft) { pressKey(Key.Tab) }
}

// D-pad / arrow keys: Key.DirectionDown, DirectionUp, DirectionLeft, DirectionRight
```

v2 test APIs enforce `InputMode.Touch` at the start of every test. For keyboard focus tests set `ComposeUiTestConfig(inputMode = InputMode.Keyboard)` (1.13.0-rc01 API). Focus-navigation test recipes live in [accessibility.md](../testing-patterns/accessibility.md).

## Text Input

```kotlin
composeTestRule.onNodeWithTag("email").performTextInput("ada@example.com")
composeTestRule.onNodeWithTag("email").performTextClearance()
composeTestRule.onNodeWithTag("email").performTextReplacement("grace@example.com")
composeTestRule.onNodeWithTag("email").performImeAction()
composeTestRule.onNodeWithTag("email").assertTextEquals("grace@example.com")
```

`performTextInput` sends text "in similar way to IME". `assertTextEquals` searches `Text` and `EditableText`; pass `includeInputText = true` to also check the raw input of fields with visual transformations, such as passwords.

## Scrolling

```kotlin
composeTestRule.onNodeWithTag("row-40").performScrollTo()            // call on the item
composeTestRule.onNodeWithTag("list").performScrollToIndex(40)      // call on the container
composeTestRule.onNodeWithTag("list").performScrollToKey("id-40")
```

`performScrollTo` fails with `AssertionError` if a scroll is needed and `mainClock.autoAdvance` is `false`, because scroll animations need clock frames. Re-enable auto-advance first; see [clock-control.md](../advanced/clock-control.md).

## Chaining and Return Values

Most assertions and actions return the same `SemanticsNodeInteraction`, so they chain. You cannot chain actions inside a `perform` lambda; make separate calls.

```kotlin
// Good: one perform call per action
composeTestRule.onNodeWithTag("field").performTextInput("hello")
composeTestRule.onNodeWithText("Submit").performClick()
```

Text actions such as `performTextInput` and `performImeAction` return `Unit` and end a chain. `performKeyPress` returns a `Boolean` (true if the event was consumed).

## Common Issues & Solutions

| Issue                                              | Solution                                                                         |
| -------------------------------------------------- | -------------------------------------------------------------------------------- |
| Assertion fails right after a state change in test | Go through the rule so it synchronizes; see [synchronization.md](synchronization.md) |
| `performScrollTo` throws `AssertionError`          | No scroll parent, or `autoAdvance` is `false`                                    |
| `assertTextEquals` fails with extra text           | Merged tree holds several texts; list all of them or use `assertTextContains`    |
| Password field text does not match                 | `assertTextEquals(..., includeInputText = true)`                                 |
| Keyboard focus test sees touch mode                | Set `inputMode = InputMode.Keyboard` in `ComposeUiTestConfig`                    |
| Exact `Dp` comparison off by a hair                | Pass `tolerance`                                                                 |

## Anti-Patterns to Avoid

| Anti-Pattern                                  | Problem                              | Solution                                            |
| --------------------------------------------- | ------------------------------------ | --------------------------------------------------- |
| `isDisplayed()` used as an assertion          | Test cannot fail                     | `assertIsDisplayed()`                               |
| `performGesture { ... }`                      | Deprecated                           | `performTouchInput { ... }`                         |
| Reading state after mutating it with no sync  | UI appears paused, no recomposition  | Assert or act through the rule, or `waitForIdle()`  |
| Chaining actions inside `perform`             | Not supported                        | Separate `perform...()` calls                       |

## Related References

- **Finding nodes**: See [semantics-finders.md](semantics-finders.md)
- **Waiting and clock**: See [synchronization.md](synchronization.md)
- **Clock control for scroll and animation**: See [clock-control.md](../advanced/clock-control.md)
- **Focus and accessibility tests**: See [accessibility.md](../testing-patterns/accessibility.md)

## Sources

- https://developer.android.com/develop/ui/compose/testing/apis
- https://developer.android.com/develop/ui/compose/testing/migrate-v2
- https://developer.android.com/develop/ui/compose/touch-input/focus/testing-focus
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/ComposeUiTestConfig
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/package-summary
- https://developer.android.com/jetpack/androidx/releases/compose-ui
