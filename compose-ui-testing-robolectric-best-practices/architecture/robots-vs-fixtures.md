# Organize reusable test code with robots and fixtures

Use this guide when Compose tests repeat user actions, resource setup, or data construction. It covers Android local tests in `src/test` with Robolectric. A robot describes UI intent. A fixture owns resources. A helper transforms data without owning a lifecycle.

## Table of contents

- [Choose the smallest reusable unit](#choose-the-smallest-reusable-unit)
- [Keep robots focused on user intent](#keep-robots-focused-on-user-intent)
- [Give fixtures explicit ownership](#give-fixtures-explicit-ownership)
- [Keep data helpers pure](#keep-data-helpers-pure)
- [Combine the patterns](#combine-the-patterns)
- [Avoid hidden lifecycle and state](#avoid-hidden-lifecycle-and-state)
- [Troubleshoot the abstraction](#troubleshoot-the-abstraction)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the smallest reusable unit

| Repeated responsibility | Use | Keep out |
| --- | --- | --- |
| A short, unique action | Inline Compose APIs | A one-method abstraction that only renames `performClick` |
| A meaningful flow reused across tests | Screen or component robot | Repository creation, global configuration, activity launch |
| A resource with setup and cleanup | JUnit rule or explicit fixture | UI navigation hidden in its constructor |
| Fresh in-memory fake with no cleanup | A local value or test instance field | A singleton shared across tests |
| Data construction or formatting | Pure Kotlin function | Counters, files, network, mutable caches |
| Several resources with ordered setup | Explicit JUnit rule ordering | Assumptions about field declaration order |

Start inline. Extract a robot when repetition obscures the behavior under test. Do not treat the upstream guide's interaction counts as Android rules. A two-action flow with difficult semantics scoping can earn a robot sooner than ten straightforward assertions used once.

Use this selection sequence:

1. If the code acquires a resource, identify its cleanup owner first.
2. If the code interacts with semantics, keep it beside the screen or component it describes.
3. If the code only constructs values, make it a function.
4. If none of those applies, keep the code in the test until a real responsibility emerges.

JUnit 4 rules are not Playwright's lazy dependency-injected fixtures. An instance field initializes for each JUnit test instance, and a rule wraps test evaluation. Make dependencies and order visible.

## Keep robots focused on user intent

The data shape here is a message string and a rendered receipt. The robot receives a `ComposeContentTestRule`; it does not create one. It queries semantics through that rule and leaves ownership of content to the test.

This illustrative robot uses the `MessagePanel` contract from the [canonical example](../examples/FixtureUi.kt). It needs `ui-test-junit4` and the imports below. The example is not a separately compiled fixture source.

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.ComposeContentTestRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput

class MessageRobot(private val compose: ComposeContentTestRule) {
	fun send(message: String) {
		compose.onNodeWithText("Message").performTextInput(message)
		compose.onNodeWithText("Send").performClick()
	}

	fun assertSending() {
		compose.onNodeWithText("Sending").assertIsDisplayed()
	}

	fun assertReceipt(receipt: String) {
		compose.onNodeWithText(receipt).assertIsDisplayed()
		compose.onNodeWithText("Sending").assertDoesNotExist()
	}
}
```

The test still tells the story. The following fragment assumes the canonical `MessagePanel`, a fresh controllable sender, and a configured Compose rule. `ControlledSender` is private in the canonical test, so create a test-local equivalent rather than importing it.

```kotlin
val sender = ControlledSender()
compose.setContent { MessagePanel(sender) }
val messages = MessageRobot(compose)

messages.send("Hello")
messages.assertSending()
compose.runOnIdle { sender.complete("Delivered Hello") }
messages.assertReceipt("Delivered Hello")
```

Keep the release of the fake visible in the test. A robot method named `sendAndWaitForSuccess` that also completes the sender would supply the outcome it claims to observe.

Prefer methods such as `send`, `openDraft`, or `confirmArchive`. Avoid a generic `click(name)` method. Generic methods erase which screen contract the robot owns without making the test shorter.

Use a component robot when the same component appears on several screens. Scope its matchers to a stable group identity. Do not build a hierarchy of base robots just to share a rule reference.

Requery through `SemanticsNodeInteraction` when acting. Do not retain fetched `SemanticsNode` snapshots across recomposition or navigation. A cached node's properties describe the earlier tree, not necessarily the current UI.

## Give fixtures explicit ownership

A fresh fake can be an ordinary local value. A file, executor, database, or test-owned coroutine scope needs cleanup even if the assertion fails.

The following complete illustrative fixture uses JUnit 4's `ExternalResource` and Java's `ExecutorService`. It owns only its executor. It does not promise that cancelling a running task stops arbitrary production code.

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

If application setup depends on the executor before its activity launches, order the rules explicitly. This fragment assumes Compose UI 1.12.1 and an otherwise configured Robolectric test class.

```kotlin
import androidx.compose.ui.test.junit4.v2.createComposeRule
import org.junit.Rule
import org.junit.rules.RuleChain

private val executorFixture = ExecutorFixture()
private val compose = createComposeRule()

@get:Rule
val rules: RuleChain = RuleChain.outerRule(executorFixture).around(compose)
```

The outer fixture starts first and tears down last. This example uses a test-owned composition, mounted later with one `compose.setContent` call. When a real activity sets its own content, do not have the robot or fixture call `setContent` again.

If setup allocates several resources and fails halfway, release the already allocated resources before propagating the setup error. Do not assume a teardown callback can clean a resource that setup never successfully published.

Use JUnit's `TemporaryFolder` for test files rather than a hard-coded shared directory. Create a database per test when mutation is in scope. Install dependency overrides before the consumer starts and restore them after disposal.

## Keep data helpers pure

A helper returns a new value on every call. It does not reserve accounts or mutate a shared counter.

```kotlin
data class MessageDraft(val text: String, val recipient: String)

fun draft(
	text: String = "Hello",
	recipient: String = "reader@example.test",
): MessageDraft = MessageDraft(text, recipient)
```

This illustrative Kotlin helper requires no Android APIs. Fixed data makes local in-memory tests reproducible. Unique IDs are needed only when tests share an external namespace. If they do, include a run identifier and clean up exactly the records that run creates.

Do not use the production price formatter as the expected-value generator in a test of that formatter. Supply an independently chosen expected string. Otherwise the same defect can appear on both sides of the assertion.

## Combine the patterns

An example layout in an Android module is:

```text
src/test/kotlin/example/messages/
  MessagePanelTest.kt
  MessageRobot.kt
  ControlledSender.kt
  MessageData.kt
src/test/kotlin/example/support/
  ExecutorFixture.kt
```

Keep feature-specific helpers beside their tests. Move a helper into `support` only when several features use its contract.

| Owner | Responsibility |
| --- | --- |
| Test | Scenario, initial data, action order, expected visible outcome |
| Robot | Screen-specific semantics queries and user actions |
| Fixture | Acquisition, publication, teardown |
| Fake | Controlled boundary behavior and request observations |
| Helper | Pure value construction |

A robot does not automatically improve synchronization. Compose actions and assertions synchronize known work. They do not retry arbitrary business assertions. Keep a controllable request pending to observe loading, release it explicitly, then assert the visible result.

## Avoid hidden lifecycle and state

Faulty illustrative test:

```kotlin
val robot = MessageRobot(compose)
robot.send("Hello")
compose.onNodeWithText("Send").assertExists()
```

If the button's handler becomes a no-op, the assertion still passes. The test observes a control, not delivery. Correct it by mounting fresh state, asserting `Sending`, completing the fake, and asserting the returned receipt, as above.

Other abstraction failures have different repairs:

| Anti-pattern | Failure mechanism | Correction |
| --- | --- | --- |
| Robot creates users or opens a database | UI helper now owns hidden side effects and cleanup | Move resource ownership to a fixture |
| Robot constructor clicks through onboarding | Construction changes UI before the scenario starts | Add an explicit intent method |
| Companion-object sender | A completed deferred leaks into the next test | Create one sender per test |
| Fixture mounts every possible screen | Unused state and jobs affect synchronization | Mount the smallest screen for this scenario |
| Base class replaces dispatchers globally | Rule startup order controls behavior invisibly | Prefer injected dependencies and explicit ordering |
| Robot stores the expected final state | Test can agree with itself while UI is wrong | Pass independent expected values to assertions |

## Troubleshoot the abstraction

| Symptom | Observe | Fix |
| --- | --- | --- |
| Test passes alone, fails in class | Fake identity, completed deferreds, global overrides | Move mutable ownership to the test |
| Robot action finds two nodes | Merged tree and matching ancestor identities | Scope the robot to the intended component |
| Receipt never appears | Was the fake released, and which scheduler resumes it? | Release the actual fake, then synchronize |
| Activity content disappears | Which owner called `setContent`? | Keep exactly one content owner |
| Test worker hangs after success | Threads, executors, scopes owned by fixtures | Cancel and terminate owned work |

## Review checklist

- Does every helper have one visible responsibility?
- Can the reader see the initial state and expected result in the test?
- Does each mutable fake belong to one test?
- Does cleanup run after assertion failure?
- Does the robot query the intended semantics identity rather than an index?
- Would the test fail if the action did nothing?
- Are asynchronous completions visible rather than hidden in a robot?

## Related guides and sources

- [Screen robots](../core/screen-robots.md) covers matcher and method design.
- [Fixtures and hooks](../core/fixtures-hooks.md) covers JUnit lifecycle.
- [When to fake](when-to-fake.md) chooses the dependency boundary.
- [Isolation](../references/isolation.md) describes thread and state ownership.
- [Compose common patterns](https://developer.android.com/develop/ui/compose/testing/common-patterns) documents isolated composable tests.
- [Robolectric best practices](https://robolectric.org/best-practices/) describes Android-object mocking and rogue-thread hazards.
