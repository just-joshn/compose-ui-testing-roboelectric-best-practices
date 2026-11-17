# Choosing Test Types: Unit, Robolectric, or Device

## Table of Contents

1. [Decision Matrix](#decision-matrix)
2. [Unit Tests (Local JVM)](#unit-tests-local-jvm)
3. [Robolectric UI Tests](#robolectric-ui-tests)
4. [Device Tests](#device-tests)
5. [Layering Test Types](#layering-test-types)
6. [Source Sets and Shared Tests](#source-sets-and-shared-tests)
7. [Common Mistakes](#common-mistakes)
8. [Related References](#related-references)
9. [Sources](#sources)

> **When to use**: Deciding where a test should run. Ask: "What is the lowest layer of the pyramid that gives the team the right level of feedback?"

## Decision Matrix

| Scenario                          | Recommended Type           | Rationale                                                 |
| --------------------------------- | -------------------------- | --------------------------------------------------------- |
| Form validator logic              | Unit (local JVM)           | No Android framework needed                               |
| ViewModel state transitions       | Unit (local JVM)           | Fakes for repositories; no UI                             |
| Repository / use case             | Unit (local JVM)           | Test doubles replace database and remote sources          |
| Sign-in form UI behavior          | Component, Robolectric     | Behavior fidelity on Robolectric is more than enough      |
| Sign-in form appearance           | Component, screenshot test | Official tool: Compose Preview Screenshot Testing         |
| UI sending credentials to an auth manager | Feature, JVM test with fakes | Fakes stand in for the auth manager's responses |
| Whole screen, debuggable build    | Application, Robolectric   | UI behavior test running on Robolectric                   |
| Font scale / theme reactions      | Robolectric                | Pixel accuracy not critical                               |
| Edge-to-edge, picture-in-picture  | Device                     | System UI is not simulated                                |
| `WebView` content                 | Device                     | Unsupported on Robolectric                                |
| Accessibility checks              | Device (API 34+)           | `enableAccessibilityChecks` does not work on Robolectric  |
| Critical user journey             | Device, release candidate  | End-to-end Compose UI behavior test on a minified build   |

## Unit Tests (Local JVM)

**Ideal for**:

- ViewModels and presenters
- Data layer and repositories
- Domain layer (use cases)
- Utility classes (math, validation, formatting)
- Edge cases: negative/zero/boundary values, all network errors, corrupted JSON, full storage, objects recreated mid-process

**Avoid for**:

- Verifying framework or library behavior
- Unit tests for activities, fragments, and services (little value)
- Anything that needs Android `Context` inside a ViewModel

```kotlin
// src/test/java/.../SignInViewModelTest.kt
class SignInViewModelTest {
    @Test
    fun rejectsEmptyPassword() = runTest {
        val viewModel = SignInViewModel(FakeUserRepository())

        viewModel.submit(email = "alex@company.org", password = "")

        assertEquals(SignInError.EmptyPassword, viewModel.state.value.error)
    }
}
```

Run these on the plain JVM with no Robolectric. Using Robolectric for unit tests is a last resort: legacy code, or APIs that depend on Android classes.

## Robolectric UI Tests

**Ideal for**:

- Isolated UI behavior for components, features, and whole screens
- A Compose test verifying the UI changed after a click
- Reactions to font sizes, themes, locales, and screen sizes
- Screenshots when pixel accuracy is not critical

**Avoid for**:

- System UI (edge-to-edge, picture-in-picture)
- Unsupported features such as `WebView`
- Accessibility checks (not supported on Robolectric)
- Pixel-perfect visual verification (fidelity is lower; different devices render slightly differently)

```kotlin
// src/test/java/.../SignInScreenTest.kt
@RunWith(AndroidJUnit4::class)
class SignInScreenTest {
    @get:Rule val composeTestRule = createAndroidComposeRule<ComponentActivity>()

    @Test
    fun showsWelcomeAfterContinue() {
        composeTestRule.setContent { SignInScreen(repository = FakeUserRepository()) }

        composeTestRule.onNodeWithText("Continue").performClick()

        composeTestRule.onNodeWithText("Welcome").assertIsDisplayed()
    }
}
```

The Robolectric blog states the same `createAndroidComposeRule<ComponentActivity>()` / `runComposeUiTest { }` code runs on a device and on the JVM from one binary. Setup is in [configuration.md](../core/configuration.md).

## Device Tests

Use instrumented tests "only in cases where you must test against the behavior of a real device."

| Needs a device when...                 | Why                                              |
| -------------------------------------- | ------------------------------------------------ |
| Edge-to-edge, picture-in-picture       | System UI is not part of the simulation          |
| `WebView`                              | Unsupported feature on Robolectric               |
| Real hardware or cross-process IPC     | Robolectric emulates only enough of Android      |
| Foldable posture logic                 | Posture changes do not trigger a configuration change |
| Accessibility Test Framework checks    | API 34+, "does not work on Robolectric"          |
| Release candidate journeys             | Minified release build on phones, foldables, tablets |

Robolectric "doesn't have a screen like an emulator does, and some APIs are only partially supported."

## Layering Test Types

Five layers, smallest to largest:

| Layer             | Runs on                                   | Example                                                 |
| ----------------- | ----------------------------------------- | ------------------------------------------------------- |
| Unit              | Local JVM, no Android framework           | Form validator                                          |
| Component         | Local, Robolectric, or emulator           | Custom button screenshot test                           |
| Feature           | Local, Robolectric, emulator, or device   | UI behavior test of state management in one screen      |
| Application       | Debuggable build                          | Configuration changes on a foldable, localization, a11y |
| Release candidate | Minified release build                    | Critical user journeys                                  |

### Execution Profile

| When          | Layers                                       |
| ------------- | -------------------------------------------- |
| Every commit  | Unit and Component, affected modules         |
| Pre-merge     | Unit, Component, Feature                     |
| Post-merge    | Application                                  |
| Nightly       | Release candidate on phone, foldable, tablet |

Bias effort toward smaller and more frequent tests. One test class per screen is a good starting point for screen UI tests. Coverage "should not be used as the only metric."

## Source Sets and Shared Tests

| Source set     | Runs on                         | Gradle task                  |
| -------------- | ------------------------------- | ---------------------------- |
| `src/test`     | Local JVM (UI tests use Robolectric) | `./gradlew test`        |
| `src/androidTest` | Device or emulator           | `./gradlew connectedCheck`   |

Any UI test in `test` runs with Robolectric. To convert an instrumented test, move it to `test` and add the Robolectric dependencies.

To share one test body, add a `src/sharedTest/java` directory to both source sets (the 2021 `sharedTest` pattern). `AndroidJUnit4` delegates to `RobolectricTestRunner` on the JVM and to `AndroidJUnit4ClassRunner` on a device.

```kotlin
// src/sharedTest/java/.../CheckoutScreenTest.kt: one body, two runners
@RunWith(AndroidJUnit4::class)
class CheckoutScreenTest { /* ... */ }
```

## Common Mistakes

| Anti-Pattern                                   | Problem                                                    | Better Approach                                            |
| ---------------------------------------------- | ---------------------------------------------------------- | ---------------------------------------------------------- |
| Every test on an emulator                      | Slow, flaky; Robolectric handles most behavior tests       | Robolectric for behavior, device for what it cannot do     |
| Robolectric for pure logic                     | Unneeded framework overhead                                | Plain JVM unit test with fakes                             |
| Unit tests for activities and fragments        | Little value; entry points only                            | Test the ViewModel; test the screen via the compose rule   |
| `Context` inside ViewModels                    | Forces Robolectric where a JVM test would do               | Interfaces plus DI; keep logic out of Android classes      |
| Cross every theme x font size in screenshots   | Thousands of screenshot files, most giving no extra feedback | Pick screenshots that give unique feedback               |
| Pixel-perfect assertions on Robolectric        | Fidelity is lower; devices render slightly differently     | Robolectric screenshots only when pixel accuracy is not critical |
| Trusting 4.13 or `API 16+` from Android pages  | Stale numbers                                              | Use robolectric.org: 4.18 supports API 24-37               |

## Related References

- **Test anatomy and rules**: See [test-suite-structure.md](../core/test-suite-structure.md)
- **Gradle and Robolectric setup**: See [configuration.md](../core/configuration.md)
- **Fakes and DI seams**: See [test-doubles.md](test-doubles.md)
- **Component tests**: See [component-testing.md](../testing-patterns/component-testing.md)
- **Screenshot testing**: See [visual-regression.md](../testing-patterns/visual-regression.md)
- **Accessibility**: See [accessibility.md](../testing-patterns/accessibility.md)
- **Screen sizes**: See [device-configuration.md](../advanced/device-configuration.md)
- **CI**: See [ci-cd.md](../infrastructure-ci-cd/ci-cd.md)

## Sources

- https://developer.android.com/training/testing/fundamentals
- https://developer.android.com/training/testing/fundamentals/what-to-test
- https://developer.android.com/training/testing/fundamentals/strategies
- https://developer.android.com/training/testing/local-tests
- https://developer.android.com/training/testing/local-tests/robolectric
- https://developer.android.com/training/testing/ui-tests
- https://developer.android.com/training/testing/ui-tests/behavior
- https://developer.android.com/training/testing/ui-tests/screenshot
- https://developer.android.com/training/testing/instrumented-tests
- https://developer.android.com/training/testing/different-screens
- https://robolectric.org/compatibility_table/
- https://robolectric.org/blog/2021/10/06/sharedTest/
- https://robolectric.org/blog/2026/07/03/designing-local-testing-libraries/
