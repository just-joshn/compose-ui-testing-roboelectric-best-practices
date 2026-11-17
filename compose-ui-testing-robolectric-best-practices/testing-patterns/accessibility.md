# Accessibility Testing

## Table of Contents

1. [Manual and Automated Testing](#manual-and-automated-testing)
2. [Semantics](#semantics)
3. [Accessibility Checks](#accessibility-checks)
4. [Focus Navigation Tests](#focus-navigation-tests)
5. [Input Mode](#input-mode)
6. [Related References](#related-references)
7. [Sources](#sources)

## Manual and Automated Testing

An essential way of testing accessibility is a form of manual testing: by turning accessibility services, like TalkBack or Switch Access, on, and checking if everything works as expected.

In conjunction with manual verification, you should also use automated testing to flag any potential issues that could impact user experience as you make continual changes to your app.

Existing Compose testing APIs allow you to write automated tests that interact with semantic elements and to assert the properties defined in your UI.

## Semantics

The semantics framework is primarily used for accessibility, so tests take advantage of the information exposed by semantics about the UI hierarchy. Developers decide what and how much to expose.

For example, given a button that consists of an icon and a text element, the default semantics tree only contains the text label "Like". This is because some composables, such as `Text`, already expose some properties to the semantics tree. You can add properties to the semantics tree by using a `Modifier`.

```kotlin
MyButton(
    modifier = Modifier.semantics { contentDescription = "Add to favorites" }
)
```

## Accessibility Checks

For automated accessibility testing, you can also use the Accessibility Test Framework, the same underlying framework that powers Accessibility Scanner and accessibility checks in Espresso, to perform some accessibility-related checks automatically, starting with Compose 1.8.0.

To enable the checks, add the `ui-test-junit4-accessibility` dependency, call `enableAccessibilityChecks()` in the `AndroidComposeTestRule`, and trigger an action or `tryPerformAccessibilityChecks`:

```kotlin
@Rule
@JvmField
val composeTestRule = createAndroidComposeRule<ComponentActivity>()

@Test
fun noAccessibilityLabel() {
    composeTestRule.setContent {
        Box(
            modifier = Modifier
                .size(50.dp, 50.dp)
                .background(color = Color.Gray)
                .clickable { }
                .semantics {
                    contentDescription = ""
                }
        )
    }

    composeTestRule.enableAccessibilityChecks()

    // Any action (such as performClick) will perform accessibility checks too:
    composeTestRule.onRoot().tryPerformAccessibilityChecks()
}
```

This specific test fails with an exception and a message that the item may not have a label readable by accessibility services.

Other available checks look for accessibility issues with color contrast, small touch target size, or elements' traversal order.

`enableAccessibilityChecks` enables accessibility checks that will be run before every action that is expected to change the UI.

The API reference for `enableAccessibilityChecks` says: "This requires API 34+ (Android U), and currently does not work on Robolectric."

Enabling accessibility checks is currently only supported for `AndroidComposeTestRule`. If you have a custom `ComposeTestRule` implementation that delegates to `AndroidComposeTestRule`, make sure to call this function on the `AndroidComposeTestRule` instead.

If you're mixing Views with Compose and you're already using an `AccessibilityValidator`, or you need to configure one, you can set it in the rule:

```kotlin
// Optionally, set AccessibilityValidator manually
val accessibilityValidator = AccessibilityValidator()
    .setThrowExceptionFor(
        AccessibilityCheckResult.AccessibilityCheckResultType.WARNING
    )

composeTestRule.enableAccessibilityChecks(accessibilityValidator)

composeTestRule.onRoot().tryPerformAccessibilityChecks()
```

The default value of the `accessibilityValidator` parameter is `AccessibilityValidator().setRunChecksFromRootView(true)`.

In combination with manual testing, automated tests using both Compose APIs as well as the Accessibility Test Framework can help you detect possible problems early on in the development process.

## Focus Navigation Tests

Automating focus navigation tests ensures your app delivers a consistent and predictable user experience across hardware keyboards, D-pads, and accessibility tools. Compose provides built-in testing APIs to simulate key input and verify focus states.

To write focus tests, use `createComposeRule()` from the Compose testing library:

```kotlin
@RunWith(AndroidJUnit4::class)
class FocusNavigationTest {
    @get:Rule
    val composeTestRule = createComposeRule()
```

By default, Compose testing environments initialize in touch mode. To configure whether your test environment starts in touch mode or keyboard mode, see the default input mode configuration, described in the [Input Mode](#input-mode) section.

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

### One-Dimensional Focus Traversal

Simulate Tab and Shift+Tab key presses using `performKeyInput` to verify that focus advances through the UI in appearance order. As a best practice, verify both forward navigation (`Key.Tab`) and reverse navigation (`Key.Tab` with `Key.ShiftLeft` held down) to ensure two-way traversal integrity:

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

### Two-Dimensional Directional Traversal

Simulate arrow keys or D-pad directional keys using `Key.DirectionDown`, `Key.DirectionUp`, `Key.DirectionRight`, and `Key.DirectionLeft`.

```kotlin
@Test
fun arrowKeys_moveFocusTwoDimensionallyWithoutWrap() {
    composeTestRule.setContent {
        AppTheme {
            GridLayoutScreen()
        }
    }

    val topLeftButton = composeTestRule.onNodeWithTag("btn_top_left")
    val bottomLeftButton = composeTestRule.onNodeWithTag("btn_bottom_left")

    topLeftButton.performClick()
    topLeftButton.assertIsFocused()

    // Down arrow moves focus downward to bottom-left button
    topLeftButton.performKeyInput {
        pressKey(Key.DirectionDown)
    }
    bottomLeftButton.assertIsFocused()

    // Directional keys do not wrap around: pressing Down on bottom element stays focused
    bottomLeftButton.performKeyInput {
        pressKey(Key.DirectionDown)
    }
    bottomLeftButton.assertIsFocused()
}
```

### Text Field Focus Behavior

Verify that single-line text fields advance focus on Tab, while multi-line text fields retain focus:

```kotlin
@Test
fun textField_handlesTabAccordingToLineLimits() {
    composeTestRule.setContent {
        AppTheme {
            FormScreen()
        }
    }

    val singleLineNode = composeTestRule.onNodeWithTag("single_line_field")
    val multiLineNode = composeTestRule.onNodeWithTag("multi_line_field")
    val submitButtonNode = composeTestRule.onNodeWithTag("submit_button")

    // Single-line field advances focus on Tab
    singleLineNode.performClick()
    singleLineNode.assertIsFocused()
    singleLineNode.performKeyInput { pressKey(Key.Tab) }
    multiLineNode.assertIsFocused()

    // Multi-line field keeps focus and inserts '\t'
    multiLineNode.performKeyInput { pressKey(Key.Tab) }
    multiLineNode.assertIsFocused()
    submitButtonNode.assertIsNotFocused()

    // Shift + Tab escapes multi-line field to previous target
    multiLineNode.performKeyInput {
        withKeyDown(Key.ShiftLeft) { pressKey(Key.Tab) }
    }
    singleLineNode.assertIsFocused()
}
```

## Input Mode

The `ComposeUiTestConfig` class is included, starting in version 1.13, in the `junit4` and `ui-test` parts of the `androidx.compose.ui` AndroidX artifact (`androidx.compose.ui:ui-test-junit4:1.13.0-alpha01+` and `androidx.compose.ui:ui-test:1.13.0-alpha01+`).

Tests can fail during migration if they rely on non-touch input modes configured through instrumentation APIs before the test starts. Within the setup functions for tests, the system enforces `InputMode.Touch` by default at the start of each test for more determinism and to prevent state leakage, overriding ambient device state and pre-test setup. To resolve this, specify the required input mode in `ComposeUiTestConfig`:

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

## Related References

- **Selectors**: See [semantics-finders.md](../core/semantics-finders.md) for `contentDescription` finders and merged trees
- **Component tests**: See [component-testing.md](component-testing.md) for isolating composables
- **Debugging**: See [debugging.md](../debugging/debugging.md) for printing the semantics tree
- **Device configuration**: See [device-configuration.md](../advanced/device-configuration.md) for font scale and other settings

## Sources

- https://developer.android.com/develop/ui/compose/accessibility/testing
- https://developer.android.com/develop/ui/compose/testing/semantics
- https://developer.android.com/develop/ui/compose/testing/migrate-v2
- https://developer.android.com/develop/ui/compose/touch-input/focus/testing-focus
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/junit4/ComposeTestRule
