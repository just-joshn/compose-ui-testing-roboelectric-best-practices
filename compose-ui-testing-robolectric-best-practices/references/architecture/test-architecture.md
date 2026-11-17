# Choosing Test Types: Robolectric or Device

## Table of Contents

1. [Recommendations](#recommendations)
2. [Robolectric UI Tests](#robolectric-ui-tests)
3. [Device Tests](#device-tests)
4. [Robolectric for Unit Tests](#robolectric-for-unit-tests)
5. [Source Sets](#source-sets)
6. [Related References](#related-references)
7. [Sources](#sources)

## Recommendations

You must decide whether Robolectric's implementation is good enough for each use case, but here are some recommendations:

- Use Robolectric for isolated UI behavior tests for components, feature or application tests. In general these tests check the state management and behavior of the UIs and don't interact with external dependencies.
- Use Robolectric to take screenshots when the pixel accuracy is not critical. For example, to test how a component reacts to different font sizes or themes.

## Robolectric UI Tests

Robolectric can also run UI tests such as Espresso or Compose tests.

Most UI tests don't interact with the framework and you can run them on Robolectric.

### Behavior Tests

You can run behavior tests on Robolectric as the fidelity needed for it is more than enough. For example, when a Compose test verifies that the UI has changed after clicking a button.

### Screenshot Tests

You can run other UI tests with Robolectric, such as screenshot tests. However the fidelity is lower as different devices render screens slightly differently.

Robolectric can take screenshots natively, but you need a third-party library to perform screenshot testing with it.

## Device Tests

Robolectric is not a complete replacement for an emulator because it doesn't support all the features and APIs.

Robolectric doesn't have a screen like an emulator does, and some APIs are only partially supported.

However, it emulates enough parts of Android to run unit tests and most UI tests reliably.

Robolectric provides enough fidelity to run most UI tests but some cases will still require device tests, for example those related to system UI like edge-to-edge or picture-in-picture, or when relying on unsupported features, like `WebView`.

`ComposeTestRule.enableAccessibilityChecks`: This requires API 34+ (Android U), and currently does not work on Robolectric.

Instrumented tests: It is good practice to also run instrumented tests. That is, tests that run directly on-device.

## Robolectric for Unit Tests

Robolectric was conceived as a way to enable "unit testing" in Android apps. For example, you can simulate the launch of an Activity and test the logic inside it, calling all the lifecycle methods.

In most cases, only use Robolectric for unit testing as a last resort: with legacy code or when using APIs that depend on Android classes. When possible, refactor your code so that it's testable without Robolectric shadows, or test the feature using a different type of test, such as a UI test.

In general, if you implement a testable architecture you shouldn't need to use Robolectric for unit testing as your code should be testable in isolation, with no dependencies on the Android framework.

## Source Sets

You can convert an instrumented test to Robolectric by moving it to the `test` source set and setting up the Robolectric dependencies.

```kotlin
android {
  testOptions {
    unitTests {
      isIncludeAndroidResources = true
    }
  }
}
```

Any UI test present in the `test` source set runs with Robolectric.

## Related References

- **Gradle and Robolectric setup**: See [configuration.md](../core/configuration.md)
- **Shadows and mocks**: See [test-doubles.md](test-doubles.md)
- **Screenshot testing**: See [visual-regression.md](../testing-patterns/visual-regression.md)
- **Accessibility**: See [accessibility.md](../testing-patterns/accessibility.md)
- **CI**: See [ci-cd.md](../infrastructure-ci-cd/ci-cd.md)

## Sources

- https://developer.android.com/training/testing/local-tests/robolectric
- https://developer.android.com/develop/ui/compose/testing
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/junit4/ComposeTestRule
