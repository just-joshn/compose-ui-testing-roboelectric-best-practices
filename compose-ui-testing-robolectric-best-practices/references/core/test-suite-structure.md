# Test Suite Structure

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Test Anatomy](#test-anatomy)
3. [Rule and Test Functions (v2)](#rule-and-test-functions-v2)
4. [v2 APIs](#v2-apis)
5. [Setting Content](#setting-content)
6. [Running on Robolectric](#running-on-robolectric)
7. [Test Scope](#test-scope)
8. [Cautions](#cautions)
9. [Related References](#related-references)
10. [Sources](#sources)

## Quick Reference

```kotlin
class MyComposeTest {

    @get:Rule val composeTestRule = createComposeRule()
    // use createAndroidComposeRule<YourActivity>() if you need access to
    // an activity

    @Test
    fun myTest() {
        // Start the app
        composeTestRule.setContent {
            MyAppTheme {
                MainScreen(uiState = fakeUiState, /*...*/)
            }
        }

        composeTestRule.onNodeWithText("Continue").performClick()

        composeTestRule.onNodeWithText("Welcome").assertIsDisplayed()
    }
}
```

## Test Anatomy

Compose provides a set of testing APIs to find elements, verify their attributes, and perform user actions.

`ui-test-junit4`: This module includes a `ComposeTestRule` and an implementation for Android called `AndroidComposeTestRule`. Through this rule you can set Compose content or access the activity. You construct the rules using factory functions, either `createComposeRule` or, if you need access to an activity, `createAndroidComposeRule`.

## Rule and Test Functions (v2)

| API | Description |
| --- | --- |
| `createComposeRule()` | This method is useful for tests in compose libraries where it is irrelevant where the compose content is hosted (e.g. an Activity on Android). For Android this will use the default Activity (`android.app.Activity`). |
| `createAndroidComposeRule()` | This method is useful for tests that require a custom Activity. This is usually the case for tests where the compose content is set by that Activity, instead of via the test rule's `setContent`. |
| `createEmptyComposeRule()` | This method is useful for tests that need to create their own compose host during the test. The returned test rule will not create a host, and consequently does not provide a `setContent` method. |
| `runComposeUiTest` | Sets up the test environment, runs the given test and then tears down the test environment. Implementations of this method will launch a Compose host (such as an Activity on Android) for you. |
| `runAndroidComposeUiTest` | Variant of `runComposeUiTest` that allows you to specify which Activity should be launched. |
| `runEmptyComposeUiTest` | Variant of `runComposeUiTest` that does not launch an Activity to host Compose content in and thus acts as an "empty shell". |

## v2 APIs

v2 versions of the Compose testing APIs (`createComposeRule`, `createAndroidComposeRule`, `runComposeUiTest`, `runAndroidComposeUiTest`, etc) are now available to improve control over coroutine execution. This update does not duplicate the entire API surface; only the APIs that establish the test environment have been updated.

The v1 APIs are deprecated, and it's strongly recommended to migrate to the new APIs.

While the v1 APIs relied on the `UnconfinedTestDispatcher`, the v2 APIs use the `StandardTestDispatcher` by default for the running composition.

### API Mappings

| Deprecated (v1) | Replacement (v2) |
| --- | --- |
| `androidx.compose.ui.test.junit4.createComposeRule` | `androidx.compose.ui.test.junit4.v2.createComposeRule` |
| `androidx.compose.ui.test.junit4.createAndroidComposeRule` | `androidx.compose.ui.test.junit4.v2.createAndroidComposeRule` |
| `androidx.compose.ui.test.junit4.createEmptyComposeRule` | `androidx.compose.ui.test.junit4.v2.createEmptyComposeRule` |
| `androidx.compose.ui.test.junit4.AndroidComposeTestRule` | `androidx.compose.ui.test.junit4.v2.AndroidComposeTestRule` |
| `androidx.compose.ui.test.runComposeUiTest` | `androidx.compose.ui.test.v2.runComposeUiTest` |
| `androidx.compose.ui.test.runAndroidComposeUiTest` | `androidx.compose.ui.test.v2.runAndroidComposeUiTest` |
| `androidx.compose.ui.test.runEmptyComposeUiTest` | `androidx.compose.ui.test.v2.runEmptyComposeUiTest` |
| `androidx.compose.ui.test.AndroidComposeUiTestEnvironment` | `androidx.compose.ui.test.v2.AndroidComposeUiTestEnvironment` |

### runComposeUiTest

The `runComposeUiTest` API automatically executes your test block within its own `runTest` scope. The test clock is synchronized with the Compose environment, so you no longer need to manage the scheduler manually.

```kotlin
@Test
fun testWithCoroutines() = runComposeUiTest {
    setContent {
        var status by remember { mutableStateOf("Loading...") }
        LaunchedEffect(Unit) {
            delay(1000)
            status = "Done!"
        }
        Text(text = status)
    }

    onNodeWithText("Loading...").assertIsDisplayed()
    mainClock.advanceTimeBy(1000 + 16 /* Frame buffer */)
    onNodeWithText("Done!").assertIsDisplayed()
}
```

## Setting Content

Oftentimes you need to set the content under test using `composeTestRule.setContent` and you also need to access activity resources, for example to assert that a displayed text matches a string resource. However, you can't call `setContent` on a rule created with `createAndroidComposeRule()` if the activity already calls it.

A common pattern to achieve this is to create an `AndroidComposeTestRule` using an empty activity such as `ComponentActivity`.

```kotlin
class MyComposeTest {

    @get:Rule
    val composeTestRule = createAndroidComposeRule<ComponentActivity>()

    @Test
    fun myTest() {
        // Start the app
        composeTestRule.setContent {
            MyAppTheme {
                MainScreen(uiState = exampleUiState, /*...*/)
            }
        }
        val continueLabel = composeTestRule.activity.getString(R.string.next)
        composeTestRule.onNodeWithText(continueLabel).performClick()
    }
}
```

`ComponentActivity` needs to be added to your app's `AndroidManifest.xml` file. Enable that by adding this dependency to your module:

```kotlin
debugImplementation("androidx.compose.ui:ui-test-manifest:$compose_version")
```

## Running on Robolectric

Robolectric can also run UI tests such as Espresso or Compose tests. You can convert an instrumented test to Robolectric by moving it to the `test` source set and setting up the Robolectric dependencies.

Any UI test present in the `test` source set runs with Robolectric.

### AndroidX Test

It is now possible to use the AndroidX test runner in Robolectric tests.

```kotlin
import androidx.test.ext.junit.runners.AndroidJUnit4

@RunWith(AndroidJUnit4::class)
class SandwichTest
```

- Robolectric is intended to be fully compatible with Android's official testing libraries since version 4.0.
- Using the AndroidX Test APIs reduces the cognitive load for you as a developer, with just one set of APIs to learn for the same Android concept, no matter if you are writing an Robolectric test or an instrumentation test.

### Robolectric versus device tests

- You can run behavior tests on Robolectric as the fidelity needed for it is more than enough. For example, when a Compose test verifies that the UI has changed after clicking a button.
- Robolectric provides enough fidelity to run most UI tests but some cases will still require device tests, for example those related to system UI like edge-to-edge or picture-in-picture, or when relying on unsupported features, like `WebView`.
- Most UI tests don't interact with the framework and you can run them on Robolectric.
- Robolectric is not a complete replacement for an emulator because it doesn't support all the features and APIs.

## Test Scope

`ComposeTestRule` lets you start an activity displaying any composable: your full application, a single screen, or a small element. It's also a good practice to check that your composables are correctly encapsulated and they work independently, allowing for easier and more focused UI testing.

This doesn't mean you should *only* create unit UI tests. UI tests scoping larger parts of your UI are also very important.

## Cautions

- Using `createComposeRule` in conjunction with `runTest` creates two separate clocks: one for Compose, and one for the test coroutine scope. This configuration can force you to manually synchronize the test scheduler. If you're using Compose test APIs alongside the Kotlin `runTest` API, it's strongly recommended to switch to `runComposeUiTest`.
- Avoid using `androidx.compose.ui.test.junit4.ComposeTestRule` (e.g., `createComposeRule`) inside `runAndroidComposeUiTest` or any of their respective variants. Since these APIs independently manage the test environment, mixing them may lead to unexpected behavior.
- Avoid using `androidx.compose.ui.test.junit4.ComposeTestRule` (e.g., `createComposeRule`) inside `runEmptyComposeUiTest` or any of their respective variants. Since these APIs independently manage the test environment, mixing them may lead to unexpected behavior.
- v1 APIs (`UnconfinedTestDispatcher`): When a coroutine was launched, it executed immediately on the current thread, often finishing before the next line of test code ran. Unlike production behavior, this immediate execution could inadvertently mask real timing issues or race conditions that would occur in a live application.
- In most cases, only use Robolectric for unit testing as a last resort: with legacy code or when using APIs that depend on Android classes. When possible, refactor your code so that it's testable without Robolectric shadows, or test the feature using a different type of test, such as a UI test.

## Related References

- **Dependencies and `@Config`**: See [configuration.md](configuration.md)
- **Finding nodes**: See [semantics-finders.md](semantics-finders.md)
- **Waiting and the test clock**: See [synchronization.md](synchronization.md)
- **Robolectric runtime modes**: See [runtime-modes.md](runtime-modes.md)

## Sources

- https://developer.android.com/develop/ui/compose/testing
- https://developer.android.com/develop/ui/compose/testing/common-patterns
- https://developer.android.com/develop/ui/compose/testing/migrate-v2
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/junit4/AndroidComposeTestRule
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/junit4/ComposeTestRule
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/junit4/v2/package-summary
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/v2/package-summary
- https://developer.android.com/training/testing/local-tests/robolectric
- https://robolectric.org/androidx_test/
