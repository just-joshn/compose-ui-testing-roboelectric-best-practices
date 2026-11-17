# Views, Espresso & UiAutomator Interoperability

## Table of Contents

1. [Espresso and Compose Together](#espresso-and-compose-together)
2. [Scoping Compose Searches to Views](#scoping-compose-searches-to-views)
3. [Main Thread Synchronization](#main-thread-synchronization)
4. [Interoperability with UiAutomator](#interoperability-with-uiautomator)
5. [Related References](#related-references)
6. [Sources](#sources)

## Espresso and Compose Together

In a hybrid app, you can find Compose components inside view hierarchies and views inside Compose composables (via the `AndroidView` composable).

There are no special steps needed to match either type. You match views with Espresso's `onView`, and Compose elements with the `ComposeTestRule`.

```kotlin
@Test
fun androidViewInteropTest() {
    // Check the initial state of a TextView that depends on a Compose state.
    Espresso.onView(withText("Hello Views")).check(matches(isDisplayed()))
    // Click on the Compose button that changes the state.
    composeTestRule.onNodeWithText("Click here").performClick()
    // Check the new value.
    Espresso.onView(withText("Hello Compose")).check(matches(isDisplayed()))
}
```

Robolectric can also run UI tests such as Espresso or Compose tests.

Espresso is the View matching and interaction library of choice for instrumentation tests. Since Robolectric 4.0, Espresso APIs are now supported in Robolectric tests.

Robolectric has very limited APIs for View interaction. In most cases, test writers can just use Android APIs, such as `Activity.findViewById()` which was safe since Robolectric tests do not have to worry about synchronization between test and UI threads.

## Scoping Compose Searches to Views

The `onRootWithViewInteraction` API is included in `androidx.compose.ui:ui-test-junit4:1.12.0-alpha01+` and `androidx.compose.ui:ui-test:1.12.0-alpha01+`. This API is experimental and subject to change.

When migrating complex UIs to Compose, you might encounter identical Compose elements nested inside multiple traditional Android Views—such as within a `RecyclerView` or a `ViewPager`. In these scenarios, a standard Compose search like `onNodeWithText("Save")` might fail with a "Multiple nodes found" error.

Instead of modifying your production code to inject dynamic test tags to distinguish these elements, you can scope your Compose test directly to a specific Android View.

Use the `onRootWithViewInteraction` API on your test rule. This function accepts an Espresso `ViewInteraction`, allowing you to leverage Espresso to isolate a specific container View and perform Compose interactions exclusively within that scoped hierarchy.

This API is specifically designed for testing Compose components nested inside Views. To test Views nested inside Compose, continue using standard Espresso interactions.

### API

| Receiver | Artifact |
| --- | --- |
| `ComposeTestRule.onRootWithViewInteraction` | `androidx.compose.ui:ui-test-junit4` |
| `ComposeUiTest.onRootWithViewInteraction` | `androidx.compose.ui:ui-test` |

```kotlin
fun ComposeTestRule.onRootWithViewInteraction(
    interaction: ViewInteraction
): SemanticsNodeInteractionsProvider
```

`onRootWithViewInteraction`: It resolves the View from the Espresso interaction, locates all Compose roots within that view hierarchy, and creates a new, scoped `SemanticsNodeInteractionsProvider`.

### With a Rule

Scopes the Compose interaction to the View hierarchy matched by the provided Espresso `ViewInteraction`.

```kotlin
// Select the "Header" View container
val headerInteraction = onView(withId(header_id))

// Scope the Compose interaction to only the Header
composeTestRule
    .onRootWithViewInteraction(headerInteraction)
    .onNodeWithContentDescription("Settings")
    .performClick()
```

### Interact with a List Item

If you need to interact with a Compose element inside a specific `RecyclerView` row, use Espresso to locate the row, then scope your Compose interaction to it. This ignores identical Compose elements in all other rows.

```kotlin
@Test
fun testComposeButtonInsideRecyclerViewItem() = runComposeUiTest {
    // Scroll to the desired position using Espresso
    Espresso.onView(withId(recyclerViewId))
        .perform(RecyclerViewActions.scrollToPosition<MyViewHolder>(3))

    // Define an Espresso ViewInteraction that uniquely identifies the row
    val rowView = Espresso.onView(
        allOf(
            withId(rootViewId),
            hasDescendant(withText("Item #3"))
        )
    )

    // Scope the Compose search strictly to that specific row View
    onRootWithViewInteraction(rowView)
        .onNode(hasText("Like"))
        .performClick()
}
```

### Resolve Ambiguity in ViewPagers

When multiple fragments with identical Compose layouts are in memory simultaneously, you can scope the search to the specific fragment's root View ID to prevent matching ambiguity.

```kotlin
@Test
fun testComposeButtonInsideViewPagerItem() = runComposeUiTest {
    // Swipe to the desired page using Espresso
    Espresso.onView(withId(viewPagerViewId)).perform(swipeLeft())

    // Identify the specific container view using Espresso
    val fragmentB = Espresso.onView(withId(fragmentRootViewId))

    // The generic text "Save" is now unique within this view scope
    onRootWithViewInteraction(fragmentB)
        .onNode(hasText("Save"))
        .assertIsDisplayed()
}
```

## Main Thread Synchronization

Compose tests are synchronized by default with your UI. When you call an assertion or an action with the `ComposeTestRule`, the test is synchronized beforehand, waiting until the UI tree is idle.

Compose testing now supports main thread synchronization, allowing you to safely call `waitForIdle`— and by extension, Compose UI actions and assertions — directly from the main thread. Changes to support main thread synchronization are included in `androidx.compose.ui:ui-test-junit4:1.13.0-alpha01+` and `androidx.compose.ui:ui-test:1.13.0-alpha01+`.

Previously, Compose testing strictly enforced a two-thread model: test execution occurred on a background test thread, while UI updates happened on the main thread. Calling synchronization methods like `waitForIdle` or `runOnIdle` from the main thread (for example, inside a `runOnUiThread` block) would throw an `IllegalStateException` because the framework enforced strict thread checks to prevent main-thread synchronization. With main thread synchronization enabled, the Compose test framework can now advance the clock and process pending work even when blocking calls are made on the main thread.

### When to Use Main Thread Synchronization

While keeping tests on the background thread remains the standard for pure Compose tests, main thread synchronization is highly advantageous in a few specific scenarios:

- **Complex View interoperability**: When testing hybrid UIs containing both Compose and legacy Android Views, manipulating Views often requires running on the main thread. You can now interact with Views and assert on Compose nodes sequentially without constantly switching thread contexts.
- **Synchronous state mutations**: If your architecture relies on strictly main-thread-bound state holders, you can now mutate state and immediately wait for the Compose UI to settle without leaving the main thread.
- **Custom test runners**: If you are building custom testing infrastructure or utilizing environments where the test runner inherently executes on the main thread, Compose tests now execute cleanly without requiring background-thread delegation.

For standard, Compose-only tests, you don't need to change your existing test code. The default background-thread execution remains fully supported and performant.

Historically, because synchronization was strictly prohibited on the main thread, developers had to bounce back-and-forth between the background test runner thread and the UI thread, leading to disjointed tests:

```kotlin
@Test
fun testBidirectionalInteropUIUpdates_old() {
    val scenario = launchFragmentInContainer<InteropFragment>()
    composeTestRule.waitForIdle()
    scenario.onFragment { fragment ->
        fragment.legacyButton.performClick()
    }
    // Jump to Test Thread to verify state settles inside compose
    composeTestRule.waitForIdle()
    composeTestRule.onNodeWithText("Legacy Clicks: 1").assertIsDisplayed()
    composeTestRule.onNodeWithText("Increment Legacy TextView").performClick()
    composeTestRule.waitForIdle()
    // Jump back to Main Thread to verify target view state settles
    scenario.onFragment { fragment ->
        assert(fragment.legacyTextView.text.toString() == "Compose Clicks: 1")
    }
}
```

With main thread synchronization enabled, the assertions for Compose and View hierarchies can be executed in the same block:

```kotlin
@Test
fun testBidirectionalInteropUIUpdates_new() {
    val scenario = launchFragmentInContainer<InteropFragment>()
    composeTestRule.waitForIdle()
    scenario.onFragment { fragment ->
        fragment.legacyButton.performClick()
        composeTestRule.waitForIdle()
        composeTestRule.onNodeWithText("Legacy Clicks: 1").assertIsDisplayed()
        composeTestRule.onNodeWithText("Increment Legacy TextView").performClick()
        composeTestRule.waitForIdle()
        assert(fragment.legacyTextView.text.toString() == "Compose Clicks: 1")
    }
}
```

## Interoperability with UiAutomator

By default, composables are accessible from UiAutomator only by their convenient descriptors (displayed text, content description, etc.). If you want to access any composable that uses `Modifier.testTag`, you need to enable the semantic property `testTagsAsResourceId` for the particular composable's subtree. Enabling this behavior is useful for composables that don't have any other unique handle, such as scrollable composables (for example, `LazyColumn`).

This feature is available in Jetpack Compose version 1.2.0-alpha08 and higher.

Enable the semantic property only once high in your composables hierarchy to ensure all nested composables with `Modifier.testTag` are accessible from UiAutomator.

```kotlin
Scaffold(
    // Enables for all composables in the hierarchy.
    modifier = Modifier.semantics {
        testTagsAsResourceId = true
    }
){
    // Modifier.testTag is accessible from UiAutomator for composables nested here.
    LazyColumn(
        modifier = Modifier.testTag("myLazyColumn")
    ){
        // Content
    }
}
```

Any composable with the `Modifier.testTag(tag)` can be accessible with the use of `By.res(resourceName)` using the same `tag` as the `resourceName`.

Make sure you don't use `By.res(resourcePackage, resourceId)` as this formats the argument as `$resourcePackage:id/$resourceId`, which is different from `Modifier.testTag`.

```kotlin
val device = UiDevice.getInstance(getInstrumentation())

val lazyColumn: UiObject2 = device.findObject(By.res("myLazyColumn"))
// Some interaction with the lazyColumn.
```

## Related References

- [test-suite-structure.md](../core/test-suite-structure.md) for rule choice and `ComponentActivity`
- [synchronization.md](../core/synchronization.md) for idling, `waitUntil`, and main-thread sync
- [semantics-finders.md](../core/semantics-finders.md) for matchers and `testTag`
- [runtime-modes.md](../core/runtime-modes.md) for the Looper mode

## Sources

- https://developer.android.com/develop/ui/compose/testing/interoperability
- https://developer.android.com/develop/ui/compose/testing/synchronization
- https://developer.android.com/training/testing/local-tests/robolectric
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/junit4/ComposeTestRule
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/ComposeUiTest
- https://robolectric.org/androidx_test/
