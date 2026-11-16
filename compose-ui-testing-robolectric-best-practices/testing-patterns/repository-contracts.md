# Test repository and API contracts

Use this guide to test data behavior without mounting Compose when the claim concerns a repository, client, serializer, or HTTP service. Use Robolectric only when the boundary needs Android resources, storage, or framework behavior. Keep plain Kotlin contract tests on the JVM without an activity host.

## Table of contents

- [Choose the boundary](#choose-the-boundary)
- [Build an isolated client fixture](#build-an-isolated-client-fixture)
- [Check CRUD behavior](#check-crud-behavior)
- [Verify the real request and response](#verify-the-real-request-and-response)
- [Test error contracts](#test-error-contracts)
- [Seed UI tests without bypassing their action](#seed-ui-tests-without-bypassing-their-action)
- [Test uploads and workflows](#test-uploads-and-workflows)
- [Validate decoding and domain constraints](#validate-decoding-and-domain-constraints)
- [Organize execution and cleanup](#organize-execution-and-cleanup)
- [Avoid false integration claims](#avoid-false-integration-claims)
- [Troubleshoot failures](#troubleshoot-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the boundary

| Question | Test layer | What the test does not establish |
| --- | --- | --- |
| Does the screen show a repository failure? | Compose plus fake repository | Actual transport or server behavior |
| Does the repository map responses correctly? | Real repository plus controlled client boundary | Wire encoding if the client is fake |
| Does the client send correct JSON and headers? | Real client plus local HTTP test server | Production backend enforcement |
| Does the store persist an update? | Real store plus isolated database or files | Remote synchronization |
| Does the service reject an unauthorized request? | Dedicated service integration suite | Native UI behavior |
| Does submission update the visible screen? | Compose through the real action with controlled data | Backend persistence if the repository is fake |
| Does a GraphQL response carry partial data? | GraphQL client and repository contract | Rendering unless tested separately |

Do not launch Compose to check a serializer. Conversely, do not replace a UI result assertion with an API response assertion when the claim concerns what the user sees.

## Build an isolated client fixture

Give each test its own client configuration, credentials, store, response script, and cleanup owner. Prefer an injected base URL over a global endpoint switch.

For a local HTTP server fixture:

1. Start a fresh server on an allocated port.
2. Construct the production client with that server's URL.
3. Install a test token provider before the first request.
4. Queue the exact response for the request under test.
5. Execute the public repository operation.
6. Inspect the recorded request and returned domain result.
7. Close response bodies, shut down the client resources your fixture owns, and stop the server in teardown.

### Complete local HTTP contract

The data shapes are `CreateItem`, decoded `CreatedItem`, `UploadDocument`, and decoded `DocumentReceipt`. The illustrative client below implements these two endpoints completely. It is not the consuming app's production repository and does not establish backend enforcement.

This standalone Kotlin/JVM example uses Kotlin 2.2.10, JDK 17, JUnit 4.13.2, and the **4.12.0** OkHttp API, not MockWebServer 5's `mockwebserver3` package. Put the complete Kotlin block in `src/test/kotlin/ItemHttpContractTest.kt`. In a Kotlin/JVM module with `mavenCentral()`, add:

```kotlin
dependencies {
	testImplementation("junit:junit:4.13.2")
	testImplementation("com.squareup.okhttp3:okhttp:4.12.0")
	testImplementation("com.squareup.okhttp3:mockwebserver:4.12.0")
	testImplementation("org.json:json:20240303")
}
```

`org.json:json` supplies the decoder on a plain JVM. For an Android local test that uses Android's `org.json`, omit that dependency and run with the project's Robolectric runner, such as `@RunWith(RobolectricTestRunner::class)` and `@Config(manifest = Config.NONE, sdk = [35])` with `testImplementation("org.robolectric:robolectric:4.18")`. Those annotations require imports from `org.junit.runner` and `org.robolectric` and its `annotation` package. Do not use the Android stub jar without Robolectric. Neither variant needs a Compose rule or activity.

The service contract uses integer cents, JSON creation at `/api/items`, and a multipart upload at `/api/documents`. Both return 201 with JSON. Any other status becomes `ItemHttpFailure` before success decoding. Transport `IOException` and malformed JSON remain separate failures. No refresh, retries, or persistence are implied.

```kotlin
import java.io.Closeable
import java.io.IOException
import java.util.concurrent.TimeUnit
import okhttp3.HttpUrl
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

data class CreateItem(val title: String, val priceCents: Int)
data class CreatedItem(val id: String, val title: String, val priceCents: Int)
data class UploadDocument(
	val filename: String,
	val mimeType: String,
	val bytes: ByteArray,
	val description: String,
)
data class DocumentReceipt(
	val id: String,
	val filename: String,
	val mimeType: String,
	val size: Int,
)
class ItemHttpFailure(val status: Int) : IOException("HTTP $status")

class ItemHttpClient(private val baseUrl: HttpUrl, private val token: String) : Closeable {
	private val http = OkHttpClient.Builder()
		.callTimeout(5, TimeUnit.SECONDS)
		.followRedirects(false)
		.retryOnConnectionFailure(false)
		.build()

	fun create(input: CreateItem): CreatedItem {
		val body = JSONObject().put("title", input.title).put("priceCents", input.priceCents)
		val json = post("api/items", body.toString().toRequestBody("application/json".toMediaType()))
		return CreatedItem(json.getString("id"), json.getString("title"), json.getInt("priceCents"))
	}

	fun upload(input: UploadDocument): DocumentReceipt {
		val body = MultipartBody.Builder().setType(MultipartBody.FORM)
			.addFormDataPart("description", input.description)
			.addFormDataPart("file", input.filename, input.bytes.toRequestBody(input.mimeType.toMediaType()))
			.build()
		val json = post("api/documents", body)
		return DocumentReceipt(
			json.getString("id"), json.getString("filename"), json.getString("mimeType"), json.getInt("size"),
		)
	}

	private fun post(path: String, body: RequestBody): JSONObject {
		val request = Request.Builder().url(requireNotNull(baseUrl.resolve(path)))
			.header("Authorization", "Bearer $token")
			.header("Accept", "application/json").post(body).build()
		return http.newCall(request).execute().use { response ->
			if (response.code != 201) throw ItemHttpFailure(response.code)
			if (response.body?.contentType()?.subtype != "json") throw IOException("Expected JSON")
			JSONObject(requireNotNull(response.body).string())
		}
	}

	override fun close() {
		http.connectionPool.evictAll()
		http.dispatcher.executorService.shutdown()
	}
}

class ItemHttpContractTest {
	@Test fun createsItemOverHttp() {
		MockWebServer().use { server ->
			server.start()
			server.enqueue(MockResponse().setResponseCode(201)
				.setHeader("Content-Type", "application/json")
				.setBody("""{"id":"101","title":"Hammer","priceCents":1999}"""))
			ItemHttpClient(server.url("/"), "local-token").use { client ->
				assertEquals(CreatedItem("101", "Hammer", 1999), client.create(CreateItem("Hammer", 1999)))
				val request = requireNotNull(server.takeRequest(1, TimeUnit.SECONDS))
				assertEquals("POST", request.method)
				assertEquals("/api/items", request.path)
				assertEquals("Bearer local-token", request.getHeader("Authorization"))
				assertEquals("application/json", request.getHeader("Accept"))
				assertTrue(requireNotNull(request.getHeader("Content-Type")).startsWith("application/json"))
				val body = JSONObject(request.body.readUtf8())
				assertEquals(2, body.length())
				assertEquals("Hammer", body.getString("title"))
				assertEquals(1999, body.getInt("priceCents"))
			}
		}
	}

	@Test fun uploadsMultipartBytesAndDecodesReceipt() {
		MockWebServer().use { server ->
			server.start()
			server.enqueue(MockResponse().setResponseCode(201)
				.setHeader("Content-Type", "application/json")
				.setBody("""{"id":"d1","filename":"report.txt","mimeType":"text/plain","size":7}"""))
			ItemHttpClient(server.url("/"), "local-token").use { client ->
				val input = UploadDocument("report.txt", "text/plain", "report\n".toByteArray(Charsets.UTF_8), "Monthly report")
				assertEquals(DocumentReceipt("d1", "report.txt", "text/plain", 7), client.upload(input))
				val request = requireNotNull(server.takeRequest(1, TimeUnit.SECONDS))
				assertEquals("POST", request.method)
				assertEquals("/api/documents", request.path)
				assertEquals("Bearer local-token", request.getHeader("Authorization"))
				val contentType = requireNotNull(request.getHeader("Content-Type"))
				assertTrue(contentType.startsWith("multipart/form-data; boundary="))
				val boundary = contentType.substringAfter("boundary=")
				val parts = request.body.readUtf8().split("--$boundary")
				val description = parts.single { it.contains("name=\"description\"") }
				assertEquals("Monthly report\r\n", description.substringAfter("\r\n\r\n"))
				val file = parts.single { it.contains("name=\"file\"") }
				assertTrue(file.contains("filename=\"report.txt\""))
				assertTrue(file.contains("Content-Type: text/plain\r\n"))
				assertEquals("report\n\r\n", file.substringAfter("\r\n\r\n"))
			}
		}
	}

	@Test fun rejectsHttpErrorBeforeTryingToDecodeHtml() {
		MockWebServer().use { server ->
			server.start()
			server.enqueue(MockResponse().setResponseCode(401)
				.setHeader("Content-Type", "text/html").setBody("<h1>Unauthorized</h1>"))
			ItemHttpClient(server.url("/"), "expired-token").use { client ->
				val error = assertThrows(ItemHttpFailure::class.java) { client.create(CreateItem("Hammer", 1999)) }
				assertEquals(401, error.status)
				assertEquals("/api/items", requireNotNull(server.takeRequest(1, TimeUnit.SECONDS)).path)
			}
		}
	}
}
```

Run `./gradlew test --tests '*ItemHttpContractTest'` in that standalone module. The multipart inspection deliberately uses a small UTF-8 text fixture with no boundary-like payload. Use a MIME parser and byte assertions for arbitrary binary uploads. `use` closes the client and server even if decoding or an assertion fails, and attaches close failures as suppressed exceptions. Every response body closes inside the client. Real calls have a five-second wall-clock timeout, independent of any coroutine scheduler.

This example does not inherit the canonical Compose fixture's execution evidence. When adapting it to an app, construct the actual production client instead of copying this illustrative implementation into a test and claiming it covers the app.

Create separate user and admin client fixtures if their roles matter. Never mutate one client's bearer token halfway through concurrent tests. A recording fake token provider proves header attachment, not server authorization.

For service integration, load dedicated test credentials through CI secrets. Fail clearly when required configuration is missing. Do not silently fall back to a production URL or another user's cached session.

## Check CRUD behavior

The domain shape below is an illustrative repository contract. It uses immutable items and public operations. It is not a transport implementation or a compiled fixture example.

```kotlin
import java.math.BigDecimal

data class Item(
	val id: String,
	val title: String,
	val price: BigDecimal,
)

interface ItemRepository {
	suspend fun create(title: String, price: BigDecimal): Item
	suspend fun get(id: String): Item?
	suspend fun replace(id: String, title: String, price: BigDecimal): Item
	suspend fun changePrice(id: String, price: BigDecimal): Item
	suspend fun delete(id: String)
}
```

This illustrative JUnit fragment requires JUnit 4 and `kotlinx-coroutines-test` in `testImplementation`. The surrounding test must provide `repository`, a fresh real `ItemRepository` implementation backed by an isolated store or local server. Do not run it against a fake and describe the result as proof of the production repository.

```kotlin
import java.math.BigDecimal
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

@Test fun createdItemCanBeReplacedPatchedAndDeleted() = runTest {
	val created = repository.create("Hammer", BigDecimal("19.99"))
	try {
		assertEquals("Hammer", repository.get(created.id)?.title)
		val replaced = repository.replace(created.id, "Claw hammer", BigDecimal("24.99"))
		assertEquals("Claw hammer", replaced.title)
		val patched = repository.changePrice(created.id, BigDecimal("22.50"))
		assertEquals("Claw hammer", patched.title)
		assertEquals(BigDecimal("22.50"), patched.price)
	} finally {
		repository.delete(created.id)
	}
	assertNull(repository.get(created.id))
}
```

The preserved title proves that the partial update did not accidentally act as a full replacement. Use the project's money type and scale policy rather than adopting `BigDecimal` blindly.

Keep individual operation tests too. A chained CRUD test stops at its first failure and cannot replace focused missing-item, conflict, and invalid-transition cases.

Use IDs returned by creation. Hardcoded service IDs can belong to another test or disappear after a database reset.

## Verify the real request and response

A repository return value can be correct while a request is wrong. In real-client tests, inspect relevant wire behavior independently.

| Operation | Request observations | Response observations |
| --- | --- | --- |
| List | Method, path, page, limit, filter, sort | Status, content type, decoded items, pagination |
| Create | POST body, required headers, auth | Created status, returned ID and values |
| Replace | PUT body contains complete replacement | Unspecified fields follow replacement policy |
| Partial update | PATCH body contains intended change | Unchanged fields remain intact |
| Delete | DELETE path and identity | Empty successful body handled without JSON parsing |
| Token request | Form encoding if required by service | Token presence and expiry mapping |
| Upload | Multipart field names, filename, MIME type, bytes | Metadata and size mapping |

Do not assert every incidental header supplied by the HTTP engine. Assert headers that the contract depends on, such as authentication, content type, conditional requests, and retry metadata.

For a JSON success response, validate status before decoding the body. An HTML error page or empty 204 response must not be parsed as a normal item.

For list responses, check item identities and pagination metadata together. Test an empty final page, filtering, stable sort behavior, and the absence of duplicates across pages when those are repository guarantees.

Do not infer cache correctness merely from a cache-control header. Test the client's actual cache read, expiry, and invalidation behavior at the owner of that policy.

## Test error contracts

Keep transport status, decoding failure, and domain rejection distinct. The exact mapping belongs to the consuming app's contract.

| Input or response | Client or repository expectation | UI expectation in a separate test |
| --- | --- | --- |
| 400 or 422 field rejection | Structured field errors retained | Correct field message and editable input |
| 401 | Unauthenticated result or refresh policy | Sign-in or session-expired flow |
| 403 | Forbidden result, not automatic success after retry | Permission explanation |
| 404 | Missing item according to endpoint policy | Not-found state |
| 409 | Conflict or version mismatch | Conflict resolution without silent overwrite |
| 429 with retry metadata | Bounded retry policy and parsed delay | Appropriate waiting or retry feedback |
| 500 or 503 | Service failure | Recoverable error where supported |
| Timeout or connection failure | Transport failure | Offline or retry state |
| Malformed JSON | Decoding failure, not empty success | Safe generic failure |
| Coroutine cancellation | Cancellation propagates | No stale result applied to disposed UI |

Do not flood a shared environment to trigger rate limiting. Script a 429 in the local client test. Test the server's actual rate-limiting policy only in an isolated service environment with explicit limits.

Test retry bounds with an injected time source or the scheduler that owns backoff. Include a final failure after the maximum attempts and a successful recovery case. Non-idempotent creation must not be retried blindly.

For auth refresh, script expired-token failure, refresh success, and retried operation. Also test refresh rejection and concurrent requests according to the client's refresh policy. A fake repository cannot validate those headers or refresh exchanges.

## Seed UI tests without bypassing their action

Use repositories or APIs to create prerequisite catalog items, accounts, and workspaces. Keep the action under test in the UI.

For a workspace dashboard case:

1. Create an isolated owner and workspace in the chosen test layer.
2. Mount or launch the screen with the intended session.
3. Navigate through the user action under test.
4. Assert the workspace name and relevant visible details.
5. Delete only the resources created by the test.

For local Compose tests, seed a fresh fake or isolated store. For device end-to-end tests, use a dedicated service fixture with unique identities. Those are different claims and should have different test names.

If the test claims **Create workspace** works, do not seed the created workspace itself. Seed only prerequisites, click the real create action, and assert the resulting workspace and persistence at the appropriate layer.

Use unique per-run resource names for shared service environments. A timestamp alone may collide across workers. Use a random run ID and retain returned resource IDs for cleanup.

## Test uploads and workflows

The [complete local HTTP contract](#complete-local-http-contract) executes a real multipart request and checks the field name, filename, MIME type, transferred text bytes, and decoded receipt. Extend it with unsupported MIME type, empty content, and an oversized response rejection. Do not allocate a huge buffer merely to test UI error presentation.

Local URI parsing or fake upload completion does not test Android document picker grants. Use a device case for picker selection and a client contract for transferred bytes.

For an order workflow, create the product, create a cart, submit the order, and read back the order and stock. Assert every transition's result before continuing. Use exact decimal expectations from the product's money policy.

For publication or approval workflows, verify an allowed transition and a forbidden reversal in independent tests. A UI that hides the forbidden button does not prove the backend rejects the request.

Track cleanup as resources are created. If creating a cart fails, delete the product already created. Cleanup code must run on assertion failures too. Preserve the original test failure if cleanup also fails, and report leftover resource IDs without credentials.

## Validate decoding and domain constraints

Generated or typed DTOs establish only part of a response contract. A string can decode successfully while containing an invalid date, blank title, unsupported enum, or negative amount.

Use the production serializer and mapper with response fixtures for:

- Missing required fields and explicit nulls.
- Unknown fields under the configured compatibility policy.
- Unknown enum values and supported fallback behavior.
- Invalid timestamps, offsets, and numeric boundaries.
- Empty and nested collections.
- Valid optional fields omitted by older service versions.

Assert the public domain result or the specific decoding failure. Do not compute the expected result by calling the mapper under test a second time.

A local recorded JSON fixture can drift from the service schema. Keep a small service contract suite or schema-validation job to detect that drift. A fake returning a domain object bypasses serialization entirely.

## Organize execution and cleanup

Keep plain repository tests separate from hosted Compose tests. Use a Robolectric runner only for Android-dependent boundaries such as Android storage behavior. Never hide framework errors with `unitTests.isReturnDefaultValues = true`.

For an `app` module and a test named `ItemRepositoryContractTest`, run:

```shell
./gradlew :app:testDebugUnitTest --tests '*ItemRepositoryContractTest'
```

Use the actual module, variant, and class. Separate live-service integration tests from default local tests so credentials and network availability do not silently change the local suite's meaning.

Use a fresh database or temporary directory per test. Close databases, stop local servers, cancel scopes, and close owned executors. Do not depend on method order or a previous test's login.

`runTest` controls its test scheduler, not every client thread. For real network integration, use the client's bounded request timeout and an explicit completion observation. Do not block a Compose test thread waiting for work that requires that thread to progress.

## Avoid false integration claims

| Anti-pattern | Failure mechanism | Correct approach |
| --- | --- | --- |
| Test only the repository fake | Production serialization and policy never execute | Exercise the real repository or client |
| Check body but not status | Error fallback JSON can resemble success | Validate status and body contract |
| Parse every response as JSON | Empty and HTML responses fail misleadingly | Branch at the response boundary |
| Use production credentials in local tests | Risky writes and nonreproducible state | Isolated test environment and secret injection |
| Reuse mutable clients with changing users | Headers and caches leak across tests | Separate per-test sessions |
| Skip cleanup after a failed assertion | Later cases see stale data | Fixture teardown or `finally` |
| Claim authorization from a hidden UI action | A direct request may still succeed | Test actual service rejection |

## Troubleshoot failures

| Symptom | Observe | Correction |
| --- | --- | --- |
| Connection refused | Allocated port, base URL, server startup | Start the owned server before constructing the client |
| JSON decoding fails | Status, content type, redacted response | Handle empty or error responses before normal decoding |
| Unexpected 401 | Token source and recorded authorization header | Configure the intended session explicitly |
| Passes locally, fails in CI | URL, credentials, schema version, isolated data | Make environment requirements explicit and seed owned data |
| Test never completes | Client timeout, scope ownership, scheduler | Bound network work and advance only owned test scheduling |
| Service data collides | Run ID and created resource IDs | Use unique namespaces and cleanup only owned resources |

## Review checklist

- [ ] The real boundary under test is named.
- [ ] Requests, statuses, and decoded results have appropriate assertions.
- [ ] CRUD and important failure paths are covered.
- [ ] Auth, transport, decoding, and domain errors remain distinct.
- [ ] Every created resource has cleanup even on failure.
- [ ] UI tests retain user-visible outcome assertions.
- [ ] Fakes are not reported as service integration evidence.

## Related guides and sources

- [GraphQL](graphql.md) covers response envelopes and partial data.
- [Network fakes](../advanced/network-fakes.md) covers controlled asynchronous boundaries.
- [When to fake](../architecture/when-to-fake.md) chooses test layers.
- [File transfers](file-transfers.md) covers document and transfer boundaries.
- [OkHttp 4.12.0 MockWebServer](https://github.com/square/okhttp/blob/parent-4.12.0/mockwebserver/README.md) documents the version-scoped server and recorded request API.
- [OkHttp 4.12.0 multipart source](https://github.com/square/okhttp/blob/parent-4.12.0/okhttp/src/main/kotlin/okhttp3/MultipartBody.kt) defines the multipart builder and wire encoding.
- [JSON-java 20240303](https://github.com/stleary/JSON-java/tree/20240303) supplies the standalone JVM JSON implementation.
- [Android data layer](https://developer.android.com/topic/architecture/data-layer) describes repository responsibilities.
- [Testing coroutines](https://developer.android.com/kotlin/coroutines/test) describes schedulers and test dispatchers.
- [Robolectric best practices](https://robolectric.org/best-practices/) covers framework boundaries and leaked threads.
