# Test document selection, import, and export

Use this guide for choosing files, importing content, generating exports, and verifying saved bytes. Android apps exchange documents through URIs and streams. A document URI is not necessarily a filesystem path. For upload progress, cancellation, retry, and authenticated downloads, use [file transfers](file-transfers.md).

## Table of contents

- [Choose the file boundary](#choose-the-file-boundary)
- [Set up deterministic documents](#set-up-deterministic-documents)
- [Test the picker result](#test-the-picker-result)
- [Verify import behavior](#verify-import-behavior)
- [Verify exports and content](#verify-exports-and-content)
- [Cover multiple files and dropped content](#cover-multiple-files-and-dropped-content)
- [Avoid path assumptions](#avoid-path-assumptions)
- [Isolate and synchronize](#isolate-and-synchronize)
- [Troubleshoot failures](#troubleshoot-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the file boundary

| Goal | Local test | Integration handoff |
| --- | --- | --- |
| User chooses a document | Controlled activity result and selected-name UI | Real document picker |
| App parses CSV or JSON | Real parser against deterministic bytes | Provider stream access if needed |
| App exports a report | Real serializer into a per-test sink, then parse output | Document creation and provider permissions |
| User replaces a file | Select, clear, select again, assert current selection | None for selection state alone |
| User selects multiple documents | Stable URI identities and per-row actions | Provider multi-select behavior |
| User drags a document from another app | Test ingestion handler and resulting UI | Real drag events and URI grant transfer |
| User opens an export in another app | Verify share intent metadata | Receiving app can open the content URI |

Do not add a fake HTTP layer to a test of local serialization. Use the smallest boundary that preserves the claim. Conversely, a fake document reader cannot prove that a real content provider supplies readable bytes.

## Set up deterministic documents

Keep Robolectric tests under `src/test` with Android resources, a declared host, and the dependencies in [setup](../references/setup.md). The canonical fixture uses Compose UI 1.12.1 and the v2 rule factory.

Give each selected document these independent properties:

- A stable URI for identity.
- A display name for the UI.
- A declared MIME type, which remains untrusted input.
- A readable stream, or a controlled read failure.
- Optional size metadata, including an unknown-size case.

Use valid fixture bytes when a parser or decoder runs. A string called `report.pdf` is not a valid PDF. Keep fixtures small, synthetic, and free of customer data.

For a screen-only test, inject a document reader keyed by URI. For an adapter test, exercise `ContentResolver` through a test provider or supported framework test setup. Keep these claims separate.

## Test the picker result

Android's activity result registry can deliver a controlled result without opening the system picker. The following illustrative helper and composable use `GetContent`. They are not compiled by this fixture.

Dependencies include AndroidX Activity Compose, AndroidX Core, Compose Material3, and the test dependencies in setup. Place imports at the top of the test file.

```kotlin
import android.app.Activity
import android.content.Intent
import android.net.Uri
import androidx.activity.result.ActivityResultRegistry
import androidx.activity.result.contract.ActivityResultContract
import androidx.core.app.ActivityOptionsCompat

class PickerRegistry(private val selected: Uri?) : ActivityResultRegistry() {
	override fun <I, O> onLaunch(
		requestCode: Int,
		contract: ActivityResultContract<I, O>,
		input: I,
		options: ActivityOptionsCompat?
	) {
		val data = selected?.let { Intent().setData(it) }
		dispatchResult(
			requestCode,
			if (selected == null) Activity.RESULT_CANCELED else Activity.RESULT_OK,
			data
		)
	}
}

```

Inject the registry through `LocalActivityResultRegistryOwner` in the following composable. Keep the owner stable for the mounted test composition. This example receives one registry created before `setContent`.

```kotlin
import android.net.Uri
import androidx.activity.compose.LocalActivityResultRegistryOwner
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.ActivityResultRegistry
import androidx.activity.result.ActivityResultRegistryOwner
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.remember

@Composable
fun ControlledDocumentPicker(
	registry: ActivityResultRegistry,
	onSelected: (Uri?) -> Unit
) {
	val owner = remember(registry) {
		object : ActivityResultRegistryOwner {
			override val activityResultRegistry = registry
		}
	}
	CompositionLocalProvider(LocalActivityResultRegistryOwner provides owner) {
		val launcher = rememberLauncherForActivityResult(
			ActivityResultContracts.GetContent(),
			onSelected
		)
		Button(onClick = { launcher.launch("text/csv") }) { Text("Choose CSV") }
	}
}
```

In a rule test, create a fresh registry with `content://test.documents/contacts`, mount this control and the real selection state owner, then click **Choose CSV**. Assert the visible display name supplied by the reader. Repeat with `null` and assert that cancellation leaves the existing selection unchanged if that is the product contract.

The registry tests callback delivery. Add a separate contract test for the request's MIME filter and action. A controlled result alone does not prove the picker filtered disallowed content, or that the returned URI is readable.

For long-lived document access, use the appropriate open-document contract and explicitly test persistable URI permission behavior in an Android integration test. `GetContent` and persistent document access are not interchangeable.

## Verify import behavior

Drive the user workflow, not just the parser:

1. Provide a selected document with a deterministic name and valid CSV bytes.
2. Trigger the import through the real screen.
3. Hold the reader pending if the loading state matters.
4. Complete the read and assert a preview or imported-row summary.
5. Confirm the import and assert the resulting records.

Supplement the UI assertion with repository contents when duplicate handling matters. Assert that invalid input leaves previous records unchanged.

Test malformed bytes, truncated content, unsupported encoding when applicable, empty input, and read denial. Map failures to useful UI, not raw provider exceptions. A display-name suffix is not a parser validation strategy.

For clearing and replacement, select `old.csv`, remove it through the UI, then select `new.csv`. Assert that `new.csv` appears and `old.csv` does not. Keep stable URI identity separate from filename because two providers can return the same name.

## Verify exports and content

For the local workflow, give the real export code a fresh destination stream or temporary file. Trigger **Export**, complete any controlled work, and assert the success message. Then inspect the actual bytes written by that action.

This standalone illustrative example defines a small exporter and invokes its operation boundary. It needs JUnit 4.13.2 and the JDK, not a Compose host. `Contact` is the input record. `ExportResult` reports completed rows. The injected `openDestination` factory owns destination selection, so the test can inspect a fresh file that only the exporter creates.

The tested CSV contract is deliberately limited. It writes a fixed `name,email` header, preserves input order, uses UTF-8 without a BOM, ends every record with CRLF, and writes unquoted fields. Commas, double quotes, CR, and LF are rejected in either field before opening the destination. Empty fields and Unicode text are supported. It is not a general CSV serializer or a spreadsheet-formula sanitizer.

```kotlin
import java.io.OutputStream
import java.io.OutputStreamWriter
import java.nio.charset.StandardCharsets.UTF_8
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

private data class Contact(val name: String, val email: String)
private data class ExportResult(val rowsWritten: Int)

private class ContactCsvExporter(private val openDestination: () -> OutputStream) {
	fun export(contacts: List<Contact>): ExportResult {
		contacts.forEach { contact ->
			listOf(contact.name, contact.email).forEach { field ->
				require(field.none { it == ',' || it == '"' || it == '\r' || it == '\n' }) {
					"This exporter accepts only unquoted CSV fields"
				}
			}
		}
		OutputStreamWriter(openDestination(), UTF_8).use { writer ->
			writer.append("name,email\r\n")
			contacts.forEach { contact ->
				writer.append(contact.name).append(',').append(contact.email).append("\r\n")
			}
		}
		return ExportResult(contacts.size)
	}
}

class CsvExportOperationTest {
	@get:Rule val files = TemporaryFolder()

	@Test fun exportProducesOrderedUtf8Records() {
		val output = files.root.resolve("contacts.csv")
		assertFalse(output.exists())
		val exporter = ContactCsvExporter { output.outputStream() }
		val result = exporter.export(listOf(
			Contact("Alice", "alice@example.test"),
			Contact("Zoë", "zoe@example.test"),
			Contact("", ""),
		))
		assertEquals(ExportResult(rowsWritten = 3), result)
		assertArrayEquals(
			("name,email\r\nAlice,alice@example.test\r\n" +
				"Zoë,zoe@example.test\r\n,\r\n").toByteArray(UTF_8),
			output.readBytes(),
		)
	}

	@Test fun emptyExportStillProducesHeader() {
		val output = files.root.resolve("empty.csv")
		val result = ContactCsvExporter { output.outputStream() }.export(emptyList())
		assertEquals(ExportResult(0), result)
		assertArrayEquals("name,email\r\n".toByteArray(UTF_8), output.readBytes())
	}

	@Test fun unsupportedFieldsAreRejectedBeforeDestinationOpens() {
		val output = files.root.resolve("invalid.csv")
		val exporter = ContactCsvExporter { output.outputStream() }
		for (delimiter in listOf(",", "\"", "\r", "\n")) {
			for (invalid in listOf(Contact("A${delimiter}B", "a@test"), Contact("A", "a${delimiter}b"))) {
				assertThrows(IllegalArgumentException::class.java) {
					exporter.export(listOf(Contact("Valid", "valid@test"), invalid))
				}
				assertFalse("Rejected input must not create or truncate output", output.exists())
			}
		}
	}
}
```

A disconnected exporter, missing row, wrong ordering, encoding change, or newline change fails the byte assertion. The expected byte literal is an independent oracle, not the data written by the test. The exporter closes its acquired stream with `use`. An I/O exception propagates instead of returning success. For large documents, run this operation off the UI thread and test the screen's pending and failure states separately.

In an app adapter, `openDestination` can open the chosen URI through `ContentResolver.openOutputStream`, with a null result treated as an open failure. The caller chooses the URI before invoking the operation. A UI test must click **Export** and verify the success state plus this operation's produced artifact. The operation tests above do not prove that button wiring, document creation, URI grants, or provider behavior.

If the app supports quoted commas, escaped quotes, or embedded newlines, use its general CSV writer and parse its output with a compatible parser. Include records with each of those characters. Do not extend this limited contract by splitting on commas or counting newline characters.

Choose content checks by format:

| Format | Verify |
| --- | --- |
| CSV | Headers, decoded records, ordering if promised, quoting, encoding |
| JSON | Parsed object fields and types, schema or version, expected records |
| PDF | Valid document structure and extracted business text with a compatible parser |
| Spreadsheet | Worksheet identity, cell types, formulas if promised, record values |
| Image | Successful decode, dimensions, relevant visual output |

A filename, nonzero length, or magic prefix alone cannot prove a correct report. Parse the artifact when feasible. Check the name and MIME type too, but treat them as metadata.

For document creation, verify that the adapter requests the intended suggested filename and MIME type. On Android, create the document through a real provider and reopen it through its URI to check saved bytes.

## Cover multiple files and dropped content

Select multiple distinct URIs and assert each document row. Remove one by its stable row identity and verify the other rows remain. Include duplicate display names to catch selectors that choose an arbitrary first row.

For a batch export, verify the exact expected set of outputs. Do not stop after the first completion. Use a completion barrier owned by the batch operation, then inspect every artifact.

For drag-and-drop, test the ingestion adapter with the same normalized document input used by the picker. This proves shared validation and import behavior. It does not exercise the drag event handler or cross-app grant transfer. Test actual drag interaction on Android with a source app and target app when that feature ships.

## Avoid path assumptions

Bad practice is converting `uri.path` to `File` and testing with a local disk path. The test can pass while document-provider URIs fail because their path is not a filesystem location.

Correct it by reading through the resolver adapter and testing both readable and denied URI results. Keep filesystem-path tests only for code whose explicit contract is app-owned files.

Do not write all test exports to a shared `downloads/report.csv`. Parallel tests can overwrite one another and falsely pass against stale content.

## Isolate and synchronize

Use fresh temporary directories and document fakes per test. Close input and output streams with `use`. Release test provider state, callbacks, and URI grants owned by integration tests.

Install result handling before triggering selection. Compose synchronization does not complete file I/O or a deferred reader. Complete the reader explicitly, or wait on a bounded observable condition and then assert the UI result.

Delete temporary outputs after checks, but preserve sanitized failure artifacts in the test report when they help diagnose serialization defects.

## Troubleshoot failures

| Symptom | Observe | Correction |
| --- | --- | --- |
| Filename shown but import empty | Bytes read and parser result | Use real fixture content and assert imported records |
| Cancellation clears old selection unexpectedly | Result reducer and prior state | Define and test cancellation semantics |
| URI works locally but not from picker | Resolver access and URI grants | Stop treating content URIs as paths |
| Export test sees old data | Output ownership and unique path | Use a per-test sink and inspect the current action's artifact |
| Multiple files choose the wrong remove action | Row identity and semantics | Scope by stable document identity |
| UI remains loading | I/O owner and pending fake | Release or fail the correct operation |

## Review checklist

- [ ] Selection metadata and readable bytes are tested separately.
- [ ] Cancellation, replacement, and duplicate names have explicit behavior.
- [ ] The export assertion inspects content produced by the user action.
- [ ] Streams and temporary outputs have local ownership.
- [ ] Provider permissions and system picker behavior have integration coverage.

## Related guides and sources

- [File transfers](file-transfers.md) covers network transfer state.
- [Host integration](host-integration.md) covers result ownership.
- [Activity results](https://developer.android.com/training/basics/intents/result) documents test registries.
- [Storage access framework](https://developer.android.com/training/data-storage/shared/documents-files) documents URI-based document access.
- [ContentResolver](https://developer.android.com/reference/android/content/ContentResolver) documents stream access.
