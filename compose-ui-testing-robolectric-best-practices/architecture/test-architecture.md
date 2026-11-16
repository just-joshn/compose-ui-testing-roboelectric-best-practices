# Choose the test layer for a Compose feature

Use this guide when deciding where a regression belongs. Choose the smallest test that exercises the failure mechanism. A Robolectric Compose test runs Android UI code locally, but it is not an end-to-end test of the device, transport, and backend.

## Table of contents

- [Choose a layer by claim](#choose-a-layer-by-claim)
- [Test domain and repository contracts](#test-domain-and-repository-contracts)
- [Test component behavior locally](#test-component-behavior-locally)
- [Test screen orchestration](#test-screen-orchestration)
- [Hand off device and service claims](#hand-off-device-and-service-claims)
- [Layer an inventory feature](#layer-an-inventory-feature)
- [Avoid duplicate or missing coverage](#avoid-duplicate-or-missing-coverage)
- [Troubleshoot coverage gaps](#troubleshoot-coverage-gaps)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose a layer by claim

| Claim | First test layer | What remains unproven |
| --- | --- | --- |
| Invalid quantity is rejected | Pure domain unit test | Error rendering |
| Empty form displays required-field error | Robolectric component UI test | Backend validation |
| Save starts loading and then displays receipt | Robolectric screen test with controlled repository | HTTP and server persistence |
| JSON maps a 409 response to duplicate SKU | Repository adapter contract test | Server actually returns that response |
| Server rejects unauthorized deletion | Service integration test | Client presentation |
| Navigation action opens the detail screen | Local navigation integration test | External intent resolution and system back behavior |
| OAuth returns through a browser callback | Device and controlled provider integration | Other provider configurations |
| Dialog labels and actions exist | Local Compose semantics test | TalkBack traversal |
| Layout responds to width or locale | Configured local UI test | Real device pixels, IME, and insets |
| Real-time updates change a row | Local UI test with a controlled stream | Socket reconnect, server ordering, and cross-client delivery |
| Checkout completes with a payment SDK | Local state tests plus SDK/device sandbox integration | Production gateway behavior |
| State survives actual process death | Dedicated lifecycle and device test | Not established by remounting a composable |

Do not assign percentages to these layers by convention. The source guide's sample proportions and timings describe a browser example, not measured Android targets. Allocate tests according to failure risk and the contracts each layer owns.

## Test domain and repository contracts

Keep business-rule permutations below UI when the UI does not add relevant behavior. The data shape in this illustrative example is a requested quantity and a validation result. It uses ordinary Kotlin and JUnit 4 only.

```kotlin
import org.junit.Assert.assertEquals
import org.junit.Test

sealed interface QuantityCheck {
	data object Valid : QuantityCheck
	data class Invalid(val message: String) : QuantityCheck
}

fun checkQuantity(quantity: Int): QuantityCheck =
	if (quantity > 0) QuantityCheck.Valid
	else QuantityCheck.Invalid("Enter a quantity greater than zero")

class QuantityCheckTest {
	@Test fun rejectsZero() {
		assertEquals(
			QuantityCheck.Invalid("Enter a quantity greater than zero"),
			checkQuantity(0),
		)
	}

	@Test fun acceptsPositiveQuantity() {
		assertEquals(QuantityCheck.Valid, checkQuantity(2))
	}
}
```

A repository test has a different boundary. Keep the real serialization and response mapper when testing response interpretation. Supply a controlled transport response and assert the domain result. Cover missing fields, malformed responses, pagination, unauthorized responses, and conflict mapping at that boundary.

If the claim is server authorization, call the real service in a dedicated test environment. Hiding a Delete button or returning a fake `Forbidden` result does not prove that the server rejects a forged request.

For an owned API, maintain both adapter contract tests and service integration coverage. A UI test does not need to contact the service to prove that an error message is displayed.

## Test component behavior locally

Use a component test for a small real UI with local state. The following complete illustrative test covers the action-to-error path. It needs an Android test host, resources, Compose Material3, `ui-test-junit4`, Robolectric, and JUnit 4. Put it in `src/test`. Use the setup described in [configuration](../core/configuration.md).

```kotlin
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class QuantityFormTest {
	@get:Rule val compose = createComposeRule()

	@Test fun emptySubmitShowsValidationError() {
		compose.setContent {
			var submitted by remember { mutableStateOf(false) }
			Column {
				Button(onClick = { submitted = true }) { Text("Save") }
				if (submitted) Text("Quantity is required")
			}
		}

		compose.onNodeWithText("Quantity is required").assertDoesNotExist()
		compose.onNodeWithText("Save").performClick()
		compose.onNodeWithText("Quantity is required").assertIsDisplayed()
	}
}
```

This example demonstrates test structure, not a replacement implementation for your production form. Mount the production component in a real regression test. Keep all validation permutations in domain tests and choose representative rendering cases here.

Test initial enabled state, invalid input feedback, corrected input, disabled submission during work, and success reset where the component owns those behaviors. A callback payload assertion can supplement the visible outcome. It cannot replace it when the claim is screen behavior.

Semantics tests can check labels, enabled state, click actions, and selected state. They do not certify accessibility-service behavior. Use device accessibility testing for traversal and announcements.

## Test screen orchestration

A stateless rendering test supplies `Loading`, `Error`, or `Success` directly. It proves that state renders correctly. It does not prove that pressing Save produces those states.

For orchestration, mount the real screen owner and inject a repository fake at its external boundary:

1. Create a fresh fake with a pending completion.
2. Mount the screen once.
3. Enter data through semantics and press Save.
4. Assert loading and unavailable duplicate submission if those are contracts.
5. Complete the fake with a specific receipt.
6. Assert the receipt is displayed and loading has ended.

The compiled [message example](../examples/FixtureUiTest.kt), `sendShowsReceiptAfterCompletion`, follows this sequence. Its sender observation checks the payload, while the receipt assertion checks what the user sees.

A local navigation test may use the real navigation graph and fake data boundaries. Assert the destination's content after a user action. A navigation-controller assertion can help diagnose routing, but it does not prove the destination rendered.

Keep one content owner. If `createAndroidComposeRule` launches a production activity that calls `setContent`, do not call `setContent` again from the test. If the test owns the composition, use one call and mount the smallest screen needed.

## Hand off device and service claims

Keep a small set of integrated journeys for failures that local tests cannot expose:

- Launch the actual application and exercise critical navigation.
- Verify permission requests and result delivery on supported Android versions.
- Exercise OAuth through the intended browser or provider test environment.
- Check real IME, focus, insets, and system back behavior.
- Verify a payment SDK against its sandbox without production charges.
- Test transport authentication and backend authorization outside a repository fake.

Give each journey explicit seed data, ownership, and cleanup. Do not create a whole account through UI when account creation is merely setup for an unrelated inventory test. Seed through a controlled test API, then drive the behavior actually under test.

Use a dedicated service environment, not the production backend. Isolate account and record identifiers across workers. A nightly integration suite is useful only if failures have an owner and block or inform an explicit release decision.

## Layer an inventory feature

A practical inventory suite separates these responsibilities:

```text
Domain tests
  rejects zero and negative quantities
  enforces archive rules for pending orders

Repository contract tests
  maps successful creation response
  maps duplicate SKU and authorization errors
  preserves pagination cursor

Robolectric component tests
  displays required-field feedback
  renders empty list and error states
  exposes row actions with meaningful semantics

Robolectric screen tests
  saving displays pending state and created item
  retry replaces load error with returned content
  archive confirmation changes only the selected item

Device and service integration tests
  application launch reaches inventory
  real client and test service create a persisted item
  unauthorized API deletion is rejected
```

Do not assert every quantity permutation through all layers. Repeat a behavior only when the higher layer adds a distinct claim, such as wiring or persistence.

If domain and component tests pass but the screen test fails, inspect state collection and dependency wiring. If local screen tests pass but integrated tests fail, inspect transport mapping, host lifecycle, navigation, and environment configuration before rewriting selectors.

## Avoid duplicate or missing coverage

Faulty illustrative rendering-only test:

```kotlin
compose.setContent { InventoryScreen(state = InventoryState.Saved("SKU-7")) }
compose.onNodeWithText("SKU-7 saved").assertIsDisplayed()
```

This is valid only as a rendering test. It passes when Save does nothing because the test supplies `Saved` itself.

Correct the orchestration claim by mounting the real state owner, performing Save, completing its controlled repository, and asserting `SKU-7 saved`. Keep the rendering-only test if conditional presentation is independently valuable.

| Mistake | Consequence | Better choice |
| --- | --- | --- |
| Every rule tested through device UI | Slow diagnosis and unnecessary setup | Domain tests plus representative UI feedback |
| All UI dependencies mocked | Compose behavior itself is no longer exercised | Real UI and fake external boundary |
| All tests hit a live service | UI failures inherit service availability | Local controlled states plus explicit integration suite |
| Fake response described as HTTP coverage | Missing serialization and authorization regressions | Adapter and service tests |
| One journey covers an entire feature | First failure hides later checks | Focused journeys with clear outcomes |

## Troubleshoot coverage gaps

| Symptom | Observation | Repair |
| --- | --- | --- |
| UI tests pass while production fails to parse JSON | Was the serializer bypassed by a domain fake? | Add adapter contract coverage |
| Validation tests pass but no message appears | Do tests invoke the actual user action? | Add action-to-feedback UI coverage |
| Local UI passes but activity launch fails | Is the real host and manifest exercised? | Add a host integration test |
| Fake behavior diverges from service | Compare domain outcomes with adapter contracts | Update shared contract cases |
| Screen test hangs | Identify pending fake, coroutine scheduler, or busy resource | Control the actual owner of work |

## Review checklist

- Does the test name state the layer's actual claim?
- Does it exercise the real code that can break that claim?
- Are fakes explicit and fresh per test?
- Does synchronization match the owner of asynchronous work?
- Are device and backend claims covered elsewhere?
- Would a no-op user action fail the orchestration test?
- Is repeated coverage justified by a distinct integration risk?

## Related guides and sources

- [When to fake](when-to-fake.md) chooses local boundaries.
- [Repository contracts](../testing-patterns/repository-contracts.md) covers adapters.
- [Component testing](../testing-patterns/component-testing.md) covers isolated UI.
- [Host integration](../testing-patterns/host-integration.md) covers activity ownership.
- [Compose testing](https://developer.android.com/develop/ui/compose/testing) documents UI testing APIs.
- [Android testing strategies](https://developer.android.com/training/testing/fundamentals/strategies) describes test scope and tradeoffs.
- [Robolectric local tests](https://developer.android.com/training/testing/local-tests/robolectric) describes the local Android layer.
