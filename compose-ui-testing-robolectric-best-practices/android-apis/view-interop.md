# Test Compose and Android View interop

## Table of contents

- [Choose the test layer](#choose-the-test-layer)
- [Mount an Android View inside Compose](#mount-an-android-view-inside-compose)
- [Query the correct hierarchy](#query-the-correct-hierarchy)
- [Test updates and callbacks](#test-updates-and-callbacks)
- [Test dynamic content and disposal](#test-dynamic-content-and-disposal)
- [Handle WebView and embedded providers](#handle-webview-and-embedded-providers)
- [Handle navigation and load failures](#handle-navigation-and-load-failures)
- [Synchronize and isolate interop](#synchronize-and-isolate-interop)
- [Avoid hierarchy shortcuts](#avoid-hierarchy-shortcuts)
- [Troubleshoot failures](#troubleshoot-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the test layer

Use this guide for `AndroidView`, `AndroidViewBinding`, `ComposeView`, and screens that embed a native widget or web content. The useful analogue to an iframe is a boundary between content owners and query systems. An Android View is not a browser frame.

Robolectric can test supported View behavior and Compose's surrounding state locally. It does not provide a full WebView browser or JavaScript engine. A Compose finder cannot enter a WebView document, even with `useUnmergedTree = true`.

| Content | Query or control | What the test proves |
| --- | --- | --- |
| Compose controls surrounding a widget | Compose semantics finders | Host interactions and visible state |
| Native View inside `AndroidView` | View hierarchy queries or Espresso where supported | Native widget properties and event wiring |
| Compose inside a `ComposeView` | Compose semantics with a correctly hosted owner | Composed content behavior |
| WebView bridge callback | Fake the app-facing embedded-content boundary | Native state handling of that callback |
| WebView DOM, nested frames, cross-origin provider | Device WebView test with an appropriate web-testing tool | Real embedded web integration |
| Payment or OAuth provider | Provider sandbox integration on a device | Provider handoff and return handling |

Do not search every hierarchy and click the first matching label. Name the owner before choosing the finder.

## Mount an Android View inside Compose

Use the `factory` block to construct the View. Use `update` to apply current Compose state. Creating a View outside `AndroidView` and retaining it across tests can preserve a stale context, listener, or parent.

Illustrative standalone local test. It needs Android resources, the default host manifest, Compose Material3, Compose UI test JUnit4 1.12.1, JUnit 4, and Robolectric. It is not part of the compiled canonical fixture.

```kotlin
import android.widget.TextView
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class InteropLabelTest {
	@get:Rule val rule = createComposeRule()

	@Test fun nativeLabelReceivesUpdatedState() {
		lateinit var label: TextView
		rule.setContent {
			var selected by remember { mutableStateOf("Standard") }
			Column {
				AndroidView(
					factory = { context ->
						TextView(context).also { label = it }
					},
					update = { it.text = selected },
				)
				Button(onClick = { selected = "Express" }) {
					Text("Choose express")
				}
				Text("Delivery: $selected")
			}
		}
		rule.runOnIdle { assertEquals("Standard", label.text.toString()) }
		rule.onNodeWithText("Choose express").performClick()
		rule.onNodeWithText("Delivery: Express").assertIsDisplayed()
		rule.runOnIdle { assertEquals("Express", label.text.toString()) }
	}
}
```

The View reference is test-local and exists only to inspect the adapter's output. The UI assertion proves the action changed the host state. The native property assertion proves that `update` applied that state. This does not prove device rendering of the TextView.

## Query the correct hierarchy

For a production View with an Android resource ID, scope native queries to that ID and its meaningful parent. If you use Espresso locally, add the project's compatible Espresso dependency and keep a Robolectric-aware test host. Robolectric supports AndroidX Test integration, but that does not make every Espresso feature or custom widget supported.

For Compose labels, use `onNodeWithText` or other semantics matchers. For native `EditText`, use a native View action. `performTextInput` operates on Compose semantics actions, not arbitrary View objects.

Print Compose's merged and unmerged trees for Compose failures. Inspect the Android View hierarchy for a native child. Absence from one tree is not proof that the widget is absent from the other.

For nested interop, first identify the containing View, then the intended child. Use a stable View ID or domain identity. Avoid child index zero unless order itself is the tested behavior.

When a dialog or popup creates another Compose root, scope through the dialog's semantics or meaningful identity. A popup is not a nested `AndroidView` and does not require a View lookup.

## Test updates and callbacks

Cover both directions of the adapter.

1. Change Compose state through a real UI action.
2. Assert the native View receives the new value.
3. Trigger a supported native user action.
4. Assert the host's user-visible result.

A callback count alone can pass when the host ignores the callback. A visible host result alone can miss a stale native widget if the test never exercises that widget.

For an embedded picker, choose a concrete value through the native control, then assert a Compose summary. For text entry, assert the native field's new text and the host's validation result. Avoid calling the callback directly when the claim is that the View listener is correctly attached.

Use a direct callback invocation only in a separate host-boundary test. Label that test as result handling, not widget interaction.

## Test dynamic content and disposal

For a widget shown on demand, assert the host's initial state, click **Open widget**, then observe the widget's ready state. Do not wait for a fixed interval and assume creation finished.

If the widget appears in a lazy list, scroll to its stable item identity before interacting. List recycling can reuse Views. Test the current item identity and value after reuse so a listener cannot accidentally retain the previous item.

When using the `AndroidView` overload with reuse callbacks, make reset behavior explicit. `onReset` prepares a reusable View for another item. `onRelease` handles permanent removal. Test release against the ownership contract of the real widget, such as removing listeners or stopping a media session.

For `ComposeView` inside a View screen, select a composition disposal strategy appropriate to the host lifecycle. A fragment's view lifecycle and the fragment instance lifetime are different. Verify that replacing the fragment view does not leave the old composition active.

Local removal proves local disposal only. It does not prove process-death restoration or device resource release.

## Handle WebView and embedded providers

Keep web content behind an app-owned boundary that reports ready, completed, cancelled, or failed outcomes. Test the surrounding native screen with a fake boundary. Keep the real provider integration separate.

A useful local payment test performs this sequence:

1. Click **Pay** in the Compose host.
2. Assert the host shows the embedded-payment pending state.
3. Deliver an app-facing success result with a fixed transaction identifier.
4. Assert the receipt and order status.
5. In another test, deliver cancellation or failure and assert the recovery action.

Do not instantiate a Robolectric WebView, call `loadUrl`, and infer that scripts or nested frames executed. A shadow recording a requested URL establishes only that request. It cannot establish cross-origin behavior, cookies, redirects, or provider completion.

For an actual WebView device test, use controlled test content or the provider's sandbox. Wait for a specific ready element or bridge event. Exercise the intended DOM element with web-aware tooling. Verify the native result after returning from the provider.

OAuth testing must also verify the intended supported browser or SDK flow. Do not recommend embedded credential entry merely because the upstream browser guide uses an iframe example.

## Handle navigation and load failures

Test native route handling independently from web navigation. A bridge message that says an article was selected can drive a native article screen. Assert that article's identity after the host handles the message.

For load failures, inject the adapter's failed result and assert the host's explanation and retry button. Click **Retry**, hold the second attempt pending, then complete it successfully. This proves retry behavior rather than hiding a failure behind a test-side reload.

Do not catch every assertion and reconstruct the widget until the test passes. That can mask missing listener registration, incorrect URLs, and broken UI state. Preserve the first failure and diagnose its owner.

If the embedded content navigates to a new document, test stale callbacks. A completion from the old document must not overwrite the current request when the application promises request isolation.

## Synchronize and isolate interop

Compose synchronization does not mean an arbitrary widget, web renderer, or SDK is ready. Wait on an app-facing ready condition, a supported idling resource, or a controlled callback.

Use the Compose clock for Compose-owned animation only. Android handlers and widget executors have separate ownership. Advance a known looper task only when that task is the source of the transition.

Construct fresh Views, contexts, fake provider sessions, and listeners per test. Dispose the test-owned composition through its rule. Close app-owned SDK sessions and remove native listeners on the proper lifecycle boundary.

Avoid storing native Views in singletons or companion objects. A View retains its context and may still belong to an old parent.

## Avoid hierarchy shortcuts

| Anti-pattern | Failure mechanism | Correction |
| --- | --- | --- |
| Query WebView text with Compose semantics | The DOM is not a Compose semantics subtree | Test the host locally and web integration on a device |
| Query every root and choose the first match | Identical labels can belong to another owner | Scope by meaningful host or widget identity |
| Recreate the native View on every recomposition | Listeners and native state can reset | Construct in `factory` and apply state in `update` |
| Invoke only a callback and claim widget coverage | Native listener wiring is bypassed | Perform a native action in an adapter test |
| Retry a failed assertion by reloading | The test conceals the first broken transition | Inject and assert the app's real retry flow |

## Troubleshoot failures

| Symptom | Observation | Fix |
| --- | --- | --- |
| Compose finder sees no native text | Native View exists in its own hierarchy | Use the native query system |
| Native label remains stale | Inspect `update` and state observation | Apply the current value in `update` |
| Callback uses an old list item | Inspect reuse and listener capture | Reset identity and listener state on reuse |
| View already has a parent | View instance survived another mount | Construct it inside the current factory |
| WebView loads but no script result arrives | Determine whether this is a local shadow | Move script execution claims to a device test |
| Old widget updates the new screen | Inspect release and callback cancellation | Remove listeners and reject stale results |

## Review checklist

- Is each assertion in the correct hierarchy?
- Do tests cover state updates and callback wiring separately?
- Is widget readiness explicit rather than inferred from Compose idle?
- Are lazy reuse and permanent disposal distinguished?
- Are failure, cancellation, and retry visible to the user?
- Are DOM execution and provider integration tested outside Robolectric?

## Related guides and sources

- [System services](system-services.md) covers platform adapters.
- [Third-party integrations](../advanced/third-party.md) covers provider boundaries.
- [Multiple roots](../advanced/multiple-roots.md) covers dialogs and popups.
- [Views in Compose](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/views-in-compose) documents `AndroidView`, update, reset, and release.
- [Compose in Views](https://developer.android.com/develop/ui/compose/migrate/interoperability-apis/compose-in-views) documents `ComposeView` lifecycle ownership.
- [Robolectric AndroidX Test integration](https://robolectric.org/androidx_test/) describes local AndroidX Test support.
- [Espresso-Web](https://developer.android.com/training/testing/espresso/web) describes WebView interaction for instrumented tests.
