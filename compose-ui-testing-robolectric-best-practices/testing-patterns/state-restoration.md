# State Restoration Testing

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Patterns](#patterns)
3. [Decision Guide](#decision-guide)
4. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
5. [Common Issues & Solutions](#common-issues--solutions)
6. [Related References](#related-references)
7. [Sources](#sources)

> **When to use**: Verifying that UI state survives configuration changes and process death, especially `rememberSaveable` in composables and `SavedStateHandle` in ViewModels.
> **Prerequisites**: [test-suite-structure.md](../core/test-suite-structure.md), [semantics-finders.md](../core/semantics-finders.md)

## Quick Reference

```kotlin
// Simulate recreation without recreating the activity
val restorationTester = StateRestorationTester(composeTestRule)
restorationTester.setContent { MainScreen() }   // NOT composeTestRule.setContent
// ...change state...
restorationTester.emulateSavedInstanceStateRestore()
// ...assert state is back...
```

| Event | UI logic state | ViewModel business logic state |
|---|---|---|
| Configuration change | `rememberSaveable` | Automatic |
| System-initiated process death | `rememberSaveable` | `SavedStateHandle` |

`emulateSavedInstanceStateRestore()` saves everything stored via `rememberSaveable`, disposes the composition, and composes the content again. State held in plain `remember` or `state()` is lost by design.

## Patterns

### Testing rememberSaveable with StateRestorationTester

**Use when**: A composable keeps UI element state (expanded/collapsed, selection, text input, scroll position) that must survive recreation.
**Avoid when**: The state lives in a ViewModel. Test that with `SavedStateHandle` (below).

```kotlin
@RunWith(AndroidJUnit4::class)
class ChatBubbleRestorationTest {
    @get:Rule
    val composeTestRule = createComposeRule()

    @Test
    fun detailsStayExpandedAfterRecreation() {
        val restorationTester = StateRestorationTester(composeTestRule)
        restorationTester.setContent { ChatBubble(message = sampleMessage) }

        composeTestRule.onNodeWithText(sampleMessage.content).performClick()
        composeTestRule.onNodeWithText(sampleMessage.timestamp).assertIsDisplayed()

        restorationTester.emulateSavedInstanceStateRestore()

        composeTestRule.onNodeWithText(sampleMessage.timestamp).assertIsDisplayed()
    }
}
```

`ChatBubble` is the docs' example composable: `var showDetails by rememberSaveable { mutableStateOf(false) }` toggled by `onClick`.

The docs say this tester helps verify `rememberSaveable` "without relying on activity recreation". The Robolectric blog (2026-07-03) states the same `createAndroidComposeRule<ComponentActivity>()` / `runComposeUiTest { }` code runs on a device and on the JVM. No source states `StateRestorationTester` specifically on Robolectric; treat the `src/test` placement as unverified until your suite proves it.

### Proving remember Loses State and rememberSaveable Keeps It

**Use when**: You want a regression test that a refactor from `rememberSaveable` to `remember` is caught.

```kotlin
@Test
fun plainRememberIsLostOnRestore() {
    val restorationTester = StateRestorationTester(composeTestRule)
    restorationTester.setContent { CounterWithPlainRemember() }

    composeTestRule.onNodeWithTag("increment").performClick()
    restorationTester.emulateSavedInstanceStateRestore()

    // Good: the test documents the contract. Plain remember resets.
    composeTestRule.onNodeWithTag("count").assertTextEquals("0")
}
```

`CounterWithPlainRemember` is a placeholder for your own composable. Per the API reference, state stored via regular `state()` or `remember()` is lost.

### Non-Primitive State and Custom Savers

**Use when**: The saved type is a data class, not a primitive.

`rememberSaveable` stores primitives in the `Bundle` automatically. For other types the docs list `Parcelize`, `listSaver`, `mapSaver`, or a custom `Saver`. The restoration test is identical: set content through the tester, mutate, restore, assert on the UI. A wrong saver fails at the assertion after `emulateSavedInstanceStateRestore()`.

### Activity Recreation (Config Changes)

**Use when**: You need the real activity lifecycle, not just local composable state.

The docs say to simulate a configuration change in any UI test by calling `Activity.recreate()`, and to prefer `StateRestorationTester` in Compose because it is "efficient" and does not restart the activity.

```kotlin
@get:Rule
val composeTestRule = createAndroidComposeRule<ComponentActivity>()

@Test
fun inputSurvivesRecreate() {
    composeTestRule.setContent { UserInputScreen() }
    composeTestRule.onNodeWithTag("message").performTextInput("hello")

    composeTestRule.runOnUiThread { composeTestRule.activity.recreate() }

    composeTestRule.onNodeWithTag("message").assertTextEquals("hello")
}
```

The `runOnUiThread { activity.recreate() }` wrapper is illustrative, not a documented recipe. A documented Robolectric example does recreate an activity: Android's Robolectric strategies page runs an Espresso test in `src/test` with `ActivityScenario.recreate()` under `@RunWith(AndroidJUnit4::class)`. Whether a Compose rule keeps resolving nodes after `recreate()` on Robolectric is not covered by any source page.

Resizing the screen mid-test does not work for logic that detects foldable postures, because posture changes do not trigger a configuration change.

### ViewModel State: SavedStateHandle

**Use when**: Business logic state in a ViewModel must survive process death.

The state-saving page shows `SavedStateHandle` with `saveable()` (Compose `State`, experimental) and `getStateFlow()` (`StateFlow`). ViewModels are plain classes, so a unit test constructs one directly with `SavedStateHandle()`.

```kotlin
class ConversationViewModelTest {
    @Test
    fun updateStoresMessage() {
        val viewModel = ConversationViewModel(SavedStateHandle())

        viewModel.update(TextFieldValue("hi"))

        assertEquals("hi", viewModel.message.text)
    }
}
```

`ConversationViewModel` is the docs' example (`var message by savedStateHandle.saveable(stateSaver = TextFieldValue.Saver) { ... }`). This proves the API contract, not a real process-death round trip. For that, the Robolectric blog describes the Lifecycle library's `viewModelScenario { }` with `scenario.recreate()` ("simulate process death", round-tripping saved state through a real `Parcel`). The blog gives no Gradle coordinate, so look it up before use. See [coroutines-viewmodels.md](coroutines-viewmodels.md) for dispatcher setup.

## Decision Guide

| Goal | Tool | Notes |
|---|---|---|
| Local composable state survives restore | `StateRestorationTester` | Fast; no activity restart |
| Real lifecycle, config change | `Activity.recreate()` | Heavier; see caveats above |
| ViewModel state survives process death | `SavedStateHandle` test, or `viewModelScenario { }` | Bundle APIs only for small state |
| Layout adapts to size or font | Device configuration, not restoration | See [device-configuration.md](../advanced/device-configuration.md) |
| Foldable posture logic | Not covered by resizing the screen | Posture changes do not trigger a config change |

## Anti-Patterns to Avoid

| Don't | Problem | Do Instead |
|---|---|---|
| `composeTestRule.setContent` then `emulateSavedInstanceStateRestore()` | Restore applies to the tester's content only | Call `restorationTester.setContent { }` |
| Expect `remember { }` state to survive | Lost by design | Use `rememberSaveable` and test it |
| Treat the tester as an activity lifecycle test | It tests local composable state only, no Activity callbacks | Use `Activity.recreate()` for lifecycle integration |
| Save large objects in `rememberSaveable` | Bundle size limit; `TransactionTooLarge` risk | Save IDs or keys, restore heavy data from the data layer |
| Save business-logic UI state in `SavedStateHandle` | Complex or large data does not belong there | Restore it from the data layer after recreation |

## Common Issues & Solutions

### State is not restored in the test but works in the app

**Cause**: Content was set with `composeTestRule.setContent` instead of the tester, or the state is held with `remember`.
**Fix**: Use `restorationTester.setContent { }`; switch the state holder to `rememberSaveable`.

### Non-primitive state fails to restore

**Cause**: The type has no saver. **Fix**: Use `Parcelize`, `listSaver`, `mapSaver`, or a custom `Saver`.

## Related References

- [test-suite-structure.md](../core/test-suite-structure.md) — rules and `setContent`
- [component-testing.md](component-testing.md) — testing composables in isolation
- [coroutines-viewmodels.md](coroutines-viewmodels.md) — ViewModel and coroutine setup
- [device-configuration.md](../advanced/device-configuration.md) — font scale, locale, window size overrides

## Sources

- https://developer.android.com/develop/ui/compose/state-saving
- https://developer.android.com/develop/ui/compose/testing/common-patterns
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/junit4/StateRestorationTester
- https://developer.android.com/training/testing/different-screens
- https://developer.android.com/training/testing/local-tests/robolectric
- https://robolectric.org/blog/2026/07/03/designing-local-testing-libraries/
