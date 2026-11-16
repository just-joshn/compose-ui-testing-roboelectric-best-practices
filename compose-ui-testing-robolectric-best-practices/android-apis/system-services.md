# Test Android system-service behavior

## Table of contents

- [Choose the test boundary](#choose-the-test-boundary)
- [Set up a local service test](#set-up-a-local-service-test)
- [Exercise location and permission outcomes](#exercise-location-and-permission-outcomes)
- [Verify clipboard behavior](#verify-clipboard-behavior)
- [Verify notifications and their actions](#verify-notifications-and-their-actions)
- [Exercise camera and microphone states](#exercise-camera-and-microphone-states)
- [Synchronize and isolate services](#synchronize-and-isolate-services)
- [Avoid false confidence](#avoid-false-confidence)
- [Troubleshoot failures](#troubleshoot-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the test boundary

Use this guide when a Compose screen depends on location, permissions, the clipboard, notifications, camera, or microphone access. Test application decisions locally. Test the actual permission dialog, hardware, and system presentation on a device.

Browser permission grants do not translate to one Android context setting. Android behavior depends on the manifest, runtime SDK, target SDK, permission result, and service state. Permission granted does not mean a provider is enabled or hardware is available.

| Claim | Local approach | Separate evidence |
| --- | --- | --- |
| Denied location offers manual entry | Inject the denied result into the screen's permission boundary | Device permission dialog and Settings round trip |
| Coordinates select a delivery area | Fake a location source with explicit coordinates | Real provider updates and accuracy |
| Copy action writes the expected value | Inspect the Android clipboard after the UI action | System clipboard overlay and privacy behavior |
| Reminder action builds the expected notification | Test the notification adapter or a supported Robolectric shadow | Notification shade, channel settings, and delivery |
| Notification action opens a conversation | Test the intent's destination and rendered route | Tap the actual notification on a device |
| Camera failure offers audio-only mode | Fake the capture boundary | CameraX, microphone, and hardware integration |

Prefer constructor parameters or callbacks for application boundaries. Use the real Android service when the adapter itself is the subject. Do not mock `Context` to make framework setup pass.

## Set up a local service test

Put tests in the Android module's `src/test`. Use `testImplementation`, Android resource inclusion, and a Robolectric runner. A hosted Compose test also needs a declared activity. Follow [setup](../references/setup.md) before testing a service.

The examples below assume the Compose 1.12.1 v2 rule. They are illustrative additions, not compiled fixture tests. The fixture's [canonical tests](../examples/FixtureUiTest.kt) establish the rule, runner, SDK 35, and PAUSED looper pattern.

Use an explicit SDK when a behavior changes across Android versions. For notifications, include cases below and above the runtime notification-permission boundary if the application supports both. Check Robolectric's supported SDKs and the test-worker JDK before adding that matrix.

## Exercise location and permission outcomes

Model the app-facing result independently from the platform dialog. A useful matrix distinguishes these states:

| Result | Expected UI decision |
| --- | --- |
| Granted with usable coordinates | Show the selected area or nearby results |
| Denied | Explain the limitation and offer manual location |
| Permanently denied under the app's policy | Offer a Settings action, without repeatedly requesting |
| Granted but provider disabled | Offer provider enablement or manual entry |
| Granted but no fix yet | Show a pending state with cancellation if supported |
| Approximate coordinates | Accept reduced accuracy or explain why precision is needed |
| Provider failure | Show recoverable error and retry |

For a UI test, feed outcomes through the same app-owned boundary that production uses. Do not set a final label directly and call that a permission-flow test.

Illustrative test fragment, inside a Robolectric class with `val rule = createComposeRule()`. It requires a project-defined `LocationPermissionFake` and `StoreFinder`. The fake exposes a result callback and records requests. `StoreFinder` owns its permission-to-UI transition.

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick

val permission = LocationPermissionFake()
rule.setContent { StoreFinder(permission = permission) }
rule.onNodeWithText("Find nearby").performClick()
rule.runOnIdle { permission.answerDenied() }
rule.onNodeWithText("Location access denied").assertIsDisplayed()
rule.onNodeWithText("Enter postal code").assertIsDisplayed()
```

The visible fallback is the main assertion. A request-count assertion may supplement it. Add a granted case with fixed latitude, longitude, and accuracy, then assert the resulting store or area rather than the fake's coordinates alone.

For changing locations, emit one coordinate, assert its visible area, emit another coordinate, and assert the new area. Keep the previous result until the next update if that is the product contract. Test stale updates after leaving the screen when cancellation matters.

For platform permission-adapter tests, grant or deny permissions using the supported Robolectric application shadow for the resolved version. That changes the simulated permission check. It does not display or test Android's system dialog. Test an Activity Result contract's result mapping separately from the screen's explanation text.

## Verify clipboard behavior

Use the Android clipboard to test the application's adapter. Do not substitute desktop keyboard shortcuts for Android paste behavior.

Illustrative test-method fragment. It needs the standard hosted Compose test setup, `androidx.test:core` on the test classpath, and the project-defined `SharePanel` that copies its link and shows confirmation. It runs entirely on the local test SDK.

```kotlin
import android.content.ClipboardManager
import android.content.Context
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals

val context = ApplicationProvider.getApplicationContext<Context>()
val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE)
	as ClipboardManager
rule.setContent { SharePanel(link = "https://example.test/share/42") }
rule.onNodeWithText("Copy link").performClick()
rule.onNodeWithText("Link copied").assertIsDisplayed()
rule.runOnIdle {
	val copied = clipboard.primaryClip?.getItemAt(0)?.coerceToText(context)
	assertEquals("https://example.test/share/42", copied?.toString())
}
```

The clipboard inspection proves the side effect. The confirmation proves the action's visible result. Neither proves the Android clipboard overlay or cross-app access restrictions.

For paste, seed a `ClipData.newPlainText` value through the adapter or service. Trigger the application's explicit paste action and assert the editable text. Cover an empty clipboard, non-text content, and a rejected URI if the application supports those cases. A test that calls `performTextInput` proves text entry, not paste integration.

Clear test-owned clipboard content in cleanup when multiple cases reuse a host. Never read the developer machine's clipboard.

## Verify notifications and their actions

Split notification testing into three claims.

1. A user action enables a reminder or subscription and shows a result.
2. The notification adapter builds the expected channel, identifier, content, and destination intent.
3. Android displays the notification and dispatches its action correctly.

Test the first with a controlled app boundary. Test the second with an Android adapter test and supported `ShadowNotificationManager` inspection. Test the third on a device.

On API levels that require notification channels, create the channel as production does. On API levels that require runtime permission, test granted and denied paths. Do not patch permission checks to true in every test and conclude that notification settings work.

For notification clicks, verify a stable conversation identifier rather than an exact serialized intent string. Launch the app's target through its normal route-entry boundary in a local host test and assert the conversation title. Keep real `PendingIntent` flags, task-stack behavior, and tapping a shade action in device coverage.

For push subscriptions, use a fake registration result to test the UI's enabled, rejected, and expired states. Fake push delivery does not establish transport registration, token rotation, server fan-out, or background delivery.

## Exercise camera and microphone states

Use a fake capture controller for UI tests. Expose app-facing states such as unavailable, starting, preview ready, recording, and failed. Do not create a fake image and describe it as a working camera preview.

Cover these independent decisions:

- Permission denied offers the designed fallback.
- Permission granted but camera unavailable shows a recoverable error.
- Front and rear camera selection changes the selected label.
- Starting capture disables duplicate start actions if required.
- Stopping capture returns the screen to its ready state.
- Leaving the screen releases the app-owned capture session.
- Microphone denial allows audio-free behavior only if the app supports it.

Assert the selected device or visible capture status after a UI action. Supplement with adapter ownership assertions for `start` and `close` when resource lifecycle is the contract.

Device tests must cover actual preview rendering, audio input, rotation, interruptions, and privacy indicators. Robolectric UI success is not evidence for those behaviors.

## Synchronize and isolate services

Register listeners before triggering the action that can emit an update. Unregister them when their owner leaves the composition or activity. Create fresh location sources and capture controllers for every test.

Deliver fake callbacks on the thread expected by the production contract. Use `rule.runOnIdle` for a controlled main-thread state update, then make semantics assertions outside that block. Do not invoke synchronized Compose assertions inside a platform callback.

Compose's clock does not produce GPS fixes, notification deliveries, or camera frames. Release a held fake explicitly. For an external adapter callback, use a bounded observable wait or a correct idling resource. See [synchronization](../references/synchronization.md).

Restore service state, permission overrides, settings, and listeners after each test. Keep any global shadow mutation in one test's ownership. Do not share mutable fakes between parallel workers.

## Avoid false confidence

| Anti-pattern | Failure mechanism | Correction |
| --- | --- | --- |
| Assert only `permission == granted` | The screen may ignore denial or never request access | Drive the action and assert both outcomes |
| Mock every `Context` service lookup | Framework code receives incomplete Android objects | Use Robolectric's application and fake app-owned boundaries |
| Use a real location or camera in CI | Results depend on hardware and environment | Supply explicit app-facing values locally |
| Treat a shadow notification as displayed | A shadow records requests, not the notification shade | Keep a device presentation test |
| Advance `mainClock` for location updates | The location provider is not owned by Compose time | Emit the source result explicitly |

## Troubleshoot failures

| Symptom | Observe first | Fix |
| --- | --- | --- |
| Grant has no effect | Which permission and SDK the adapter checks | Configure that permission before adapter creation |
| Coordinates never appear | Listener registration, callback thread, and enabled provider state | Register first and deliver through the actual boundary |
| Clipboard contains an old link | Action target and test-owned clipboard setup | Clear state and assert the current link |
| Notification record is empty | Channel, permission branch, and adapter invocation | Repair the missing precondition, not the timeout |
| Camera state hangs at starting | Who completes the fake's start operation | Complete or fail it explicitly |
| Test passes only after another method | Global shadow state, settings, or singleton service | Restore globals and create fresh app-facing fakes |

## Review checklist

- Does each test separate permission from service availability?
- Does a user action lead to a visible result?
- Are callback delivery and listener cleanup controlled?
- Are clipboard and notification side effects inspected only within their actual local claim?
- Does the suite include denial and recovery?
- Are real dialogs, hardware, privacy UI, and delivery assigned to device coverage?

## Related guides and sources

- [View interop](view-interop.md) covers embedded native content.
- [Background work](background-work.md) covers queued delivery and push handling.
- [System surfaces](../testing-patterns/system-surfaces.md) covers system-owned UI boundaries.
- [Android runtime permissions](https://developer.android.com/training/permissions/requesting) describes permission requests and denial.
- [Location permissions](https://developer.android.com/develop/sensors-and-location/location/permissions) describes accuracy and access boundaries.
- [Copy and paste](https://developer.android.com/develop/ui/views/touch-and-input/copy-paste) describes clipboard integration.
- [Notifications](https://developer.android.com/develop/ui/views/notifications) describes channels and permission behavior.
- [Robolectric shadow Javadoc](https://robolectric.org/javadoc/latest/) documents service inspection APIs. Match the version to the resolved dependency.
