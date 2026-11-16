# Evidence and limits

Sources were consulted on 2026-11-16. Documentation describes contracts. Executable observations establish only the pinned fixture and commands recorded in the repository's evidence report. Neither establishes device fidelity or a general compatibility range.

## Primary sources

| Claim or decision | Primary evidence |
| --- | --- |
| Compose test dependencies and default host | [Compose testing setup](https://developer.android.com/develop/ui/compose/testing), [common patterns](https://developer.android.com/develop/ui/compose/testing/common-patterns) |
| Merged/unmerged trees, selection, actions, assertions | [Testing APIs](https://developer.android.com/develop/ui/compose/testing/apis), [semantics](https://developer.android.com/develop/ui/compose/accessibility/semantics) |
| Compose clock, external work, idling resources | [Synchronization](https://developer.android.com/develop/ui/compose/testing/synchronization), published `MainTestClock` and `IdlingResource` KDoc |
| v1 deprecation and v2 scheduling | [v2 migration](https://developer.android.com/develop/ui/compose/testing/migrate-v2), [Compose UI release notes](https://developer.android.com/jetpack/androidx/releases/compose-ui) |
| Stable version versus release candidate | [Compose release table](https://developer.android.com/jetpack/androidx/releases/compose), [stable BOM 2026.09.00 POM](https://dl.google.com/dl/android/maven2/androidx/compose/compose-bom/2026.09.00/compose-bom-2026.09.00.pom) |
| Runner and Android resources | [Robolectric getting started](https://robolectric.org/getting-started/), [AndroidX Test integration](https://robolectric.org/androidx_test/) |
| Supported SDKs and JDK minimums | [Robolectric compatibility table](https://robolectric.org/compatibility_table/), [4.18 release notes](https://github.com/robolectric/robolectric/releases/tag/robolectric-4.18) |
| Default looper and configuration | [Robolectric configuration](https://robolectric.org/configuring/), [LooperMode KDoc](https://robolectric.org/javadoc/latest/org/robolectric/annotation/LooperMode.html) |
| Isolation and device limits | [Robolectric best practices](https://robolectric.org/best-practices/), [Android local Robolectric tests](https://developer.android.com/training/testing/local-tests/robolectric) |
| Build-tool defaults | [AGP 9.2 release notes](https://developer.android.com/build/releases/past-releases/agp-9-2-0-release-notes) |

Published sources inspected where guides were insufficient:

- [`ui-test:1.12.1` sources](https://dl.google.com/dl/android/maven2/androidx/compose/ui/ui-test/1.12.1/ui-test-1.12.1-sources.jar) define finder defaults, singular-match errors, clock ownership, and idling-resource behavior.
- [`ui-test-junit4:1.12.1` sources](https://dl.google.com/dl/android/maven2/androidx/compose/ui/ui-test-junit4/1.12.1/ui-test-junit4-1.12.1-sources.jar) define v1 deprecation and the v2 factories.
- [`ui-test-manifest:1.12.1` AAR](https://dl.google.com/dl/android/maven2/androidx/compose/ui/ui-test-manifest/1.12.1/ui-test-manifest-1.12.1.aar) registers `androidx.activity.ComponentActivity` in its manifest.

## Resolve conflicting evidence narrowly

The fetched Android Robolectric guide still samples Robolectric 4.13 and says API support starts at 21. Robolectric 4.18 release notes remove SDK 23, and its compatibility table starts at 24. Use the versioned release notes and table for 4.18.

Compose's Maven `<release>` metadata points to 1.13.0-rc01. AndroidX identifies 1.12.1 as stable. The stable BOM pins 1.12.1. Do not select a release candidate solely from the Maven tag.

The 1.12.1 `createComposeRule` KDoc names `android.app.Activity` and a test manifest. The published manifest AAR declares `ComponentActivity`, consistent with the common-patterns guide. Use the actual artifact for the host declaration.

The synchronization guide summarizes Android measure/draw limitations. The 1.12.1 clock KDoc says measure/layout can run synchronously when time advances, while drawing remains Choreographer-driven. Do not infer that clock advancement proves rendering.

Current online examples can include 1.13-only configuration and main-thread synchronization. The stable 1.12.1 fixture does not validate those APIs.

## Executable observations

Executed on macOS arm64 with JDK 17.0.21.0.3, Gradle 9.4.1, AGP 9.2.0, AGP built-in Kotlin and Compose compiler plugin 2.2.10, stable Compose BOM 2026.09.00, UI testing 1.12.1, Material3 1.4.0, Robolectric 4.18, and JUnit 4.13.2. Compile SDK is 37. Runtime SDK is 35 with PAUSED looper. This is one tested combination, not a compatibility range.

Eight fixture tests passed without skips. Three compiled UI mutations failed the intended assertions, then passed after restoration. Excluding Android resources broke default activity resolution. Restoring resources restored the pass. The v1/v2 probe observed different callback ordering. It did not measure performance.

The repository evidence report records commands, named tests, source provenance, and agent-task outcomes. The canonical Kotlin examples are compiled as the Android library fixture's test source set. Do not infer that an unrun code fragment has been validated merely because it resembles those examples.

## Claims not established

- Real-device rendering, screenshot fidelity, GPU behavior, frame timing, or performance.
- TalkBack traversal, real accessibility-service integration, or overall accessibility compliance. Semantics assertions are useful but narrower.
- System UI, edge-to-edge, picture-in-picture, real IME or keyboard behavior, hardware, or unsupported framework features such as WebView.
- Real transport or service integration when the UI test uses a fake.
- Process death, activity recreation, or persistence merely because a composition was disposed and remounted.
- All JDKs, Android APIs, Gradle versions, variants, runners, or Compose rule environments.
- A custom idling resource or arbitrary independent coroutine scheduler. They are documented options, not fixture-validated integrations.

Use a device or emulator when the claim depends on real Android behavior. Keep those checks separate from the fast local behavior tests.
