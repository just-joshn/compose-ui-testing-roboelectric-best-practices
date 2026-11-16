# Test app features exposed through system UI

Use this guide for notification actions, app widgets, quick settings tiles, shortcuts, and app-owned popup controls. These are Android analogues of browser extension entry points, not browser extensions running inside Robolectric. Test shared behavior locally, then verify registration and interaction through the real Android host.

## Table of contents

- [Choose the boundary](#choose-the-boundary)
- [Set up a local entry-point test](#set-up-a-local-entry-point-test)
- [Test controls and persistence](#test-controls-and-persistence)
- [Test background communication](#test-background-communication)
- [Verify registration and permissions](#verify-registration-and-permissions)
- [Hand off to Android integration tests](#hand-off-to-android-integration-tests)
- [Avoid false evidence](#avoid-false-evidence)
- [Isolate and synchronize](#isolate-and-synchronize)
- [Troubleshoot failures](#troubleshoot-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the boundary

| Feature or claim | Local workflow | Separate evidence |
| --- | --- | --- |
| App popup enables a feature | Compose click and state assertion | Device window positioning if relevant |
| Notification action updates an item | Exercise the action handler with an identified item, then render repository state | Tap the actual notification action on Android |
| Widget displays a summary | Test its state transformation and the equivalent app screen | Launcher-hosted widget rendering and update delivery |
| Tile changes connection state | Test the shared connection controller | Actual tile service lifecycle and quick settings interaction |
| Scheduled refresh updates data | Controlled worker or repository test, then a UI consumer test | OS scheduling and background restrictions |
| Shortcut opens a destination | Verify intent parsing and destination rendering | Installed shortcut resolution and task behavior |
| Permission denied | Controlled permission result and explanatory UI | Real permission dialog and API-specific restrictions |

Compose semantics can inspect app-owned Compose dialogs. They do not inspect the notification shade, launcher, or quick settings UI. A Glance widget is not a Compose UI semantics tree. Use its own testing support for widget-specific rendering rather than mounting Glance code in a Compose rule.

## Set up a local entry-point test

Keep local tests in the Android module's `src/test`. Follow [setup](../references/setup.md) for `testImplementation`, Android resources, a declared activity host, and the Robolectric runner. The canonical examples use Compose UI 1.12.1 and the v2 rule factory.

Define the shared contract before testing the system adapter. An action needs a stable item identity and an operation. It does not need a reference to a composable or a global activity.

For a notification that marks message `message-42` read, test these layers separately:

1. Decode the notification action into a request containing `message-42`.
2. Invoke the real action handler with a fresh fake repository.
3. Verify that the handler updates that message and leaves other messages unchanged.
4. Render the app screen from the updated repository and assert the read state.
5. On Android, tap the notification action and verify the same result.

If step 4 supplies a prebuilt final state, label it a rendering test. It does not prove the action-to-repository path.

## Test controls and persistence

The following illustrative test is complete apart from the project's Android build setup. It demonstrates a popup-like control backed by state outside the popup. It is not compiled by this repository's fixture.

Required dependencies are Compose Material3, Compose UI testing, JUnit 4, Robolectric, and the default host manifest described in setup.

```kotlin
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class FeatureControlsTest {
	@get:Rule val compose = createComposeRule()

	@Test fun reopeningControlsRetainsEnabledState() {
		var open by mutableStateOf(true)
		var enabled by mutableStateOf(false)
		compose.setContent {
			Column {
				Button(onClick = { open = !open }) {
					Text(if (open) "Close controls" else "Open controls")
				}
				if (open) {
					Text(if (enabled) "Feature enabled" else "Feature disabled")
					Button(onClick = { enabled = true }) { Text("Enable") }
				}
			}
		}
		compose.onNodeWithText("Enable").performClick()
		compose.onNodeWithText("Feature enabled").assertIsDisplayed()
		compose.onNodeWithText("Close controls").performClick()
		compose.onNodeWithText("Feature enabled").assertDoesNotExist()
		compose.onNodeWithText("Open controls").performClick()
		compose.onNodeWithText("Feature enabled").assertIsDisplayed()
	}
}
```

The expected result is retained state across removal and reappearance of the controls. This test does not prove disk persistence, activity recreation, or process restoration. For durable settings, create a second repository instance against the same per-test store and check its loaded value. For process restoration, run a separate Android test with an explicit restart protocol.

Test two feature instances when the app supports them. Give each instance an identity and assert that enabling one does not enable the other. Avoid a singleton fake that accidentally makes both instances share state.

## Test background communication

Treat background work as a producer and the screen as a consumer. A test-controlled producer can emit pending, success, and failure states without waiting for an OS alarm.

For a refresh action:

1. Mount the real screen with a repository whose refresh suspends on a fresh deferred result.
2. Click **Refresh** and assert the pending indicator.
3. Complete the deferred with an identified result.
4. Synchronize Compose and assert the new visible summary.
5. In a second test, fail the deferred and assert the recovery action.

Use the [canonical controlled sender](../examples/FixtureUiTest.kt) as the local synchronization pattern. This preserves the source topic's popup-to-background communication workflow without pretending Android has extension service workers.

Test alarm or worker request construction separately from delivery. Assert the intended identity, schedule, and constraints using the scheduler's supported test tools. Advancing `mainClock` does not cause Android to deliver an alarm or run an OS-managed job.

## Verify registration and permissions

Inspect the merged manifest for the actual variant under test. Check component names, exported status, intent filters, and required permissions. Do not infer registration from a unit test that directly constructs the handler.

For intent-based actions, verify action, data, extras, and flags. Two actions that differ only in extras can collide if their pending-intent identities are otherwise equal. Include a regression case for distinct item actions and inspect the adapter's identity policy.

For permission-gated features, cover granted, denied, and permanently unavailable app states. A fake permission result proves the explanation and fallback. It does not prove that Android displays a permission prompt or grants access.

Do not claim that posting a notification proves visibility. Notification permission, channel settings, user settings, foreground restrictions, and OS policy can affect presentation.

## Hand off to Android integration tests

Use an installed app and a device or emulator for the Android-owned entry point. Record the app variant, API level, launcher when relevant, and initial permissions.

A notification workflow needs these observations:

1. Trigger the feature through the installed app.
2. Inspect the notification title and actions in the notification shade.
3. Tap the action associated with the intended item.
4. Return to the app and verify the visible state.
5. Repeat with denied permission and a disabled channel when those cases matter.

For widgets, add and remove the widget through a launcher and verify updates after reopening the app. For tiles, add the tile and exercise inactive, active, and unavailable states. For shortcuts, verify both a cold launch and an existing task.

Use a small API-level matrix selected by behavior changes, not a browser-name matrix. Add OEM or launcher coverage only where the product depends on those hosts.

## Avoid false evidence

Bad practice is to invoke a receiver method directly and label the test "notification action works on Android". Direct invocation bypasses manifest resolution, pending-intent identity, permission checks, and system UI.

Correct the claim to "the action handler marks the identified message read". Keep that local test, then add the installed-app workflow above for delivery.

Do not query app semantics for text expected inside a launcher widget. A failed finder there reflects the wrong test layer, not necessarily a broken widget.

## Isolate and synchronize

Create fresh repositories, permission results, and action identities per test. Restore notification settings, remove test widgets, and cancel test notifications in integration cleanup.

Keep shared-state tests intentional. Reopening controls can reuse one repository within a test. Independent tests must not reuse it. Cancel pending jobs and unregister listeners even when an assertion fails.

Register listeners before triggering a one-shot event. Prefer durable state flows for UI consumption so a completed background result is not lost before collection starts.

## Troubleshoot failures

| Symptom | Observe | Correction |
| --- | --- | --- |
| Handler passes but tap does nothing | Installed manifest and action intent | Fix registration or pending-intent mapping |
| Wrong item updates | Intent data and item identity | Give each action the correct stable identity |
| Screen never updates | Repository emission and active collector | Release the fake or repair lifecycle collection |
| Permission test always succeeds | Real versus fake permission path | Add a separate denied-permission device case |
| Reopen loses setting | State owner and storage reload | Move durable state outside the transient controls |
| Widget text cannot be found | Which host owns the rendering | Use widget-specific or launcher integration tests |

## Review checklist

- [ ] Local tests identify the exact action and item.
- [ ] UI assertions follow actions rather than checking only callback counts.
- [ ] Reopen, disk persistence, and process restoration have distinct claims.
- [ ] Manifest and permission evidence names the tested variant and API.
- [ ] System UI interaction has its own installed-app test.

## Related guides and sources

- [Background work](../android-apis/background-work.md) covers scheduler boundaries.
- [Multiple roots](../advanced/multiple-roots.md) covers app-owned dialogs.
- [System services](../android-apis/system-services.md) covers Android adapters.
- [Android notification guidance](https://developer.android.com/develop/ui/views/notifications) describes system notification behavior.
- [App widgets](https://developer.android.com/develop/ui/views/appwidgets/overview) describes launcher-hosted widgets.
- [Quick settings tiles](https://developer.android.com/develop/ui/views/quicksettings-tiles) describes tile registration and lifecycle.
- [Robolectric limits](../references/evidence.md) separates fixture evidence from platform behavior.
