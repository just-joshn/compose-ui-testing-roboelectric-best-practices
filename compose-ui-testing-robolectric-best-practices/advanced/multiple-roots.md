# Test dialogs, popups, and multiple Compose roots

## Table of contents

- [Choose the correct boundary](#choose-the-correct-boundary)
- [Open and scope a dialog](#open-and-scope-a-dialog)
- [Inspect every root](#inspect-every-root)
- [Test popup menus and dismissal](#test-popup-menus-and-dismissal)
- [Handle external activities and provider windows](#handle-external-activities-and-provider-windows)
- [Coordinate multiple app views](#coordinate-multiple-app-views)
- [Own content and cleanup](#own-content-and-cleanup)
- [Avoid root shortcuts](#avoid-root-shortcuts)
- [Troubleshoot](#troubleshoot)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the correct boundary

Use this guide when one user's interaction opens dialogs, menus, another app-owned view, or an external activity. For independently authenticated users, use [multi-user testing](multi-user.md).

A Compose semantics root is not a browser tab. A dialog can create a separate root within the same app and session. A Custom Tab or another app's activity is outside the Compose tree. Creating another root does not create isolated app storage or identity.

| Scenario | Local test approach | Separate integration claim |
| --- | --- | --- |
| Confirmation dialog | Open through UI, scope by dialog semantics | System window behavior if relevant |
| Dropdown popup | Open through UI, match actual menu content | Real focus and input behavior |
| In-app editor and preview | One host with explicit group identity | Multi-window lifecycle if supported |
| External help link | Record app-owned launcher request and result | Browser destination on device |
| OAuth provider window | Fake launcher and deliver controlled callback | Provider browser and redirect integration |
| Multiple activities | Real declared hosts where supported | Task stack and multi-window on device |

Start with the [Android local host setup](../references/setup.md). Use a single rule-managed content owner unless the actual product requires several hosts.

## Open and scope a dialog

Trigger the dialog through the user action. Assert dialog content, perform its action, and assert the effect on the underlying screen. Opening and closing a dialog without checking the parent result misses broken confirmation wiring.

Complete illustrative test for the fixture's Compose UI 1.12.1 environment. It requires foundation, Material3, Compose UI tests, JUnit, Robolectric, Android resources, and the default host manifest. It is not a canonical fixture test.

```kotlin
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasAnyAncestor
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.isDialog
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.LooperMode

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
@LooperMode(LooperMode.Mode.PAUSED)
class ArchiveDialogTest {
	@get:Rule val rule = createComposeRule()

	@Test fun confirmationArchivesDraft() {
		rule.setContent {
			var open by remember { mutableStateOf(false) }
			var archived by remember { mutableStateOf(false) }
			Column {
				Text(if (archived) "Draft archived" else "Draft active")
				Button(onClick = { open = true }) { Text("Archive") }
			}
			if (open) {
				AlertDialog(
					onDismissRequest = { open = false },
					title = { Text("Archive draft?") },
					confirmButton = {
						Button(onClick = {
							archived = true
							open = false
						}) { Text("Archive") }
					},
				)
			}
		}
		rule.onNodeWithText("Archive").performClick()
		rule.onNodeWithText("Archive draft?").assertIsDisplayed()
		rule.onNode(hasText("Archive") and hasAnyAncestor(isDialog()))
			.performClick()
		rule.onNodeWithText("Draft archived").assertIsDisplayed()
		rule.onNode(isDialog()).assertDoesNotExist()
	}
}
```

The parent and dialog both say **Archive** after opening. A singular text finder is then ambiguous. Scope the second action to the dialog rather than selecting whichever match is first.

Add a cancellation test that leaves **Draft active** visible. If the dialog contains form fields, enter text inside that dialog's group and assert the parent result after submission.

## Inspect every root

When multiple roots exist, `onRoot()` may be ambiguous. Inspect all roots rather than assuming the main activity is the only one.

Illustrative diagnostics fragment for a configured rule:

```kotlin
import androidx.compose.ui.test.isRoot
import androidx.compose.ui.test.printToString

val roots = rule.onAllNodes(isRoot(), useUnmergedTree = true)
val count = roots.fetchSemanticsNodes().size
repeat(count) { index ->
	println(roots[index].printToString())
}
```

Indexing is appropriate here because the operation intentionally prints every root. Do not carry those indices into action selectors. Root ordering is not a user identity contract.

Find the dialog marker, title, tag, text, and available actions in the dump. Check both merged and unmerged trees if a child is missing. `clearAndSetSemantics` replaces descendant information in the merged tree. Child nodes can remain available to unmerged test inspection without being exposed with their original semantics to accessibility services.

Do not make the test pass by querying only the activity root when the action lives in another window. Conversely, do not assume every overlay is a dialog. Some sheets are in the normal composition.

## Test popup menus and dismissal

Open a menu through its anchor. Assert the intended option, choose it, and assert the resulting destination or changed state. Verify the menu is absent afterward when the product closes it on selection.

For repeated labels, scope to a menu identity or a meaningful containing group exposed by the actual tree. A test tag can identify the popup content when visible semantics are insufficient. It must not replace accessible labels.

Test dismissal through supported user actions. For example, use the menu's close action when one exists. If Back or outside-tap behavior is part of the requirement, drive the host or input boundary and verify the result. Calling `onDismissRequest` directly is a callback test, not a dismissal integration test.

Avoid assertions that depend on root count alone. A popup could create one root with the wrong content. Use root count only when root creation itself is relevant, then assert actual content and behavior.

Keep animation handling ordinary unless you need an intermediate frame. Default Compose synchronization is usually sufficient for menu opening and closing. If an external request supplies menu data, release that request separately.

## Handle external activities and provider windows

A browser page, system picker, provider SDK activity, or external app is not searchable with Compose finders. Do not wait for its text in your app's semantics tree.

Introduce or use the existing app-owned launcher boundary. A local test can record the requested destination, hold completion, and deliver success, cancellation, unavailable-handler, or failure results.

For a help link:

1. Click **Help** in the actual screen.
2. Verify the launcher receives the expected allowlisted URI.
3. Simulate an unavailable handler.
4. Assert the app's fallback, such as **Copy help link**.

Do not catch any launch failure and accept either result. Configure success and failure as separate tests so each path must execute.

For account linking, assert **Connecting**, return a controlled provider result, then complete the app's exchange boundary. Assert **Account connected** only after exchange success. Return cancellation in another test and verify the app remains usable.

Do not infer provider security from the callback fake. See [third-party services](third-party.md) for state correlation, PKCE, provider tenants, and device handoffs.

For Android Activity Result integration, test your app's registration and result mapping separately from the screen rendering. Register callbacks before launch. A fake result delivered directly to a ViewModel does not prove Activity Result wiring.

## Coordinate multiple app views

If the product has editor and preview panes in one host, give each meaningful identity. Inject the shared document repository into both, drive the editor action, and assert the preview updates. Keep identity and data sharing explicit.

A single process with a shared `StateFlow` proves local observation. It does not prove synchronization across separate app processes or devices. Test actual transport separately.

If two independent screen owners are needed, construct them with explicit session and repository ownership. Mount them in tagged groups under one test composition where that matches the claim. Avoid introducing multiple activity rules merely to imitate browser contexts.

For actual multi-activity behavior, declare each host and install dependencies before launch. Track each scenario and close it in `finally`. Do not assume a Compose rule automatically owns every activity opened outside its host.

Use a device or emulator to verify task stacks, external browser return, multi-window focus, and real Back behavior. Keep the local test's name limited to the boundary it exercises.

## Own content and cleanup

Use one `setContent` call for a rule-owned host. If the real activity sets its own content, do not overlay another composition through the rule.

Create fresh launcher results, repositories, and listeners per test. Remove callback registrations and cancel pending work in teardown. Do not leave a provider callback able to target the next test's screen owner.

For shared local document state, dispose both consumers and verify the production ownership contract if cancellation is relevant. Do not globally drain all loopers to make a popup disappear.

Assertions must remain outside UI-thread `runOnIdle` callbacks. Use the callback to release controlled state, then query the semantics tree from the test thread.

## Avoid root shortcuts

Bad practice is `onAllNodesWithText("Archive")[0].performClick()` after opening the dialog. It can click the background anchor again and leave the intended confirmation untested.

Correct it by matching the dialog's ancestor and asserting **Draft archived** afterward. Add the cancellation case to prove that opening alone does not archive.

Another anti-pattern assumes an external browser shares the app's Compose tree. Replace that local assumption with launcher contract tests and a separate browser-return device scenario.

## Troubleshoot

| Symptom | Observation | Correction |
| --- | --- | --- |
| `onRoot()` finds several nodes | Every root dump | Query the intended dialog or group |
| Confirmation matches twice | Parent and dialog text | Add dialog ancestor scope |
| Menu text absent | Actual popup tree and animation state | Inspect roots before changing selectors |
| External provider text never appears | Foreground activity and launcher boundary | Test app result locally, provider on device |
| Parent stays unchanged after confirm | Callback-to-state path | Assert the actual parent result |
| Later test receives an old callback | Callback registration and job lifetime | Remove listeners and cancel pending work |

## Review checklist

- Is each window classified as app Compose content or an external activity?
- Does the selector use meaning rather than root order?
- Is the parent result asserted after dialog or menu actions?
- Are cancellation and launch failure deliberate cases?
- Does one owner control content and cleanup?
- Are cross-process and task-stack claims assigned to device coverage?

## Related guides and sources

- [Multi-user testing](multi-user.md), [third-party services](third-party.md), and [authentication](authentication.md).
- [View interop](../android-apis/view-interop.md) and [host integration](../testing-patterns/host-integration.md).
- [Compose testing APIs](https://developer.android.com/develop/ui/compose/testing/apis) describes tree queries.
- [Compose dialogs](https://developer.android.com/develop/ui/compose/components/dialog) describes dialog content and dismissal.
- [Activity results](https://developer.android.com/training/basics/intents/result) describes registration and launch lifecycle.
- [Evidence and limits](../references/evidence.md) separates JVM behavior from real system integration.
