# Test Compose integration with its Android host

Use this guide when behavior crosses between a Compose screen and its activity, application, lifecycle, intent handlers, or platform adapters. The Android analogue of Electron's host and renderer split is an explicit application boundary. It is not a second JavaScript process that a Compose rule can evaluate.

## Table of contents

- [Choose the host](#choose-the-host)
- [Configure local hosting](#configure-local-hosting)
- [Launch the real activity](#launch-the-real-activity)
- [Test host messages and results](#test-host-messages-and-results)
- [Cover native features](#cover-native-features)
- [Test lifecycle and multiple windows](#test-lifecycle-and-multiple-windows)
- [Verify packaged behavior](#verify-packaged-behavior)
- [Avoid host shortcuts](#avoid-host-shortcuts)
- [Isolate and synchronize](#isolate-and-synchronize)
- [Troubleshoot failures](#troubleshoot-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the host

| Goal | Host choice | Additional layer |
| --- | --- | --- |
| Test a reusable screen | Default `createComposeRule()` host with one test-owned `setContent` | None for that screen contract |
| Verify activity-created content | `createAndroidComposeRule<AppActivity>()` | Installed-app smoke test for packaging |
| Verify launch intent decoding | Controlled launch with the actual host or adapter test | Android resolver for exported intents |
| Handle a document result | Injected activity-result registry or app picker adapter | Device document picker and URI grants |
| Verify application initialization | Local integration test with real application setup and isolated dependencies | Cold installed-app launch |
| Verify another process or service | Local client contract test | Instrumented IPC and service test |
| Verify system windows or multi-window | Local state and app-owned root tests | Android window management test |

A real activity test exercises more initialization than a component test. Keep both when they protect different contracts. Do not make every component test boot the entire app.

## Configure local hosting

Use the Android module's `src/test` source set, `testImplementation` dependencies, Android resources, a Robolectric runner, and a supported SDK. [Setup](../references/setup.md) documents the default host manifest and version constraints.

The fixture uses Compose UI 1.12.1 with the v2 rule factory. Do not copy the 1.13-only environment configuration into that dependency set.

Choose one content owner:

- With the default rule, the test calls `setContent` once.
- With an activity that calls `setContent` in `onCreate`, the activity owns content. The test does not install another composition.
- With a custom empty host, explicitly document that the test owns content and declare that host in the selected manifest.

Install dependency replacements before an automatically launching rule starts the activity. A replacement in the test method is too late if `onCreate` already constructed the production repository.

Use existing dependency-injection test facilities or an application factory with deterministic cleanup. Avoid adding a mutable production singleton solely to let tests replace dependencies after startup.

## Launch the real activity

This illustrative fragment is a complete test class except for the app's real `HomeActivity`. It assumes that activity is declared, sets its own content, and renders **Open settings** and then **Settings**. It is not compiled by this fixture.

Required dependencies are Compose UI testing, Robolectric, and JUnit 4. The activity's module provides AndroidX Activity and its runtime UI dependencies.

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.v2.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class HomeActivityTest {
	@get:Rule val compose = createAndroidComposeRule<HomeActivity>()

	@Test fun opensSettingsFromHostContent() {
		compose.onNodeWithText("Open settings").performClick()
		compose.onNodeWithText("Settings").assertIsDisplayed()
	}
}
```

The expected result is the activity-owned navigation destination. Inspect the actual semantics if **Settings** appears in more than one place. Scope the destination by meaningful identity instead of choosing the first match.

For a custom launch intent, use a launch mechanism that supplies the intent before `onCreate`. Do not mutate `activity.intent` after launch and claim to test initial routing. Test malformed data, missing extras, and valid input as separate cases.

## Test host messages and results

Model communication as requests and results with domain identity. Examples include `OpenDocument`, `ShareReport(reportId)`, and a selected-document result. Keep Android intent parsing in an adapter rather than making a composable parse arbitrary extras.

For app-to-host communication:

1. Mount the real screen with a fresh host adapter fake.
2. Trigger **Share report** for a specific report.
3. Assert the expected visible pending or confirmation state if the product has one.
4. Inspect the fake request for report identity and format.
5. In an adapter test, verify the Android intent action, MIME type, URI, and flags.

For host-to-app communication:

1. Register the result callback before launch.
2. Trigger the request through the UI.
3. Deliver a selected URI or cancellation through the controlled registry or adapter.
4. Assert the selected filename, preview, or unchanged state after cancellation.

See [file operations](file-operations.md) for an activity-result registry example. A synchronous fake result tests callback wiring. A delayed result test is also useful for duplicate launches and lifecycle changes.

Binder IPC, a remote service, and a local callback are different contracts. A fake service proves client reactions to returned values. A real cross-process test must also verify binding, disconnection, parceling, permissions, and recovery from a dead service.

## Cover native features

| Feature | Local assertion | Integration assertion |
| --- | --- | --- |
| Open or save dialog | Request metadata, cancellation, result-driven UI | Real provider selection and persisted access |
| App menu | Tap semantic menu item and assert destination | System overflow placement only if relevant |
| Notification | Notification adapter request and resulting app state | Permission, channel, posting, and action delivery |
| Clipboard | Copy request content and visible feedback | Platform clipboard policy and paste behavior |
| Share sheet | Share intent metadata and URI grant configuration | Real receiving app can read the shared content |
| App version | Build metadata formatting | Installed artifact reports the intended version |

Do not replace Android `Context` with a generic mock to intercept all native operations. Use a narrow adapter for a component test and real Android objects in an adapter integration test.

For clipboard, clear test content after the integration workflow and avoid secrets. Verifying a fake clipboard string does not prove keyboard paste or Android's clipboard privacy UI.

For notification delivery, use [system entry points](system-surfaces.md). For WebView content, use [view interop](../android-apis/view-interop.md) and a real WebView integration environment.

## Test lifecycle and multiple windows

For activity recreation, exercise recreation through the activity scenario and verify the intended state category. A selected tab may use saved state. A loaded document may require durable repository state and a still-valid URI grant.

Do not call `setContent` a second time to simulate recreation. Removing and remounting a composable proves composition behavior, not activity saved-state restoration.

For app-owned dialogs and popups, query the root associated with the intended content. Avoid assuming there is exactly one root after opening a dialog. [Multiple roots](../advanced/multiple-roots.md) describes scoping.

For real multi-window, freeform resize, picture-in-picture, system bars, and IME behavior, run an Android integration workflow. Record window size, API level, orientation, and navigation mode. Local layout constraints can cover adaptive decisions but not window manager behavior.

## Verify packaged behavior

A passing local test uses merged resources and local framework simulation. It does not prove the installed APK has the expected signing, manifest, shrinker rules, resource packaging, app links, or startup configuration.

Use the actual application module and variant. The following commands are illustrative and assume an `app` module with standard debug tasks:

```bash
./gradlew :app:testDebugUnitTest --tests 'com.example.HomeActivityTest'
./gradlew :app:assembleDebug
```

Run the resulting artifact through a separate installed-app smoke workflow. Verify a cold launch, initial destination, a native operation, and relaunch. For release-only behavior, use a testable release-like artifact rather than treating debug as equivalent.

Identify the artifact by commit, variant, application ID, version, and checksum. A test against yesterday's APK is not evidence for today's change.

## Avoid host shortcuts

Bad practice is adding `compose.setContent { HomeScreen() }` to a rule that already launches `HomeActivity`. The test bypasses or conflicts with the activity's own content and can stop exercising the host wiring.

Correct it by keeping the activity-owned content test above. Put isolated `HomeScreen` tests under a default rule in a different class.

Do not disable platform security settings to make a host test pass without a documented reason. Test security configuration with the intended packaged variant.

## Isolate and synchronize

Close manually launched scenarios with structured cleanup. Let rule-owned scenarios follow the rule lifecycle. Restore dependency replacements, unregister callbacks, cancel test-owned scopes, and clear per-test storage.

Compose actions synchronize known UI work, not arbitrary application startup tasks. Hold background initialization with a controllable fake, then release it and assert the ready screen. Do not block the main thread waiting for a host callback.

## Troubleshoot failures

| Symptom | Observe | Correction |
| --- | --- | --- |
| Activity cannot launch | Merged manifest, resources, selected variant | Declare the host and include Android resources |
| Wrong repository used | Construction time relative to rule launch | Install the replacement before launch |
| Duplicate content error | Both activity and test call `setContent` | Choose one owner |
| Intent route test passes falsely | When the intent is installed | Supply the launch intent before creation |
| Dialog finder is ambiguous | All roots and matching nodes | Scope to the intended dialog |
| Local pass but installed crash | Artifact, shrinker, manifest, and startup logs | Reproduce with the tested packaged variant |

## Review checklist

- [ ] The rule matches the intended host and content owner.
- [ ] Dependency replacements precede application startup.
- [ ] Requests and results carry stable domain identity.
- [ ] Cancellation and lifecycle cases have visible outcomes.
- [ ] Local callbacks are not labeled as IPC or system delivery proof.
- [ ] Packaged behavior has a separate installed-artifact workflow.

## Related guides and sources

- [Dependency injection](../frameworks/dependency-injection.md) covers replacement timing.
- [Navigation](../frameworks/navigation.md) covers destination behavior.
- [Compose common patterns](https://developer.android.com/develop/ui/compose/testing/common-patterns) describes activity rules.
- [Activity results](https://developer.android.com/training/basics/intents/result) describes result registration and test registries.
- [Activity testing](https://developer.android.com/guide/components/activities/testing) describes activity scenarios.
- [Robolectric AndroidX integration](https://robolectric.org/androidx_test/) describes local AndroidX Test support.
