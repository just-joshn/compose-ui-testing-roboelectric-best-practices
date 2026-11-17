# CI/CD Integration

## Table of Contents

1. [Running Tests Outside the Emulator](#running-tests-outside-the-emulator)
2. [Java Version](#java-version)
3. [Android-all Downloads](#android-all-downloads)
4. [Linux arm64 Runners](#linux-arm64-runners)
5. [Differences from a Device](#differences-from-a-device)
6. [Related References](#related-references)
7. [Sources](#sources)

## Running Tests Outside the Emulator

Robolectric lets you run your tests on your workstation, or on your continuous integration environment, in a regular JVM, without an emulator. Because of this, the dexing, packaging, and installing steps aren't necessary, reducing test cycles from minutes to seconds so you can iterate quickly and refactor your code with confidence.

Any UI test present in the `test` source set runs with Robolectric.

Robolectric works with various build systems. If you are starting a new project, we recommend Gradle as a first choice, since it is the default build system for Android.

## Java Version

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

Robolectric now supports API 24 (N) up to 37 (Cinnamon Bun), matching AndroidX's minimum SDK.

### Java 17 and Higher

When running tests on Java 17 or higher, the JVM requires --add-opens flags so that Robolectric can access internal OpenJDK classes and APIs (java.lang, java.io, jdk.internal.access, etc.). Add the following jvmArgs to your unit test configuration in build.gradle / build.gradle.kts:

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

## Android-all Downloads

A new android-all jar is uploaded to MavenCentral for each Android release.

These pre-instrumented Android-all jars are published on MavenCentral. They are lazily downloaded and during tests runtime using `MavenArtifactFetcher`.

### System Properties

Some additional options can be configured globally by setting these system properties:

| Property | Description | Default |
| --- | --- | --- |
| `robolectric.enabledSdks` | Comma-separated list of SDK levels or names (e.g. 33, 34 or TIRAMISU, UPSIDE_DOWN_CAKE) which are enabled for this process. Only tests targeting a listed SDKs will be run. | All SDKs |
| `robolectric.offline` | Set to true to disable runtime fetching of jars. | false |
| `robolectric.dependency.dir` | Specifies a folder containing runtime dependencies. | null |
| `robolectric.dependency.repo.id` | Set the ID of the Maven repository to use for the runtime dependencies. | mavenCentral |
| `robolectric.dependency.repo.url` | Set the URL of the Maven repository to use for the runtime dependencies. | `https://repo1.maven.org/maven2` |
| `robolectric.dependency.repo.username` | Username of the repository that you defined in robolectric.dependency.repo.url. | null |
| `robolectric.dependency.repo.password` | Password of the repository that you defined in robolectric.dependency.repo.url. | null |

Since Robolectric 4.9.1, you can now add these parameters:

| Property | Description | Default |
| --- | --- | --- |
| `robolectric.dependency.proxy.host` | Set the host of the proxy to use for the runtime dependencies. | null |
| `robolectric.dependency.proxy.port` | Set the port number of the proxy to use for the runtime dependencies. | 0 |

### Custom Mirror and Proxy

When using Gradle, you can configure the System Properties for unit tests with the `android.testOptions.unitTests.all` block. For example, to override the Maven repository URL and ID to download the runtime dependencies from a repository other than Maven Central:

```kotlin
android {
  testOptions {
    unitTests.all {
      it.systemProperty("robolectric.dependency.repo.url", "https://local-mirror/repo")
      it.systemProperty("robolectric.dependency.repo.id", "local")

      // Username and password only needed when the local repository needs account information.
      it.systemProperty("robolectric.dependency.repo.username", "username")
      it.systemProperty("robolectric.dependency.repo.password", "password")

      // Since Robolectric 4.9.1, these are available
      it.systemProperty("robolectric.dependency.proxy.host", project.findProperty("systemProp.https.proxyHost") ?: System.getenv("ROBOLECTRIC_PROXY_HOST"))
      it.systemProperty("robolectric.dependency.proxy.port", project.findProperty("systemProp.https.proxyPort") ?: System.getenv("ROBOLECTRIC_PROXY_PORT"))
    }
  }
}
```

## Linux arm64 Runners

Robolectric's native runtime now includes Linux arm64 (aarch64) native libraries, so tests that use native SQLite (the default) and native graphics (`@GraphicsMode(NATIVE)`) can run on Linux arm64 environments, such as GitHub's `ubuntu-24.04-arm` runners, AWS Graviton machines, and arm64 Docker containers on Apple silicon. No configuration is needed.

As on Apple silicon, the legacy SQLite mode (`SQLiteMode.Mode.LEGACY`) isn't supported on Linux arm64.

## Differences from a Device

Android libcore and OpenJDK have different implementations. Because of that, you may notice different behaviours when running your app on a device or emulator, and running your tests on the JVM with Robolectric.

Below is an incomplete list of differences you may encounter.

### Timezone Handling

When using `SimpleDateFormat#parse()` to parse a timezone using the `Z` marker, Android supports time zones with a colon (i.e. 08:00), while OpenJDK doesn't (i.e. 0800). To work around this:

- If your min SDK version is 24 or higher, you can use the `X` marker instead.
- Use the `java.time` API, with library desugaring enabled.
- Run the corresponding tests using regular Android tests.

### Month Names

When using `DateTimeFormatter.ofPattern(String)` to create a formatter displaying a short month name (using the `MMM` pattern), Android will use three-characters names (i.e. Jan), while OpenJDK will use three-characters names followed by a period (i.e. Jan.). In this case, we recommend running the corresponding tests as regular Android tests.

## Related References

- **Gradle and Robolectric setup**: See [configuration.md](../core/configuration.md)
- **Choosing test types**: See [test-architecture.md](../architecture/test-architecture.md)

## Sources

- https://robolectric.org
- https://robolectric.org/getting-started
- https://robolectric.org/compatibility_table
- https://robolectric.org/upgrade_to_version_4
- https://robolectric.org/architecture
- https://robolectric.org/configuring
- https://robolectric.org/best-practices
- https://github.com/robolectric/robolectric/releases
- https://developer.android.com/training/testing/local-tests/robolectric
