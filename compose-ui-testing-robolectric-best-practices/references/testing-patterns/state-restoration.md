# State Restoration Testing

## Table of Contents

1. [Verify State Restoration](#verify-state-restoration)
2. [StateRestorationTester API Reference](#staterestorationtester-api-reference)
3. [Activity Recreation on Robolectric](#activity-recreation-on-robolectric)
4. [Related References](#related-references)
5. [Sources](#sources)

## Verify State Restoration

Verify that the state of your Compose elements is correctly restored when the activity or process is recreated. Perform such checks without relying on activity recreation with the `StateRestorationTester` class.

This class lets you simulate the recreation of a composable. It's especially useful to verify the implementation of `rememberSaveable`.

```kotlin
class MyStateRestorationTests {

    @get:Rule
    val composeTestRule = createComposeRule()

    @Test
    fun onRecreation_stateIsRestored() {
        val restorationTester = StateRestorationTester(composeTestRule)

        restorationTester.setContent { MainScreen() }

        // TODO: Run actions that modify the state

        // Trigger a recreation
        restorationTester.emulateSavedInstanceStateRestore()

        // TODO: Verify that state has been correctly restored.
    }
}
```

## StateRestorationTester API Reference

### androidx.compose.ui:ui-test-junit4 StateRestorationTester

Helps to test the state restoration for your Composable component. Instead of calling `ComposeContentTestRule.setContent` you need to use `setContent` on this object, then change your state so there is some change to be restored, then execute `emulateSavedInstanceStateRestore` and assert your state is restored properly. Note that this tests only the restoration of the local state of the composable you passed to `setContent` and useful for testing `androidx.compose.runtime.saveable.rememberSaveable` integration. It is not testing the integration with any other life cycles or Activity callbacks.

#### emulateSavedInstanceStateRestore

Saves all the state stored via savedInstanceState or `androidx.compose.runtime.saveable.rememberSaveable`, disposes current composition, and composes again the content passed to `setContent`. Allows to test how your component behaves when the state restoration is happening. Note that the state stored via regular `state()` or `remember()` will be lost.

### androidx.compose.ui:ui-test StateRestorationTester

Helps to test the state restoration for your Composable component. Instead of calling `ComposeUiTest.setContent` you need to use `setContent` on this object, then change your state so there is some change to be restored, then execute `emulateSaveAndRestore` and assert your state is restored properly. Note that this only tests the restoration of the local state of the composable you passed to `setContent` and it is useful for testing uses of `rememberSaveable`. It is not testing the integration with app and/or platform specific lifecycles.

#### emulateSaveAndRestore

Emulates a save and restore cycle of the current composition. First all state that is remembered with `rememberSaveable` is stored, then the current composition is disposed, and finally the composition is composed again. This allows you to test how your component behaves when state restoration is happening. Note that state stored via `remember` will be lost.

### Classes

| Artifact | Class | Constructor | Function | Added in |
| --- | --- | --- | --- | --- |
| `androidx.compose.ui:ui-test-junit4` | `class StateRestorationTester` | `StateRestorationTester(composeTestRule: ComposeContentTestRule)` | `emulateSavedInstanceStateRestore()` | 1.0.0 |
| `androidx.compose.ui:ui-test` | `@ExperimentalTestApi class StateRestorationTester` | `StateRestorationTester(composeTest: ComposeUiTest)` | `emulateSaveAndRestore()` | 1.2.0 |

## Activity Recreation on Robolectric

Robolectric was conceived as a way to enable "unit testing" in Android apps. For example, you can simulate the launch of an Activity and test the logic inside it, calling all the lifecycle methods.

Robolectric can also run UI tests such as Espresso or Compose tests. Any UI test present in the `test` source set runs with Robolectric.

```kotlin
import androidx.test.espresso.Espresso.onView

@RunWith(AndroidJUnit4::class)
class AddContactActivityTest {
    @Test
    fun inputTextShouldBeRetainedAfterActivityRecreation() {
        // GIVEN
        val contactName = "Test User"
        val scenario = ActivityScenario.launchActivity<AddContactActivity>()

        // WHEN
        // Enter contact name
        onView(withId(R.id.contact_name_text))
            .perform(typeText(contactName))
        // Destroy and recreate Activity
        scenario.recreate()

        // THEN
        // Check contact name was preserved.
        onView(withId(R.id.contact_name_text))
            .check(matches(withText(contactName)))
     }
}
```


## Related References

- [test-suite-structure.md](../core/test-suite-structure.md) - rules and `setContent`
- [component-testing.md](component-testing.md) - testing composables in isolation
- [coroutines.md](coroutines.md) - coroutine setup
- [device-configuration.md](../advanced/device-configuration.md) - device configuration overrides

## Sources

- https://developer.android.com/develop/ui/compose/testing/common-patterns
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/junit4/StateRestorationTester
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/StateRestorationTester
- https://developer.android.com/training/testing/local-tests/robolectric
