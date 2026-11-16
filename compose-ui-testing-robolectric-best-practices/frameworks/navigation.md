# Test Compose navigation and route entry

## Table of contents

- [Choose the navigation test](#choose-the-navigation-test)
- [Set up a controlled NavHost](#set-up-a-controlled-navhost)
- [Drive navigation through UI actions](#drive-navigation-through-ui-actions)
- [Test arguments and invalid destinations](#test-arguments-and-invalid-destinations)
- [Test nested graphs and retained state](#test-nested-graphs-and-retained-state)
- [Test authentication and return destinations](#test-authentication-and-return-destinations)
- [Test deep links and external entry](#test-deep-links-and-external-entry)
- [Separate data loading from navigation](#separate-data-loading-from-navigation)
- [Synchronize and isolate navigation](#synchronize-and-isolate-navigation)
- [Avoid navigation shortcuts](#avoid-navigation-shortcuts)
- [Troubleshoot failures](#troubleshoot-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the navigation test

Use this guide for screen transitions, route arguments, nested graphs, back-stack behavior, authentication gates, and deep links. The examples use Navigation Compose's `NavHost` and `NavController`. If the application uses Navigation 3 or a custom navigation state model, test that model rather than adding Navigation Compose only for tests.

Android navigation does not have server-rendered pages, HTTP status codes, or browser history. Preserve the intent of those upstream checks through destination content, route-entry validation, and back-stack behavior.

| Claim | Smallest useful test | Additional boundary |
| --- | --- | --- |
| Button requests a destination | Stateless screen plus callback | Does not prove NavHost wiring |
| Button opens the correct screen | Real NavHost with controlled repositories | Backend remains outside the claim |
| Route argument chooses item 42 | Real destination rendering with known item data | External URI dispatch needs host coverage |
| Back returns to previous content | Real graph and pop action | Device system Back needs device evidence |
| Protected destination redirects | Controlled session and real route policy | Backend authorization remains separate |
| App link launches the right activity | Declared host and intent handling | Verified-domain and browser dispatch on device |
| Feature installation enables a route | Fake availability for local UI | Real dynamic delivery on device |

## Set up a controlled NavHost

Use `androidx.navigation:navigation-compose` and `androidx.navigation:navigation-testing` at compatible project versions. Put local tests in `src/test` with `testImplementation`, the Robolectric runner, Android resources, and the default Compose activity host manifest.

Pass the controller into the production graph so the test can observe it. Keep destination screens independent of the controller where possible. Screens can accept navigation callbacks while the graph wires those callbacks.

Illustrative complete local test. It requires Material3, Compose UI test JUnit4 1.12.1, Navigation Compose and testing, JUnit 4, and Robolectric. It uses string routes to avoid requiring a serialization plugin in the example. Keep the consuming project's typed routes if it already uses them. This snippet is not compiled in the canonical fixture.

```kotlin
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.navigation.NavType
import androidx.navigation.compose.ComposeNavigator
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import androidx.navigation.testing.TestNavHostController
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class CatalogNavigationTest {
	@get:Rule val rule = createComposeRule()

	@Test fun opensItemAndReturnsToCatalog() {
		lateinit var controller: TestNavHostController
		rule.setContent {
			val context = LocalContext.current
			controller = remember {
				TestNavHostController(context).apply {
					navigatorProvider.addNavigator(ComposeNavigator())
				}
			}
			NavHost(controller, startDestination = "catalog") {
				composable("catalog") {
					Column {
						Text("Catalog")
						Button(onClick = { controller.navigate("item/42") }) {
							Text("Open notebook")
						}
					}
				}
				composable(
					"item/{id}",
					arguments = listOf(navArgument("id") { type = NavType.IntType }),
				) { entry ->
					Column {
						Text("Item ${entry.arguments?.getInt("id")}")
						Button(onClick = { controller.popBackStack() }) {
							Text("Back to catalog")
						}
					}
				}
			}
		}
		rule.onNodeWithText("Catalog").assertIsDisplayed()
		rule.onNodeWithText("Open notebook").performClick()
		rule.onNodeWithText("Item 42").assertIsDisplayed()
		rule.runOnIdle {
			assertEquals("item/{id}", controller.currentDestination?.route)
			assertEquals(42, controller.currentBackStackEntry?.arguments?.getInt("id"))
		}
		rule.onNodeWithText("Back to catalog").performClick()
		rule.onNodeWithText("Catalog").assertIsDisplayed()
		rule.onNodeWithText("Item 42").assertDoesNotExist()
	}
}
```

The UI action proves graph wiring. The route and argument assertions supplement the visible item check. Calling `controller.navigate` directly in the test would bypass the button's wiring.

## Drive navigation through UI actions

For feature flows, click the actual screen control, assert the destination's unique content, and assert the old destination is no longer the active UI where appropriate. A route string alone can pass while the destination is blank or renders the wrong item.

Use controller operations directly for setup or an explicitly controller-level contract. Do not describe a direct `navigate` test as proof of a user action.

Test back behavior through the application's Back control when that control is the claim. A controller `popBackStack` test does not prove the device's system Back dispatch, predictive Back animation, or task finishing. Keep those checks in host or device coverage.

Do not choose the first repeated **Open** button. Scope by item identity in the semantics tree. The [semantics selector guide](../core/semantics-selectors.md) covers duplicate labels.

## Test arguments and invalid destinations

Pass stable identifiers rather than entire mutable domain objects. Load destination data through the repository for that identifier. A rendered item title is stronger evidence than a route template string.

Cover these route-entry cases:

| Input | Expected behavior |
| --- | --- |
| Known identifier | Render that item's content |
| Well-formed but missing identifier | Show the application's not-found state |
| Malformed identifier | Reject at the route-entry boundary |
| Optional filter omitted | Apply the documented default |
| Filter and sort supplied | Render the selected controls and resulting order |
| Untrusted external return target | Reject or normalize according to the app's allowlist |

Use typed routes when the project supports them. Assert destination identity through the corresponding typed API rather than formatting serialization internals. Keep string-route tests aligned with the actual route schema.

An unknown internal route can legitimately be a programming error. Do not require every app to add a generic 404 screen. External input must have a deliberate validation policy, while invalid internal navigation should fail visibly during development.

## Test nested graphs and retained state

For a shared shell, navigate between children and assert that the shell remains visible while the child content changes. Verify user-observable retained state, such as a selected tab or filter. Do not inspect a private marker merely to prove no recreation occurred.

For tab navigation with saved back stacks, navigate into a detail destination, switch tabs, return, and assert the intended destination and state. Also assert the intended top-level Back behavior. A stack that grows on every tab click can still show the correct screen once.

Choose state scope deliberately. A destination-scoped ViewModel should not be silently shared across independent routes. A graph-scoped ViewModel should survive child navigation when the graph remains on the stack.

Use a test-local repository and owner graph for each method. Do not reuse a controller from another test or host.

## Test authentication and return destinations

Inject session state rather than signing into a live identity provider in every navigation test. Start unauthenticated, enter a protected destination through its normal entry boundary, and assert the sign-in screen.

Complete the fake session transition through the supported UI or session boundary. Assert the original allowed destination appears. Inspect the return destination as a supplementary policy check.

Add cases for session expiry while viewing a protected screen, cancellation of sign-in, and sign-out clearing sensitive back-stack entries. After sign-out, a Back action must not expose protected content if the application promises that protection.

A navigation gate is not authorization. Use backend contract tests to prove protected operations reject unauthenticated or unauthorized requests. A fake session cannot establish server policy.

## Test deep links and external entry

Separate URI parsing, navigation handling, and Android dispatch.

1. Test parser acceptance and rejection with explicit URIs.
2. Test graph handling of a valid deep link with known repository data.
3. Test the declared activity's intent handling and visible destination.
4. Verify browser dispatch, verified app links, and task behavior on a device.

For activity-hosted tests, use the real declared host and the project's launch arrangement. If the activity sets content itself, do not call another `setContent`.

Test warm entry as well as cold entry if `onNewIntent` is supported. Confirm that a second link updates the destination rather than displaying the old item. Keep invalid and unauthorized targets in the matrix.

Notification routes use the same validation rules. A locally inspected destination intent does not prove Android delivered a real notification tap.

## Separate data loading from navigation

Hold repository work to test loading after route entry. Assert the pending destination state, release the response, and assert the loaded item. For failure, assert the destination's retry UI and exercise recovery.

Do not wait for a route to be active and conclude that data loaded. Do not wait for an arbitrary network response and conclude that the correct destination rendered.

For image loading on a destination, fake the image boundary when testing layout or error UI. Test actual decoding and network loading separately. A semantics image description proves accessibility identity, not decoded pixels or resource caching.

Server components, server actions, HTTP security headers, and hydration have no direct Navigation Compose equivalent. Keep backend contracts in integration tests. Locally verify initial content and that the destination remains interactive after composition.

## Synchronize and isolate navigation

Keep clock auto-advance enabled for ordinary settled-state navigation. Transition animations can leave outgoing and incoming content present temporarily. Wait for the intended settled semantics rather than choosing a duplicate by index.

If the transition itself is under test, disable auto-advance before triggering it and advance the Compose clock deliberately. Do not infer device animation fidelity from that local test.

Read controller state on the main thread with `runOnIdle`, and keep synchronized semantics assertions outside the block. Create a fresh controller, graph, session, and repositories per test.

## Avoid navigation shortcuts

| Anti-pattern | Failure mechanism | Correction |
| --- | --- | --- |
| Call `navigate` and claim the button works | The callback is bypassed | Click the button and assert destination content |
| Assert only a route string | The destination may render wrong data | Assert a unique item or screen result |
| Ignore back-stack cleanup on sign-out | Protected content may remain reachable | Exercise Back after sign-out |
| Supply final destination state and claim loading | Repository orchestration is bypassed | Hold and complete the route's data boundary |
| Treat pop as real system Back | Host dispatch and task behavior are not exercised | Keep device Back coverage |
| Reuse a controller between tests | Old entries and owners leak | Create a fresh graph per method |

## Troubleshoot failures

| Symptom | Observe | Fix |
| --- | --- | --- |
| Navigator not found | Controller navigator registration | Add the navigator required by the tested graph |
| Correct route, wrong item | Argument parsing and repository lookup | Assert and repair identity mapping |
| Duplicate labels during transition | Current roots and animation state | Settle the transition or scope meaningful identity |
| Tab clicks grow the stack | Navigation options and saved-state policy | Test repeated tab selection and intended stack behavior |
| Deep link works only at cold launch | Warm intent handling | Route new intents through the supported entry path |
| Two content owners conflict | Activity's content and test `setContent` | Choose one owner |

## Review checklist

- Does the test use the navigation library already in the app?
- Do UI actions, destination identity, and visible content agree?
- Are argument errors and missing data distinguished?
- Are nested state retention and Back behavior covered?
- Are authentication gates separate from backend authorization?
- Are device intent dispatch and system Back claims kept separate?

## Related guides and sources

- [State and ViewModels](state-viewmodels.md) covers destination state ownership.
- [Dependency injection](dependency-injection.md) covers route dependencies.
- [Authentication flows](../advanced/authentication-flows.md) covers session boundaries.
- [Navigation Compose testing](https://developer.android.com/guide/navigation/testing/compose) documents `TestNavHostController` and UI-driven checks.
- [Navigation with Compose](https://developer.android.com/develop/ui/compose/navigation) covers arguments and deep links.
- [Android app links](https://developer.android.com/training/app-links) covers external dispatch and verification.
