# Configure Robolectric

## When to use

Use when the goal is to set up Robolectric for a module, choose or fix its configuration, or get the tests running under a JDK or CI environment.

## Delegate

- Delegate to one read-only subagent: read the build files and test configuration, run the baseline, and report the current setup with file and line.
- Keep for yourself: every change to the build and test configuration.
- After verification, delegate the challenge to a fresh reviewer: compare the changed configuration with its reference sections.

## Investigate and design

### Investigate

1. Read the module's build files, the test configuration, and the CI configuration. Record the JDK in use and the Robolectric and Compose versions. Run the tests and record the exact command and result.
2. Check where the tests live. You can convert an instrumented test to Robolectric by moving it to the `test` source set and setting up the Robolectric dependencies: [configuration.md](../references/core/configuration.md#quick-reference).
3. Check the Robolectric dependencies in the module's `build.gradle`/`build.gradle.kts` file, including `isIncludeAndroidResources`: [configuration.md](../references/core/configuration.md#robolectric-dependencies).
4. Check the Compose test dependencies in the module containing your UI tests: [configuration.md](../references/core/configuration.md#compose-ui-test-dependencies).
5. Check the Android API levels the tests run against. By default, Robolectric runs your code against the `targetSdk` specified in the module's build file or `AndroidManifest.xml` file: [configuration.md](../references/core/configuration.md#sdk-level).
6. Check the JDK against the minimum Java version for those API levels. The minimum is 17 for API 34 and 35, and 21 for API 36 and 37: [configuration.md](../references/core/configuration.md#android).
7. Check whether the tests run on Java 17 or higher. When running tests on Java 17 or higher, the JVM requires `--add-opens` flags so that Robolectric can access internal OpenJDK classes and APIs: [ci-cd.md](../references/infrastructure-ci-cd/ci-cd.md#java-17-and-higher).
8. Check where the test runtime gets its jars. Pre-instrumented android-all jars are published on MavenCentral, and they are lazily downloaded during tests runtime using `MavenArtifactFetcher`: [ci-cd.md](../references/infrastructure-ci-cd/ci-cd.md#android-all-downloads).
9. Check the CI machine architecture. Robolectric's native runtime includes Linux arm64 (aarch64) native libraries, so tests that use native SQLite (the default) and native graphics (`@GraphicsMode(NATIVE)`) can run on Linux arm64 environments. No configuration is needed. The legacy SQLite mode (`SQLiteMode.Mode.LEGACY`) isn't supported on Linux arm64: [ci-cd.md](../references/infrastructure-ci-cd/ci-cd.md#linux-arm64-runners).
10. If resources may not be loading for a library, enable debug logging by setting the system property `robolectric.logging.enabled = true`: [debugging.md](../references/debugging/debugging.md#debug-logging).

### Design

- Change only the settings the findings call for, and keep each change traceable to its finding.
- Add the Robolectric dependencies and `isIncludeAndroidResources`: [configuration.md](../references/core/configuration.md#robolectric-dependencies).
- For Java 17 and higher, add the `--add-opens` flags as `jvmArgs` in the unit test configuration: [configuration.md](../references/core/configuration.md#java-17-and-higher).
- To configure one test class or method, use the `@Config` annotation. Annotations on methods take precedence over class-level ones: [configuration.md](../references/core/configuration.md#config-annotation).
- To configure all tests in a package or group of packages, create a `robolectric.properties` file in the appropriate package, generally under `src/test/resources`: [configuration.md](../references/core/configuration.md#properties-file).
- `sdk` and `minSdk`/`maxSdk` may not be specified in the same `@Config` annotation or file; `minSdk` and `maxSdk` may be specified together: [configuration.md](../references/core/configuration.md#sdk-level).
- Some additional options can be configured globally by setting system properties. When using Gradle, you can configure the system properties for unit tests with the `android.testOptions.unitTests.all` block: [configuration.md](../references/core/configuration.md#system-properties).
- To download the runtime dependencies from a repository other than Maven Central, set `robolectric.dependency.repo.url` and `robolectric.dependency.repo.id`: [ci-cd.md](../references/infrastructure-ci-cd/ci-cd.md#custom-mirror-and-proxy).
- To disable runtime fetching of jars, set `robolectric.offline` to true: [ci-cd.md](../references/infrastructure-ci-cd/ci-cd.md#system-properties).
- To use the AndroidX test runner in Robolectric tests, use `@RunWith(AndroidJUnit4::class)`: [test-suite-structure.md](../references/core/test-suite-structure.md#androidx-test).

## Implement and clean

- Change only the build and test configuration the design names.
- Revert any configuration changed only to investigate.

## Verify actual behavior

- Run the test task for the module and compare the result with the baseline. Record the command and output.
- Run the same task in the CI environment and record the result.
- Remove each added setting in turn and confirm that the failure it addressed returns, then restore it.
- Re-read every setting against its reference file or official page, and drop any you cannot tie to one.
- When a result differs between a device and the JVM, note that Android libcore and OpenJDK have different implementations, so you may notice different behaviours: [ci-cd.md](../references/infrastructure-ci-cd/ci-cd.md#differences-from-a-device).

## Deliver artifact and evidence

- Report each finding with the build or CI file and line, the documented statement it relies on, and the official page that states it.
- List separately anything about the project that no official page covers, and mark it not documented.
- Give the baseline command and result.

## Sources

- https://robolectric.org/getting-started/
- https://robolectric.org/configuring/
- https://robolectric.org/compatibility_table/
- https://robolectric.org/androidx_test/
- https://github.com/robolectric/robolectric/releases
- https://developer.android.com/develop/ui/compose/testing
- https://developer.android.com/training/testing/local-tests/robolectric
