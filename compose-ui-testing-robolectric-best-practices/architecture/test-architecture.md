# Choosing Test Types: Robolectric or Device

## Table of Contents

1. [Robolectric UI Tests](#robolectric-ui-tests)
2. [Device Tests](#device-tests)
3. [Robolectric for Unit Tests](#robolectric-for-unit-tests)
4. [Source Sets and Shared Tests](#source-sets-and-shared-tests)
5. [Related References](#related-references)
6. [Sources](#sources)

## Robolectric UI Tests

Robolectric can also run UI tests such as Espresso or Compose tests.

Most UI tests don't interact with the framework and you can run them on Robolectric. You can run behavior tests on Robolectric as the fidelity needed for it is more than enough. For example, when a Compose test verifies that the UI has changed after clicking a button.

You can run other UI tests with Robolectric, such as screenshot tests. However the fidelity is lower as different devices render screens slightly differently.

You must decide whether Robolectric's implementation is good enough for each use case, but here are some recommendations:

- Use Robolectric for isolated UI behavior tests for components, feature or application tests. In general these tests check the state management and behavior of the UIs and don't interact with external dependencies.
- Use Robolectric to take screenshots when the pixel accuracy is not critical. For example, to test how a component reacts to different font sizes or themes.

Robolectric can take screenshots natively, but you need a third-party library to perform screenshot testing with it.

A post on robolectric.org says the same createAndroidComposeRule<ComponentActivity>() / runComposeUiTest { } code runs on a device and on the JVM from one binary, with no Robolectric-specific source set. The post calls itself an outside read of the code as it stands in mid-2026, not an official AndroidX position.

## Device Tests

Robolectric is not a complete replacement for an emulator because it doesn't support all the features and APIs.

Robolectric provides enough fidelity to run most UI tests but some cases will still require device tests, for example those related to system UI like edge-to-edge or picture-in-picture, or when relying on unsupported features, like WebView.

Robolectric doesn't have a screen like an emulator does, and some APIs are only partially supported.

Accessibility checks enabled with `enableAccessibilityChecks` require API 34+ (Android U), and currently do not work on Robolectric.

A post on robolectric.org that calls itself an outside read, not an official AndroidX position, says anything that truly needs real hardware or cross-process IPC still belongs in an instrumented test.

## Robolectric for Unit Tests

In most cases, only use Robolectric for unit testing as a last resort: with legacy code or when using APIs that depend on Android classes. When possible, refactor your code so that it's testable without Robolectric shadows, or test the feature using a different type of test, such as a UI test.

## Source Sets and Shared Tests

You can convert an instrumented test to Robolectric by moving it to the `test` source set and setting up the Robolectric dependencies. Any UI test present in the `test` source set runs with Robolectric.

A 2021 post on robolectric.org describes a widely-used pattern called sharedTest to share tests between local and instrumentation tests. The steps below are that post's.

The first thing that sharedTest needs is AndroidJUnit4 test runner.

The second thing to enable sharedTest is to create a directory called sharedTest, at the same directory level with test and androidTest.

The next step we should do is to add sharedTest directory to test's and androidTest's source directory.

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

The last thing is to test it with ./gradlew test for local tests on Robolectric and ./gradlew connectedCheck for instrumentation tests on Emulator.

AndroidJUnit4 delegates tests to a real test runner based on running environment: if the current running environment has RobolectricTestRunner, it delegates to Robolectric's RobolectricTestRunner; otherwise to androidx.test's AndroidJUnit4ClassRunner.

## Related References

- **Gradle and Robolectric setup**: See [configuration.md](../core/configuration.md)
- **Fakes, mocks, and shadows**: See [test-doubles.md](test-doubles.md)
- **Screenshot testing**: See [visual-regression.md](../testing-patterns/visual-regression.md)
- **Accessibility**: See [accessibility.md](../testing-patterns/accessibility.md)
- **CI**: See [ci-cd.md](../infrastructure-ci-cd/ci-cd.md)

## Sources

- https://developer.android.com/training/testing/local-tests/robolectric
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/junit4/ComposeTestRule
- https://robolectric.org/blog/2021/10/06/sharedTest
- https://robolectric.org/blog/2026/07/03/designing-local-testing-libraries
