# Test forms and validation

Use this guide for text entry, selection, validation, dependent fields, wizards, and asynchronous submission in Compose. Run local UI cases with Robolectric. Test server validation and transport separately through the real client or service contract.

## Table of contents

- [Choose actions by control](#choose-actions-by-control)
- [Test required fields and recovery](#test-required-fields-and-recovery)
- [Test formatting and validation timing](#test-formatting-and-validation-timing)
- [Select dropdowns, toggles, and dates](#select-dropdowns-toggles-and-dates)
- [Test suggestions and debounce](#test-suggestions-and-debounce)
- [Test conditional and dependent fields](#test-conditional-and-dependent-fields)
- [Complete a multistep wizard](#complete-a-multistep-wizard)
- [Hold submission pending](#hold-submission-pending)
- [Test reset and dirty-form confirmation](#test-reset-and-dirty-form-confirmation)
- [Keep state and schedulers isolated](#keep-state-and-schedulers-isolated)
- [Avoid false-green form tests](#avoid-false-green-form-tests)
- [Troubleshoot failures](#troubleshoot-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose actions by control

| Control or claim | Action | Assertion |
| --- | --- | --- |
| Insert text at the current selection | `performTextInput` | Editable text and dependent state |
| Replace the whole field value | `performTextReplacement` | Exact new value |
| Clear a field | `performTextClearance` | Empty editable value and validation behavior |
| Submit using the configured IME action | `performImeAction` | Same outcome as the supported submit path |
| Checkbox or switch | Inspect state, then `performClick` if a change is needed | `assertIsOn` or `assertIsOff` |
| Radio or selectable option | Click the intended option | Selected semantics and dependent UI |
| Custom dropdown | Open trigger, choose visible named option | Selected label and downstream fields |
| Read-only date field | Open picker and select a date | Displayed date and submitted date value |
| Validation | Trigger the app's validation event | Error text, error semantics, and blocked progression |
| Async submission | Click with a controlled boundary pending | Loading, disabled action, then success or error |

Compose has no HTML `required` attribute or native browser constraint-validation bubble. The app owns validation rules, when errors appear, and what accessibility metadata describes them.

Do not assume `performTextInput` is equivalent to browser `fill`. It inserts text rather than replacing the complete value. Use replacement when a test needs to remove a previous invalid input.

## Test required fields and recovery

This illustrative complete example defines its own small form. It uses Material3, Compose UI test 1.12.1, JUnit 4, and Robolectric. Use the [local setup](../references/setup.md) with Android resources and the default activity manifest. This example is not compiled by the fixture.

```kotlin
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextReplacement
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.LooperMode

@Composable
private fun NameForm() {
	var name by remember { mutableStateOf("") }
	var attempted by remember { mutableStateOf(false) }
	var submitted by remember { mutableStateOf(false) }
	val invalid = attempted && name.isBlank()
	Column {
		TextField(
			value = name,
			onValueChange = { name = it },
			label = { Text("Name") },
			isError = invalid,
		)
		if (invalid) Text("Name is required")
		Button(onClick = {
			attempted = true
			if (name.isNotBlank()) submitted = true
		}) { Text("Send inquiry") }
		if (submitted) Text("Inquiry received for $name")
	}
}

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
@LooperMode(LooperMode.Mode.PAUSED)
class NameFormTest {
	@get:Rule val compose = createComposeRule()

	@Test fun emptySubmissionShowsErrorThenValidInputRecovers() {
		compose.setContent { MaterialTheme { NameForm() } }
		compose.onNodeWithText("Send inquiry").performClick()
		compose.onNodeWithText("Name is required").assertIsDisplayed()
		compose.onNodeWithText("Inquiry received for Carol").assertDoesNotExist()
		compose.onNodeWithText("Name").performTextReplacement("Carol")
		compose.onNodeWithText("Name is required").assertDoesNotExist()
		compose.onNodeWithText("Send inquiry").performClick()
		compose.onNodeWithText("Inquiry received for Carol").assertIsDisplayed()
	}
}
```

The recovery assertion follows this form's on-change error policy. For a form that clears errors only on blur or resubmission, trigger that event instead. Do not change the test until it happens to match an unintended validation policy.

For a real form, assert that invalid submission does not reach its repository boundary. Pair that case with valid submission so a permanently disconnected submit handler cannot pass both cases.

## Test formatting and validation timing

Keep exhaustive rule combinations in pure validator tests. Use UI tests for representative invalid input, error display, focus timing, correction, and submission.

| Rule | Pure tests | UI case |
| --- | --- | --- |
| Required name | Empty, whitespace, valid Unicode | Empty submit shows error and stays on form |
| Email policy | App-supported formats and invalid boundaries | Invalid input shows the expected field error |
| Password policy | Each required rule and valid comparison | Visible rule feedback changes after correction |
| Amount range | Below minimum, exact limits, above maximum | Displayed error and valid submission |
| Matching fields | Equal, unequal, changed original | Confirmation error updates when either field changes |

For blur validation, move focus to another named control. Clicking a submit button is not a reliable substitute if the form's focus policy retains the field. Assert input focus where that timing is the subject of the test.

For visual transformations, such as currency separators or masked account numbers, distinguish the stored value from the displayed value. Inspect actual semantics before using `assertTextEquals`. A label and editable text can share a node.

Do not assert raw password text in logs or failure messages. Use synthetic credentials. Cover that a masked field remains usable and submits the correct synthetic value through the boundary without leaking production secrets.

## Select dropdowns, toggles, and dates

Compose dropdowns are UI components, not native HTML selects. Open the trigger and choose the intended option by visible text or meaningful semantics. If the menu is a separate popup root, include that root in diagnosis and scope repeated labels deliberately.

A click toggles a checkbox. It is not an idempotent `check()` operation. Assert the initial state, click once, and assert the new state. For a reusable helper that promises "ensure checked", inspect the current toggle state before deciding whether to click.

For radios, select the named option and assert both the chosen state and any deselected alternative required by the contract. A selected label alone may not show that multiple options became selected accidentally.

For dates, use an editable field only when the app exposes one. For a read-only date field, open its picker, navigate from a fixed initial month, and select a fully identified day. A matcher for `15` can match adjacent-month cells or several calendars.

Inject business time for date limits. Test UTC conversion, local time-zone display, and daylight-saving boundaries in formatter or repository tests. The Compose clock does not change `LocalDate.now()`.

### Work through selection and back navigation

This standalone illustrative example defines a small booking component and its test. It uses the same dependencies and host as `NameFormTest` above. `BookingDraft` owns the selections. `BookingStep` owns progression. Menu and picker visibility are transient presentation state, not booking fields.

The date picker is a real, deliberately limited calendar for June 2026, which starts on Monday. Its supported range is June 1 through June 30. Selecting a day invokes `onSelected`, updates the draft, and closes the dialog. It is not a substitute for testing your production Material date picker. In that case, mount that picker and use its actual full-date semantics for the configured locale.

```kotlin
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsOff
import androidx.compose.ui.test.assertIsOn
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import java.time.LocalDate
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

private enum class BookingStep { Options, Review, Complete }
private enum class Room { Standard, Suite }
private data class BookingDraft(
	val room: Room = Room.Standard,
	val breakfast: Boolean = false,
	val arrival: LocalDate? = null,
)

@Composable
private fun JunePicker(onSelected: (LocalDate) -> Unit, onDismiss: () -> Unit) {
	Dialog(onDismissRequest = onDismiss) {
		Surface {
			Column(Modifier.padding(12.dp)) {
				Text("June 2026")
				Text("Mon Tue Wed Thu Fri Sat Sun")
				(1..30).toList().chunked(7).forEach { week ->
					Row {
						week.forEach { day ->
							val date = LocalDate.of(2026, 6, day)
							Text(
								day.toString(),
								Modifier.weight(1f)
									.clickable(role = Role.Button) { onSelected(date) }
									.semantics { contentDescription = "Choose $date" }
									.padding(vertical = 12.dp),
							)
						}
						repeat(7 - week.size) { Spacer(Modifier.weight(1f)) }
					}
				}
				Button(onClick = onDismiss) { Text("Cancel date") }
			}
		}
	}
}

@Composable
private fun BookingWizard(onBook: (BookingDraft) -> Unit) {
	var draft by remember { mutableStateOf(BookingDraft()) }
	var step by remember { mutableStateOf(BookingStep.Options) }
	var menuOpen by remember { mutableStateOf(false) }
	var pickerOpen by remember { mutableStateOf(false) }
	Column {
		when (step) {
			BookingStep.Options -> {
				Text("Booking options")
				Box {
					Button(onClick = { menuOpen = true }) { Text("Room: ${draft.room}") }
					DropdownMenu(expanded = menuOpen, onDismissRequest = { menuOpen = false }) {
						Room.entries.forEach { room ->
							DropdownMenuItem(text = { Text(room.name) }, onClick = {
								draft = draft.copy(room = room)
								menuOpen = false
							})
						}
					}
				}
				Checkbox(
					checked = draft.breakfast,
					onCheckedChange = { draft = draft.copy(breakfast = it) },
					modifier = Modifier.semantics { contentDescription = "Include breakfast" },
				)
				Text(if (draft.breakfast) "Breakfast included" else "Room only")
				Button(onClick = { pickerOpen = true }) {
					Text("Arrival: ${draft.arrival ?: "Choose date"}")
				}
				Button(
					enabled = draft.arrival != null,
					onClick = { step = BookingStep.Review },
				) { Text("Next") }
			}
			BookingStep.Review -> {
				Text("Review booking")
				Text("${draft.room}, ${draft.arrival}, breakfast=${draft.breakfast}")
				Button(onClick = { step = BookingStep.Options }) { Text("Previous") }
				Button(onClick = { onBook(draft); step = BookingStep.Complete }) {
					Text("Confirm booking")
				}
			}
			BookingStep.Complete -> Text("Booking complete")
		}
	}
	if (pickerOpen) JunePicker(
		onSelected = { draft = draft.copy(arrival = it); pickerOpen = false },
		onDismiss = { pickerOpen = false },
	)
}

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class BookingControlsTest {
	@get:Rule val compose = createComposeRule()

	@Test fun selectionsSurviveBackAndReachBookingCallback() {
		val booked = mutableListOf<BookingDraft>()
		compose.setContent { MaterialTheme { BookingWizard(onBook = { booked.add(it) }) } }
		compose.onNodeWithText("Booking options").assertIsDisplayed()
		compose.onNodeWithText("Room: Standard").performClick()
		compose.onNodeWithText("Suite").performClick()
		compose.onNodeWithText("Room: Suite").assertIsDisplayed()
		compose.onNodeWithContentDescription("Include breakfast")
			.assertIsOff().performClick().assertIsOn()
		compose.onNodeWithText("Breakfast included").assertIsDisplayed()
		compose.onNodeWithText("Arrival: Choose date").performClick()
		compose.onNodeWithText("June 2026").assertIsDisplayed()
		compose.onNodeWithContentDescription("Choose 2026-06-15").performClick()
		compose.onNodeWithText("June 2026").assertDoesNotExist()
		compose.onNodeWithText("Arrival: 2026-06-15").assertIsDisplayed()
		compose.onNodeWithText("Next").performClick()
		compose.onNodeWithText("Review booking").assertIsDisplayed()
		compose.onNodeWithText("Suite, 2026-06-15, breakfast=true").assertIsDisplayed()
		compose.onNodeWithText("Previous").performClick()
		compose.onNodeWithText("Booking options").assertIsDisplayed()
		compose.onNodeWithText("Room: Suite").assertIsDisplayed()
		compose.onNodeWithContentDescription("Include breakfast").assertIsOn()
		compose.onNodeWithText("Arrival: 2026-06-15").assertIsDisplayed()
		compose.onNodeWithText("Next").performClick()
		compose.onNodeWithText("Confirm booking").performClick()
		compose.onNodeWithText("Booking complete").assertIsDisplayed()
		compose.runOnIdle {
			assertEquals(listOf(BookingDraft(Room.Suite, true, LocalDate.of(2026, 6, 15))), booked)
		}
	}
}
```

The test changes selections only through the controls. A no-op dropdown, toggle, day callback, back handler, or submit handler breaks a corresponding UI or payload assertion. The callback is an in-memory booking boundary, not evidence of a server reservation.

## Test suggestions and debounce

Use a fresh suggestion fake that can hold and complete a request. Mount the real field and suggestion UI.

1. Replace the query with `456 Elm`.
2. If the feature debounces, start its coroutine and advance the scheduler that owns the debounce.
3. Complete the fake with a known suggestion.
4. Wait for that suggestion through a bounded condition if external progress is involved.
5. Select **456 Elm Street**.
6. Assert the street, city, region, and postal code shown in the form.

Do not simulate slow typing with wall-clock sleeps. `performTextReplacement` is suitable when behavior depends on the query value, not individual key events. Use key injection only when the component actually handles keys.

Add a stale-response case. Start query A, change to B, complete B, then complete A. Assert that A does not overwrite the current suggestions or selected address. The test must exercise the real cancellation or request-identity logic rather than directly supply B as final UI state.

Test dismissal independently. Open suggestions, perform the supported dismissal action, assert they disappear, and verify the typed custom value remains if that behavior is supported.

## Test conditional and dependent fields

For an applicant-type form, choose **Business**, assert business fields appear, enter their values, then choose **Individual**. Assert that the hidden business fields do not appear in the submission payload if the product excludes them.

Checking only disappearance can miss stale hidden values being sent. Checking only a payload can miss fields that remain visible.

For dependent country, province, and city choices:

- Seed a known country with two provinces and distinct cities.
- Select the country and assert the province control becomes usable.
- Select a province and a city.
- Change the country.
- Assert old province and city values are cleared or reset according to the contract.

Hold dependent lookups pending to test disabled and loading states. Fail one lookup and verify the error and retry without losing unrelated input.

## Complete a multistep wizard

Use one representative full path and focused cases for each step's rules.

| Case | Action | Expected observation |
| --- | --- | --- |
| Empty first step | Click **Next** | Stay on guest information with required errors |
| Valid first step | Fill fields, click **Next** | Room-selection heading appears |
| Back navigation | Click **Previous** | Entered name and email remain |
| Invalid date range | Choose checkout before check-in | Stay on room selection with range error |
| Review | Continue with valid data | Confirmation shows the chosen guest and room |
| Final submit | Confirm with controlled repository | Pending state, then booking receipt |

The [worked booking test](#work-through-selection-and-back-navigation) exercises options, review, back, and confirmation against one retained `BookingDraft`. Extend that component's contract for guest validation and date ranges rather than pretending the small example covers those rules.

Assert the current heading at each transition. A shared **Next** button existing at the end does not prove the intended step changed.

Do not seed the final booking when the test claims to prove booking creation through the wizard. Seed unrelated catalog data through repositories instead of repeating setup UI in every case.

## Hold submission pending

Use a fresh `CompletableDeferred` in a repository fake. The compiled [message panel example](../examples/FixtureUiTest.kt) demonstrates pending, completion, and receipt assertions.

For a form, start with valid values and click submit. While the fake remains pending, assert the loading label and disabled submit action. Attempt the supported duplicate-submit route, such as the IME action, if duplicate prevention is a requirement. Check that only one external request is outstanding.

Complete the fake with success and assert the confirmation or destination content. In a separate test, return a field-level rejection such as **Email address already registered**. Assert the field error, retained user input, and enabled retry action.

Test a general transport failure separately from server validation. The form may keep entered values for both, but it should not label a network outage as an invalid email.

A fake rejection proves client presentation. Verify real status codes, response decoding, and server enforcement in [repository contracts](repository-contracts.md).

## Test reset and dirty-form confirmation

Change several field types before reset. Click **Reset** and assert the exact default text, toggle state, selected option, and cleared validation messages.

If reset requires confirmation, cover both **Keep editing** and **Discard changes**. After cancellation, edited values remain. After confirmation, defaults return. Check pending suggestion state or derived totals too when reset promises to clear them.

Do not mutate backing state directly to test the reset button. That bypasses the handler that can be broken.

## Keep state and schedulers isolated

Create a new form state, repository fake, deferred, and wizard owner for every test. Call `setContent` once. Do not reuse a successful submission result in a later pending-state case.

Compose actions and assertions synchronize known work but do not retry arbitrary business assertions. For external suggestions or submission, release the fake and use a bounded observable condition where needed. Advance only the scheduler that owns debounce or validation work.

Restore locale, injected clocks, and dispatcher overrides after each case. Cancel pending test-owned jobs. A composition-scoped job and a ViewModel-scoped job may have different disposal lifetimes.

## Avoid false-green form tests

| Anti-pattern | Failure mechanism | Correct approach |
| --- | --- | --- |
| Append new input over an old invalid value | The field contains both values | Use `performTextReplacement` |
| Toggle without asserting the initial state | The action may uncheck instead of check | Assert precondition and resulting state |
| Mutate ViewModel fields instead of entering text | Binding and event handlers are bypassed | Use semantics input actions |
| Assert only that submit was called | The UI may remain stuck in loading | Assert pending and result content |
| Test every invalid value in one UI method | Early failure hides later rules | Use pure rule tests plus focused UI cases |
| Sleep after selecting a country | Data may arrive earlier or later | Control the fake or wait for a bounded condition |
| Claim backend validation from a fake | The real service was never called | Add client and service contract tests |

## Troubleshoot failures

| Symptom | Observe | Correction |
| --- | --- | --- |
| Input action finds no editable node | Merged and unmerged text, actions | Select the actual editable control, not a decorative label |
| Entered text does not persist | Controlled state feedback | Feed `onValueChange` into observable state |
| Validation does not appear | Trigger policy and current focus | Blur, submit, or advance the correct scheduler |
| Date field rejects text replacement | Read-only state and picker UI | Interact with the supported picker |
| Dropdown selection is ambiguous | Popup roots and duplicate options | Scope to the intended menu or option identity |
| Loading never appears | Already completed fake | Create a pending fake per test |
| Suggestions are stale | Request completion order | Test cancellation or request identity at the real owner |

## Review checklist

- [ ] Text insertion and replacement are chosen deliberately.
- [ ] Invalid submission blocks progression and recovers after correction.
- [ ] Validation triggers match the product policy.
- [ ] Hidden and dependent fields have payload checks where relevant.
- [ ] Wizard back navigation preserves expected input.
- [ ] Pending, success, field rejection, and general failure are separate cases.
- [ ] Reset is exercised through the real action.
- [ ] Fakes are not presented as backend evidence.

## Related guides and sources

- [Component testing](component-testing.md) covers controlled wrappers.
- [Accessibility](accessibility.md) covers error semantics and focus.
- [Clock control](../advanced/clock-control.md) covers timers and schedulers.
- [Compose testing APIs](https://developer.android.com/develop/ui/compose/testing/apis) documents semantics actions and assertions.
- [Compose synchronization](https://developer.android.com/develop/ui/compose/testing/synchronization) explains explicit waits.
- [Text input](https://developer.android.com/develop/ui/compose/text/user-input) describes field state and editing behavior.
