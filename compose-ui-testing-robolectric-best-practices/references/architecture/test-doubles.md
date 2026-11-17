# Test Doubles: Shadows and Mocks

## Table of Contents

1. [Test APIs and Isolation](#test-apis-and-isolation)
2. [No Mocking Frameworks Required](#no-mocking-frameworks-required)
3. [Shadows](#shadows)
4. [Compose Test Example](#compose-test-example)
5. [Custom Shadows](#custom-shadows)
6. [Mocking and Spying on Android Classes](#mocking-and-spying-on-android-classes)
7. [Activity Lifecycle](#activity-lifecycle)
8. [Threads and Executors](#threads-and-executors)
9. [Related References](#related-references)
10. [Sources](#sources)

## Test APIs and Isolation

Unlike traditional emulator-based Android tests, Robolectric tests run inside a sandbox which allows the Android environment to be precisely configured to the desired conditions for each test, isolates each test from its neighbors, and extends the Android framework with test APIs which provide minute control over the Android framework's behavior and visibility of state for assertions.

While much of the Android framework will work as expected inside a Robolectric test, some Android components' regular behavior doesn't translate well to unit tests: hardware sensors need to be simulated, system services need to be loaded with test fixture data. In those cases, Robolectric provides a test double that's suitable for most unit testing scenarios.

## No Mocking Frameworks Required

An alternate approach to Robolectric is to use mock frameworks such as Mockito or to mock out the Android SDK. While this is a valid approach, it often yields tests that are essentially reverse implementations of the application code.

Robolectric allows a test style that is closer to black box testing, making the tests more effective for refactoring and allowing the tests to focus on the behavior of the application instead of the implementation of Android. You can still use a mocking framework along with Robolectric if you like.

## Shadows

Robolectric works by creating a runtime environment that includes the real Android framework code. However, there are limitations:

- Android native code cannot execute on your development machine.
- There are no Android system services running on your development machine.
- Android includes next to no APIs suitable for testing.

Robolectric fills these gaps with a set of classes known as Shadows. Each shadow can modify or extend the behavior of a corresponding class in the Android OS.

You can also use Robolectric's fakes (called shadows) as dependencies for unit tests. For example, if your class uses a Bundle or you need to fake a Bluetooth connection.

Shadow classes always need a public no-arg constructor so that the Robolectric framework can instantiate them. They are associated to the class that they Shadow with an `@Implements` annotation on the class declaration. Shadow methods must be marked with the `@Implementation` annotation.

```kotlin
@Implements(ImageView::class)
class ShadowImageView : ShadowView {
  @Implementation
  protected fun setImageResource(resId: Int) {
    // Implementation goes here
  }
}
```

### Test APIs

Many test APIs are extensions to individual Android classes, and can be accessed using the `shadowOf()` method:

```kotlin
// Retrieve all the toasts that have been displayed
val toasts = shadowOf(application).shownToasts
```

Additional test APIs are accessible as static methods on special classes called shadows, which correspond to Android framework classes:

```kotlin
// Simulate a new display being plugged into the device
ShadowDisplayManager.addDisplay("xlarge-port")
```

## Compose Test Example

A typical UI test for Compose looks like this:

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

## Custom Shadows

Custom shadows are structured much the same as normal shadow classes. They must include the `@Implements` annotation on the class definition. Your shadow class may also extend one of the stock Robolectric shadows if you like.

```kotlin
@Implements(Bitmap::class)
class MyShadowBitmap {
  @RealObject private lateinit var realBitmap: Bitmap
  private var bitmapQuality: Int = -1

  @Implementation
  fun compress(format: Bitmap.CompressFormat, quality: Int, stream: OutputStream): Boolean {
    bitmapQuality = quality
    return realBitmap.compress(format, quality, stream)
  }

  fun getQuality(): Int {
    return bitmapQuality
  }
}
```

Custom Shadows get hooked up to Robolectric using the `@Config` annotation on the test class or test method, using the `shadows` array attribute.

```kotlin
@Config(
  sdk = Build.VERSION_CODES.TIRAMISU,
  shadows = [ShadowFoo::class, ShadowBar::class]
)
class SandwichTest
```

If you would like your custom shadows to be applied to all tests in your suite or a certain package, you can configure shadows through the `robolectric.properties` file.

Note, by default `Shadows.shadowOf()` method will not work with custom shadows. You can instead use `Shadow.extract()` and cast the return value to the custom Shadow class you implemented.

Typically `@Implementation` methods should have the `protected` modifier. The intention is to reduce the API surface area of the Shadows; the test author should always call such methods on the Android framework class directly.

Don't override `equals`, `hashCode` and `toString` in shadows. Avoid this unless you are mimicking behaviour in the class being shadowed. To test equality for comparisons in tests prefer helpers or assertion library extensions. Prefer adding a `describe()` method instead of shadowing `toString()`.

Rather than using shadows as glorified argument captors, prefer writing a shadow that encourages testing behaviour. For example, don't add a method that exposes registered listeners, rather add an `@Implementation` for a method that would invoke those listeners.

### Use Caution When Shadowing Your Own Code

Robolectric provides a lot of power which requires responsible usage. Shadows are ideal for testing interaction with the Android framework as the framework doesn't support dependency injection and makes liberal use of static code.

Before writing custom shadows for your own code, consider if you can't better refactor your code and use a popular mocking library such as Mockito.

## Mocking and Spying on Android Classes

DON'T mock or spy on Android classes that will be acted on by other Android code (e.g. `Context`, `SharedPreferences`, and many others). Stubbing is very brittle and can lead to breakages on Robolectric or Android Platform upgrades. The small exceptions to this rule are classes with very narrow responsibilities, such as event listeners.

DO test layout inflation in your Robolectric test and ensure that click listeners are set up correctly by testing the Activity and layout interaction directly, rather than mocking the `LayoutInflater` or providing an abstraction over the `View`.

DO use public lifecycle APIs (e.g., via `Robolectric.buildActivity()`), rather than exposing `@VisibleForTesting` methods when testing Android components such as Activitys and Services. Calling those methods directly makes it difficult to refactor the code under test later.

## Activity Lifecycle

Robolectric provides `Robolectric.setupActivity()` for the coarse-grained use case where you require a launched activity in the resumed state and visible for the user to interact with. Robolectric also provides `Robolectric.buildActivity()`, which returns an `ActivityController` that allows the developer to step through the Activity lifecycle. This has proved problematic as it requires developers to fully understand valid lifecycle transitions and possible valid states. Using an Activity in an invalid state has undefined behavior and can cause compatibility issues when running on different Android test runtimes or when upgrading to newer versions of Robolectric.

`ActivityScenario` provides a replacement for both of these use cases, but places tighter restrictions around lifecycle transitions, namely that invalid or incomplete transitions are not possible. If you'd like a Rule-based equivalent please use `ActivityScenarioRule` instead.

```kotlin
import androidx.lifecycle.Lifecycle
import androidx.test.core.app.ActivityScenario

class LocationTrackerActivityTest {
    @Test
    fun locationListenerShouldBeUnregisteredInCreatedState() {
        // GIVEN
        val scenario = ActivityScenario.launchActivity<LocationTrackerActivity>()

        // WHEN
        scenario.moveToState(Lifecycle.State.CREATED)

        // THEN
        scenario.onActivity { activity ->
            assertThat(activity.locationListener).isNull()
        }
    }
}
```

## Threads and Executors

DO limit the number of threads that are running during each test. Rogue threads often cause test pollution because they are not automatically cleaned up between tests.

Oftentimes threads are inadvertently spawned when using third-party libraries (e.g., for networking) or background processing components. One of the main sources of additional threads during tests are ExecutorServices that maintain thread pools.

If possible, mock dependent components that spawn threads, or use `MoreExecutors.directExecutor()`. If it's necessary to run multiple threads during a test, make sure to explicitly stop all threads and ExecutorServices to avoid test pollution.

## Related References

- **Choosing test types**: See [test-architecture.md](test-architecture.md)
- **Coroutine tests**: See [coroutines.md](../testing-patterns/coroutines.md)

## Sources

- https://developer.android.com/develop/ui/compose/testing
- https://developer.android.com/training/testing/local-tests/robolectric
- https://robolectric.org
- https://robolectric.org/best-practices
- https://robolectric.org/extending
- https://robolectric.org/androidx_test
- https://robolectric.org/writing-a-test
- https://robolectric.org/configuring
