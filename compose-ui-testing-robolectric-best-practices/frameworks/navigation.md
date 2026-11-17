# Navigation Compose Testing Patterns

## Table of Contents

1. [Setup](#setup)
2. [Test Screens with Callbacks, Not NavController](#test-screens-with-callbacks-not-navcontroller)
3. [Test the NavHost](#test-the-navhost)
4. [Test Navigation Actions](#test-navigation-actions)
5. [Fragment-Based Navigation](#fragment-based-navigation)
6. [Common Issues & Solutions](#common-issues--solutions)
7. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
8. [Related References](#related-references)
9. [Sources](#sources)

> **When to use**: Testing screens and `NavHost` graphs built with Navigation Compose.
> **Prerequisites**: [test-suite-structure.md](../core/test-suite-structure.md), [configuration.md](../core/configuration.md)

## Setup

Add the Navigation testing artifact. The official Compose navigation page shows `androidTestImplementation` and does not name a version (`$navigationVersion`).

```kotlin
// build.gradle.kts
dependencies {
    // Shown on the official page (instrumented tests):
    androidTestImplementation("androidx.navigation:navigation-testing:$navigationVersion")

    // Same artifact for Robolectric tests in src/test (the Gradle configuration
    // mapping is this skill's adaptation; the pages show androidTestImplementation only):
    testImplementation("androidx.navigation:navigation-testing:$navigationVersion")
}
```

The Robolectric blog (2026-07-03) describes `TestNavHostController` as extending the real controller and swapping only the navigator registry. Its `setCurrentDestination` is built on the production deep-link machinery, so the back stack it produces is the real one. The blog says Robolectric runs only the library's Android-host tests that need real `Bundle`/`Uri` behavior. Test rule and runner setup follow [test-suite-structure.md](../core/test-suite-structure.md): `@RunWith(AndroidJUnit4::class)` in `src/test`.

## Test Screens with Callbacks, Not NavController

"Don't pass the `NavController` directly into any composable. Instead, pass navigation callbacks (lambdas) as parameters." Every screen is then testable without a `NavController`.

```kotlin
// Good: the screen takes a lambda; the NavHost bridges to NavController
@Composable
fun ProfileScreen(
    userId: String,
    navigateToFriendProfile: (friendUserId: String) -> Unit
) { /* ... */ }

// In your NavHost
composable<Profile> { backStackEntry ->
    val profile = backStackEntry.toRoute<Profile>()
    ProfileScreen(userId = profile.id) { friendUserId ->
        navController.navigate(route = Profile(id = friendUserId))
    }
}
```

```kotlin
// Bad: a NavController parameter forces every test to build one
@Composable
fun ProfileScreen(navController: NavController) { /* ... */ }
```

Test the screen in isolation with a plain value and a recording callback:

```kotlin
@Test
fun profileScreen_friendClick_invokesCallback() {
    var clickedFriendId: String? = null
    composeTestRule.setContent {
        ProfileScreen(userId = "me", navigateToFriendProfile = { clickedFriendId = it })
    }
    composeTestRule.onNodeWithText("Open friend").performClick()
    assertEquals("friend-1", clickedFriendId)
}
```

The text `"Open friend"` and ids are illustrative. The official page says to test with "mock values and callbacks" and does not show a full example. This one uses a captured variable instead of a mocking library; see [test-doubles.md](../architecture/test-doubles.md).

The page recommends tests that cover three things: the `NavHost`, the navigation actions passed to composables, and individual screen composables.

## Test the NavHost

Wrap the `NavHost` in a composable that takes a `NavHostController`, so a test can pass a `TestNavHostController`.

```kotlin
@Composable
fun AppNavHost(navController: NavHostController) {
    NavHost(navController = navController, startDestination = Home) {
        composable<Home> { /*...*/ }
        composable<Profile> { /*...*/ }
    }
}
```

```kotlin
class NavigationTest {
    @get:Rule
    val composeTestRule = createComposeRule()

    lateinit var navController: TestNavHostController

    @Before
    fun setupAppNavHost() {
        composeTestRule.setContent {
            navController = TestNavHostController(LocalContext.current)
            navController.navigatorProvider.addNavigator(ComposeNavigator())
            AppNavHost(navController = navController)
        }
    }

    @Test
    fun appNavHost_verifyStartDestination() {
        composeTestRule
            .onNodeWithContentDescription("Start Screen")
            .assertIsDisplayed()
    }
}
```

The official example has no `@RunWith` and uses the `androidTest` configuration. On Robolectric, add `@RunWith(AndroidJUnit4::class)` and place the class in `src/test`.

## Test Navigation Actions

Two ways, both after a click. Prefer the UI.

| Approach | Use when |
| --- | --- |
| Click, then assert the destination content (`assertIsDisplayed()`) | Default. "As you want to test your concrete app's implementation, clicks on the UI are preferable." |
| Click, then compare the current route on the `TestNavHostController` | You need to assert the route or arguments themselves |

```kotlin
// Good: assert on what the user sees
@Test
fun appNavHost_clickProfile_showsProfile() {
    composeTestRule.onNodeWithContentDescription("Go to Profile").performClick()
    composeTestRule.onNodeWithContentDescription("Profile Screen").assertIsDisplayed()
}

// Good: assert on the route
@Test
fun appNavHost_clickProfile_navigatesToProfile() {
    composeTestRule.onNodeWithContentDescription("Go to Profile")
        .performClick()
    assertTrue(navController.currentBackStackEntry?.destination?.hasRoute<Profile>() ?: false)
}
```

The first test is an illustrative variant of the page's UI-assertion advice. The second is from the page.

## Fragment-Based Navigation

For View-based apps, Navigation 2.3+ provides `TestNavHostController` with `setGraph`, `setCurrentDestination`, and `setViewModelStore(ViewModelStore())` for navigation-scoped ViewModels. Unlike a real `NavHostController`, it "does not trigger the underlying `navigate()` behavior (such as the `FragmentTransaction`...)": it only updates state. The official example uses `FragmentScenario`, Espresso, and `Navigation.setViewNavController(fragment.requireView(), navController)`. Its Gradle snippet pins `nav_version = "2.10.2"`, shown as the page's example version, not a recommendation. The page says `FragmentScenario` lets you verify fragments "in both unit and instrumentation tests", but its Gradle snippet uses `androidTestImplementation` and its test uses `@RunWith(AndroidJUnit4::class)`. Espresso support on Robolectric is noted in [interoperability.md](../advanced/interoperability.md).

## Common Issues & Solutions

| Issue | Cause | Fix |
| --- | --- | --- |
| Composable cannot be tested without a `NavController` | The screen takes the controller directly | Pass navigation callbacks (lambdas) instead |
| Cannot unit-test the graph | `NavHost` created inside the app composable | Extract `AppNavHost(navController: NavHostController)` |
| Fragment test: no state change after `navigate()` | `TestNavHostController` only updates state | Assert `currentDestination`, not fragment transactions |

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
| --- | --- | --- |
| Passing `NavController` into screens | Screens need a controller in every test | Pass lambdas; the `NavHost` bridges them |
| Only asserting routes | Misses what the user sees | Click and assert displayed content; add route checks where needed |
| Re-testing Navigation's own behavior | Already tested by the library | Test your app's wiring and callbacks |
| No navigation flow tests | Misses run-time crashes in initialization | Keep simple tests of the most common navigation paths |

## Related References

- **Test structure**: See [test-suite-structure.md](../core/test-suite-structure.md) for rules, `setContent`, and `src/test` setup
- **Finders**: See [semantics-finders.md](../core/semantics-finders.md) for `onNodeWithContentDescription` and test tags
- **Component tests**: See [component-testing.md](../testing-patterns/component-testing.md) for testing screens in isolation
- **Hilt**: See [hilt.md](hilt.md) for injecting fakes into `hiltViewModel()` screens
- **State restoration**: See [state-restoration.md](../testing-patterns/state-restoration.md) for process and configuration change checks

## Sources

- https://developer.android.com/guide/navigation/testing/compose
- https://developer.android.com/guide/navigation/testing
- https://robolectric.org/blog/2026/07/03/designing-local-testing-libraries/
- https://developer.android.com/training/testing/fundamentals/what-to-test
