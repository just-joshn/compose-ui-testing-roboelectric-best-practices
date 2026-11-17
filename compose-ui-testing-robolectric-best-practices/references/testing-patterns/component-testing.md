# Component Testing

## Table of Contents

1. [Setup](#setup)
2. [Test in Isolation](#test-in-isolation)
3. [Access the Activity and Resources After Setting Your Own Content](#access-the-activity-and-resources-after-setting-your-own-content)
4. [Custom Semantics Properties](#custom-semantics-properties)
5. [Running Compose Tests on Robolectric](#running-compose-tests-on-robolectric)
6. [Best Practices](#best-practices)
7. [Related References](#related-references)
8. [Sources](#sources)

## Setup

### Add the Dependencies

First, add the following dependencies to the `build.gradle` file of the module containing your UI tests:

```groovy
// Test rules and transitive dependencies:
androidTestImplementation("androidx.compose.ui:ui-test-junit4:$compose_version")
// Needed for createComposeRule(), but not for createAndroidComposeRule<YourActivity>():
debugImplementation("androidx.compose.ui:ui-test-manifest:$compose_version")
```

This module includes a `ComposeTestRule` and an implementation for Android called `AndroidComposeTestRule`. Through this rule you can set Compose content or access the activity.

### Write a Test

You construct the rules using factory functions, either `createComposeRule` or, if you need access to an activity, `createAndroidComposeRule`. A typical UI test for Compose looks like this:

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

## Test in Isolation

`ComposeTestRule` lets you start an activity displaying any composable: your full application, a single screen, or a small element.

It's also a good practice to check that your composables are correctly encapsulated and they work independently, allowing for easier and more focused UI testing.

This doesn't mean you should *only* create unit UI tests. UI tests scoping larger parts of your UI are also very important.

## Access the Activity and Resources After Setting Your Own Content

Oftentimes you need to set the content under test using `composeTestRule.setContent` and you also need to access activity resources, for example to assert that a displayed text matches a string resource. However, you can't call `setContent` on a rule created with `createAndroidComposeRule()` if the activity already calls it.

A common pattern to achieve this is to create an `AndroidComposeTestRule` using an empty activity such as `ComponentActivity`.

```kotlin
class MyComposeTest {

    @get:Rule
    val composeTestRule = createAndroidComposeRule<ComponentActivity>()

    @Test
    fun myTest() {
        // Start the app
        composeTestRule.setContent {
            MyAppTheme {
                MainScreen(uiState = exampleUiState, /*...*/)
            }
        }
        val continueLabel = composeTestRule.activity.getString(R.string.next)
        composeTestRule.onNodeWithText(continueLabel).performClick()
    }
}
```

`ComponentActivity` needs to be added to your app's `AndroidManifest.xml` file. Enable that by adding this dependency to your module:

```kotlin
debugImplementation("androidx.compose.ui:ui-test-manifest:$compose_version")
```

## Custom Semantics Properties

### Define the Property

You can create custom semantics properties to expose information to tests. To do this, define a new `SemanticsPropertyKey` and make it available using the `SemanticsPropertyReceiver`.

```kotlin
// Creates a semantics property of type Long.
val PickedDateKey = SemanticsPropertyKey<Long>("PickedDate")
var SemanticsPropertyReceiver.pickedDate by PickedDateKey
```

### Set the Property in the Modifier

Now use that property in the `semantics` modifier:

```kotlin
val datePickerValue by remember { mutableStateOf(0L) }
MyCustomDatePicker(
    modifier = Modifier.semantics { pickedDate = datePickerValue }
)
```

### Assert the Property in a Test

From tests, use `SemanticsMatcher.expectValue` to assert the value of the property:

```kotlin
composeTestRule
    .onNode(SemanticsMatcher.expectValue(PickedDateKey, 1445378400)) // 2015-10-21
    .assertExists()
```

### When to Use Custom Semantics Properties

You should only use custom Semantics properties when it's hard to match a specific item using the given finders and matchers.

Using custom Semantics properties to expose visual properties such as colors, font size or rounded corner radius is not recommended, as it can pollute production code and wrong implementations can lead to bugs that are hard to find.

## Running Compose Tests on Robolectric

### Convert an Instrumented Test

Robolectric can also run UI tests such as Espresso or Compose tests. You can convert an instrumented test to Robolectric by moving it to the `test` source set and setting up the Robolectric dependencies.

```kotlin
android {
  testOptions {
    unitTests {
      isIncludeAndroidResources = true
    }
  }
}
```

Any UI test present in the `test` source set runs with Robolectric.

### Robolectric Versus Device Tests

You can run behavior tests on Robolectric as the fidelity needed for it is more than enough. For example, when a Compose test verifies that the UI has changed after clicking a button.

You must decide whether Robolectric's implementation is good enough for each use case, but here are some recommendations:

- Use Robolectric for isolated UI behavior tests for components, feature or application tests. In general these tests check the state management and behavior of the UIs and don't interact with external dependencies.

In summary, Robolectric provides enough fidelity to run most UI tests but some cases will still require device tests, for example those related to system UI like edge-to-edge or picture-in-picture, or when relying on unsupported features, like `WebView`.

## Best Practices

DON'T mock or spy on Android classes that will be acted on by other Android code (e.g. `Context`, `SharedPreferences`, and many others). Stubbing is very brittle and can lead to breakages on Robolectric or Android Platform upgrades. The small exceptions to this rule are classes with very narrow responsibilities, such as event listeners.

## Related References

- **Setup**: See [test-suite-structure.md](../core/test-suite-structure.md) for rules and test anatomy
- **Selectors**: See [semantics-finders.md](../core/semantics-finders.md) for finders and custom semantics keys
- **Assertions**: See [assertions-actions.md](../core/assertions-actions.md) for assertions and actions
- **State restoration**: See [state-restoration.md](state-restoration.md) for `StateRestorationTester`
- **Accessibility**: See [accessibility.md](accessibility.md) for focus and accessibility checks
- **Device configuration**: See [device-configuration.md](../advanced/device-configuration.md) for `DeviceConfigurationOverride`

## Sources

- https://developer.android.com/develop/ui/compose/testing
- https://developer.android.com/develop/ui/compose/testing/common-patterns
- https://developer.android.com/training/testing/local-tests/robolectric
- https://robolectric.org/getting-started
- https://robolectric.org/best-practices
