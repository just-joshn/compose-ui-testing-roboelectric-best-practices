# Organize interactions with screen robots

Use a robot when several tests repeat meaningful interactions or selectors for the same screen or component. A robot wraps the real Compose testing API. It does not own the activity, repositories, or mutable application state.

## Contents

- [Choose the smallest helper](#choose-the-smallest-helper)
- [Build a focused robot](#build-a-focused-robot)
- [Compose component robots](#compose-component-robots)
- [Represent navigation honestly](#represent-navigation-honestly)
- [Construct robots with fixtures](#construct-robots-with-fixtures)
- [Keep lifecycle and synchronization explicit](#keep-lifecycle-and-synchronization-explicit)
- [Avoid robot anti-patterns](#avoid-robot-anti-patterns)
- [Troubleshoot robot failures](#troubleshoot-robot-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the smallest helper

| Situation | Use | Avoid |
| --- | --- | --- |
| One short test with unique selectors | Inline actions and assertions | A robot for every composable |
| Repeated interaction vocabulary | A focused screen robot | A generic action dispatcher |
| Repeated card, row, or dialog | A scoped component robot | Unscoped repeated text |
| Creating fakes, sessions, databases | A test fixture or rule | Robot constructors with setup side effects |
| A repeated matcher only | A matcher function | A whole screen inheritance hierarchy |
| Multiple screens in a journey | Composed robots with explicit outcome checks | Treating returned objects as proof of navigation |

Prefer a class with a few concrete methods over a fluent domain-specific language that hides which test rule and state it uses. Tests must still show their important inputs and expected results.

## Build a focused robot

The data passed to this illustrative robot is a Compose rule plus user input. The robot holds no application state. It uses the canonical `MessagePanel` labels.

The declaration needs `ui-test-junit4` and its transitive UI test artifact. It is illustrative, not an additional compiled fixture file.

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.ComposeTestRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextReplacement

class MessageRobot(private val rule: ComposeTestRule) {
	fun enterMessage(message: String) {
		rule.onNodeWithText("Message").performTextReplacement(message)
	}

	fun send() {
		rule.onNodeWithText("Send").performClick()
	}

	fun assertSendDisabled() {
		rule.onNodeWithText("Send").assertIsNotEnabled()
	}

	fun assertSending() {
		rule.onNodeWithText("Sending").assertIsDisplayed()
	}

	fun assertReceipt(receipt: String) {
		rule.onNodeWithText(receipt).assertIsDisplayed()
	}
}
```

Use the v2 factory to create the rule, but import the helper's interface from `androidx.compose.ui.test.junit4.ComposeTestRule`. There is no reason to require the concrete activity rule when the robot only queries semantics.

A usage fragment inside a hosted test follows. It assumes `PendingSender` from [assertions and waiting](assertions-waiting.md), the canonical `MessagePanel`, and one test-owned `rule`:

```kotlin
import fixture.MessagePanel

val sender = PendingSender()
rule.setContent { MessagePanel(sender) }
val messages = MessageRobot(rule)
messages.assertSendDisabled()
messages.enterMessage("Hello")
messages.send()
messages.assertSending()
rule.runOnIdle { sender.complete("Delivered Hello") }
messages.assertReceipt("Delivered Hello")
```

The action and the assertion have separate names. A reviewer can see that the receipt, rather than a callback count, defines success.

Expose a specific `SemanticsNodeInteraction` only when callers need an assertion that the robot does not reasonably own. Do not expose every internal node as a public property preemptively.

## Compose component robots

A repeated component needs a stable scope. This illustrative robot assumes an unmerged tagged group whose Open control remains a descendant, as in canonical `DraftActions`:

```kotlin
import androidx.compose.ui.test.hasAnyAncestor
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.ComposeTestRule
import androidx.compose.ui.test.performClick

class DraftCardRobot(
	private val rule: ComposeTestRule,
	private val cardTag: String,
) {
	fun open() {
		rule.onNode(
			hasText("Open") and hasAnyAncestor(hasTestTag(cardTag)),
		).performClick()
	}
}
```

Construct `DraftCardRobot(rule, "draft")` and `DraftCardRobot(rule, "archive")` for distinct identities. If production merges the group into a single clickable node, change the selector to that node's combined text and tag. Do not force the old hierarchy through unmerged search unless the child contract actually matters.

For a dialog component, scope its confirm and cancel controls to a dialog identity. Do not globally click `Confirm` when the background screen can expose the same text.

Component composition usually replaces base-screen inheritance. A toolbar robot and a message robot can share the same rule without sharing mutable state or inheriting an activity owner.

## Represent navigation honestly

A method can return another robot to help the caller continue a journey. The return value only constructs a helper. It does not prove the destination exists.

Prefer this explicit sequence in a test:

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick

rule.onNodeWithText("Settings").performClick()
rule.onNodeWithText("Notification preferences").assertIsDisplayed()
```

Wrap these in separately named action and destination assertion methods only when repeated. Do not add a fake `goto()` that bypasses navigation if the test claims to exercise navigation. Mounting the destination directly is a valid rendering test with a narrower claim.

For navigation-controller assertions, keep a visible destination assertion too. The route string alone does not prove that the user can see the expected content.

## Construct robots with fixtures

Create robots after the test has its rule and scenario. A constructor stores references only. It must not call `setContent`, launch an activity, sign in, or wait for background work.

A plain factory function is sufficient if construction repeats:

```kotlin
import androidx.compose.ui.test.junit4.ComposeTestRule

fun messageRobot(rule: ComposeTestRule): MessageRobot = MessageRobot(rule)
```

Do not introduce a factory for one call site. Use a `ComposeContentTestRule` parameter only for a fixture that actually owns `setContent`. Keep robots on `ComposeTestRule` so their lifecycle responsibilities remain clear.

Avoid companion-object robots or a shared robot registry. A robot tied to a previous test's rule is not valid in the next test.

## Keep lifecycle and synchronization explicit

Let normal Compose actions and assertions synchronize known Compose work. A robot should not add `Thread.sleep`, arbitrary clock jumps, or global looper drains.

If an action starts a request, the test fixture owns the controlled fake. The robot performs the user action. The test completes the fake and checks the rendered result through the robot. This separation keeps the producer visible.

Use explicit clock-control methods only when the robot's contract concerns a timed interaction, and name the clock and expected transition. Do not hide a two-second frame advance inside `send()`.

When content is recreated, re-query semantics through matchers. Do not cache fetched `SemanticsNode` snapshots or coordinates in robot fields.

## Avoid robot anti-patterns

| Anti-pattern | Failure mechanism | Correction |
| --- | --- | --- |
| `clickButton(index)` | Encodes layout order, not intent | Name `send`, `openDraft`, or another user action |
| `loginAndAssertEverything()` | Hides setup and unrelated expectations | Separate input, submit, and named result assertions |
| Constructor mounts content | Competes with activity or test ownership | Mount once in the fixture |
| Base robot stores global fake | Leaks requests and state across tests | Pass only the test's rule and scope |
| Helper catches assertion failures | Turns a regression into a log | Let framework assertions fail the test |
| One robot for the whole app | Changes require unrelated edits | Split by screen or repeated component |

## Troubleshoot robot failures

| Symptom | Observe | Fix |
| --- | --- | --- |
| Several tests fail after text change | One centralized selector and actual semantics | Update intentional wording once, retain outcome checks |
| Wrong repeated row opens | Scope and tree shape | Match stable group identity |
| Robot passes but journey fails later | Missing destination assertion | Assert the new screen immediately |
| Works only after another test | Constructor effects or shared rule | Create robot and dependencies per test |
| Timeout inside a friendly method | Underlying finder and producer | Preserve method input, semantics dump, and original exception |

## Review checklist

- Each method describes one user intent or one named expectation.
- Constructors have no lifecycle side effects.
- Component identity is explicit.
- The test still shows business inputs and final results.
- No helper hides sleeps, retries, fake completion, or shared mutable state.
- Inline tests remain available when no repetition justifies a robot.

## Related guides and sources

- [Semantics selectors](semantics-selectors.md) explains query identity and tree choice.
- [Fixtures and hooks](fixtures-hooks.md) owns resource setup and teardown.
- [Robots versus fixtures](../architecture/robots-vs-fixtures.md) separates interaction helpers from lifecycle management.
- [Testing APIs](https://developer.android.com/develop/ui/compose/testing/apis) documents the wrapped APIs.
- [Common Compose test patterns](https://developer.android.com/develop/ui/compose/testing/common-patterns) describes isolated component testing.
