# Test Suite Structure

## Table of Contents

1. [Test Anatomy](#test-anatomy)
2. [Choosing a Rule](#choosing-a-rule)
3. [Setting Content](#setting-content)
4. [Where Tests Live](#where-tests-live)
5. [Shared JVM and Device Tests](#shared-jvm-and-device-tests)
6. [Test Scope](#test-scope)
7. [Common Issues & Solutions](#common-issues--solutions)
8. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
9. [Related References](#related-references)
10. [Sources](#sources)

## Test Anatomy

Compose provides a set of testing APIs to find elements, verify their attributes, and perform user actions.

The `ui-test-junit4` module includes a `ComposeTestRule` and an implementation for Android called `AndroidComposeTestRule`. Through this rule you can set Compose content or access the activity. You construct the rules using factory functions, either `createComposeRule` or, if you need access to an activity, `createAndroidComposeRule`.

A typical UI test for Compose looks like this:

```kotlin
// file: app/src/androidTest/java/com/package/MyComposeTest.kt

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

## Choosing a Rule

| API | What the API reference says |
| --- | --- |
| `createComposeRule()` | Useful for tests in compose libraries where it is irrelevant where the compose content is hosted (for example, an Activity on Android). On Android it uses the default Activity (`android.app.Activity`). |
| `createAndroidComposeRule<YourActivity>()` | Useful for tests that require a custom Activity. This is usually the case for tests where the compose content is set by that Activity, instead of via the test rule's `setContent`. |
| `createEmptyComposeRule()` | Does not create a compose host for you. Useful for tests that need to create their own compose host during the test. The returned test rule does not provide a `setContent` method. |
| `runComposeUiTest { }` | Sets up the test environment, runs the block, and then tears down the test environment. Launches a Compose host (such as an Activity on Android) for you. |
| `runAndroidComposeUiTest<A> { }` | Variant of `runComposeUiTest` that allows you to specify which Activity should be launched. |
| `runEmptyComposeUiTest { }` | Variant of `runComposeUiTest` that does not launch an Activity to host Compose content in and thus acts as an "empty shell". |

The v2 versions of the Compose testing APIs are now available to improve control over coroutine execution. This update does not duplicate the entire API surface; only the APIs that establish the test environment have been updated.

The v1 APIs are deprecated, and it's strongly recommended to migrate to the new APIs.

While the v1 APIs relied on the `UnconfinedTestDispatcher`, the v2 APIs use the `StandardTestDispatcher` by default for the running composition.

The deprecated `androidx.compose.ui.test.junit4.createComposeRule`, `createAndroidComposeRule` and `createEmptyComposeRule` are replaced by the functions of the same names in `androidx.compose.ui.test.junit4.v2`. The deprecated `androidx.compose.ui.test.runComposeUiTest`, `runAndroidComposeUiTest` and `runEmptyComposeUiTest` are replaced by the functions of the same names in `androidx.compose.ui.test.v2`.

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

You can't call `setContent` on a rule created with `createAndroidComposeRule()` if the activity already calls it. A common pattern to achieve this is to create an `AndroidComposeTestRule` using an empty activity such as `ComponentActivity`.

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

## Where Tests Live

- Robolectric can also run UI tests such as Espresso or Compose tests. You can convert an instrumented test to Robolectric by moving it to the `test` source set and setting up the Robolectric dependencies.
- Any UI test present in the `test` source set runs with Robolectric.
- Most UI tests don't interact with the framework and you can run them on Robolectric. You can run behavior tests on Robolectric as the fidelity needed for it is more than enough. For example, when a Compose test verifies that the UI has changed after clicking a button.
- Robolectric is not a complete replacement for an emulator because it doesn't support all the features and APIs.
- Robolectric provides enough fidelity to run most UI tests but some cases will still require device tests, for example those related to system UI like edge-to-edge or picture-in-picture, or when relying on unsupported features, like `WebView`.
- Robolectric is intended to be fully compatible with Android's official testing libraries since version 4.0, and it is now possible to use the AndroidX test runner in Robolectric tests.

```kotlin
import androidx.test.ext.junit.runners.AndroidJUnit4

@RunWith(AndroidJUnit4::class)
class SandwichTest {
}
```

## Shared JVM and Device Tests

The Robolectric blog post "sharedTest" (2021) shows a pattern called `sharedTest` to share tests between local and instrumentation tests. According to the post, the first thing that `sharedTest` needs is the `AndroidJUnit4` test runner, a test runner that supports both Robolectric and androidx.test.

The post says that if `AndroidJUnit4` finds the current running environment has `RobolectricTestRunner`, it delegates tests to Robolectric's `RobolectricTestRunner`; otherwise to androidx.test's `AndroidJUnit4ClassRunner`.

The post says the second thing to enable `sharedTest` is to create a directory called `sharedTest`, at the same directory level with `test` and `androidTest`. The next step it gives is to add the `sharedTest` directory to the source directories of `test` and `androidTest`:

```groovy
// share the unified tests
sourceSets {
    test {
        java.srcDir 'src/sharedTest/java'
    }
    androidTest {
        java.srcDir 'src/sharedTest/java'
    }
}
```

The post's last step is to test it with `./gradlew test` for local tests on Robolectric and `./gradlew connectedCheck` for instrumentation tests on an emulator.

## Test Scope

`ComposeTestRule` lets you start an activity displaying any composable: your full application, a single screen, or a small element. It's also a good practice to check that your composables are correctly encapsulated and they work independently, allowing for easier and more focused UI testing.

This doesn't mean you should *only* create unit UI tests. UI tests scoping larger parts of your UI are also very important.

## Common Issues & Solutions

| Issue | Solution |
| --- | --- |
| You can't call `setContent` on a rule created with `createAndroidComposeRule()` because the activity already calls it. | Create an `AndroidComposeTestRule` using an empty activity such as `ComponentActivity`. |
| You launch a task (for example, a ViewModel loads data), but your assertion fails immediately because the data is still in a "Loading" state. | With the v2 APIs, coroutines are queued rather than executed immediately. Use `waitForIdle` or `runOnIdle` to execute queued tasks before asserting. |
| Auto-advancing is disabled and launching a coroutine does not result in immediate execution because the test clock is paused. | To execute coroutines in the queue without advancing the virtual clock, use the `runCurrent()` API: `composeTestRule.mainClock.scheduler.runCurrent()`. |
| `createComposeRule` used with `runTest` creates two separate clocks: one for Compose, and one for the test coroutine scope. | Switch to `runComposeUiTest`. |

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
| --- | --- | --- |
| Using `createComposeRule` together with `runTest` | The code is marked "NOT RECOMMENDED": it creates two separate clocks, and you may need to manually synchronize the test scheduler. | Use `runComposeUiTest`. |
| Using a `ComposeTestRule` (for example `createComposeRule`) inside `runAndroidComposeUiTest` or its variants | The API reference says these APIs independently manage the test environment, so mixing them may lead to unexpected behavior. | Avoid mixing them. |
| Relying on `UnconfinedTestDispatcher` behavior (the v1 APIs) | Immediate execution could inadvertently mask real timing issues or race conditions that would occur in a live application. | Migrate to the v2 APIs. |
| Using Robolectric for unit testing as a first choice | The Android Robolectric page says to only use Robolectric for unit testing as a last resort: with legacy code or when using APIs that depend on Android classes. | Refactor your code so that it's testable without Robolectric shadows, or test the feature using a different type of test, such as a UI test. |

## Related References

- **Dependencies and `@Config`**: See [configuration.md](configuration.md)
- **Finding nodes**: See [semantics-finders.md](semantics-finders.md)
- **Waiting and the test clock**: See [synchronization.md](synchronization.md)
- **Robolectric runtime modes**: See [runtime-modes.md](runtime-modes.md)

## Sources

- https://developer.android.com/develop/ui/compose/testing
- https://developer.android.com/develop/ui/compose/testing/common-patterns
- https://developer.android.com/develop/ui/compose/testing/migrate-v2
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/junit4/v2/package-summary
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/v2/package-summary
- https://developer.android.com/training/testing/local-tests/robolectric
- https://robolectric.org/androidx_test/
- https://robolectric.org/blog/2021/10/06/sharedTest/
