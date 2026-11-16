# Test GraphQL clients and repository integration

Use this guide for GraphQL queries, variables, mutations, authentication, and response mapping in an Android app. Test the real client and repository boundary on the JVM. Use Compose with controlled repository results to test how those results appear to users. A fake does not prove GraphQL transport or service enforcement.

## Table of contents

- [Choose the test boundary](#choose-the-test-boundary)
- [Keep HTTP and GraphQL outcomes distinct](#keep-http-and-graphql-outcomes-distinct)
- [Test a query with variables](#test-a-query-with-variables)
- [Run a complete local GraphQL contract](#run-a-complete-local-graphql-contract)
- [Test mutations and read-back](#test-mutations-and-read-back)
- [Exercise response envelopes](#exercise-response-envelopes)
- [Test repository mapping](#test-repository-mapping)
- [Test validation and authorization](#test-validation-and-authorization)
- [Build authenticated fixtures and helpers](#build-authenticated-fixtures-and-helpers)
- [Connect results to Compose](#connect-results-to-compose)
- [Keep caches and scheduling isolated](#keep-caches-and-scheduling-isolated)
- [Avoid false-green GraphQL tests](#avoid-false-green-graphql-tests)
- [Troubleshoot failures](#troubleshoot-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the test boundary

| Claim | Execute | Observe |
| --- | --- | --- |
| Variables and operation name are serialized correctly | Production GraphQL client against a local HTTP server | Recorded request body and headers |
| GraphQL error metadata survives decoding | Production response decoder | Data, errors, path, and relevant extensions |
| Partial results map to the right domain state | Real repository with controlled client response | Usable data plus recoverable warning |
| A mutation updates cached query results | Real client and fresh normalized cache | Subsequent observed query state |
| The service denies an operation | Dedicated service integration suite | Actual denied response for the test identity |
| A screen handles denial | Compose with controlled repository denial | User-facing permission message and safe actions |
| A real device sends authenticated operations | Device integration suite | Transport result and screen outcome |

Most client and mapping tests need neither Compose nor Robolectric. Use Robolectric only when the actual integration needs Android facilities. Hosted UI tests remain in `src/test` with the runner, resources, and manifest host from [setup](../references/setup.md).

## Keep HTTP and GraphQL outcomes distinct

An HTTP 200 response does not mean the operation succeeded. GraphQL responses may contain `data`, `errors`, or both. Non-200 responses, transport exceptions, malformed envelopes, and GraphQL execution errors are different cases.

| Observation | Interpretation to test |
| --- | --- |
| Successful HTTP response, data, no errors | Complete operation result |
| Successful HTTP response, data and errors | Partial execution result, subject to app policy |
| Successful HTTP response, null data and errors | Operation failed or non-null propagation removed usable data |
| Response with errors but no data | Often a request or validation failure before execution |
| Unsuccessful HTTP response | HTTP-layer failure, possibly with a GraphQL body |
| No HTTP response | Transport failure or cancellation |
| Invalid JSON or invalid envelope | Protocol or decoding failure |

Do not teach that GraphQL always returns HTTP 200 on error. Status behavior depends on response media type, failure phase, and server contract. Check both the HTTP result and decoded GraphQL envelope.

Error `extensions.code` values such as `BAD_USER_INPUT` and `UNAUTHENTICATED` are service conventions, not universal GraphQL enums. Test your schema and service's documented values.

## Test a query with variables

Use the app's generated operations when the project has them. Otherwise keep shared documents near the client contract rather than duplicating strings across UI tests.

An illustrative wire request for a local HTTP-server test is:

```json
{
  "operationName": "FetchItem",
  "query": "query FetchItem($id: ID!) { item(id: $id) { id title reviews { id rating } } }",
  "variables": { "id": "101" }
}
```

Run the production client with ID `101`, then inspect the recorded request. Assert the operation name, variable key `id`, variable value, endpoint, method, and authentication header required by your service.

Prefer semantic JSON assertions to exact byte-string equality. Whitespace and object-key ordering are not operation behavior. Generated clients may send a persisted-query hash instead of a full document. Assert the configured protocol, including fallback behavior when applicable.

Script a successful response:

```json
{
  "data": {
    "item": {
      "id": "101",
      "title": "Widget",
      "reviews": [{ "id": "r1", "rating": 4 }]
    }
  }
}
```

Assert that the real decoder and repository return item `101`, title `Widget`, and the expected review. Assert that no unexpected GraphQL errors were discarded. Use the client's actual response type, not a hand-built domain fake, when the claim includes decoding.

Queries may use GET when the server and client support it. Mutations use POST in the usual GraphQL-over-HTTP workflow. Do not accept a test that accidentally performs a mutation through a cacheable query request.

## Run a complete local GraphQL contract

The request shape is `FetchItem(id)`. The decoded envelope retains nullable `FetchItemData`, nullable item and reviews, and a list of errors with typed path segments and an optional service code. The repository maps this envelope to `ItemOutcome` without throwing away partial data.

This illustrative, operation-specific client uses OkHttp **4.12.0**, not a generated GraphQL client. It has no schema compiler or normalized cache. Assume this service schema:

```graphql
type Query { item(id: ID!): Item }
type Item { id: ID!, title: String!, reviews: [Review!] }
type Review { id: ID!, rating: Int! }
```

`reviews` is nullable, so a failed reviews resolver may leave the item intact with `reviews: null`. If the actual schema declares `reviews: [Review!]!`, use its null propagation rules instead. The local server scripts responses and does not execute or validate this schema.

Use a standalone Kotlin/JVM module with Kotlin 2.2.10, JDK 17, `mavenCentral()`, and these version-scoped dependencies:

```kotlin
dependencies {
	testImplementation("junit:junit:4.13.2")
	testImplementation("com.squareup.okhttp3:okhttp:4.12.0")
	testImplementation("com.squareup.okhttp3:mockwebserver:4.12.0")
	testImplementation("org.json:json:20240303")
}
```

Put this complete block in `src/test/kotlin/GraphQlHttpContractTest.kt`. It needs no Compose rule, activity, coroutine fixture, undefined mapper, or generated client. For Android's `org.json` under Robolectric, use the dependency and runner variation in [repository contracts](repository-contracts.md#complete-local-http-contract) instead of the standalone JSON dependency.

```kotlin
import java.io.Closeable
import java.io.IOException
import java.util.concurrent.TimeUnit
import okhttp3.HttpUrl
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Test

data class FetchItem(val id: String)
data class Review(val id: String, val rating: Int)
data class GraphItem(val id: String, val title: String, val reviews: List<Review>?)
data class FetchItemData(val item: GraphItem?)
sealed interface ErrorPath {
	data class Field(val name: String) : ErrorPath
	data class Index(val value: Int) : ErrorPath
}
data class GraphError(val message: String, val path: List<ErrorPath>, val code: String?)
data class FetchItemEnvelope(val data: FetchItemData?, val errors: List<GraphError>)
class GraphHttpFailure(val status: Int) : IOException("HTTP $status")

class ItemGraphClient(private val baseUrl: HttpUrl, private val token: String) : Closeable {
	companion object {
		val QUERY = "query FetchItem(${'$'}id: ID!) { item(id: ${'$'}id) { id title reviews { id rating } } }"
	}
	private val http = OkHttpClient.Builder().callTimeout(5, TimeUnit.SECONDS)
		.followRedirects(false).retryOnConnectionFailure(false).build()

	fun fetch(input: FetchItem): FetchItemEnvelope {
		val body = JSONObject().put("operationName", "FetchItem").put("query", QUERY)
			.put("variables", JSONObject().put("id", input.id))
		val request = Request.Builder().url(requireNotNull(baseUrl.resolve("graphql")))
			.header("Authorization", "Bearer $token").header("Accept", "application/json")
			.post(body.toString().toRequestBody("application/json".toMediaType())).build()
		return http.newCall(request).execute().use { response ->
			if (!response.isSuccessful) throw GraphHttpFailure(response.code)
			if (response.body?.contentType()?.subtype != "json") throw IOException("Expected JSON")
			decode(JSONObject(requireNotNull(response.body).string()))
		}
	}

	private fun decode(root: JSONObject): FetchItemEnvelope {
		require(root.has("data") || root.has("errors")) { "Missing GraphQL envelope" }
		val errors = if (!root.has("errors")) emptyList() else {
			val values = root.getJSONArray("errors")
			require(values.length() > 0) { "Empty errors array" }
			List(values.length()) { index ->
				val error = values.getJSONObject(index)
				val path = if (!error.has("path")) emptyList() else {
					val segments = error.getJSONArray("path")
					List(segments.length()) { position ->
						when (val segment = segments.get(position)) {
							is String -> ErrorPath.Field(segment)
							is Int -> ErrorPath.Index(segment)
							else -> throw IOException("Invalid GraphQL error path")
						}
					}
				}
				val extensions = if (error.isNull("extensions")) null else error.getJSONObject("extensions")
				val code = if (extensions == null || extensions.isNull("code")) null else extensions.getString("code")
				GraphError(error.getString("message"), path, code)
			}
		}
		val data = if (root.isNull("data")) null else {
			val value = root.getJSONObject("data")
			val rawItem = value.get("item")
			val item = if (rawItem == JSONObject.NULL) null else {
				val json = value.getJSONObject("item")
				val rawReviews = json.get("reviews")
				val reviews = if (rawReviews == JSONObject.NULL) null else {
					val values = json.getJSONArray("reviews")
					List(values.length()) { index ->
						val review = values.getJSONObject(index)
						Review(review.getString("id"), review.getInt("rating"))
					}
				}
				GraphItem(json.getString("id"), json.getString("title"), reviews)
			}
			FetchItemData(item)
		}
		require(data != null || errors.isNotEmpty()) { "Null data without errors" }
		return FetchItemEnvelope(data, errors)
	}

	override fun close() {
		http.connectionPool.evictAll()
		http.dispatcher.executorService.shutdown()
	}
}

sealed interface ItemOutcome {
	data class Complete(val id: String, val title: String) : ItemOutcome
	data class Partial(val id: String, val title: String, val warning: String) : ItemOutcome
	data class Rejected(val code: String?) : ItemOutcome
	data object Unavailable : ItemOutcome
}

class GraphItemRepository(private val client: ItemGraphClient) {
	fun fetchItem(id: String): ItemOutcome = map(client.fetch(FetchItem(id)))

	fun map(envelope: FetchItemEnvelope): ItemOutcome {
		val item = envelope.data?.item
		return when {
			item != null && envelope.errors.isEmpty() -> ItemOutcome.Complete(item.id, item.title)
			item != null -> ItemOutcome.Partial(item.id, item.title, "Some item details are unavailable")
			envelope.errors.isNotEmpty() -> ItemOutcome.Rejected(envelope.errors.first().code)
			else -> ItemOutcome.Unavailable
		}
	}
}

class GraphQlHttpContractTest {
	@Test fun partialReviewFailureKeepsTheItemUsable() {
		MockWebServer().use { server ->
			server.start()
			val partial = """
				{
				  "data": { "item": { "id": "101", "title": "Widget", "reviews": null } },
				  "errors": [{ "message": "Reviews unavailable", "path": ["item", "reviews"],
				    "extensions": { "code": "REVIEWS_UNAVAILABLE" } }]
				}
			""".trimIndent()
			server.enqueue(MockResponse().setHeader("Content-Type", "application/json").setBody(partial))
			ItemGraphClient(server.url("/"), "local-token").use { client ->
				val envelope = client.fetch(FetchItem("101"))
				assertEquals(GraphItem("101", "Widget", null), envelope.data?.item)
				assertNull(envelope.data?.item?.reviews)
				assertEquals(listOf(GraphError("Reviews unavailable",
					listOf(ErrorPath.Field("item"), ErrorPath.Field("reviews")), "REVIEWS_UNAVAILABLE")), envelope.errors)
				assertEquals(ItemOutcome.Partial("101", "Widget", "Some item details are unavailable"),
					GraphItemRepository(client).map(envelope))
				val request = requireNotNull(server.takeRequest(1, TimeUnit.SECONDS))
				assertEquals("POST", request.method)
				assertEquals("/graphql", request.path)
				assertEquals("Bearer local-token", request.getHeader("Authorization"))
				assertEquals("application/json", request.getHeader("Accept"))
				assertEquals("application/json; charset=utf-8", request.getHeader("Content-Type"))
				val body = JSONObject(request.body.readUtf8())
				assertEquals("FetchItem", body.getString("operationName"))
				assertEquals(ItemGraphClient.QUERY, body.getString("query"))
				assertEquals(1, body.getJSONObject("variables").length())
				assertEquals("101", body.getJSONObject("variables").getString("id"))
			}
		}
	}

	@Test fun httpFailureIsNotMistakenForGraphExecutionFailure() {
		MockWebServer().use { server ->
			server.start()
			server.enqueue(MockResponse().setResponseCode(503)
				.setHeader("Content-Type", "text/html").setBody("<h1>Unavailable</h1>"))
			ItemGraphClient(server.url("/"), "local-token").use { client ->
				val error = assertThrows(GraphHttpFailure::class.java) { client.fetch(FetchItem("101")) }
				assertEquals(503, error.status)
				assertEquals("/graphql", requireNotNull(server.takeRequest(1, TimeUnit.SECONDS)).path)
			}
		}
	}
}
```

Run `./gradlew test --tests '*GraphQlHttpContractTest'` in that standalone module. This contract executes real HTTP and its defined decoder and mapper. It is not Compose UI evidence or proof that a production schema accepts the document. To cover an app, replace the illustrative client and repository with the actual implementation.

The client accepts this service's `application/json` responses. It checks HTTP failure before JSON parsing and deliberately retains errors for successful HTTP responses. A service using `application/graphql-response+json` needs that media type in both negotiation and validation, with its documented status policy. This small decoder preserves only the fields modeled above, not error locations or arbitrary extensions. Use generated operation types and the production decoder when the app has them.

`use` closes response bodies, then owned client resources, then the server even after assertion failures. Close failures become suppressed exceptions rather than replacing the assertion. Calls have a five-second real timeout and recorded-request waits are bounded. These timeouts do not use Compose or coroutine virtual clocks.

## Test mutations and read-back

For a create mutation, assert the input object's shape and types. Distinguish omitted fields from explicit null when the schema gives them different meanings.

```json
{
  "operationName": "AddItem",
  "query": "mutation AddItem($input: ItemInput!) { addItem(input: $input) { id title status } }",
  "variables": {
    "input": { "title": "New widget", "status": "DRAFT" }
  }
}
```

In a local client test, queue a known created ID and assert the mapped result. In service integration, use the actual returned ID for a subsequent query and cleanup. Never hardcode a shared mutable item ID.

For an update, query the initial item, execute the mutation, and read back the result. If normalized caching is part of the claim, use the real cache and production cache policy. Supplying updated query data directly through a fake cannot prove invalidation.

For optimistic updates, hold the mutation pending, observe the optimistic state, then fail the mutation. Assert rollback and the visible error. Add a success case that reconciles a temporary ID with the server ID if the app supports that behavior.

## Exercise response envelopes

Keep JSON fixtures for distinct response shapes. Pass them through the actual client decoder, then assert the public response or repository result.

A partial-data fixture can retain the item while a review resolver fails:

```json
{
  "data": {
    "item": { "id": "101", "title": "Widget", "reviews": null }
  },
  "errors": [
    {
      "message": "Reviews unavailable",
      "path": ["item", "reviews"],
      "extensions": { "code": "REVIEWS_UNAVAILABLE" }
    }
  ]
}
```

This fixture assumes `reviews` is nullable in the operation's schema. If a non-null field fails, null propagation can remove its parent or all usable data. Use fixtures consistent with the actual generated schema.

A request validation fixture has errors and no executed data:

```json
{
  "errors": [
    {
      "message": "Variable input is invalid",
      "extensions": { "code": "BAD_USER_INPUT" }
    }
  ]
}
```

Keep this case separate from a valid mutation whose payload contains business validation fields such as `userErrors`. Some schemas report domain rejection in `data` without a top-level GraphQL error. Test that schema contract explicitly.

Include null data with errors, malformed JSON, a missing required response field, and a transport failure. Do not convert every failure into `emptyList()` or a missing item.

## Test repository mapping

The [complete contract](#run-a-complete-local-graphql-contract) defines `ItemOutcome` and `GraphItemRepository.map` together. Its partial-data test passes the actual HTTP-decoded envelope into that mapper and asserts the retained item and safe warning. There is no undefined fixture helper.

This illustrative policy retains any usable item with a warning when errors coexist. It maps errors without an item to `Rejected` and an error-free missing item to `Unavailable`. A real app may need a separate not-found result or code-specific rejection policy. Test those distinctions in the production mapper rather than adopting this policy silently.

The warning is app-controlled. Do not display arbitrary resolver exception text to users or put access tokens in assertion output.

A helper that returns only `data` makes it impossible for this test to detect discarded errors. Preserve the full envelope until the repository applies its explicit policy.

## Test validation and authorization

For variable validation, test wrong variable names, omitted required input, null required input, and incompatible scalar values at the real client or service layer. Generated Kotlin types prevent some invalid calls, but they do not prove server validation or custom scalar behavior.

For authorization, test unauthenticated and authenticated-but-forbidden identities separately. An unauthenticated response may be HTTP 401 or a GraphQL error under the service's contract. Forbidden fields may coexist with usable public data.

In local client tests, script the response and assert the mapping. In service integration, execute the actual protected operation with dedicated test identities and assert denial. Do not infer protection from an admin button being hidden.

For mutation rejection, assert no resource was created or changed through a subsequent read in the service integration suite. A returned error message alone may coexist with an unintended side effect.

## Build authenticated fixtures and helpers

Construct one client per test session identity with an explicit endpoint and token provider. Use separate admin and ordinary-user fixtures rather than mutating shared headers.

If login itself is a GraphQL mutation, check HTTP status, GraphQL errors, and the presence of the expected token before constructing the authenticated client. Do not treat `data.login == null` as an empty authenticated session.

A useful operation helper centralizes endpoint and headers, retains status and envelope, and adds redacted diagnostic context. It must not assert success unconditionally because error-path tests need to inspect failures.

Avoid a generic unchecked cast that promises `T` while decoding arbitrary JSON. Use generated operation types or the production decoder. Keep operation names in failure reports so errors from a shared `/graphql` endpoint remain identifiable.

## Connect results to Compose

Test rendering and orchestration at their actual boundaries:

1. Start the real screen with a controlled repository awaiting a result.
2. Assert loading without completing the result.
3. Complete with a partial item result.
4. Assert **Widget** remains visible and the recoverable reviews warning appears.
5. In separate cases, complete with rejection or transport unavailability and assert the appropriate user-facing state.

If you directly pass `ItemOutcome.Partial` into a stateless composable, name the test as rendering only. The real client and repository integration tests above establish response decoding and mapping.

Use the compiled [message panel example](../examples/FixtureUiTest.kt) for pending fake completion and bounded UI observation. It demonstrates synchronization, not a GraphQL implementation.

## Keep caches and scheduling isolated

Create a fresh client cache, token provider, HTTP response script, and repository state per test. Close owned network resources and cancel watchers in teardown. A previous query result must not satisfy a later test before its scripted response is consumed.

Separate cache-first, network-only, and cache-and-network cases when those policies are used. Assert the expected sequence of public results instead of relying on a single final item value.

Use `runTest` only for coroutine work it controls. Client network threads and Compose clocks may have different owners. Do not advance the Compose clock to complete a network request. Bound real request timeouts and explicitly release local scripted responses.

## Avoid false-green GraphQL tests

| Anti-pattern | Failure mechanism | Correction |
| --- | --- | --- |
| Assert HTTP success only | Resolver errors may accompany HTTP 200 | Inspect status, data, and errors |
| Discard errors in a generic helper | Partial data silently looks complete | Preserve the envelope until mapping |
| Treat all nulls as not found | Authorization or null propagation may be responsible | Check errors and schema nullability |
| Mock a repository and claim GraphQL coverage | Wire protocol and decoding never execute | Add real client and repository tests |
| Match only the `/graphql` URL | Every operation uses that endpoint | Match operation identity and variables |
| Share normalized caches | Old data can satisfy later assertions | Fresh cache and watchers per test |

## Troubleshoot failures

| Symptom | Observe | Correction |
| --- | --- | --- |
| HTTP 200 but missing item | Envelope errors, error path, nullability | Apply the app's partial or failure policy |
| Cannot query field | Operation document and schema version | Refresh or correct the operation against the actual schema |
| Variables ignored | Recorded keys, operation definitions, scalar encoding | Match case-sensitive variable names and types |
| Mutation passes but later query is stale | Cache IDs, policy, watcher lifecycle | Test and repair cache update or invalidation |
| Auth test unexpectedly succeeds | Actual token and cache source | Use the intended identity and force the appropriate network path |
| Test hangs after result | Active watchers and owned scopes | Cancel subscriptions and close fixture resources |

## Review checklist

- [ ] Status, transport failure, and GraphQL execution errors remain distinct.
- [ ] Queries assert operation identity and variables.
- [ ] Mutations assert returned data and read-back where relevant.
- [ ] Partial data and null propagation have schema-correct fixtures.
- [ ] Authorization mapping and actual service enforcement are separate tests.
- [ ] Helpers preserve response envelopes and redact secrets.
- [ ] Caches, watchers, and session state are isolated.

## Related guides and sources

- [Repository contracts](repository-contracts.md) covers HTTP fixtures and cleanup.
- [Network fakes](../advanced/network-fakes.md) covers controlled responses.
- [Error testing](../debugging/error-testing.md) covers user-facing failure behavior.
- [OkHttp 4.12.0 MockWebServer](https://github.com/square/okhttp/blob/parent-4.12.0/mockwebserver/README.md) documents the pinned local-server API.
- [JSON-java 20240303](https://github.com/stleary/JSON-java/tree/20240303) supplies the standalone JVM decoder.
- [GraphQL response documentation](https://graphql.org/learn/response/) explains data, errors, and partial results.
- [GraphQL over HTTP](https://graphql.github.io/graphql-over-http/draft/) defines request and response transport considerations.
- [Compose synchronization](https://developer.android.com/develop/ui/compose/testing/synchronization) explains the local UI boundary.
