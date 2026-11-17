# Views, Espresso & UiAutomator Interoperability

## Table of Contents

1. [Compose Inside Views, Views Inside Compose](#compose-inside-views-views-inside-compose)
2. [Espresso and the Compose Rule Together](#espresso-and-the-compose-rule-together)
3. [Scoping Compose Finders to a View](#scoping-compose-finders-to-a-view)
4. [Synchronization Across Frameworks](#synchronization-across-frameworks)
5. [UiAutomator (Device Only)](#uiautomator-device-only)
6. [Common Issues & Solutions](#common-issues--solutions)
7. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
8. [Related References](#related-references)
9. [Sources](#sources)

## Compose Inside Views, Views Inside Compose

In a hybrid app, Compose components sit inside view hierarchies and views sit inside composables through `AndroidView`. There are "no special steps" to match either: match Views with Espresso's `onView`, and Compose elements with the Compose test rule, in the same test.

| Target | API |
| --- | --- |
| View | `Espresso.onView(...)` |
| Composable | `composeTestRule.onNode*(...)` |
| Compose nested in a specific View | `onRootWithViewInteraction(viewInteraction)` (experimental) |
| Composable with `Modifier.testTag` from UiAutomator | `By.res(tag)` after enabling `testTagsAsResourceId` |

Robolectric supports Espresso APIs since 4.0. Robolectric has very limited APIs for `View` interaction, so test writers can use Android APIs such as `Activity.findViewById()`, which is safe because Robolectric tests do not have to synchronize test and UI threads.

## Espresso and the Compose Rule Together

```kotlin
@RunWith(AndroidJUnit4::class)
class InteropTest {
    @get:Rule val composeTestRule = createAndroidComposeRule<ComponentActivity>()

    @Test
    fun androidViewInteropTest() {
        // Check the initial state of a TextView that depends on a Compose state.
        Espresso.onView(withText("Hello Views")).check(matches(isDisplayed()))

        // Click on the Compose button that changes the state.
        composeTestRule.onNodeWithText("Click here").performClick()

        // Check the new value.
        Espresso.onView(withText("Hello Compose")).check(matches(isDisplayed()))
    }
}
```

The Android page shows only the test body, inside a class with a `composeTestRule`. The `createAndroidComposeRule<ComponentActivity>()` setup and `AndroidJUnit4` runner are this skill's wiring. For what the rule requires, see [test-suite-structure.md](../core/test-suite-structure.md).

Whether a given Espresso matcher or action behaves identically on Robolectric and on a device is not documented. Keep interop tests small, and run them on a device when the View side depends on real rendering.

## Scoping Compose Finders to a View

`onRootWithViewInteraction` is in `androidx.compose.ui:ui-test-junit4:1.12.0-alpha01+` and `androidx.compose.ui:ui-test:1.12.0-alpha01+`. It is experimental and subject to change. Stable `ui-test` is 1.12.1 per the release page.

When identical composables sit inside multiple Views, such as rows of a `RecyclerView` or fragments of a `ViewPager`, a finder like `onNodeWithText("Save")` can fail with "Multiple nodes found". Scope the search instead of adding dynamic test tags to production code.

### Interact with a List Item

```kotlin
@Test
fun testComposeButtonInsideRecyclerViewItem() = runComposeUiTest {
    // Scroll to the desired position using Espresso
    Espresso.onView(withId(recyclerViewId))
        .perform(RecyclerViewActions.scrollToPosition<MyViewHolder>(3))

    // Define an Espresso ViewInteraction that uniquely identifies the row
    val rowView = Espresso.onView(
        allOf(withId(rootViewId), hasDescendant(withText("Item #3")))
    )

    // Scope the Compose search strictly to that row View
    onRootWithViewInteraction(rowView)
        .onNode(hasText("Like"))
        .performClick()
}
```

### Resolve Ambiguity in ViewPagers

```kotlin
@Test
fun testComposeButtonInsideViewPagerItem() = runComposeUiTest {
    Espresso.onView(withId(viewPagerViewId)).perform(swipeLeft())

    val fragmentB = Espresso.onView(withId(fragmentRootViewId))

    // "Save" is now unique within this view scope
    onRootWithViewInteraction(fragmentB)
        .onNode(hasText("Save"))
        .assertIsDisplayed()
}
```

### With a Rule

The `ComposeTestRule` extension (`androidx.compose.ui.test.junit4.onRootWithViewInteraction`) returns a `SemanticsNodeInteractionsProvider` scoped to the matched View hierarchy.

```kotlin
import androidx.compose.ui.test.junit4.onRootWithViewInteraction

val headerInteraction = onView(withId(header_id))

composeTestRule
    .onRootWithViewInteraction(headerInteraction)
    .onNodeWithContentDescription("Settings")
    .performClick()
```

Direction matters: the API is for Compose nested inside Views. To test Views nested inside Compose, "continue using standard Espresso interactions".

Neither the Android page nor the API reference states Robolectric support for this API specifically. Treat it as device-verified and confirm it on the JVM before depending on it.

## Synchronization Across Frameworks

Compose and Espresso each synchronize with the UI, and the Compose rule waits for idle before assertions and actions. Since `1.13.0-alpha01+`, `waitForIdle` and `runOnIdle` can be called from the main thread (previously `IllegalStateException`). This helps with View interop, main-thread state holders, and custom runners. "For standard, Compose-only tests, you don't need to change your existing test code."

The v2 APIs are in `ui-test(-junit4)` 1.11.0-alpha03+ and `ComposeUiTestConfig` in 1.13.0-alpha01+ (1.13.0-rc01 is the current release candidate). Details: [synchronization.md](../core/synchronization.md).

On Robolectric the main Looper is `PAUSED` by default. Espresso and AndroidX Test APIs idle the main Looper automatically. For raw posted work outside those APIs, use `shadowOf(getMainLooper()).idle()`. See [runtime-modes.md](../core/runtime-modes.md).

## UiAutomator (Device Only)

UiAutomator reaches composables only by displayed text, content description, and similar descriptors by default. To reach `Modifier.testTag`, enable `testTagsAsResourceId` once, high in the hierarchy (Compose 1.2.0-alpha08+).

```kotlin
Scaffold(
    // Enables for all composables in the hierarchy.
    modifier = Modifier.semantics { testTagsAsResourceId = true }
) {
    LazyColumn(modifier = Modifier.testTag("myLazyColumn")) { /* Content */ }
}

// Instrumented test (UiAutomator)
val device = UiDevice.getInstance(getInstrumentation())
val lazyColumn: UiObject2 = device.findObject(By.res("myLazyColumn"))
```

Use `By.res(resourceName)` with the tag. Do not use `By.res(resourcePackage, resourceId)`: it formats the argument as `$resourcePackage:id/$resourceId`, which differs from `Modifier.testTag`.

The Android page shows UiAutomator only in an instrumented setting and does not state Robolectric support. The Robolectric blog says "anything that truly needs real hardware or cross-process IPC still belongs in an instrumented test."

## Common Issues & Solutions

| Issue | Cause | Fix |
| --- | --- | --- |
| "Multiple nodes found" for Compose in list rows or pager pages | Identical composables in several Views | `onRootWithViewInteraction` with an Espresso `ViewInteraction` that picks one container |
| `onRootWithViewInteraction` unresolved | Needs `ui-test(-junit4)` 1.12.0-alpha01+, experimental | Upgrade to 1.12.0-alpha01 or later |
| Cannot call `setContent` | Activity already sets content during launch | Use `createAndroidComposeRule<ComponentActivity>()` and set content in the test |
| `IllegalStateException` calling `waitForIdle` from the main thread | Behavior before 1.13.0-alpha01 | Upgrade, or avoid calling from the main thread |
| UiAutomator cannot find a tagged composable | `testTagsAsResourceId` not enabled | Set it once high in the hierarchy |

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
| --- | --- | --- |
| Adding dynamic test tags to production code to disambiguate rows | Pollutes production code | Scope with `onRootWithViewInteraction` |
| Using `onRootWithViewInteraction` for Views inside Compose | Not what it is for | Use standard Espresso interactions |
| `Thread.sleep` between Espresso and Compose steps | Both frameworks already synchronize | Rely on built-in sync; use `waitUntil` for conditions |
| Waiting on an external `CountDownLatch` | The test clock is not advanced | Use the `waitUntil` APIs or an idling resource |
| Setting `testTagsAsResourceId` on every composable | Redundant | Set it once high in the hierarchy |
| Writing UiAutomator tests for `src/test` | No source states UiAutomator works on Robolectric; the blog puts cross-process IPC in instrumented tests | Put them in `androidTest` |

## Related References

- **Rules and setup**: See [test-suite-structure.md](../core/test-suite-structure.md) for rule choice and `ComponentActivity`
- **Synchronization**: See [synchronization.md](../core/synchronization.md) for idling, `waitUntil`, and main-thread sync
- **Finders**: See [semantics-finders.md](../core/semantics-finders.md) for matchers and `testTag`
- **Runtime modes**: See [runtime-modes.md](../core/runtime-modes.md) for the paused Looper
- **Test scope**: See [test-architecture.md](../architecture/test-architecture.md) for device-only cases

## Sources

- https://developer.android.com/develop/ui/compose/testing/interoperability
- https://developer.android.com/develop/ui/compose/testing/synchronization
- https://developer.android.com/jetpack/androidx/releases/compose-ui
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/package-summary
- https://robolectric.org/androidx_test/
- https://robolectric.org/blog/2019/06/04/paused-looper/
- https://robolectric.org/blog/2026/07/03/designing-local-testing-libraries/
