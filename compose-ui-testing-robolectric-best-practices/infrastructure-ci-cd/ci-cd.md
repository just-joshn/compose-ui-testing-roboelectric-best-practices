# CI/CD Integration

## Table of Contents

1. [Java Version](#java-version)
2. [Local Tests Task](#local-tests-task)
3. [Android-all Downloads](#android-all-downloads)
4. [Custom Mirror and Proxy](#custom-mirror-and-proxy)
5. [Preloaded Jars and Offline](#preloaded-jars-and-offline)
6. [Differences from a Device](#differences-from-a-device)
7. [Related References](#related-references)
8. [Sources](#sources)

## Java Version

This table shows the minimum Java version required to run Robolectric tests against a specific version of Android.

| Android version     | API level | Java version |
| ------------------- | --------- | ------------ |
| Android 16, 17      | 36, 37    | 21           |
| Android 14, 15      | 34, 35    | 17           |
| Android 10 to 13    | 29 to 33  | 9            |
| Android 7.0 to 9    | 24 to 28  | 8            |

Robolectric 4.18 supports Android API levels 24 to 37.

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

## Local Tests Task

The 2021 sharedTest post on robolectric.org ends by saying to test with ./gradlew test for local tests on Robolectric and ./gradlew connectedCheck for instrumentation tests on Emulator.

Any UI test present in the `test` source set runs with Robolectric.

## Android-all Downloads

The Robolectric blog post on android-all downloading on CI says that in recent years, the team has received multiple issues regarding Robolectric's inability to download/resolve the necessary android-all jars when running Robolectric tests in a CI environment.

The post says Robolectric downloads the necessary android-all jars using its MavenArtifactFetcher when running Robolectric tests. It says it does not use any proxies defined by the Gradle build system. In a CI environment, especially in environments used by large companies internally, there are often network restrictions that can cause the aforementioned issues.

Some examples of the issues include "Flaky SHA mismatch on CI builds when retrieving Maven artifacts since upgrading to 4.10.x".

Some additional options can be configured globally by setting these system properties:

| Property                               | Description                                                                                                                                                      | Default                          |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------- |
| `robolectric.enabledSdks`              | Comma-separated list of SDK levels or names (e.g. 33, 34 or TIRAMISU, UPSIDE_DOWN_CAKE) which are enabled for this process. Only tests targeting a listed SDKs will be run. | All SDKs                         |
| `robolectric.offline`                  | Set to true to disable runtime fetching of jars.                                                                                                                 | false                            |
| `robolectric.dependency.dir`           | Specifies a folder containing runtime dependencies.                                                                                                              | null                             |
| `robolectric.dependency.repo.id`       | Set the ID of the Maven repository to use for the runtime dependencies.                                                                                          | mavenCentral                     |
| `robolectric.dependency.repo.url`      | Set the URL of the Maven repository to use for the runtime dependencies.                                                                                         | `https://repo1.maven.org/maven2` |
| `robolectric.dependency.repo.username` | Username of the repository that you defined in robolectric.dependency.repo.url.                                                                                  | null                             |
| `robolectric.dependency.repo.password` | Password of the repository that you defined in robolectric.dependency.repo.url.                                                                                  | null                             |

Since Robolectric 4.9.1, you can now add these parameters:

| Property                            | Description                                              | Default |
| ----------------------------------- | -------------------------------------------------------- | ------- |
| `robolectric.dependency.proxy.host` | Set the host of the proxy to use for the runtime dependencies. | null    |
| `robolectric.dependency.proxy.port` | Set the port number of the proxy to use for the runtime dependencies. | 0       |

## Custom Mirror and Proxy

When using Gradle, you can configure the System Properties for unit tests with the android.testOptions.unitTests.all block. For example, to override the Maven repository URL and ID to download the runtime dependencies from a repository other than Maven Central:

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

The post says robolectric.dependency.repo.url and robolectric.dependency.repo.id are enough for most scenarios.

## Preloaded Jars and Offline

The post says Robolectric can load android-all jars from a local directory instead of downloading them from the network when running Robolectric tests, and sets the robolectric.dependency.dir system property to that directory like the following snippet:

```kotlin
testOptions {
    unitTests {
        includeAndroidResources = true
        returnDefaultValues = true
        isIncludeUnitTestDependencies = true
        all {
            it.systemProperty(
                "robolectric.dependency.dir",
                "${rootDir}/robolectric-jars/preinstrumented"
            )
        }
    }
}
```

- Per the post, when robolectric.dependency.dir is set, Robolectric always looks for android-all jars in that directory and never downloads them, regardless of the value of robolectric.offline.
- Per the post, if a jar is missing from the directory, the tests fail with a `Path is not a file: ...` error.
- Per the post, if only some environments have these jars, such as CI machines with a pre-populated cache, only set robolectric.dependency.dir in those environments.
- Per the post, robolectric.offline is only useful when robolectric.dependency.dir is not set: setting it to true makes Robolectric look for android-all jars in the test's working directory instead.

The post says that to make it work, android-all jars need to be downloaded into the ${rootDir}/robolectric-jars/preinstrumented directory before running any Robolectric tests.

The post says that because Robolectric might add a new android-all jar for a new Android version or modify internal logic to update an existing android-all jar's version, these android-all jars might change across different Robolectric versions.

The post says that if you don't store android-all jars in your Git repository for robolectric.dependency.dir, and you don't want to modify your system properties for Robolectric in your build.gradle.kts, you can try to download android-all jars in a script and download them manually before running any Gradle tasks.

## Differences from a Device

Android libcore and OpenJDK have different implementations. Because of that, you may notice different behaviours when running your app on a device or emulator, and running your tests on the JVM with Robolectric.

When using SimpleDateFormat#parse() to parse a timezone using the Z marker, Android supports time zones with a colon (i.e. 08:00), while OpenJDK doesn't (i.e. 0800). To work around this:

- If your min SDK version is 24 or higher, you can use the X marker instead.
- Use the java.time API, with library desugaring enabled.
- Run the corresponding tests using regular Android tests.

When using DateTimeFormatter.ofPattern(String) to create a formatter displaying a short month name (using the MMM pattern), Android will use three-characters names (i.e. Jan), while OpenJDK will use three-characters names followed by a period (i.e. Jan.). In this case, we recommend running the corresponding tests as regular Android tests.

## Related References

- **Gradle and Robolectric setup**: See [configuration.md](../core/configuration.md)
- **Choosing test types**: See [test-architecture.md](../architecture/test-architecture.md)

## Sources

- https://developer.android.com/training/testing/local-tests/robolectric
- https://robolectric.org/getting-started
- https://robolectric.org/compatibility_table
- https://robolectric.org/configuring
- https://robolectric.org/best-practices
- https://robolectric.org/blog/2021/10/06/sharedTest
- https://robolectric.org/blog/2023/11/11/improving-android-all-downloading
