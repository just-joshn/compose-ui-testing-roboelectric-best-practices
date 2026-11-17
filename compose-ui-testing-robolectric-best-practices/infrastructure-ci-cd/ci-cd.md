# CI/CD Integration

## Table of Contents

1. [Pipeline Shape](#pipeline-shape)
2. [JDK Selection](#jdk-selection)
3. [Local Tests Task](#local-tests-task)
4. [Android-all Downloads](#android-all-downloads)
5. [Custom Mirror and Proxy](#custom-mirror-and-proxy)
6. [Preloaded Jars and Offline](#preloaded-jars-and-offline)
7. [Restricting SDKs](#restricting-sdks)
8. [Flakiness and Retries](#flakiness-and-retries)
9. [Best Practices](#best-practices)
10. [Common Issues & Solutions](#common-issues--solutions)
11. [Related References](#related-references)
12. [Sources](#sources)

> **Scope**: The official docs give generic CI guidance plus Robolectric download settings. No page covers a CI provider (GitHub Actions, GitLab), sharding, or report merging for Compose/Robolectric, so none is shown here.

## Pipeline Shape

A typical CI workflow:

1. Detect a change (pull request).
2. Provision a server.
3. Fetch the code, plus the Android SDK or emulator images if needed.
4. Build: `./gradlew build`.
5. Run local tests: `./gradlew test`.
6. Start emulators and run instrumented tests.
7. Upload artifacts (test results, APKs).

Robolectric UI tests in `src/test` run in step 5 with no emulator. Run Unit and Component tests on every commit, Feature tests pre-merge, Application tests post-merge, and release candidates nightly. See [test-architecture.md](../architecture/test-architecture.md).

## JDK Selection

Pick the JDK from the highest Android API level the tests target.

| Android API under test | Minimum Java |
| ---------------------- | ------------ |
| 36-37 (Android 16, 17) | 21           |
| 34-35 (Android 14, 15) | 17           |
| 29-33 (Android 10-13)  | 9            |
| 24-28 (Android 7.0-9)  | 8            |

Robolectric 4.18 supports API 24-37. On Java 17 or higher, add `--add-opens` flags to the unit-test JVM:

```kotlin
// build.gradle.kts
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

Match the CI JDK to the one in [configuration.md](../core/configuration.md).

## Local Tests Task

```bash
./gradlew test
```

Local tests (`src/test`, including Robolectric UI tests) run on the JVM. Instrumented tests need an emulator or device and are a separate step.

Keep Robolectric dependencies and `isIncludeAndroidResources = true` in the module, as covered in [configuration.md](../core/configuration.md).

## Android-all Downloads

Robolectric downloads the android-all jar for each SDK it runs. It uses its own `MavenArtifactFetcher` and "does not use any proxies defined by the Gradle build system." Restricted CI networks (Artifactory, corporate proxies) cause failures here.

| Property                                | Purpose                                              | Default                          |
| --------------------------------------- | ---------------------------------------------------- | -------------------------------- |
| `robolectric.dependency.repo.url`       | Maven repository for runtime dependencies            | `https://repo1.maven.org/maven2` |
| `robolectric.dependency.repo.id`        | Repository ID                                        | `mavenCentral`                   |
| `robolectric.dependency.repo.username`  | Repository username                                  | `null`                           |
| `robolectric.dependency.repo.password`  | Repository password                                  | `null`                           |
| `robolectric.dependency.proxy.host`     | Proxy host (since 4.9.1)                             | `null`                           |
| `robolectric.dependency.proxy.port`     | Proxy port (since 4.9.1)                             | `0`                              |
| `robolectric.dependency.dir`            | Folder with preloaded jars                           | `null`                           |
| `robolectric.offline`                   | Disable runtime fetching of jars                     | `false`                          |

## Custom Mirror and Proxy

```kotlin
// build.gradle.kts
android {
  testOptions {
    unitTests {
      isIncludeAndroidResources = true
      all {
        it.systemProperty("robolectric.dependency.repo.url", "https://local-mirror/repo")
        it.systemProperty("robolectric.dependency.repo.id", "local")
        // Username and password only needed when the repository requires an account
        it.systemProperty("robolectric.dependency.repo.username", "username")
        it.systemProperty("robolectric.dependency.repo.password", "password")
        // Since Robolectric 4.9.1
        it.systemProperty("robolectric.dependency.proxy.host", System.getenv("ROBOLECTRIC_PROXY_HOST"))
        it.systemProperty("robolectric.dependency.proxy.port", System.getenv("ROBOLECTRIC_PROXY_PORT"))
      }
    }
  }
}
```

`repo.url` and `repo.id` are enough for most scenarios.

## Preloaded Jars and Offline

Load android-all jars from a local directory instead of downloading:

```kotlin
// build.gradle.kts
android {
  testOptions {
    unitTests {
      all {
        it.systemProperty(
          "robolectric.dependency.dir",
          "${rootDir}/robolectric-jars/preinstrumented"
        )
      }
    }
  }
}
```

- When `robolectric.dependency.dir` is set, Robolectric always reads from it and never downloads, regardless of `robolectric.offline`.
- A missing jar fails the test with `Path is not a file: ...`.
- Set it only in environments that have the jars (for example CI machines with a pre-populated cache).
- `robolectric.offline=true` only matters when `robolectric.dependency.dir` is not set: Robolectric then looks for jars in the test's working directory.

Alternative: fetch the jars with a script before any Gradle task, so no Gradle properties change. Populate the directory with the jars for your Robolectric version before tests run.

## Restricting SDKs

`robolectric.enabledSdks` takes a comma-separated list of SDK levels or names (for example `33, 34` or `TIRAMISU, UPSIDE_DOWN_CAKE`); only tests targeting a listed SDK run. Default: all SDKs.

```kotlin
android { testOptions { unitTests.all { it.systemProperty("robolectric.enabledSdks", "34") } } }
```

## Flakiness and Retries

Fix flaky tests first. A retry mechanism (JUnit rule, CI step) is acceptable on big tests: "Add retrying mechanisms to big tests, but always fix flaky tests." Use `waitUntil` to wait for conditions. See [flaky-tests.md](../debugging/flaky-tests.md) and [synchronization.md](../core/synchronization.md).

## Best Practices

| Practice                                         | Benefit                                         |
| ------------------------------------------------ | ----------------------------------------------- |
| Run `./gradlew test` on every commit             | Fast feedback without an emulator               |
| Match CI JDK to the highest API under test       | Meets the minimum Java per Android API level       |
| Set `robolectric.dependency.repo.*` behind a mirror | Reliable android-all resolution              |
| Preload jars into `robolectric.dependency.dir`   | No network dependency on CI                     |
| Upload test results as artifacts                 | Debug failures after the run                    |
| Keep instrumented tests in a separate step       | Local lane stays emulator-free                  |
| Limit threads in tests                           | Avoid cross-test pollution                      |

## Common Issues & Solutions

| Problem                                              | Cause                                                       | Fix                                                               |
| ---------------------------------------------------- | ----------------------------------------------------------- | ----------------------------------------------------------------- |
| android-all not downloaded on CI                     | Network restrictions; Gradle proxy settings are not used    | Set repo URL/ID or proxy properties above                         |
| Flaky SHA mismatch retrieving Maven artifacts        | Reported after upgrading to 4.10.x on CI                    | Mirror or preload the jars                                        |
| `Path is not a file: ...`                            | `robolectric.dependency.dir` set but jar missing            | Populate the directory, or unset the property                     |
| Failure on JDK 17+ about internal access             | Missing `--add-opens` flags                                 | Add the `jvmArgs` block                                           |
| SDK 36/37 tests fail on JDK 17                       | API 36-37 need Java 21                                      | Use JDK 21                                                        |
| Tests differ between Mac and Linux (screenshots)     | Platform rendering differences                              | Record screenshots on CI, or tolerate small changes; see [visual-regression.md](../testing-patterns/visual-regression.md) |
| `SimpleDateFormat`/`DateTimeFormatter` output differs | Android libcore vs OpenJDK                                  | Use `X` marker (min SDK 24+) or `java.time` with desugaring       |

## Related References

- **Gradle and JDK setup**: See [configuration.md](../core/configuration.md)
- **Choosing test types and lanes**: See [test-architecture.md](../architecture/test-architecture.md)
- **Flaky tests**: See [flaky-tests.md](../debugging/flaky-tests.md)
- **Waiting without sleeps**: See [synchronization.md](../core/synchronization.md)
- **Screenshot tests on CI**: See [visual-regression.md](../testing-patterns/visual-regression.md)

## Sources

- https://developer.android.com/training/testing/continuous-integration
- https://developer.android.com/training/testing/fundamentals/strategies
- https://developer.android.com/training/testing/instrumented-tests/stability
- https://developer.android.com/training/testing/ui-tests/screenshot
- https://robolectric.org/getting-started/
- https://robolectric.org/compatibility_table/
- https://robolectric.org/configuring/
- https://robolectric.org/best-practices/
- https://robolectric.org/blog/2023/11/11/improving-android-all-downloading/
