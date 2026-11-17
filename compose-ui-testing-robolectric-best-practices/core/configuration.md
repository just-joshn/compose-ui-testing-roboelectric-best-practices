# Configuration

## Table of Contents

1. [Version Reference](#version-reference)
2. [Gradle Dependencies](#gradle-dependencies)
3. [Compose Test Environment](#compose-test-environment)
4. [JDK Requirements](#jdk-requirements)
5. [Configuring Robolectric](#configuring-robolectric)
6. [SDK, Qualifiers, and Application](#sdk-qualifiers-and-application)
7. [System Properties](#system-properties)
8. [Common Issues & Solutions](#common-issues--solutions)
9. [Related References](#related-references)
10. [Sources](#sources)

## Version Reference

| Component | Version | Source |
| --- | --- | --- |
| `androidx.compose.ui:ui-*` | Stable `1.12.1`; release candidate `1.13.0-rc01` | Compose UI release notes (latest update November 04, 2026) |
| Robolectric | `4.18`, the newest release on the Robolectric GitHub releases page (published 2026-11-13) | GitHub releases |
| Robolectric `4.18` Android API levels | 24 to 37 | Robolectric compatibility table |
| JUnit | `junit:junit:4.13.2` | Robolectric Getting Started |

The Android Robolectric page's example uses `org.robolectric:robolectric:4.13`, while Robolectric Getting Started uses `org.robolectric:robolectric:4.18`.

## Gradle Dependencies

The Compose testing page's setup section says to add the following dependencies to the `build.gradle` file of the module containing your UI tests:

```groovy
// Test rules and transitive dependencies:
androidTestImplementation("androidx.compose.ui:ui-test-junit4:$compose_version")
// Needed for createComposeRule(), but not for createAndroidComposeRule<YourActivity>():
debugImplementation("androidx.compose.ui:ui-test-manifest:$compose_version")
```

The Robolectric Getting Started page says to start by adding the following to your module's `build.gradle`/`build.gradle.kts` file:

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

## Compose Test Environment

The `ComposeUiTestConfig` class is included, starting in version 1.13, in the `junit4` and `ui-test` parts of the `androidx.compose.ui` AndroidX artifact (`androidx.compose.ui:ui-test-junit4:1.13.0-alpha01+` and `androidx.compose.ui:ui-test:1.13.0-alpha01+`).

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

## JDK Requirements

The Robolectric compatibility table shows the minimum Java version required to run Robolectric tests against a specific version of Android:

| Android API level | Minimum Java version |
| --- | --- |
| 37, 36 | 21 |
| 35, 34 | 17 |
| 33, 32, 31, 30, 29 | 9 |
| 28, 27, 26, 25, 24 | 8 |

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

## Configuring Robolectric

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

To configure all Robolectric tests within a package or group of packages, create a file named `robolectric.properties` in the appropriate package. Generally, this file would be placed within the appropriate package directory under `src/test/resources` in your project tree. Robolectric will search for properties files up the hierarchy of packages (including the unnamed default package at the top level), with values in deeper packages overriding values in more shallow packages. When test classes or methods have `@Config` annotations, those override any config from properties files.

```properties
# src/test/resources/com/mycompany/app/robolectric.properties
sdk=33
shadows=com.mycompany.ShadowFoo,com.mycompany.ShadowBar
```

If you wish to change the default for any configurable value for all your tests, you can provide a `GlobalConfigProvider` service implementation.

## SDK, Qualifiers, and Application

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

The `@Config` Javadoc for 4.18 describes these elements:

| Element | Javadoc description |
| --- | --- |
| `sdk` | The Android SDK level to emulate. This value will also be set as `Build.VERSION.SDK_INT`. |
| `minSdk` | The minimum Android SDK level to emulate when running tests on multiple API versions. |
| `maxSdk` | The maximum Android SDK level to emulate when running tests on multiple API versions. |
| `qualifiers` | Qualifiers specifying device configuration for this test, such as "fr-normal-port-hdpi". If the string is prefixed with '+', the qualifiers that follow are overlaid on any more broadly-scoped qualifiers. |
| `application` | The Application class to use in the test, this takes precedence over any application specified in the AndroidManifest.xml. |
| `fontScale` | The default font scale. In U+, users will have a slider to determine font scale. In all previous APIs, font scales are either small (0.85f), normal (1.0f), large (1.15f) or huge (1.3f) |
| `shadows` | A list of shadow classes to enable, in addition to those that are already present. |
| `instrumentedPackages` | A list of instrumented packages, in addition to those that are already instrumented. |

## System Properties

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

## Common Issues & Solutions

| Issue | Solution |
| --- | --- |
| Robolectric needs to access internal OpenJDK classes and APIs on Java 17 or higher. | The JVM requires `--add-opens` flags; add the `jvmArgs` to your unit test configuration. |
| Running tests against Android API 36 or 37. | The minimum Java version is 21. |
| `sdk` and `minSdk`/`maxSdk` are specified together. | They may not be specified in the same `@Config` annotation or file. |
| You are not sure if resources are being loaded for a particular library. | Enable debug logging by setting the system property `robolectric.logging.enabled = true` and run your tests. |

## Related References

- **Test anatomy and rules**: See [test-suite-structure.md](test-suite-structure.md)
- **Runtime modes**: See [runtime-modes.md](runtime-modes.md)
- **Screen sizes and locales**: See [device-configuration.md](../advanced/device-configuration.md)
- **CI downloads and JDK**: See [ci-cd.md](../infrastructure-ci-cd/ci-cd.md)

## Sources

- https://developer.android.com/develop/ui/compose/testing
- https://developer.android.com/develop/ui/compose/testing/migrate-v2
- https://developer.android.com/jetpack/androidx/releases/compose-ui
- https://developer.android.com/training/testing/local-tests/robolectric
- https://robolectric.org/getting-started/
- https://robolectric.org/configuring/
- https://robolectric.org/compatibility_table/
- https://robolectric.org/javadoc/4.18/org/robolectric/annotation/Config.html
- https://github.com/robolectric/robolectric/releases
