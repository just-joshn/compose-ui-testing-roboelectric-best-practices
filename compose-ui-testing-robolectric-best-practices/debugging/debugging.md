# Debugging & Troubleshooting

## Table of Contents

1. [Debug Tools](#debug-tools)
2. [Semantics Tree Printing](#semantics-tree-printing)
3. [Merged vs Unmerged Tree](#merged-vs-unmerged-tree)
4. [Identifying Flaky Tests](#identifying-flaky-tests)
5. [Failure Artifacts](#failure-artifacts)
6. [Debugging Robolectric Environment Issues](#debugging-robolectric-environment-issues)
7. [Debugging Rendering and Screenshots](#debugging-rendering-and-screenshots)
8. [Common Issues & Solutions](#common-issues--solutions)
9. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
10. [Related References](#related-references)
11. [Sources](#sources)

## Debug Tools

The main way to solve problems in Compose tests is to look at the semantics tree.

| Tool                                              | Use when                                              | Notes                                                          |
| ------------------------------------------------- | ----------------------------------------------------- | -------------------------------------------------------------- |
| `printToLog(tag)`                                 | You can read the log output                           | Debug-level Android log message                                |
| `printToString()`                                 | You want the tree in an assertion message or `println` | Returns `String`; works on one node or a node collection       |
| `useUnmergedTree = true`                          | A child node is "missing"                             | See [Merged vs Unmerged Tree](#merged-vs-unmerged-tree)        |
| `TestFailurePolicy`                               | You want artifacts on every failure                   | Compose 1.13.0-alpha01+, see [Failure Artifacts](#failure-artifacts) |
| `robolectric.logging.enabled`                     | Resources or SDK setup look wrong                     | Robolectric debug logging                                      |
| Robolectric Simulator                             | You need to see what Robolectric renders              | Experimental, 4.15+                                            |

## Semantics Tree Printing

```kotlin
@RunWith(AndroidJUnit4::class)
class CheckoutTest {
    @get:Rule
    val composeTestRule = createAndroidComposeRule<ComponentActivity>()

    @Test
    fun showsTotal() {
        composeTestRule.setContent { CheckoutScreen() }

        // Print the whole tree at any point in the test
        composeTestRule.onRoot().printToLog("TAG")

        // Limit depth: 0 prints just this node
        composeTestRule.onRoot().printToLog("TAG", maxDepth = 2)

        // Get it as a String instead of relying on the log
        val tree = composeTestRule.onRoot().printToString()
        println(tree)

        composeTestRule.onNodeWithText("Total").assertIsDisplayed()
    }
}
```

The output lists each node with the properties it exposes:

```
Node #1 at (...)px
 |-Node #2 at (...)px
   OnClick = '...'
   MergeDescendants = 'true'
    |-Node #3 at (...)px
    | Text = 'Hi'
    |-Node #5 at (83.0, 86.0, 191.0, 135.0)px
      Text = 'There'
```

Both functions fetch the latest snapshot of the nodes the interaction found earlier, so output can change over time if the tree changes. Call them after the synchronization point you care about.

```kotlin
// Good: print right before the failing assertion, after state has settled
composeTestRule.waitForIdle()
composeTestRule.onRoot().printToLog("BEFORE_ASSERT")
composeTestRule.onNodeWithText("Done").assertExists()

// Bad: print immediately after mutating state; nothing has recomposed yet
myState.value = 1
composeTestRule.onRoot().printToLog("TAG")
```

The sources do not say where debug-level `printToLog` output ends up under Robolectric. If you see nothing in the Gradle test report, use `printToString()` and print or assert on the string.

## Merged vs Unmerged Tree

By default finders search the merged tree: a clickable parent merges its children's semantics, so a button with two `Text` children appears as one node with `Text = '[Hello, World]'` and `MergeDescendants = 'true'`.

```kotlin
// Print both views of the same hierarchy
composeTestRule.onRoot().printToLog("MERGED")
composeTestRule.onRoot(useUnmergedTree = true).printToLog("UNMERGED")

// Good: target a merged-away child explicitly
composeTestRule
    .onNodeWithText("World", useUnmergedTree = true)
    .assertIsDisplayed()

// Bad: assuming the child is a separate node in the default (merged) tree
composeTestRule.onNodeWithText("World").assertIsDisplayed() // may not find it
```

`useUnmergedTree` is available on all finders. For selector choice and custom semantics, see [semantics-finders.md](../core/semantics-finders.md).

## Identifying Flaky Tests

| Behavior                                    | Likely Cause                                       | Next Step                                                        |
| ------------------------------------------- | -------------------------------------------------- | ---------------------------------------------------------------- |
| Passes, then fails after a rule/API upgrade | v1 to v2 dispatcher change exposes a latent race   | [flaky-tests.md](flaky-tests.md)                                 |
| Assertion sees old state                    | No recomposition yet, or coroutine queued          | [synchronization.md](../core/synchronization.md)                 |
| "Multiple nodes found"                      | Same text or tag appears more than once            | Narrow the finder, see [semantics-finders.md](../core/semantics-finders.md) |
| Fails only on CI                            | JDK, SDK download, or environment difference       | [ci-cd.md](../infrastructure-ci-cd/ci-cd.md)                     |
| Passes on device, fails on Robolectric      | Fidelity gap (rendering, system UI, `WebView`)     | [test-architecture.md](../architecture/test-architecture.md)     |

## Failure Artifacts

`TestFailurePolicy`, `TestFailureHandler`, and `FailureContext` capture a screenshot and UI hierarchy when a test fails. They ship in `androidx.compose.ui:ui-test:1.13.0-alpha01+` and `ui-test-junit4:1.13.0-alpha01+`; 1.12.1 is the latest stable, so this needs a 1.13 pre-release (rc01 at the time of writing).

```kotlin
// Compose 1.13.0-alpha01+
class MyComposeTest {
    private val customConfig = ComposeUiTestConfig(
        failurePolicy = TestFailurePolicy(
            screenshotCaptureMode = TestFailurePolicy.CaptureMode.Enabled,
            uiHierarchyCaptureMode = TestFailurePolicy.CaptureMode.Enabled
        )
    )

    @Test
    fun myFirstTest() = runComposeUiTest(config = customConfig) {
        // ...
    }
}
```

Add a custom handler to forward artifacts elsewhere. Each handler receives a `FailureContext` with the original error and the artifacts produced by earlier handlers.

```kotlin
private val customConfig = ComposeUiTestConfig(
    failurePolicy = TestFailurePolicy(
        screenshotCaptureMode = TestFailurePolicy.CaptureMode.Enabled,
        failureHandlers = listOf(
            TestFailureHandler { context ->
                val screenshot = context.artifacts.firstOrNull {
                    it.type == FailureArtifact.Type.Screenshot
                }
                // ...
            }
        )
    )
)

@get:Rule
val rule = createComposeRule(config = customConfig)
```

To enable capture suite-wide, the docs use instrumentation runner arguments:

```kotlin
// build.gradle.kts
android {
    defaultConfig {
        testInstrumentationRunnerArguments["androidx.compose.ui.test.failure.isUiHierarchyCaptureEnabled"] = "true"
        testInstrumentationRunnerArguments["androidx.compose.ui.test.failure.isScreenshotCaptureEnabled"] = "true"
    }
}
```

Precedence: an explicit `CaptureMode.Enabled` or `Disabled` in the test policy overrides the runner argument; `CaptureMode.Unspecified` (or a `null` policy) falls back to it. The docs show the runner arguments only as instrumentation arguments and do not say whether local Robolectric runs honor them, so set the policy in code (`ComposeUiTestConfig`) for `src/test`.

## Debugging Robolectric Environment Issues

### Debug logging

```kotlin
// build.gradle.kts: set Robolectric system properties on the unit-test task
android {
    testOptions {
        unitTests.all {
            it.systemProperty("robolectric.logging.enabled", "true")
        }
    }
}
```

The Robolectric getting-started page recommends this when you are unsure whether resources are being loaded for a library: you should see a lot of resource-loading output.

### Robolectric Simulator (experimental)

Since Robolectric 4.15 you can launch an interactive preview of your app or test, useful when debugging failing Robolectric tests. The docs call it "highly experimental" and "proof-of-concept", and its rendering may not match a device 100%.

```kotlin
// build.gradle.kts, Gradle plugin route: ./gradlew simulateDebug
plugins {
    id("org.robolectric.simulator") version "1.0.3"
}

// Standalone API route
dependencies {
    testImplementation("org.robolectric:simulator:4.18")
}
```

The standalone route calls `Simulator().start()` inside a test annotated `@Config(sdk = [VANILLA_ICE_CREAM])` and `@GraphicsMode(GraphicsMode.Mode.NATIVE)`. On JDK 23 and newer, add the `--add-exports` `jvmArgs` listed on the simulator page to the unit-test configuration.

### Looper warnings

With the default `PAUSED` looper mode, Robolectric warns when a test fails with unexecuted tasks in the main `Looper` queue: that is a hint the pending work matters to the test. AndroidX Test APIs such as `ActivityScenario` and Espresso idle the main looper automatically; for other posted work use `shadowOf(Looper.getMainLooper()).idle()`. See [flaky-tests.md](flaky-tests.md) and [runtime-modes.md](../core/runtime-modes.md).

## Debugging Rendering and Screenshots

```kotlin
// After advancing the clock manually, wait for the draw pass before capturing
composeTestRule.mainClock.autoAdvance = false
composeTestRule.mainClock.advanceTimeBy(50L)
composeTestRule.waitForIdle()
val bitmap = composeTestRule.onRoot().captureToImage()
```

- `advanceTimeBy` does not trigger a draw. Assert anything rendering-related only after `waitForIdle()` or `runOnIdle`.
- If you change a state variable that is read during draw, `advanceTimeBy` will not update the UI; use `waitForIdle()`.
- `captureToImage` takes a `timeoutMillis` parameter (default 2000 ms) since 1.13.0-alpha01 for waiting on redraw passes.
- Rendering on the JVM needs native graphics: `@GraphicsMode(GraphicsMode.Mode.NATIVE)`. See [runtime-modes.md](../core/runtime-modes.md) and [visual-regression.md](../testing-patterns/visual-regression.md).
- From Robolectric 4.18 on SDK 33/34, `RuntimeShader` uniform setters forward to native code, which can change how Material ripples are drawn in screenshot tests. `robolectric.runtimeShaderScalarUniform=false` restores the old behavior (documented as temporary).

## Common Issues & Solutions

| Symptom                                                        | Cause                                                              | Fix                                                                                       |
| -------------------------------------------------------------- | ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| State changed in test but assertion sees old value             | Compose only recomposes on a sync point                            | Assert via the rule (it syncs first), or call `waitForIdle()`                             |
| Assertion sees "Loading" after upgrading to v2 rules           | v2 queues launched coroutines on a `StandardTestDispatcher`        | `composeTestRule.waitForIdle()` or `composeTestRule.runOnIdle { ... }` before asserting   |
| Child text not found                                           | Parent merged descendants                                          | `useUnmergedTree = true`, confirm with `printToLog`                                       |
| "Multiple nodes found" with Compose nested in Views            | Identical Compose content in several Views                         | `onRootWithViewInteraction` (experimental, 1.12.0-alpha01+); see [interoperability.md](../advanced/interoperability.md) |
| Test hangs or times out waiting on a condition                 | Condition reads non-Compose state, or an external `CountDownLatch` | Use `waitUntil*` APIs; the test clock is not advanced by external latches                 |
| `Main looper has queued unexecuted runnables`                  | Non-Compose work posted to main `Looper` was never idled           | `shadowOf(Looper.getMainLooper()).idle()` at the right point                              |
| Date or time strings differ from device                        | Android libcore vs OpenJDK (`Z` timezone marker, `MMM` month)      | Use `X` marker (min SDK 24+) or `java.time` with desugaring; run those tests on a device  |
| Screenshot differs between Mac and Linux CI                    | Different rendering across platforms                               | See [visual-regression.md](../testing-patterns/visual-regression.md)                                          |

## Anti-Patterns to Avoid

| Anti-Pattern                                   | Problem                                         | Solution                                                         |
| ---------------------------------------------- | ----------------------------------------------- | ---------------------------------------------------------------- |
| `Thread.sleep()` to "let the UI settle"        | Slow or flaky; hides the real race              | `waitForIdle()`, `waitUntil*`, or idling resources              |
| Guessing at selectors                          | Wasted iterations                               | `printToLog` / `printToString` first, then pick the finder       |
| Printing the tree right after mutating state   | Shows stale tree                                | Print after `waitForIdle()` or an assertion                      |
| Leaving `printToLog` calls in committed tests  | Noisy logs                                      | Remove, or use failure artifacts                                 |
| Mocking `Context` or `SharedPreferences` to dodge a failure | Brittle stubbing of Android classes | Use the real Robolectric environment or a fake                   |
| Assuming a Robolectric pass means device pass  | Fidelity differs (rendering, system UI, `WebView`) | Keep device tests for those cases                             |

## Related References

- **Flaky tests**: See [flaky-tests.md](flaky-tests.md) for timing, sync, and thread causes
- **Synchronization**: See [synchronization.md](../core/synchronization.md) for `waitForIdle`, `waitUntil*`, idling resources
- **Selectors**: See [semantics-finders.md](../core/semantics-finders.md) for merged vs unmerged trees and finders
- **Runtime modes**: See [runtime-modes.md](../core/runtime-modes.md) for `LooperMode` and `GraphicsMode`
- **Visual testing**: See [visual-regression.md](../testing-patterns/visual-regression.md) for screenshot comparison
- **CI**: See [ci-cd.md](../infrastructure-ci-cd/ci-cd.md) for android-all downloads and JDK selection

## Sources

- https://developer.android.com/develop/ui/compose/testing/debug
- https://developer.android.com/develop/ui/compose/testing/apis
- https://developer.android.com/develop/ui/compose/testing/common-patterns
- https://developer.android.com/develop/ui/compose/testing/migrate-v2
- https://developer.android.com/develop/ui/compose/testing/synchronization
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/MainTestClock
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/SemanticsNodeInteraction
- https://developer.android.com/develop/ui/compose/testing/interoperability
- https://developer.android.com/jetpack/androidx/releases/compose-ui
- https://robolectric.org/simulator/
- https://robolectric.org/configuring/
- https://robolectric.org/getting-started/
- https://robolectric.org/best-practices/
- https://robolectric.org/upgrade_to_version_4/
- https://robolectric.org/blog/2019/06/04/paused-looper/
- https://developer.android.com/training/testing/ui-tests/screenshot
- https://developer.android.com/training/testing/local-tests/robolectric
