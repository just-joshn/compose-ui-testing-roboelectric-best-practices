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

A Compose UI test sets content, finds a node, acts on it, and asserts. Local Robolectric tests live in `src/test` and use the AndroidX runner.

```kotlin
// app/src/test/java/com/example/WelcomeScreenTest.kt
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class WelcomeScreenTest {
    @get:Rule
    val composeTestRule = createComposeRule()

    @Test
    fun continueButton_showsWelcome() {
        composeTestRule.setContent { WelcomeScreen() }

        composeTestRule.onNodeWithText("Continue").performClick()

        composeTestRule.onNodeWithText("Welcome").assertIsDisplayed()
    }
}
```

The Android testing docs show this `onNodeWithText("Continue").performClick()` / `onNodeWithText("Welcome").assertIsDisplayed()` pair under `androidTest`. Moving the same test to `src/test` with Robolectric is the documented conversion path for UI tests (see [Where Tests Live](#where-tests-live)).

`createComposeRule` is imported from the `v2` package above. The v1 factories are deprecated; see [synchronization.md](synchronization.md) for what v2 changes.

## Choosing a Rule

| Need                                                        | Use                                            |
| ----------------------------------------------------------- | ---------------------------------------------- |
| Show any composable, no specific activity                   | `createComposeRule()`                          |
| A specific activity, or access to `activity` and resources  | `createAndroidComposeRule<ComponentActivity>()` |
| No host started for you (you create the host)               | `createEmptyComposeRule()`                     |
| Coroutine-heavy test, one clock for Compose and the test    | `runComposeUiTest { }`                         |
| Specific activity inside `runComposeUiTest` style           | `runAndroidComposeUiTest<A> { }`               |

All rule factories exist in `androidx.compose.ui.test.junit4.v2`; all `run*ComposeUiTest` functions in `androidx.compose.ui.test.v2`.

```kotlin
// Rule style: the rule is a JUnit @Rule, call it as composeTestRule.xxx
@get:Rule
val composeTestRule = createComposeRule()

// Function style: the receiver is ComposeUiTest, no rule field
@Test
fun greeting_isShown() = runComposeUiTest {
    setContent { Greeting("Ada") }
    onNodeWithText("Hello, Ada").assertIsDisplayed()
}
```

`runComposeUiTest` runs your block in its own `runTest` scope with the Compose clock synchronized to it. The API reference examples for these APIs use `@OptIn(ExperimentalTestApi::class)`; the release notes list `ComposeUiTest` and related testing APIs (including `ComposeTestRule` and `waitUntil` variants) as promoted from Experimental to stable in 1.13.0-alpha01.

```kotlin
// Bad: two APIs that each manage their own test environment
@get:Rule val rule = createComposeRule()

@Test
fun mixed() = runComposeUiTest { /* rule inside run*ComposeUiTest */ }
```

The API docs say to avoid using a `ComposeTestRule` (for example from `createComposeRule`) inside `runAndroidComposeUiTest` or its variants: mixing them "may lead to unexpected behavior".

## Setting Content

```kotlin
@Test
fun myTest() {
    composeTestRule.setContent {
        MyAppTheme {
            MainScreen(uiState = exampleUiState)
        }
    }
    composeTestRule.onNodeWithText("Continue").performClick()
}
```

### Access activity and resources

You cannot call `setContent` on a rule from `createAndroidComposeRule<MyActivity>()` when `MyActivity` already sets content. Use an empty activity:

```kotlin
class MyComposeTest {
    @get:Rule
    val composeTestRule = createAndroidComposeRule<ComponentActivity>()

    @Test
    fun myTest() {
        composeTestRule.setContent { MyAppTheme { MainScreen(uiState = exampleUiState) } }

        // Good: assert against the string resource, not a hard-coded copy
        val continueLabel = composeTestRule.activity.getString(R.string.next)
        composeTestRule.onNodeWithText(continueLabel).performClick()
    }
}
```

`ComponentActivity` must be in the merged `AndroidManifest.xml`. The docs enable that with `debugImplementation("androidx.compose.ui:ui-test-manifest:$compose_version")`. `createComposeRule()` also needs it; `createAndroidComposeRule<YourActivity>()` does not. Dependency setup lives in [configuration.md](configuration.md).

## Where Tests Live

| Source set          | Runs on                 | Command                            |
| ------------------- | ----------------------- | ---------------------------------- |
| `src/test`          | Local JVM (Robolectric) | `./gradlew test`                   |
| `src/androidTest`   | Device or emulator      | `./gradlew connectedCheck`         |

- To convert an instrumented UI test, "move it to the `test` source set and set up the Robolectric dependencies." Any UI test in `test` runs with Robolectric.
- Use `@RunWith(AndroidJUnit4::class)` (`androidx.test.ext.junit.runners.AndroidJUnit4`) rather than `RobolectricTestRunner`. Robolectric recommends the AndroidX Test APIs; the same runner runs on a device.
- Behavior tests suit Robolectric: the docs name "a Compose test verifies that the UI has changed after clicking a button" as an example where its fidelity is "more than enough".
- Robolectric is not an emulator. System UI such as edge-to-edge, picture-in-picture, and `WebView` still need device tests.

One test class per screen is a good starting point for screen UI tests.

```kotlin
// Good: one class per screen, named for the screen
class SignInScreenTest { /* ... */ }
class ProfileScreenTest { /* ... */ }

// Good: test names describe state and outcome
@Test
fun emptyEmail_disablesSubmit() { /* ... */ }
```

## Shared JVM and Device Tests

Because `AndroidJUnit4` delegates to `RobolectricTestRunner` when Robolectric is on the classpath (JVM) and to the device runner otherwise, one body can run in both places. The Robolectric `sharedTest` pattern adds one directory to both source sets:

```kotlin
// build.gradle.kts (android block)
sourceSets {
    getByName("test").java.srcDir("src/sharedTest/java")
    getByName("androidTest").java.srcDir("src/sharedTest/java")
}
```

```bash
./gradlew test            # local, Robolectric
./gradlew connectedCheck  # instrumented, emulator or device
```

The Robolectric 2026 blog describes Compose's own tests the same way: the same `createAndroidComposeRule<ComponentActivity>()` / `runComposeUiTest { }` code runs on a device and on the JVM from one binary, with no Robolectric-specific source set. The `sharedTest` blog shows Groovy `sourceSets` syntax; the Kotlin DSL above is the equivalent form.

## Test Scope

`ComposeTestRule` can host your full app, one screen, or one small element. Test composables in isolation to check they are correctly encapsulated, but do not stop there: "UI tests scoping larger parts of your UI are also very important."

| Scope                       | What to assert                              |
| --------------------------- | ------------------------------------------- |
| Component                   | Composable works independently, correctly encapsulated |
| Screen                      | Critical user interactions: clicks, typing in forms, visible states |
| User flow / navigation      | Run-time crashes in initialization          |

Replace dependencies with fakes through dependency injection so tests are hermetic; see [test-doubles.md](../architecture/test-doubles.md).

## Common Issues & Solutions

| Issue                                                        | Solution                                                                  |
| ------------------------------------------------------------ | ------------------------------------------------------------------------- |
| `setContent` fails or overrides content                      | Use `createAndroidComposeRule<ComponentActivity>()` with an empty activity |
| Activity not found / not declared                            | Add `ui-test-manifest` as `debugImplementation`                           |
| Assertion sees a "Loading" state after a coroutine launch    | v2 queues coroutines; call `waitForIdle()` or `runOnIdle { }`             |
| Test uses `runTest` and `createComposeRule` and times differ | Switch to `runComposeUiTest` (one clock)                                  |
| Same test needed on device and JVM                           | Target `AndroidJUnit4` and share a `sharedTest` directory                 |

## Anti-Patterns to Avoid

| Anti-Pattern                                         | Problem                                       | Solution                                          |
| ---------------------------------------------------- | --------------------------------------------- | ------------------------------------------------- |
| `RuntimeEnvironment.application` in new tests        | Robolectric-only API, less portable           | `ApplicationProvider.getApplicationContext()`     |
| Robolectric-only runner for Compose tests            | Not runnable on a device                      | `@RunWith(AndroidJUnit4::class)`                  |
| Unit tests for activities with little logic          | "Little value" per the Android testing docs   | Test composables and ViewModels                   |
| Only tiny isolated composable tests                  | Misses integration problems                   | Add screen and flow tests too                     |
| Mixing a rule with `runComposeUiTest`                | Two test environments                         | Pick one style per test                           |

## Related References

- **Dependencies and `@Config`**: See [configuration.md](configuration.md)
- **Finding nodes**: See [semantics-finders.md](semantics-finders.md)
- **Waiting and the test clock**: See [synchronization.md](synchronization.md)
- **Fakes instead of mocks**: See [test-doubles.md](../architecture/test-doubles.md)

## Sources

- https://developer.android.com/develop/ui/compose/testing
- https://developer.android.com/develop/ui/compose/testing/common-patterns
- https://developer.android.com/develop/ui/compose/testing/migrate-v2
- https://developer.android.com/training/testing/local-tests/robolectric
- https://developer.android.com/training/testing/fundamentals/what-to-test
- https://developer.android.com/training/testing/continuous-integration
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/junit4/ComposeContentTestRule
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/package-summary
- https://developer.android.com/jetpack/androidx/releases/compose-ui
- https://robolectric.org/androidx_test/
- https://robolectric.org/blog/2021/10/06/sharedTest/
- https://robolectric.org/blog/2026/07/03/designing-local-testing-libraries/
