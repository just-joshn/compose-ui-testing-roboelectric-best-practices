# Component Testing

## Table of Contents

1. [Setup & Configuration](#setup--configuration)
2. [Showing a Composable in Isolation](#showing-a-composable-in-isolation)
3. [Inputs: State and Callbacks](#inputs-state-and-callbacks)
4. [Events & Interactions](#events--interactions)
5. [Accessing Resources and the Activity](#accessing-resources-and-the-activity)
6. [Custom Semantics for Tests](#custom-semantics-for-tests)
7. [What to Test, Including Edge Cases](#what-to-test-including-edge-cases)
8. [Isolating Dependencies](#isolating-dependencies)
9. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
10. [Related References](#related-references)
11. [Sources](#sources)

## Setup & Configuration

Component tests are Compose UI tests that scope the rule to one screen or one small element. On Robolectric they live in `src/test` and run with `AndroidJUnit4`.

```kotlin
// build.gradle.kts
android {
    testOptions {
        unitTests {
            isIncludeAndroidResources = true
        }
    }
}

dependencies {
    testImplementation(platform("androidx.compose:compose-bom:2026.09.00"))
    testImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.robolectric:robolectric:4.18")
}
```

Gradle coordinates, `@Config`, and JDK requirements are covered in [configuration.md](../core/configuration.md). The `ui-test-manifest` dependency is needed for `createComposeRule()`, but not for `createAndroidComposeRule<YourActivity>()`; it also adds `ComponentActivity` to the manifest for the empty-activity pattern below.

```
src/test/java/com/example/
├── ui/
│   ├── CartRowTest.kt          # one small element
│   └── CheckoutScreenTest.kt   # one screen
```

One test class per screen is a good starting point for screen UI tests.

## Showing a Composable in Isolation

`ComposeTestRule` can display any composable: the whole app, a single screen, or a small element. Checking that a composable works independently also checks that it is correctly encapsulated.

```kotlin
@RunWith(AndroidJUnit4::class)
class CartRowTest {
    @get:Rule
    val composeTestRule = createAndroidComposeRule<ComponentActivity>()

    @Test
    fun showsItemName() {
        composeTestRule.setContent {
            AppTheme {
                CartRow(item = CartItem(name = "Tea", quantity = 2), onRemove = {})
            }
        }

        composeTestRule.onNodeWithText("Tea").assertIsDisplayed()
    }
}
```

```kotlin
// Good: a rule that shows only what you set via setContent
createAndroidComposeRule<ComponentActivity>()

// Bad: an app activity that already calls setContent; you cannot call setContent again
createAndroidComposeRule<MainActivity>()
```

Isolation does not mean unit UI tests only. Tests that scope larger parts of the UI are also very important; see [test-architecture.md](../architecture/test-architecture.md).

## Inputs: State and Callbacks

Give the composable the values it renders and callbacks it invokes, rather than its real dependencies. The Android docs' example passes a ready-made `exampleUiState`; the navigation guide likewise says to pass navigation callbacks (lambdas), not a `NavController`, and to test screens with mock values and callbacks.

```kotlin
@Test
fun clickingRemove_invokesCallback() {
    var removed: CartItem? = null
    val item = CartItem(name = "Tea", quantity = 2)

    composeTestRule.setContent {
        CartRow(item = item, onRemove = { removed = it })
    }

    composeTestRule.onNodeWithContentDescription("Remove Tea").performClick()

    composeTestRule.runOnIdle { assertEquals(item, removed) }
}
```

### Testing State Changes

Mutate observable state from the test, then assert through the rule, which syncs first.

```kotlin
@Test
fun reflectsStateChange() {
    var enabled by mutableStateOf(false)
    composeTestRule.setContent { StatusBadge(online = enabled) }

    composeTestRule.onNodeWithText("Offline").assertExists()

    enabled = true

    composeTestRule.onNodeWithText("Online").assertExists()
}
```

Without a sync call "no recomposition will occur and the UI will appear to be paused"; any assertion, action, or `waitForIdle()` triggers it. See [synchronization.md](../core/synchronization.md).

## Events & Interactions

```kotlin
// Click, then assert the resulting UI
composeTestRule.onNodeWithText("Continue").performClick()
composeTestRule.onNodeWithText("Welcome").assertIsDisplayed()

// Text input and scrolling
composeTestRule.onNodeWithTag("email").performTextInput("a@example.com")
composeTestRule.onNodeWithTag("footer").performScrollTo()

// performGesture is deprecated in favor of performTouchInput; make one perform call per action
composeTestRule.onNodeWithTag("list").performTouchInput { swipeLeft() }
```

Finders, assertions, and the full action list are in [semantics-finders.md](../core/semantics-finders.md) and [assertions-actions.md](../core/assertions-actions.md).

## Accessing Resources and the Activity

Use an `AndroidComposeTestRule` with `ComponentActivity` when you need both your own content and activity resources, for example to assert text against a string resource.

```kotlin
class MyComposeTest {
    @get:Rule
    val composeTestRule = createAndroidComposeRule<ComponentActivity>()

    @Test
    fun myTest() {
        composeTestRule.setContent {
            MyAppTheme {
                MainScreen(uiState = exampleUiState)
            }
        }

        val continueLabel = composeTestRule.activity.getString(R.string.next)
        composeTestRule.onNodeWithText(continueLabel).performClick()
    }
}
```

```kotlin
// Good: derive expected text from the resource
composeTestRule.onNodeWithText(composeTestRule.activity.getString(R.string.next))

// Bad: hardcoded string that breaks when copy or locale changes
composeTestRule.onNodeWithText("Next")
```

On Robolectric, resources require `isIncludeAndroidResources = true`.

## Custom Semantics for Tests

When a finder or matcher cannot single out an item, expose a value through a custom semantics property and match it with `SemanticsMatcher.expectValue`.

```kotlin
// Production code
val PickedDateKey = SemanticsPropertyKey<Long>("PickedDate")
var SemanticsPropertyReceiver.pickedDate by PickedDateKey

val datePickerValue by remember { mutableStateOf(0L) }
MyCustomDatePicker(
    modifier = Modifier.semantics { pickedDate = datePickerValue }
)

// Test
composeTestRule
    .onNode(SemanticsMatcher.expectValue(PickedDateKey, 1445378400)) // 2015-10-21
    .assertExists()
```

Use this only when it is hard to match the item with the standard finders. Do not expose visual properties such as colors, font size, or corner radius: it can pollute production code and wrong implementations lead to bugs that are hard to find.

## What to Test, Including Edge Cases

For a screen UI test, check critical interactions on a single screen: clicking buttons, typing in forms, and checking visible states. Cover normal paths and the edge cases that larger tests and human testers rarely hit, expressed as inputs to the composable:

| Case                                         | How to drive it in a component test                          |
| -------------------------------------------- | ------------------------------------------------------------ |
| Empty, loading, and error UI states          | Pass each state value in `setContent`                        |
| Corrupted or unexpected data                 | Pass the data the model would produce; assert fallback UI    |
| Object recreated mid-process (rotation)      | `StateRestorationTester`, see [state-restoration.md](state-restoration.md) |
| Different fonts, themes, locales, sizes      | `DeviceConfigurationOverride`, see [device-configuration.md](../advanced/device-configuration.md) |
| Focus order for keyboard and D-pad users     | See [accessibility.md](accessibility.md)                     |
| Animation intermediate states                | See [animations.md](animations.md)                           |

Behavior tests like "the UI changed after clicking a button" are well within Robolectric's fidelity. Do not test the framework or a library; test your composable's logic.

## Isolating Dependencies

Replace dependencies with fakes injected at a seam, so the composable (or its state holder) receives deterministic data. Android's guidance prefers fakes over mocks and stubs because they are lightweight and need no mocking framework.

```kotlin
// Good: a fake behind an interface
class FakeCartRepository(private val items: List<CartItem>) : CartRepository {
    override fun items(): List<CartItem> = items
}

// Bad: mocking Android classes that other Android code acts on
val context = mock<Context>()
```

Do not mock or spy on Android classes that Android code will act on, such as `Context` or `SharedPreferences`; stubbing is brittle. See [test-doubles.md](../architecture/test-doubles.md) and [coroutines-viewmodels.md](coroutines-viewmodels.md).

## Anti-Patterns to Avoid

| Anti-Pattern                                    | Problem                                    | Solution                                                 |
| ----------------------------------------------- | ------------------------------------------ | -------------------------------------------------------- |
| Only unit-scoped UI tests                       | Misses integration of larger UI parts      | Add tests scoped to bigger parts of the UI              |
| Calling `setContent` on a rule whose activity already does | Not allowed                       | `createAndroidComposeRule<ComponentActivity>()`          |
| Hardcoded strings from resources                | Breaks on copy or locale change            | `composeTestRule.activity.getString(R.string.x)`         |
| Exposing colors or font sizes via custom semantics | Pollutes production code                | Test visuals with screenshot tests                       |
| Mocking `Context` or `SharedPreferences`        | Brittle                                    | Real Robolectric environment or fakes                    |
| Asserting right after mutating state outside the rule | No recomposition yet                 | Assert via the rule, or `waitForIdle()`                  |
| Testing library or framework behavior           | No value for your code                     | Test your composable's logic                             |

## Related References

- **Setup**: See [test-suite-structure.md](../core/test-suite-structure.md) for rules and test anatomy
- **Selectors**: See [semantics-finders.md](../core/semantics-finders.md) for finders and custom semantics keys
- **Assertions**: See [assertions-actions.md](../core/assertions-actions.md) for assertions and actions
- **State restoration**: See [state-restoration.md](state-restoration.md) for `rememberSaveable` checks
- **Accessibility**: See [accessibility.md](accessibility.md) for focus and a11y checks
- **Test doubles**: See [test-doubles.md](../architecture/test-doubles.md) for fakes over mocks

## Sources

- https://developer.android.com/develop/ui/compose/testing/common-patterns
- https://developer.android.com/develop/ui/compose/testing
- https://developer.android.com/develop/ui/compose/testing/apis
- https://developer.android.com/develop/ui/compose/testing/synchronization
- https://developer.android.com/guide/navigation/testing/compose
- https://developer.android.com/training/testing/fundamentals/what-to-test
- https://developer.android.com/training/testing/fundamentals/test-doubles
- https://developer.android.com/training/testing/local-tests/robolectric
- https://robolectric.org/best-practices/
- https://robolectric.org/blog/2026/07/03/designing-local-testing-libraries/
