# Test upload and download workflows

Use this guide for transfer progress, cancellation, retry, validation, previews, and authenticated downloads. Keep the real Compose state owner under test. Control document access and transfer completion so each state is observable without a slow network or a giant file.

## Table of contents

- [Choose the test layer](#choose-the-test-layer)
- [Define controllable transfer states](#define-controllable-transfer-states)
- [Test upload progress](#test-upload-progress)
- [Test cancellation and retry](#test-cancellation-and-retry)
- [Validate selected files](#validate-selected-files)
- [Test selection and previews](#test-selection-and-previews)
- [Verify downloads](#verify-downloads)
- [Verify authentication and transport](#verify-authentication-and-transport)
- [Avoid false transfer tests](#avoid-false-transfer-tests)
- [Isolate and synchronize](#isolate-and-synchronize)
- [Troubleshoot failures](#troubleshoot-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the test layer

| Claim | Test here | Test elsewhere |
| --- | --- | --- |
| Upload displays pending and success | Real screen with controlled transfer fake | Real HTTP upload |
| Cancel prevents stale success | Real state owner with controlled late completion | Socket or worker cancellation |
| Retry starts a new attempt | Failed fake attempt followed by successful attempt | Server idempotency |
| File size policy rejects input | Validator and UI error path | Server enforcement |
| Preview displays selected image | Deterministic decoder or fixture bytes | Device codec and provider behavior |
| Download contains correct report | Real serializer or transport response parser | Authenticated service endpoint |
| Download opens in another app | Intent metadata and local document adapter | Installed receiving app and URI grants |

Use `src/test`, `testImplementation`, Android resources, a Robolectric runner, and a declared host as described in [setup](../references/setup.md). The fixture uses Compose UI 1.12.1 with the v2 rule factory.

## Define controllable transfer states

Represent a transfer by an attempt identity and a state such as idle, running, failed, cancelled, or succeeded. Keep progress inside the running state. Avoid independent `isUploading`, `hasError`, and `isDone` booleans that can disagree.

The following illustrative model describes an application boundary. It is not a built-in Android API and is not compiled by this fixture. It requires Kotlin coroutines for `StateFlow`.

```kotlin
import kotlinx.coroutines.flow.StateFlow

sealed interface TransferState {
	data object Idle : TransferState
	data class Running(val attempt: Long, val sent: Long, val total: Long?) : TransferState
	data class Failed(val attempt: Long, val message: String) : TransferState
	data class Cancelled(val attempt: Long) : TransferState
	data class Succeeded(val attempt: Long, val documentName: String) : TransferState
}

interface Transfer {
	val state: StateFlow<TransferState>
	fun start()
	fun cancel()
}
```

Let the test fake hold the current attempt pending and expose methods that advance its state. Give each test a fresh instance. The production state owner must decide whether a completion belongs to the current attempt before showing success.

Choose nullable total size when a provider or transport cannot report it. Test indeterminate progress instead of inventing a percentage from zero or unknown bytes.

## Test upload progress

Test a real action-to-state path:

1. Select a document with stable URI identity and known metadata.
2. Click **Upload**.
3. Hold the fake transfer pending and assert **Uploading**.
4. Emit a partial progress value and assert the progress semantics or visible percentage.
5. Complete the same attempt and assert the uploaded document row.
6. Assert that the pending indicator disappears.

The following illustrative body assumes `TransferScreen(transfer)` is the real app screen and `transfer.emit` is a test helper that updates its state flow. It is not a test of transport. Required imports are shown for the Compose calls.

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick

compose.setContent { TransferScreen(transfer) }
compose.onNodeWithText("Upload").performClick()
compose.onNodeWithText("Uploading").assertIsDisplayed()
compose.runOnIdle {
	transfer.emit(TransferState.Running(attempt = 1, sent = 25, total = 100))
}
compose.onNodeWithText("25%").assertIsDisplayed()
compose.runOnIdle {
	transfer.emit(TransferState.Succeeded(attempt = 1, documentName = "contacts.csv"))
}
compose.onNodeWithText("contacts.csv uploaded").assertIsDisplayed()
compose.onNodeWithText("Uploading").assertDoesNotExist()
```

The containing class needs a rule created with `createComposeRule`, the Robolectric runner, and a supported SDK. Use the [canonical controlled completion example](../examples/FixtureUiTest.kt) for that complete structure.

If the component uses progress semantics rather than text, assert its progress range with the appropriate semantics matcher for the project's version. Do not add a visible percentage just to fit this example.

For a rendering-only test, supply `Running(1, 25, 100)` directly and assert its output. Label it as rendering. It does not prove that **Upload** starts work.

## Test cancellation and retry

A cancellation test needs more than checking `cancelCalls == 1`:

1. Start attempt 1 and assert pending UI.
2. Click **Cancel upload**.
3. Assert the cancelled state and absence of success.
4. Deliver a late success for attempt 1 through the controlled boundary.
5. Assert that the screen remains cancelled and shows no uploaded document.

If the boundary's contract guarantees it never emits after cancellation, test that guarantee in the boundary's own suite. At the UI state owner, test the actual late-event behavior the architecture permits.

For retry, fail attempt 1 with a useful error, click **Retry**, and hold attempt 2 pending. Then complete attempt 2 and assert success. Inspect request history as supplementary evidence that retry uses the intended document and a new attempt identity.

Test double-click behavior when duplicate requests are costly. Keep the first request pending and verify that the UI disables the action or otherwise prevents duplicates according to the product contract.

Network cancellation, worker cancellation, and removing a composition have different ownership. A background upload may intentionally continue after navigation. Do not require composition disposal to cancel it unless that is the application's policy.

## Validate selected files

Picker MIME filters are selection aids, not a security boundary. Feed invalid metadata and bytes directly to the app validator too.

| Case | Expected observation |
| --- | --- |
| Supported type and valid bytes | Selection appears and upload becomes available |
| Unsupported declared type | Explanation appears and upload does not start |
| Allowed suffix with mismatched bytes | Real content validator rejects it where the product requires validation |
| Exactly the size limit | Accepted if the documented limit is inclusive |
| One byte over the limit | Error appears before transfer begins |
| Unknown size | Stream is bounded during reading, or policy explicitly rejects unknown size |
| Too many files | Count error with no partial transfer unless partial acceptance is intended |
| Corrupt image | Decode error and no misleading preview |
| Small or excessive image dimensions | Dimension policy error |

Use synthetic metadata for policy boundaries instead of allocating hundreds of megabytes in a UI test. Add bounded streaming tests to prove the reader stops oversized content when metadata is absent or false.

Run server-side enforcement tests independently. Client validation does not protect an endpoint from callers that bypass the app.

## Test selection and previews

Use [file operations](file-operations.md) for controlled picker results. Cover one file, multiple files, replacement, clearing, and duplicate display names. Scope remove actions by document identity.

For an image preview, assert the content description or selected-image state and use valid fixture bytes when decoding is under test. A preview node's existence does not establish that the bitmap is correct. Add an optional image comparison if visual correctness matters.

For a dropped document, exercise normalized ingestion locally, then test actual drag handling and permission transfer on Android. Selecting a document through a picker does not test a drag handler.

## Verify downloads

Separate the transfer, destination, and content checks:

1. Click the intended export or download action.
2. Hold the response pending and assert download progress if supported.
3. Complete the response into a unique per-test destination.
4. Assert a usable success state or document row.
5. Reopen the written output and validate its bytes with a compatible parser.

For CSV, inspect decoded rows and fields. For JSON, parse the object and check expected fields and types. For PDF or spreadsheet output, use a real format parser. An extension alone does not establish format correctness.

Verify the selected format changes the requested MIME type, suggested filename, and serialized bytes. A fixed application time source makes date-based filenames deterministic.

For batch downloads, assert the exact expected set of artifacts after the batch reports completion. Include partial failure and recovery if the product supports them.

For failures, cover response rejection, destination access denial, insufficient space where the adapter supports it, and interrupted writes. Assert that the UI does not advertise a corrupt partial output as complete. Test temporary-file cleanup or atomic publication in storage adapter tests.

## Verify authentication and transport

A fake transfer returning "success" does not prove credentials were sent or that access was authorized. Add repository or transport tests for request headers, body encoding, MIME type, response handling, and cancellation.

Use service integration tests with disposable accounts for these cases:

- The owner can download the intended document.
- An unauthenticated request is denied without returning document bytes.
- Another account cannot fetch the document by changing its identifier.
- Expired credentials cause the intended refresh or sign-in behavior.
- Retry does not create duplicate server objects when idempotency is promised.

Do not assume Android's download service shares the app's HTTP client's authentication state. Test the concrete download path. Do not put access tokens in filenames, logs, or failure artifacts.

Inspect real response headers when MIME type and content disposition are part of the service contract. Fake metadata only proves the client's handling of that metadata.

## Avoid false transfer tests

Bad practice is delaying a fake by ten real seconds and hoping to catch the progress bar. This creates timing races and slows every failure.

Correct it by holding a deferred completion or controlled state flow. Assert pending UI, then release it. The test decides exactly when the operation finishes.

Do not make an idling resource remain busy while asserting a deliberately pending screen. The synchronized assertion would wait for the very operation being held.

## Isolate and synchronize

Create fresh documents, attempt state, streams, and destinations per test. Close streams, cancel test-owned work, and remove partial outputs during cleanup.

Compose synchronization does not advance a real HTTP client or independent coroutine scheduler. Complete the fake, advance the correct scheduler when necessary, then assert the UI. Use a bounded wait for real external progress, followed by a final behavior assertion.

Do not advance the Compose clock and call the result a download timeout test unless the application's timeout actually uses that clock's scheduler.

## Troubleshoot failures

| Symptom | Observe | Correction |
| --- | --- | --- |
| Progress never appears | Fake completion timing and state ownership | Hold the transfer pending before asserting |
| Cancel still shows success | Attempt identity and late result handling | Reject stale completion in the state owner |
| Retry succeeds with wrong file | Request history and selected URI | Preserve the intended document across attempts |
| Small fixture rejected | Metadata, bytes, and decoder error | Use a valid file for the exercised parser |
| Download exists but is corrupt | Parsed output and publication timing | Verify bytes before reporting completion |
| Authenticated fake passes, real download fails | Concrete client's credentials and redirects | Test the real transport path |

## Review checklist

- [ ] Pending, success, failure, cancellation, and retry are observable.
- [ ] A stale attempt cannot overwrite current UI state.
- [ ] Validation covers metadata and bounded byte reading.
- [ ] Download tests inspect actual generated or received content.
- [ ] Transport and authorization claims have separate evidence.

## Related guides and sources

- [File operations](file-operations.md) covers picker and export basics.
- [Network fakes](../advanced/network-fakes.md) covers controlled asynchronous boundaries.
- [Security testing](security-testing.md) covers access control claims.
- [Storage access framework](https://developer.android.com/training/data-storage/shared/documents-files) documents document access.
- [Compose synchronization](https://developer.android.com/develop/ui/compose/testing/synchronization) describes external work.
- [Android security guidance](https://developer.android.com/privacy-and-security/security-tips) describes input and data protection.
