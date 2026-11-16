# Build deterministic test data

Use this guide for reusable scenario builders, relationships, reproducible generated values, data-driven cases, and repository seeds. Data factories create inputs. They do not replace the action-to-result path that a UI behavior test must exercise.

## Contents

- [Choose the data strategy](#choose-the-data-strategy)
- [Use immutable defaults and explicit overrides](#use-immutable-defaults-and-explicit-overrides)
- [Model traits and relationships](#model-traits-and-relationships)
- [Generate values reproducibly](#generate-values-reproducibly)
- [Run independent data-driven cases](#run-independent-data-driven-cases)
- [Load resource-backed cases](#load-resource-backed-cases)
- [Seed fresh fakes and databases](#seed-fresh-fakes-and-databases)
- [Avoid data anti-patterns](#avoid-data-anti-patterns)
- [Troubleshoot data failures](#troubleshoot-data-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the data strategy

| Requirement | Use | Avoid |
| --- | --- | --- |
| One important input | Literal in the test | Hiding the business value behind a factory |
| Repeated valid domain object | Immutable builder with defaults | Large mutable singleton fixture |
| Named boundary scenario | Named trait or data-class copy | Boolean argument combinations with unclear meaning |
| Several related objects | Builder that preserves identity and invariants | Unrelated random foreign keys |
| Broad input variety | Per-test seeded generator | Global unseeded randomness |
| Shared read-only sample payload | Test resource | Mutable source file reused as a database |
| Async loading and completion | Fresh controlled fake | Reusing a completed deferred |
| External integration records | Run-scoped IDs and cleanup ownership | Timestamp-only uniqueness or shared accounts |

Keep factory defaults valid and boring. Override the value that explains the case in the test itself. A test for an empty name should say `name = ""`, not call an opaque `specialUser()`.

## Use immutable defaults and explicit overrides

The input shape in this illustrative example is an immutable account with a role and explicit creation time. It uses Kotlin and JDK types only:

```kotlin
import java.time.Instant

enum class AccountRole { MEMBER, ADMIN }

data class Account(
	val id: String,
	val name: String,
	val email: String,
	val role: AccountRole,
	val createdAt: Instant,
)

fun account(
	id: String = "member-1",
	name: String = "Morgan",
	email: String = "morgan@example.test",
	role: AccountRole = AccountRole.MEMBER,
	createdAt: Instant = Instant.parse("2025-01-15T12:00:00Z"),
): Account = Account(id, name, email, role, createdAt)
```

A usage fragment makes the case visible:

```kotlin
val administrator = account(id = "admin-1", role = AccountRole.ADMIN)
val blankName = account(name = "")
```

Do not call `Instant.now()` by default. Time-sensitive behavior needs a fixed business time or injected clock. The Compose main clock does not change this timestamp.

Kotlin data-class `copy` is shallow. A model containing a mutable list can still share that list after copying. Prefer immutable collection interfaces plus fresh construction, and do not mutate a collection merely because the property uses `val`.

## Model traits and relationships

Use named valid states instead of a generic override map. This illustrative catalog and order model stores money as integer minor units:

```kotlin
data class Product(
	val id: String,
	val title: String,
	val unitPriceCents: Long,
	val stock: Int,
)

data class OrderLine(val product: Product, val quantity: Int)

data class Order(
	val id: String,
	val accountId: String,
	val lines: List<OrderLine>,
)

fun product(
	id: String = "notebook-1",
	title: String = "Notebook",
	unitPriceCents: Long = 1_250,
	stock: Int = 5,
): Product = Product(id, title, unitPriceCents, stock)

fun soldOutProduct(): Product = product(stock = 0)

fun orderFor(account: Account, lines: List<OrderLine>): Order =
	Order("order-1", account.id, lines.toList())
```

Specify shared identities deliberately:

```kotlin
val owner = account(id = "owner-7")
val notebook = product(id = "notebook-42")
val order = orderFor(owner, listOf(OrderLine(notebook, quantity = 2)))
```

The UI test should assert the required displayed total, such as `25.00` in an explicitly chosen locale, not compute its expected total by calling the same production pricing function. Shared input data is useful. Shared calculation of expected and actual results can hide a pricing defect.

Only generate invalid combinations for a test whose purpose is validation. Do not let a broad factory accidentally create negative quantities or an admin account with an unrelated member session.

Use a builder object with a local counter only when a test truly needs multiple distinct records. Avoid a process-global incrementing counter whose values depend on method order.

## Generate values reproducibly

Most UI scenarios need concrete, readable values rather than a Faker dependency. When generated variety adds coverage, use a generator owned by one test and record the seed.

This complete illustrative factory uses Kotlin's `Random` rather than a third-party API:

```kotlin
import kotlin.random.Random

class AccountSequence(seed: Int) {
	private val random = Random(seed)
	private var nextId = 0

	fun next(): Account {
		val id = "generated-${nextId++}"
		return account(
			id = id,
			name = "Reader ${random.nextInt(1_000)}",
			email = "$id@example.test",
		)
	}
}
```

Construct `AccountSequence(seed = 42)` per test. The local counter guarantees distinct IDs within that sequence. Random names are not a uniqueness guarantee.

Record seed, generator version, and case index when generated data fails. A seed alone may not reproduce results after a generator implementation or dependency changes.

Keep dedicated named cases for long text, Unicode, blank input, and boundary quantities. Random sampling is unlikely to hit every important boundary. See [internationalization](../testing-patterns/i18n.md) for locale and direction cases.

Do not introduce real-looking passwords, personal information, or live image URLs into generated fixtures. A remote avatar request adds an unrelated asynchronous boundary.

## Run independent data-driven cases

JUnit 4's `Parameterized` runner cannot simply replace `RobolectricTestRunner` on a Compose class. If a large parameterized matrix is justified, evaluate Robolectric's parameterized runner support for the pinned version separately. This fixture does not validate it.

For a small UI matrix, use named methods that each call a shared helper once. The helper owns one `setContent` call for that method. This complete illustrative test uses Material3 plus the configured local host:

```kotlin
import androidx.compose.material3.Text
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class AccountLabelTest {
	@get:Rule val rule = createComposeRule()

	@Test fun rendersMemberName() = assertLabel(account(name = "Morgan"))
	@Test fun rendersUnicodeName() = assertLabel(account(name = "Renée"))

	private fun assertLabel(account: Account) {
		rule.setContent { Text(account.name) }
		rule.onNodeWithText(account.name).assertIsDisplayed()
	}
}
```

This is a rendering test. It does not claim to test editing or repository orchestration. An editing test must enter a name through semantics, submit, and assert the saved result.

Do not loop over cases and call `setContent` repeatedly on one rule. Give each UI case an independent test lifecycle. Large pure validation tables usually belong in a non-UI unit test instead.

## Load resource-backed cases

Put portable read-only samples under the configured test resources directory. Do not resolve files relative to the developer's working directory.

This illustrative resource loader uses only JDK and Kotlin APIs:

```kotlin
class CaseResources {
	fun read(name: String): String {
		val stream = requireNotNull(javaClass.getResourceAsStream("/cases/$name")) {
			"Missing test resource: /cases/$name"
		}
		return stream.bufferedReader().use { it.readText() }
	}
}
```

Parse JSON or CSV into a typed case model with the consuming project's chosen parser. Validate required fields, types, and a nonempty case list before generating or executing tests. A malformed resource must fail loudly, not become zero green cases.

Keep case names stable and meaningful. Never derive a shell command, SQL identifier, or output path directly from untrusted case text.

## Seed fresh fakes and databases

Create a new repository fake from immutable seed records for each method. If the fake mutates its list, copy records into its own storage. A shallow copy is insufficient when records themselves contain mutable objects.

For async scenarios, hold a request with a fresh deferred. Assert loading, complete or fail the boundary, and then assert the resulting UI. Preloading the final state proves rendering only.

For a database-backed screen, seed the isolated database before mounting content, close it afterward, and retain its failure evidence when useful. A per-test temporary file or in-memory database is safer than a shared rollback promise across unrelated connections.

For service tests, collect created resource IDs immediately and clean up only those IDs. Use run, worker, and test identity where the service requires globally unique names. A fixed ID is preferable in a fully isolated in-memory fake.

## Avoid data anti-patterns

| Anti-pattern | Failure mechanism | Correction |
| --- | --- | --- |
| Global mutable fixture list | One test changes another's input | Construct fresh storage |
| Unseeded random values | Failure cannot be replayed | Per-test seed and captured case |
| Timestamp-only ID | Parallel collisions and unstable assertions | Local counter or external run namespace |
| Expected total from production function | Same bug affects both sides | Assert independently specified result |
| Huge factory with dozens of options | Case intent disappears | Small domain builders and named states |
| Shared completed response | Loading test starts already finished | Fresh deferred per test |

## Troubleshoot data failures

| Symptom | Observe | Fix |
| --- | --- | --- |
| Passes alone, fails in class | Mutated seeds and global counters | Fresh per-test ownership |
| Locale-dependent amount | Locale, currency, and fixed input | Pin configuration and assert intended format |
| Relationships fail unexpectedly | Record and foreign-key identities | Build related objects together |
| Generated case cannot reproduce | Seed, sequence order, dependency version | Capture all reproduction inputs |
| No cases execute | Parser outcome and discovery | Reject empty or malformed case sets |

## Review checklist

- Inputs that explain the case remain visible in the test.
- Defaults are valid, deterministic, and independent of wall clock.
- Relationships preserve required identity.
- Mutable storage and deferred responses are fresh per test.
- Expected results do not reuse the calculation under test.
- Every data-driven UI case has an independent lifecycle.

## Related guides and sources

- [Fixtures and hooks](fixtures-hooks.md) owns seeded resources and cleanup.
- [Global setup](global-setup.md) covers immutable seed preparation.
- [Forms and validation](../testing-patterns/forms-validation.md) applies boundary cases through user actions.
- [Compose common patterns](https://developer.android.com/develop/ui/compose/testing/common-patterns) describes isolated rendering tests.
- [Robolectric best practices](https://robolectric.org/best-practices/) describes isolation constraints.
