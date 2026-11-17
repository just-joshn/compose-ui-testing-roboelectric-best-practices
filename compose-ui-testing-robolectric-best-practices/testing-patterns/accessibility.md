# Accessibility Testing

## Table of Contents

1. [What Can Be Automated](#what-can-be-automated)
2. [Semantics for Accessibility](#semantics-for-accessibility)
3. [Accessibility Test Framework Checks](#accessibility-test-framework-checks)
4. [Focus Navigation Tests](#focus-navigation-tests)
5. [Input Mode](#input-mode)
6. [Manual Testing](#manual-testing)
7. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
8. [Related References](#related-references)
9. [Sources](#sources)

## What Can Be Automated

Compose's semantics framework is primarily used for accessibility, so ordinary Compose test APIs already assert accessibility-relevant properties. Beyond that, there are two automated layers. Their Robolectric status differs:

| Layer                                          | Needs                                           | On Robolectric (`src/test`)                                    |
| ---------------------------------------------- | ----------------------------------------------- | -------------------------------------------------------------- |
| Assert semantics (labels, roles, text)         | `ui-test-junit4`                                | Same Compose rule APIs as other tests                          |
| Focus traversal with `performKeyInput`         | `ui-test-junit4`                                | The focus page shows `@RunWith(AndroidJUnit4::class)` and does not mention Robolectric |
| Accessibility Test Framework checks            | `ui-test-junit4-accessibility`, API 34+         | **Does not work on Robolectric** (API 34+ only) |

The API reference for `enableAccessibilityChecks` says it requires API 34+ and "currently does not work on Robolectric"; both it and `disableAccessibilityChecks` are `@RequiresApi(34)`. Run accessibility-check tests as instrumented tests in `androidTest`. See [test-architecture.md](../architecture/test-architecture.md).

## Semantics for Accessibility

The default semantics tree for a button with an icon and a text label only contains the text. `Text` already exposes its properties; add the rest with a modifier.

```kotlin
// Good: the icon-only control exposes a label that both TalkBack and tests can use
MyButton(
    modifier = Modifier.semantics { contentDescription = "Add to favorites" }
)

// Test
composeTestRule
    .onNodeWithContentDescription("Add to favorites")
    .assertIsDisplayed()
```

```kotlin
// Bad: a clickable with no label for accessibility services
Box(
    modifier = Modifier
        .size(50.dp)
        .clickable { }
        .semantics { contentDescription = "" }
)
```

Asserting on `contentDescription` in a normal test is a cheap check that labels exist, and it does not need the Accessibility Test Framework. If a child seems missing, print the unmerged tree; see [debugging.md](../debugging/debugging.md) and [semantics-finders.md](../core/semantics-finders.md).

## Accessibility Test Framework Checks

Since Compose 1.8.0 you can run the Accessibility Test Framework, the same framework behind Accessibility Scanner and Espresso accessibility checks. Checks cover a missing label, color contrast, small touch target size, and traversal order.

```kotlin
// build.gradle.kts (the docs give no version for this artifact)
dependencies {
    androidTestImplementation("androidx.compose.ui:ui-test-junit4-accessibility")
}
```

```kotlin
// src/androidTest (device): API 34+, does not work on Robolectric
@get:Rule
val composeTestRule = createAndroidComposeRule<ComponentActivity>()

@Test
fun noAccessibilityLabel() {
    composeTestRule.setContent {
        Box(
            modifier = Modifier
                .size(50.dp, 50.dp)
                .background(color = Color.Gray)
                .clickable { }
                .semantics { contentDescription = "" }
        )
    }

    composeTestRule.enableAccessibilityChecks()

    // Any action (such as performClick) also runs the checks
    composeTestRule.onRoot().tryPerformAccessibilityChecks()
}
```

This test fails with an exception saying the item may not have a label readable by accessibility services. Checks run before every action expected to change the UI. `enableAccessibilityChecks()` is supported only for `AndroidComposeTestRule`; if you wrap the rule in a custom `ComposeTestRule`, call it on the inner `AndroidComposeTestRule`. Use `disableAccessibilityChecks()` to turn them off.

### Custom Validator

If you mix Views with Compose and already use an `AccessibilityValidator`, or need to configure one, pass it to the rule:

```kotlin
val accessibilityValidator = AccessibilityValidator()
    .setThrowExceptionFor(
        AccessibilityCheckResult.AccessibilityCheckResultType.WARNING
    )

composeTestRule.enableAccessibilityChecks(accessibilityValidator)
composeTestRule.onRoot().tryPerformAccessibilityChecks()
```

The default validator is `AccessibilityValidator().setRunChecksFromRootView(true)`.

## Focus Navigation Tests

Automating focus tests keeps the experience consistent for hardware keyboards, D-pads, and accessibility tools. Use `performKeyInput` to simulate key presses and `assertIsFocused()` / `assertIsNotFocused()` to verify state.

```kotlin
@RunWith(AndroidJUnit4::class)
class FocusNavigationTest {
    @get:Rule
    val composeTestRule = createComposeRule()

    @Test
    fun interactiveElement_isFocusTarget() {
        composeTestRule.setContent { AppTheme { CardListScreen() } }

        val firstCard = composeTestRule.onNodeWithTag("card_1")
        val secondCard = composeTestRule.onNodeWithTag("card_2")

        // Focus the first element by clicking it
        firstCard.performClick()
        firstCard.assertIsFocused()
        secondCard.assertIsNotFocused()
    }
}
```

### Tab Order (one-dimensional)

Verify both forward (`Key.Tab`) and reverse (`Key.Tab` with `Key.ShiftLeft` held) traversal.

```kotlin
@Test
fun tabKey_navigatesInAppearanceOrder() {
    composeTestRule.setContent { AppTheme { CardListScreen() } }

    val firstCard = composeTestRule.onNodeWithTag("card_1")
    val secondCard = composeTestRule.onNodeWithTag("card_2")
    val thirdCard = composeTestRule.onNodeWithTag("card_3")

    firstCard.performClick()
    firstCard.performKeyInput { pressKey(Key.Tab) }
    secondCard.assertIsFocused()

    secondCard.performKeyInput { pressKey(Key.Tab) }
    thirdCard.assertIsFocused()

    // Shift + Tab moves backward
    thirdCard.performKeyInput {
        withKeyDown(Key.ShiftLeft) { pressKey(Key.Tab) }
    }
    secondCard.assertIsFocused()
}
```

### Arrow Keys (two-dimensional)

Use `Key.DirectionDown`, `Key.DirectionUp`, `Key.DirectionRight`, and `Key.DirectionLeft`. Directional keys do not wrap around.

```kotlin
topLeftButton.performClick()
topLeftButton.performKeyInput { pressKey(Key.DirectionDown) }
bottomLeftButton.assertIsFocused()

// No wraparound: pressing Down on the bottom element keeps focus there
bottomLeftButton.performKeyInput { pressKey(Key.DirectionDown) }
bottomLeftButton.assertIsFocused()
```

### Text Fields

A single-line text field advances focus on Tab; a multi-line field inserts a tab character and keeps focus. Shift+Tab leaves the multi-line field.

```kotlin
singleLineNode.performClick()
singleLineNode.performKeyInput { pressKey(Key.Tab) }
multiLineNode.assertIsFocused()

multiLineNode.performKeyInput { pressKey(Key.Tab) }   // inserts '\t'
multiLineNode.assertIsFocused()

multiLineNode.performKeyInput {
    withKeyDown(Key.ShiftLeft) { pressKey(Key.Tab) }
}
singleLineNode.assertIsFocused()
```

## Input Mode

Compose tests start in touch mode. v2 rules enforce `InputMode.Touch` at the start of each test so input mode state cannot leak between tests. To start in keyboard mode, set it in `ComposeUiTestConfig` (`ui-test` and `ui-test-junit4` 1.13.0-alpha01+; pre-release at the time of writing, 1.12.1 is the latest stable).

```kotlin
// Per class
@get:Rule
val rule = createComposeRule(
    config = ComposeUiTestConfig(inputMode = InputMode.Keyboard)
)

// Per test
@Test
fun testKeyboardMode() = runComposeUiTest(
    ComposeUiTestConfig(inputMode = InputMode.Keyboard)
) {
    // Runs with InputMode.Keyboard
}
```

## Manual Testing

An essential part of accessibility testing is manual: turn on TalkBack or Switch Access and check that everything works. Automated tests flag regressions as the app changes; they do not replace manual passes.

## Anti-Patterns to Avoid

| Anti-Pattern                                          | Problem                                         | Solution                                                         |
| ----------------------------------------------------- | ----------------------------------------------- | ---------------------------------------------------------------- |
| Putting accessibility-check tests in `src/test`        | `enableAccessibilityChecks` does not work on Robolectric | Run them in `androidTest` on API 34+                  |
| Only automated testing                                | Misses issues only a person with a screen reader finds | Add manual TalkBack / Switch Access passes                |
| Testing only forward Tab                              | Misses broken reverse traversal                 | Test `Key.Tab` and Shift+Tab                                     |
| Expecting arrow keys to wrap                          | They do not wrap                                | Assert focus stays on the last element                           |
| Empty `contentDescription` on clickable elements       | No label for accessibility services             | Provide a meaningful label                                       |
| Relying on ambient input mode                         | v2 resets to touch each test                    | Set `inputMode` in `ComposeUiTestConfig`                         |

## Related References

- **Selectors**: See [semantics-finders.md](../core/semantics-finders.md) for `contentDescription` finders and merged trees
- **Component tests**: See [component-testing.md](component-testing.md) for isolating composables
- **Debugging**: See [debugging.md](../debugging/debugging.md) for printing the semantics tree
- **Architecture**: See [test-architecture.md](../architecture/test-architecture.md) for what belongs on a device
- **Device configuration**: See [device-configuration.md](../advanced/device-configuration.md) for font scale and other settings

## Sources

- https://developer.android.com/develop/ui/compose/accessibility/testing
- https://developer.android.com/develop/ui/compose/touch-input/focus/testing-focus
- https://developer.android.com/develop/ui/compose/testing/semantics
- https://developer.android.com/develop/ui/compose/testing/migrate-v2
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/junit4/ComposeTestRule
- https://developer.android.com/jetpack/androidx/releases/compose-ui
