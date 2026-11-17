# State Restoration Testing

## Table of Contents

1. [Verify State Restoration](#verify-state-restoration)
2. [StateRestorationTester API Reference](#staterestorationtester-api-reference)
3. [Activity Recreation on Robolectric](#activity-recreation-on-robolectric)
4. [ViewModel Process Death](#viewmodel-process-death)
5. [Related References](#related-references)
6. [Sources](#sources)

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

Instead of calling `ComposeContentTestRule.setContent` you need to use `StateRestorationTester.setContent` on this object, then change your state so there is some change to be restored, then execute `emulateSavedInstanceStateRestore()` and assert your state is restored properly.

`emulateSavedInstanceStateRestore()` saves all the state stored via savedInstanceState or `rememberSaveable`, disposes current composition, and composes again the content passed to `StateRestorationTester.setContent`. Note that the state stored via regular `state()` or `remember()` will be lost.

Note that this tests only the restoration of the local state of the composable you passed to `StateRestorationTester.setContent`. It is not testing the integration with any other life cycles or Activity callbacks.

## Activity Recreation on Robolectric

Android's Robolectric page says you can simulate the launch of an Activity and test the logic inside it, calling all the lifecycle methods. In its UI testing section, right after the sentence "Any UI test present in the `test` source set runs with Robolectric.", it shows an Espresso example that destroys and recreates the Activity with `scenario.recreate()`:

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

## ViewModel Process Death

A Robolectric blog post, which describes itself as "an outside read of the code as it stands in mid-2026, not an official AndroidX position", says a ViewModel needs a ViewModelStoreOwner + SavedStateRegistryOwner + lifecycle from its host, and the hardest thing to test is process death. `viewModelScenario { }` fabricates that owner trio in-memory and exposes `recreate()`:

```kotlin
viewModelScenario { TestViewModel(handle = createSavedStateHandle()) }.use { scenario ->
    scenario.viewModel.handle["key"] = "value"
    scenario.recreate()                                  // simulate process death
    assertThat(scenario.viewModel.handle.get<String>("key")).isEqualTo("value")
}
```

The same blog post says `recreate()` round-trips the saved state through a real Parcel (and enforces the 1 MB Binder limit), reproducing real serialization loss rather than an in-memory copy.

## Related References

- [test-suite-structure.md](../core/test-suite-structure.md) - rules and `setContent`
- [component-testing.md](component-testing.md) - testing composables in isolation
- [coroutines.md](coroutines.md) - coroutine setup
- [device-configuration.md](../advanced/device-configuration.md) - device configuration overrides

## Sources

- https://developer.android.com/develop/ui/compose/testing/common-patterns
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/junit4/StateRestorationTester
- https://developer.android.com/training/testing/local-tests/robolectric
- https://robolectric.org/blog/2026/07/03/designing-local-testing-libraries
