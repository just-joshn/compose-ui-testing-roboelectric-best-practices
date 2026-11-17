# Configuration

## Table of Contents

1. [Version Reference](#version-reference)
2. [Gradle Dependencies](#gradle-dependencies)
3. [JDK Requirements](#jdk-requirements)
4. [Configuring Robolectric](#configuring-robolectric)
5. [SDK, Qualifiers, and Application](#sdk-qualifiers-and-application)
6. [System Properties](#system-properties)
7. [Common Issues & Solutions](#common-issues--solutions)
8. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
9. [Related References](#related-references)
10. [Sources](#sources)

## Version Reference

| Component                         | Version (as of 2026-11-17)                                          |
| --------------------------------- | ------------------------------------------------------------------- |
| Compose BOM                       | `2026.09.00`                                                        |
| `ui-test`, `ui-test-junit4`, `ui-test-manifest` | `1.12.1` stable; `1.13.0-rc01` release candidate      |
| Robolectric                       | `4.18` (API 24 to 37)                                               |
| JUnit                             | `junit:junit:4.13.2` (Robolectric Getting Started)                  |

Some Android pages show older example versions (for example Robolectric `4.13`, and "API 21+" or "API 16+" support claims). Use the robolectric.org compatibility table: 4.18 supports API 24 to 37.

## Gradle Dependencies

Declare the BOM once and add the Compose test libraries without versions.

```kotlin
// app/build.gradle.kts
android {
    testOptions {
        unitTests {
            isIncludeAndroidResources = true
        }
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2026.09.00")
    implementation(composeBom)
    testImplementation(composeBom)
    androidTestImplementation(composeBom)

    // Compose test rules and transitive dependencies
    testImplementation("androidx.compose.ui:ui-test-junit4")
    // Needed for createComposeRule(), not for createAndroidComposeRule<YourActivity>()
    debugImplementation("androidx.compose.ui:ui-test-manifest")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.robolectric:robolectric:4.18")
    // AndroidJUnit4 runner; the docs show this artifact with a version variable only
    testImplementation("androidx.test.ext:junit:$testJunitVersion")
}
```

- `isIncludeAndroidResources = true` appears in the project configuration on both the Robolectric Getting Started page and the Android Robolectric page.
- `androidx.test:core` is listed as an optional "Robolectric environment" test dependency on the Android local tests page. The Robolectric AndroidX Test page imports `ApplicationProvider` and `ActivityScenario` from `androidx.test.core`.
- No allowed page gives a version for `androidx.test.ext:junit` or `androidx.test:core`; pick the current release yourself.
- The Android docs show `ui-test-junit4` under `androidTestImplementation`. Using `testImplementation` for the JVM is what the BOM page shows.

```kotlin
// Good: BOM manages every Compose test artifact together
testImplementation("androidx.compose.ui:ui-test-junit4")

// Bad: pinning one artifact against the BOM unless you need to
testImplementation("androidx.compose.ui:ui-test-junit4:1.13.0-rc01")
```

To override a BOM version for one library, keep the `platform(...)` line and give that library an explicit version. `ComposeUiTestConfig` needs `ui-test` and `ui-test-junit4` 1.13.0 (`1.13.0-alpha01+` per the migration page; `1.13.0-rc01` per the API reference). For 1.12.1, omit it.

## JDK Requirements

| Android API under test | Minimum Java |
| ---------------------- | ------------ |
| 36, 37                 | Java 21      |
| 34, 35                 | Java 17      |
| 29 to 33               | Java 9       |

On Java 17 or higher the JVM needs `--add-opens` flags so Robolectric can reach OpenJDK internals:

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

Two mechanisms: `@Config` on a class or method, and `robolectric.properties` for a package.

```kotlin
@RunWith(AndroidJUnit4::class)
@Config(sdk = [Build.VERSION_CODES.UPSIDE_DOWN_CAKE])
class SignInScreenTest {

    // Method-level @Config wins over the class-level one
    @Test
    @Config(qualifiers = "w360dp-h640dp-xhdpi")
    fun narrowPhone_stacksFields() { /* ... */ }
}
```

```properties
# src/test/resources/com/mycompany/app/robolectric.properties
sdk=33
```

- Method annotations beat class annotations; base classes are searched, so shared values can move to a base class.
- `robolectric.properties` is found by walking up the package hierarchy (including the unnamed top-level package); deeper packages override shallower ones. Place it under `src/test/resources`.
- `@Config` overrides anything from properties files.
- Global defaults for all tests: provide a `GlobalConfigProvider` service implementation.

## SDK, Qualifiers, and Application

| Setting                       | Example                                      | Notes                                                       |
| ----------------------------- | -------------------------------------------- | ----------------------------------------------------------- |
| Fixed SDKs                    | `@Config(sdk = [TIRAMISU, UPSIDE_DOWN_CAKE])` | Test runs once per listed SDK                               |
| Range                         | `@Config(minSdk = UPSIDE_DOWN_CAKE)`         | `sdk` cannot be combined with `minSdk`/`maxSdk`             |
| Default SDK                   | (nothing)                                    | Robolectric uses your module's `targetSdk`                  |
| Resource qualifiers           | `@Config(qualifiers = "fr-xlarge")`          | Dash-separated, in Android's documented qualifier order     |
| Custom `Application`          | `@Config(application = CustomApplication::class)` | Class or method level                                  |

```kotlin
// Good: one very large screen that fits every tested size without clipping or scaling
@Config(qualifiers = "w1000dp-h1000dp-480dpi")
class ResponsiveScreenTest { /* ... */ }
```

The Android screen-size page uses `qualifiers = "w1000dp-h1000dp-480dpi"` as "a very large screen size that can fit all of the test sizes" without clipping or scaling. Qualifier syntax, defaults, and `RuntimeEnvironment.setQualifiers` are covered in [device-configuration.md](../advanced/device-configuration.md).

Other `@Config` elements in the 4.18 Javadoc: `fontScale`, `instrumentedPackages`, `manifest` (deprecated), `shadows`, plus constants `ALL_SDKS`, `NEWEST_SDK`, `OLDEST_SDK`, `TARGET_SDK`. Runtime behavior has its own annotations; see [runtime-modes.md](runtime-modes.md).

## System Properties

Set globally through the `unitTests.all` block:

```kotlin
android {
    testOptions {
        unitTests.all {
            it.systemProperty("robolectric.logging.enabled", "true")
        }
    }
}
```

| Property                                | Purpose                                              | Default                          |
| --------------------------------------- | ---------------------------------------------------- | -------------------------------- |
| `robolectric.enabledSdks`               | Only run tests targeting listed SDKs                 | All SDKs                         |
| `robolectric.offline`                   | `true` disables runtime fetching of jars             | `false`                          |
| `robolectric.dependency.dir`            | Folder containing runtime dependencies               | `null`                           |
| `robolectric.dependency.repo.url` / `.id` | Maven repository for runtime dependencies          | Maven Central                    |
| `robolectric.logging.enabled`           | Debug logging                                        | `false`                          |

CI download and proxy settings are covered in [ci-cd.md](../infrastructure-ci-cd/ci-cd.md).

## Common Issues & Solutions

| Issue                                              | Solution                                                                      |
| -------------------------------------------------- | ----------------------------------------------------------------------------- |
| Robolectric cannot access JDK internals on Java 17+ | Add the `--add-opens` `jvmArgs` above                                      |
| Running tests against API 36 or 37                 | Java 21 is the minimum for those API levels                                   |
| `sdk` and `minSdk` in the same `@Config`           | Not allowed; use one form                                                     |
| Need to see what Robolectric is loading            | `robolectric.logging.enabled=true`                                            |
| Configuration ignored                              | Check precedence: method `@Config`, class `@Config`, then `robolectric.properties` |

## Anti-Patterns to Avoid

| Anti-Pattern                                     | Problem                                      | Solution                                          |
| ------------------------------------------------ | -------------------------------------------- | ------------------------------------------------- |
| Copying `4.13` from the Android Robolectric page | Older than the current release               | Use `4.18` from robolectric.org                   |
| Declaring `@Config(sdk = ...)` on every class    | Repeated, drifts                             | Base class or `robolectric.properties`            |

## Related References

- **Test anatomy and rules**: See [test-suite-structure.md](test-suite-structure.md)
- **Runtime modes**: See [runtime-modes.md](runtime-modes.md)
- **Screen sizes and locales**: See [device-configuration.md](../advanced/device-configuration.md)
- **CI downloads and JDK**: See [ci-cd.md](../infrastructure-ci-cd/ci-cd.md)

## Sources

- https://developer.android.com/develop/ui/compose/testing
- https://developer.android.com/develop/ui/compose/bom
- https://developer.android.com/develop/ui/compose/bom/bom-mapping
- https://developer.android.com/develop/ui/compose/testing/migrate-v2
- https://developer.android.com/training/testing/local-tests
- https://developer.android.com/training/testing/local-tests/robolectric
- https://developer.android.com/training/testing/different-screens/tools
- https://developer.android.com/training/testing/instrumented-tests/androidx-test-libraries/test-setup
- https://developer.android.com/jetpack/androidx/releases/compose-ui
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/ComposeUiTestConfig
- https://robolectric.org/getting-started/
- https://robolectric.org/configuring/
- https://robolectric.org/compatibility_table/
- https://robolectric.org/androidx_test/
- https://robolectric.org/javadoc/4.18/org/robolectric/annotation/Config.html
