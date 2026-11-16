# Set up an Android local Compose test

## Inspect before changing dependencies

Use the project's Android Gradle module, not a Kotlin/JVM-only module or Compose Desktop. Put Robolectric UI tests in `src/test`, use `testImplementation`, and run the local-unit-test task. `src/androidTest` and `connected...AndroidTest` target a device or emulator instead.

Inspect resolved dependencies, the Gradle wrapper, AGP, Kotlin/Compose compiler plugin, test-worker JDK, and selected SDK. A successful dependency resolution is not proof that a hosted Compose test runs.

The [evidence reference](evidence.md) lists the validation fixture's exact combination. It is a reproduction target, not an instruction to upgrade every consuming project.

## Wire the hosted test

Include these pieces in the Android module:

- Android resources for unit tests through `testOptions.unitTests.isIncludeAndroidResources = true`.
- Compose enabled and the Compose compiler plugin appropriate to that project's Kotlin setup.
- Matching Compose dependencies, preferably aligned with the project's BOM.
- `testImplementation` of `androidx.compose.ui:ui-test-junit4`, JUnit 4, and Robolectric.
- `debugImplementation` of `androidx.compose.ui:ui-test-manifest` when using the default host supplied by `createComposeRule()`.
- A Robolectric-aware runner such as `@RunWith(RobolectricTestRunner::class)`.
- An explicit supported SDK for the reproducible local example.

`createComposeRule()` hosts an Android activity. It is not an activity-free rendering API. The published manifest artifact registers `androidx.activity.ComponentActivity`. If you use `createAndroidComposeRule<YourActivity>()`, your real host must already be declared. Do not add the default manifest host as a substitute for declaring a custom activity.

For Compose 1.12.1, the canonical factory import is:

```kotlin
import androidx.compose.ui.test.junit4.v2.createComposeRule
```

The older `androidx.compose.ui.test.junit4.createComposeRule` factory is deprecated in that artifact. Do not infer an old import from a tutorial's unchanged sample.

Copy version-correct imports from the compiled examples. `onNode` is a provider member. `assertExists` and `assertDoesNotExist` are interaction members. Do not import those names as top-level extensions. An unresolved import is a compilation failure, not a missing dependency by default.

AGP 9 has built-in Kotlin support. Do not blindly apply `org.jetbrains.kotlin.android` alongside it. The fixture uses AGP's built-in Kotlin and a matching Compose compiler plugin. Older project setups have different plugin requirements. Follow their plugin documentation before modifying them.

## Establish one passing host test

Run one test that calls `setContent` once, finds a known semantics node, and asserts its visible text. Only then add async behavior or clock control. A failure before `setContent` is not a selector problem.

The [canonical Kotlin files](../examples/) show the runner, rule, SDK, and looper annotations together. The full Gradle fixture is in the source repository, outside the installable skill directory. Manual skill installation does not install an Android SDK or Gradle project.

Robolectric 4.18 documents SDK 24 through 37. API 35 needs Java 17 minimum. API 36 and 37 need Java 21 minimum. Distinguish the JDK running Gradle and test workers from the Kotlin bytecode target. A `jvmTarget` value does not change the worker's JVM.

Robolectric documents `PAUSED` as the default looper mode. The fixture selects it explicitly. Do not add legacy looper mode or drain every scheduler to repair a failure you have not classified.

## Avoid setup that hides defects

- Do not set `unitTests.isReturnDefaultValues = true` to suppress unmocked framework failures.
- Do not mix AndroidX Compose artifacts with Desktop test artifacts.
- Do not copy a release-candidate-only API into a stable dependency set.
- Do not assume the dependency's Maven `<release>` tag means stable. Check AndroidX release notes.
- Do not treat Robolectric's build-tool versions as minimum versions for all consuming projects.
- Do not install global dispatcher replacements as a substitute for understanding Compose scheduling.

## Evidence

[Compose test setup](https://developer.android.com/develop/ui/compose/testing) documents the rule and manifest dependency. [Common patterns](https://developer.android.com/develop/ui/compose/testing/common-patterns) identifies the activity host. [Robolectric getting started](https://robolectric.org/getting-started/) documents resources and the runner. Its [compatibility table](https://robolectric.org/compatibility_table/) states SDK and JDK requirements. The [AGP 9.2 release notes](https://developer.android.com/build/releases/past-releases/agp-9-2-0-release-notes) list Gradle 9.4.1, JDK 17, and KGP 2.2.10 defaults.

These pages do not provide one complete current Compose/Robolectric Gradle snippet. The fixture tests their combination. See [diagnostics.md](diagnostics.md) when the host test fails.
