# Own test fixtures and lifecycle hooks

Use this guide to create fresh fakes, install dependencies before activity launch, close test resources, and share setup without sharing mutable UI state. JUnit rules and hooks replace the fixture lifecycle mechanisms of a browser test runner. They do not provide an automatic worker-scoped Compose session.

## Contents

- [Choose a lifetime](#choose-a-lifetime)
- [Create fresh per-test fixtures](#create-fresh-per-test-fixtures)
- [Order setup before activity launch](#order-setup-before-activity-launch)
- [Manage resources with rules](#manage-resources-with-rules)
- [Seed sessions and databases](#seed-sessions-and-databases)
- [Collect failure diagnostics](#collect-failure-diagnostics)
- [Keep parallel workers independent](#keep-parallel-workers-independent)
- [Troubleshoot lifecycle failures](#troubleshoot-lifecycle-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose a lifetime

| Resource | Lifetime | Owner |
| --- | --- | --- |
| Compose rule, composition, activity | Per test | Compose rule |
| Deferred response, mutable state, fake repository | Per test | Test instance or scenario factory |
| Robot | Per test | Test, using that test's rule |
| Temporary file or database connection | Per test unless explicitly immutable | Rule or `try/finally` owner |
| Immutable JSON seed file | Build or suite input | Build task or checked-in test resource |
| Live service account | Integration-test namespace | External job with explicit cleanup |
| Application-wide dependency replacement | Narrow ordered rule | Test that installs and restores it |

JUnit 4 creates a fresh test instance for each test method. Instance properties can therefore hold per-test fakes. Companion objects, static fields, singletons, and files do not acquire per-test isolation from that rule.

Use `@Before` for repeated per-test initialization and `@After` for corresponding cleanup. Use `@BeforeClass` and `@AfterClass` only for suitable class-wide work. Neither means once across every Gradle worker, module, variant, or CI shard.

## Create fresh per-test fixtures

The following complete illustrative test uses canonical `MessagePanel` and `Sender`, available in this repository's test source set. It needs Compose test, Material3, coroutines, JUnit 4, and Robolectric dependencies. It is not another fixture-compiled file.

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import fixture.MessagePanel
import fixture.Sender
import kotlinx.coroutines.CompletableDeferred
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

private class SenderFixture : Sender {
	private val result = CompletableDeferred<String>()
	override suspend fun send(message: String): String = result.await()
	fun complete(receipt: String) {
		check(result.complete(receipt))
	}
}

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class MessageFixtureTest {
	@get:Rule val rule = createComposeRule()
	private val sender = SenderFixture()

	@Test fun deliveryRendersReceipt() {
		rule.setContent { MessagePanel(sender) }
		rule.onNodeWithText("Message").performTextInput("Fresh")
		rule.onNodeWithText("Send").performClick()
		rule.onNodeWithText("Sending").assertIsDisplayed()
		rule.runOnIdle { sender.complete("Delivered Fresh") }
		rule.onNodeWithText("Delivered Fresh").assertIsDisplayed()
	}
}
```

The rule disposes composition-owned work. If the fixture creates an independent coroutine scope, executor, or thread, the fixture must cancel or shut it down. Robolectric does not clean up rogue threads for you.

Keep options as immutable scenario inputs. Prefer `scenario(role = Admin)` or a named data-class copy to a mutable global `defaultUser` overridden by different test classes.

A factory can build a scenario on demand. Unlike Playwright's dependency injection, an ordinary Kotlin property initializer is eager. Do not assume expensive fixtures are lazy unless you deliberately implement that behavior.

## Order setup before activity launch

An Android Compose rule can launch its activity before `@Before` runs. If the activity reads its dependencies in `onCreate`, installing a replacement in `@Before` is too late.

This illustrative declaration uses an application-defined `DependencyRule`, whose `before` installs a test graph and whose `after` restores it. `MainActivity` is the application's declared activity. Those surrounding types must exist in the consuming project.

```kotlin
import androidx.compose.ui.test.junit4.v2.createAndroidComposeRule
import org.junit.Rule
import org.junit.rules.RuleChain

private val dependencies = DependencyRule()
val compose = createAndroidComposeRule<MainActivity>()

@get:Rule
val rules: RuleChain = RuleChain.outerRule(dependencies).around(compose)
```

The outer dependency rule enters first. The Compose rule then launches the activity. Teardown unwinds in reverse order, so activity disposal happens before dependency restoration.

Expose only the chain as the JUnit rule. Do not annotate the inner `compose` property with another `@Rule`, which would apply it twice.

If the activity owns `setContent`, do not call it again from the test. For a test-owned component mount, use `createComposeRule` and install local dependencies before that one `setContent` call.

## Manage resources with rules

Use a rule when cleanup must surround a whole test and occur after failures. This complete illustrative resource rule owns a JDK executor:

```kotlin
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import org.junit.rules.ExternalResource

class ExecutorFixture : ExternalResource() {
	lateinit var executor: ExecutorService
		private set

	override fun before() {
		executor = Executors.newSingleThreadExecutor()
	}

	override fun after() {
		executor.shutdownNow()
		check(executor.awaitTermination(2, TimeUnit.SECONDS)) {
			"Test executor did not terminate"
		}
	}
}
```

Use it only for code that actually needs an independent executor. Do not add one to simulate a delay that a controllable fake can express more directly. Resource setup that partially succeeds must also release partial acquisitions when later setup fails.

`try/finally` or Kotlin `use` is often smaller for a resource used by one test. Register idling resources before starting their work and unregister after composition no longer uses them. Do not let cleanup erase the original failure's diagnostics.

## Seed sessions and databases

For a local signed-in screen test, seed a fresh session repository with an explicit user and role. Do not log in through a real identity provider in every UI test. Keep a separate sign-in behavior test that drives the login UI and checks its visible result.

A fake session proves client rendering and branching. It does not prove token validity, OAuth redirects, backend authorization, or security across users.

For database-backed local behavior, create an isolated database or unique temporary path for each test. Close connections in cleanup. Seed only the records relevant to the test before mounting the UI.

Do not promise transaction rollback isolation unless all application operations use the same transaction and connection. UI work on another connection can commit outside a test's rollback. An isolated in-memory database or per-test file is often clearer. See [test data](test-data.md) for builders and [global setup](global-setup.md) for immutable migration inputs.

## Collect failure diagnostics

Use JUnit failure hooks only for observations available at that lifecycle point. A watcher outside a Compose rule can run after its roots have been disposed. A watcher inside can run while content is available, but its precise ordering must be intentional.

For a focused selector diagnosis, print the tree near the failing assertion and rethrow the original error. Do not turn the failure into a passing diagnostic test. Keep exception logs and JUnit results regardless of whether tree capture succeeds.

Capture the method name, selected SDK, qualifier, variant, and original matcher. Avoid attaching real credentials or private user data.

## Keep parallel workers independent

Shared mutable backend records are not safe just because each Compose rule is fresh. For separate integration tests, use a run identifier plus `org.gradle.test.worker` plus a per-test identifier to namespace external data. A worker number alone can repeat across CI jobs.

For local fake-only tests, deterministic fixed IDs are safe when every fake is fresh. Do not add randomness merely to distinguish objects that never share storage.

Anti-patterns include a companion-object `CompletableDeferred`, a shared mutable database snapshot, and a singleton robot holding yesterday's rule. Replace them with per-test construction. Serial execution can help diagnose a race, but it does not repair ownership.

## Troubleshoot lifecycle failures

| Symptom | Observe | Fix |
| --- | --- | --- |
| Real dependency used at startup | Rule ordering and `onCreate` reads | Install graph before activity launch |
| `setContent` called twice | Activity and test both mount | Choose one content owner |
| Loading disappears in later tests | Reused completed deferred | Construct a fresh fake |
| Process hangs after tests | Executors, threads, test-owned scopes | Cancel, close, and join owned work |
| Database test passes alone | Shared path or unclosed connection | Isolate storage and cleanup |
| Tree capture finds no root | Watcher ran after disposal | Change observation point without hiding failure |

## Review checklist

- Every mutable fixture has a per-test owner.
- Setup precedes the first consumer, including activity startup.
- Rules unwind resources in the intended order.
- Cleanup handles assertion failures and partial setup.
- Fake session and database claims stay within their tested boundary.
- A method passes alone and in its containing class.

## Related guides and sources

- [Screen robots](screen-robots.md) separates interactions from fixture ownership.
- [Isolation reference](../references/isolation.md) lists cleanup responsibilities.
- [Robolectric best practices](https://robolectric.org/best-practices/) warns about shared state and rogue threads.
- [Compose common patterns](https://developer.android.com/develop/ui/compose/testing/common-patterns) documents host and isolated content patterns.
- [JUnit 4 rules](https://junit.org/junit4/javadoc/4.13.2/org/junit/rules/RuleChain.html) defines explicit rule ordering.
