# Configuration

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Reference Tables](#reference-tables)
3. [Patterns](#patterns)
4. [Deprecations](#deprecations)
5. [Troubleshooting](#troubleshooting)
6. [Related References](#related-references)
7. [Sources](#sources)

## Quick Reference

### Compose UI Test Dependencies

First, add the following dependencies to the `build.gradle` file of the module containing your UI tests:

```groovy
// Test rules and transitive dependencies:
androidTestImplementation("androidx.compose.ui:ui-test-junit4:$compose_version")
// Needed for createComposeRule(), but not for createAndroidComposeRule<YourActivity>():
debugImplementation("androidx.compose.ui:ui-test-manifest:$compose_version")
```

### Robolectric Dependencies

Start by adding the following to your module's `build.gradle`/`build.gradle.kts` file:

```kotlin
android {
  testOptions {
    unitTests {
      isIncludeAndroidResources = true
    }
  }
}

dependencies {
  testImplementation("junit:junit:4.13.2")
  testImplementation("org.robolectric:robolectric:4.18")
}
```

## Reference Tables

### Versions

#### Compose UI

| Latest Update | Stable Release | Release Candidate | Beta Release | Alpha Release |
| --- | --- | --- | --- | --- |
| November 04, 2026 | 1.12.1 | 1.13.0-rc01 | - | - |

#### Robolectric

| Robolectric version | Android API levels |
| --- | --- |
| 4.18 | 24 → 37 |

### Android

This table shows the minimum Java version required to run Robolectric tests against a specific version of Android.

| Android version | API level | Java version |
| --- | --- | --- |
| Android 17 | 37 | 21 |
| Android 16 | 36 | 21 |
| Android 15 | 35 | 17 |
| Android 14 | 34 | 17 |
| Android 13 | 33 | 9 |
| Android 12.1 | 32 | 9 |
| Android 12 | 31 | 9 |
| Android 11 | 30 | 9 |
| Android 10 | 29 | 9 |
| Android 9 | 28 | 8 |
| Android 8.1 | 27 | 8 |
| Android 8.0 | 26 | 8 |
| Android 7.1 | 25 | 8 |
| Android 7.0 | 24 | 8 |

## Patterns

### Compose Test Environment

The `ComposeUiTestConfig` class is included in the `junit4` and `ui-test` parts of the `androidx.compose.ui` AndroidX artifact.

Compose test v2 APIs use `ComposeUiTestConfig` to customize the test environment. This configuration object consolidates environmental related APIs like `effectContext`, `runTestContext`, and `testTimeout` into a single object.

```kotlin
val testConfig = ComposeUiTestConfig(
    effectContext = EmptyCoroutineContext,
    runTestContext = EmptyCoroutineContext,
    testTimeout = 30.seconds
)

@get:Rule
val rule = createComposeRule(config = testConfig)

// OR

runComposeUiTest(config = testConfig) {}
```

### Input Mode

Compose test v2 APIs enforce `InputMode.Touch` by default at the start of each test to ensure determinism and prevent input mode state from leaking between tests. Tests can fail during migration if they rely on non-touch input modes configured through instrumentation APIs before the test starts. To resolve this, specify the required input mode in `ComposeUiTestConfig`:

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

### Java 17 and Higher

When running tests on Java 17 or higher, the JVM requires `--add-opens` flags so that Robolectric can access internal OpenJDK classes and APIs (java.lang, java.io, jdk.internal.access, etc.). Add the following `jvmArgs` to your unit test configuration in `build.gradle` / `build.gradle.kts`:

```kotlin
android {
  testOptions {
    unitTests.all {
      it.jvmArgs(
        "--add-opens=java.base/java.lang=ALL-UNNAMED",
        "--add-opens=java.base/java.util=ALL-UNNAMED",
        "--add-opens=java.base/java.io=ALL-UNNAMED",
        "--add-opens=java.base/java.net=ALL-UNNAMED",
        "--add-opens=java.base/java.security=ALL-UNNAMED",
        "--add-opens=java.base/java.text=ALL-UNNAMED",
        "--add-opens=java.base/jdk.internal.access=ALL-UNNAMED",
        "--add-opens=java.desktop/java.awt.font=ALL-UNNAMED",
        "--add-opens=jdk.compiler/com.sun.tools.javac.api=ALL-UNNAMED",
      )
    }
  }
}
```

### Config Annotation

Several aspects of Robolectric's behavior can be configured at runtime, using either `@Config` annotations for class- or method-level configuration, or `robolectric.properties` files for package-level configuration.

To configure Robolectric for a single test class or method, use the `@Config` annotation on the desired class or method. Annotations applied on methods take precedence over the ones at the class level.

Base classes are also searched for annotations. So if you find yourself specifying the same values on a large number of tests, you can create a base class and move your `@Config` annotation to that class.

```kotlin
@Config(
  sdk = Build.VERSION_CODES.TIRAMISU,
  shadows = [ShadowFoo::class, ShadowBar::class]
)
class SandwichTest
```

### Properties File

To configure all Robolectric tests within a package or group of packages, create a file named `robolectric.properties` in the appropriate package. Generally, this file would be placed within the appropriate package directory under `src/test/resources` in your project tree. Robolectric will search for properties files up the hierarchy of packages (including the unnamed default package at the top level), with values in deeper packages overriding values in more shallow packages. When test classes or methods have `@Config` annotations, those override any config from properties files.

```properties
sdk=33
shadows=com.mycompany.ShadowFoo,com.mycompany.ShadowBar
```

If you wish to change the default for any configurable value for all your tests, you can provide a `GlobalConfigProvider` service implementation.

### SDK Level

By default, Robolectric will run your code against the `targetSdk` specified in your module's `build.gradle`/`build.gradle.kts` or `AndroidManifest.xml` file. If you want to test your code under a different SDK, you can specify the desired SDK(s) using the `sdk`, `minSdk` and `maxSdk` config properties:

```kotlin
@Config(sdk = [TIRAMISU, UPSIDE_DOWN_CAKE])
class SandwichTest {
  @Test
  fun getSandwich_shouldReturnHamSandwich() {
    // will run on TIRAMISU and UPSIDE_DOWN_CAKE
  }

  @Test
  @Config(sdk = TIRAMISU)
  fun onTiramisu_getSandwich_shouldReturnChocolateWaferSandwich() {
    // will run on TIRAMISU
  }

  @Test
  @Config(minSdk = UPSIDE_DOWN_CAKE)
  fun fromUpsideDownCakeOn_getSandwich_shouldReturnTunaSandwich() {
    // will run on UPSIDE_DOWN_CAKE, VANILLA_ICE_CREAM, etc.
  }
}
```

Note that `sdk` and `minSdk`/`maxSdk` may not be specified in the same `@Config` annotation or file; however, `minSdk` and `maxSdk` may be specified together. If any of them is present, they override any SDK specification from a less-specific configuration location.

### Application Class

Robolectric will attempt to create an instance of your `Application` class as specified in the AndroidManifest. If you want to provide a custom implementation, you can specify it by setting:

```kotlin
@Config(application = CustomApplication::class)
class SandwichTest {
  @Test
  @Config(application = CustomApplicationOverride::class)
  fun getSandwich_shouldReturnHamSandwich() {
  }
}
```

### Qualifiers

You can explicitly configure the set of resource qualifiers in effect for a test:

```kotlin
class SandwichTest {
  @Test
  @Config(qualifiers = "fr-xlarge")
  fun getSandwichName() {
    assertThat(sandwich.name).isEqualTo("Grande Croque Monégasque")
  }
}
```

### Config Elements

Configuration settings that can be used on a per-class or per-test basis.

| Element | Description |
| --- | --- |
| `sdk` | The Android SDK level to emulate. This value will also be set as `Build.VERSION.SDK_INT`. |
| `minSdk` | The minimum Android SDK level to emulate when running tests on multiple API versions. |
| `maxSdk` | The maximum Android SDK level to emulate when running tests on multiple API versions. |
| `qualifiers` | Qualifiers specifying device configuration for this test, such as "fr-normal-port-hdpi". If the string is prefixed with '+', the qualifiers that follow are overlaid on any more broadly-scoped qualifiers. |
| `application` | The Application class to use in the test, this takes precedence over any application specified in the AndroidManifest.xml. |
| `fontScale` | The default font scale. In U+, users will have a slider to determine font scale. In all previous APIs, font scales are either small (0.85f), normal (1.0f), large (1.15f) or huge (1.3f) |
| `shadows` | A list of shadow classes to enable, in addition to those that are already present. |
| `instrumentedPackages` | A list of instrumented packages, in addition to those that are already instrumented. |

### System Properties

Some additional options can be configured globally by setting these system properties:

| Property | Description | Default |
| --- | --- | --- |
| `robolectric.enabledSdks` | Comma-separated list of SDK levels or names (e.g. 33, 34 or TIRAMISU, UPSIDE_DOWN_CAKE) which are enabled for this process. Only tests targeting a listed SDKs will be run. | All SDKs |
| `robolectric.offline` | Set to true to disable runtime fetching of jars. | `false` |
| `robolectric.dependency.dir` | Specifies a folder containing runtime dependencies. | `null` |
| `robolectric.dependency.repo.id` | Set the ID of the Maven repository to use for the runtime dependencies. | `mavenCentral` |
| `robolectric.dependency.repo.url` | Set the URL of the Maven repository to use for the runtime dependencies. | `https://repo1.maven.org/maven2` |
| `robolectric.logging.enabled` | Set to true to enable debug logging. | `false` |

When using Gradle, you can configure the System Properties for unit tests with the `android.testOptions.unitTests.all` block. For example, to override the Maven repository URL and ID to download the runtime dependencies from a repository other than Maven Central:

```kotlin
android {
  testOptions {
    unitTests.all {
      it.systemProperty("robolectric.dependency.repo.url", "https://local-mirror/repo")
      it.systemProperty("robolectric.dependency.repo.id", "local")
    }
  }
}
```

## Deprecations

- Within the overloads for creating setup functions in tests, several overloads that accept individual configuration parameters -- such as `effectContext`, `runTestContext`, or `testTimeout` -- are deprecated. Update your tests to use `ComposeUiTestConfig` instead.
- Alternatively, you can set `AndroidComposeUiTestFlags.isInputModeSetForDeviceTests = false` to temporarily disable setting the default input mode at the start of each test and retain legacy behavior while migrating your tests. This flag will be removed in the future, so if only a small number of tests fail, it is recommended to resolve the tests directly by changing their configuration instead.

## Troubleshooting

| Issue | Solution |
| --- | --- |
| Tests can fail during migration if they rely on non-touch input modes configured through instrumentation APIs before the test starts. | To resolve this, specify the required input mode in `ComposeUiTestConfig` |
| If you are not sure if resources are being loaded for a particular library | enable debug logging by setting the system property `robolectric.logging.enabled = true` and run your tests. |

## Related References

- **Test anatomy and rules**: See [test-suite-structure.md](test-suite-structure.md)
- **Runtime modes**: See [runtime-modes.md](runtime-modes.md)
- **Screen sizes and locales**: See [device-configuration.md](../advanced/device-configuration.md)
- **CI downloads and JDK**: See [ci-cd.md](../infrastructure-ci-cd/ci-cd.md)

## Sources

- https://developer.android.com/develop/ui/compose/testing
- https://developer.android.com/develop/ui/compose/testing/migrate-v2
- https://developer.android.com/jetpack/androidx/releases/compose-ui
- https://robolectric.org/getting-started/
- https://robolectric.org/configuring/
- https://robolectric.org/compatibility_table/
- https://robolectric.org/javadoc/4.18/org/robolectric/annotation/Config.html
- https://github.com/robolectric/robolectric/releases
