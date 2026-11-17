# Test Doubles: Fakes and Shadows

## Table of Contents

1. [Fakes](#fakes)
2. [Shadows](#shadows)
3. [Android Classes: Do Not Mock](#android-classes-do-not-mock)
4. [Threads and Executors](#threads-and-executors)
5. [Related References](#related-references)
6. [Sources](#sources)

## Fakes

A post on robolectric.org that calls itself an outside read, not an official AndroidX position, says Android's guidance also prefers fakes (lightweight, no mocking framework) over mocks, and tells consumers to "check with the authors to see if they provide any officially-supported testing infrastructures, such as fakes, that you can reliably depend on".

In general, if you implement a testable architecture you shouldn't need to use Robolectric for unit testing as your code should be testable in isolation, with no dependencies on the Android framework.

The Compose testing page shows a typical UI test that passes a fake UI state to the content under test:

```kotlin
class MyComposeTest {

    @get:Rule val composeTestRule = createComposeRule()
    // use createAndroidComposeRule<YourActivity>() if you need access to
    // an activity

    @Test
    fun myTest() {
        // Start the app
        composeTestRule.setContent {
            MyAppTheme {
                MainScreen(uiState = fakeUiState, /*...*/)
            }
        }

        composeTestRule.onNodeWithText("Continue").performClick()

        composeTestRule.onNodeWithText("Welcome").assertIsDisplayed()
    }
}
```

For authors of Robolectric-based local-testing libraries, the checklist in the same post (an outside read, not an official AndroidX position) says: Prefer a fake to a shadow. Write a plain object that implements your real interface and holds in-memory state. Reach for a Robolectric shadow only for genuine platform surfaces (a system property in AppFunctions, service binding in Tiles, a Parcel in Lifecycle), and shadow the OS outright only when the contract is the OS (XR projected).

## Shadows

You can also use Robolectric's fakes (called shadows) as dependencies for unit tests. For example, if your class uses a Bundle or you need to fake a Bluetooth connection.

Robolectric works by creating a runtime environment that includes the real Android framework code. However, there are limitations:

- Android native code cannot execute on your development machine.
- There are no Android system services running on your development machine.
- Android includes next to no APIs suitable for testing.

Robolectric fills these gaps with a set of classes known as Shadows. Each shadow can modify or extend the behavior of a corresponding class in the Android OS.

Shadow classes are associated to the class that they Shadow with an @Implements annotation on the class declaration. Shadow methods must be marked with the @Implementation annotation.

```kotlin
@Implements(ImageView::class)
class ShadowImageView : ShadowView {
  @Implementation
  protected fun setImageResource(resId: Int) {
    // Implementation goes here
  }
}
```

## Android Classes: Do Not Mock

DON'T mock or spy on Android classes that will be acted on by other Android code (e.g. Context, SharedPreferences, and many others). Stubbing is very brittle and can lead to breakages on Robolectric or Android Platform upgrades. The small exceptions to this rule are classes with very narrow responsibilities, such as event listeners.

DO test layout inflation in your Robolectric test and ensure that click listeners are set up correctly by testing the Activity and layout interaction directly, rather than mocking the LayoutInflater or providing an abstraction over the View.

DO use public lifecycle APIs (e.g., via Robolectric.buildActivity()), rather than exposing @VisibleForTesting methods when testing Android components such as Activities and Services. Calling those methods directly makes it difficult to refactor the code under test later. The AndroidX Test page on Robolectric.org says `Robolectric.buildActivity()` has proved problematic as it requires developers to fully understand valid lifecycle transitions and possible valid states, and that `ActivityScenario` provides a replacement, but places tighter restrictions around lifecycle transitions.

## Threads and Executors

DO limit the number of threads that are running during each test. Rogue threads often cause test pollution because they are not automatically cleaned up between tests. One of the main sources of additional threads during tests are ExecutorServices that maintain thread pools. If possible, mock dependent components that spawn threads, or use MoreExecutors.directExecutor(). If it's necessary to run multiple threads during a test, make sure to explicitly stop all threads and ExecutorServices to avoid test pollution.

## Related References

- **Choosing test types**: See [test-architecture.md](test-architecture.md)
- **Coroutine tests**: See [coroutines.md](../testing-patterns/coroutines.md)

## Sources

- https://developer.android.com/develop/ui/compose/testing
- https://developer.android.com/training/testing/local-tests/robolectric
- https://robolectric.org/best-practices
- https://robolectric.org/extending
- https://robolectric.org/blog/2026/07/03/designing-local-testing-libraries
