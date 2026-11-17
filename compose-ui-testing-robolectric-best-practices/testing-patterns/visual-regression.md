# Visual Regression Testing

## Table of Contents

1. [Screenshots on Robolectric](#screenshots-on-robolectric)
2. [GraphicsMode](#graphicsmode)
3. [SemanticsNodeInteraction.captureToImage](#semanticsnodeinteractioncapturetoimage)
4. [Capturing Animation Frames](#capturing-animation-frames)
5. [Robolectric Versus Device Tests](#robolectric-versus-device-tests)
6. [Exceptions Thrown by captureToImage](#exceptions-thrown-by-capturetoimage)
7. [Custom Semantics Properties for Visual Properties](#custom-semantics-properties-for-visual-properties)
8. [Related References](#related-references)
9. [Sources](#sources)

## Screenshots on Robolectric

You can run other UI tests with Robolectric, such as screenshot tests. However the fidelity is lower as different devices render screens slightly differently.

You must decide whether Robolectric's implementation is good enough for each use case.

Robolectric can take screenshots natively, but you need a third-party library to perform screenshot testing with it.

### Use Robolectric When Pixel Accuracy Is Not Critical

Use Robolectric to take screenshots when the pixel accuracy is not critical. For example, to test how a component reacts to different font sizes or themes.

## GraphicsMode

A Configurer annotation for controlling which graphics shadow implementation is used for the android.graphics package.

| Mode | Behavior |
| --- | --- |
| `NATIVE` | Use graphics shadows libraries backed by native Android graphics code. |
| `LEGACY` | Use legacy graphics shadows that are no-ops and fakes. |

Robolectric's native runtime now includes Linux arm64 (aarch64) native libraries, so tests that use native SQLite (the default) and native graphics (`@GraphicsMode(NATIVE)`) can run on Linux arm64 environments, such as GitHub's `ubuntu-24.04-arm` runners, AWS Graviton machines, and arm64 Docker containers on Apple silicon. No configuration is needed.

### Preview in the Simulator

Starting with Robolectric 4.15, it's possible to launch an interactive preview of your app or tests in a Robolectric environment.

The Robolectric simulator can be a useful way to preview how your UI would look in a Robolectric environment. This can be helpful, for instance, when debugging failing Robolectric tests.

UI rendered in the Robolectric simulator may not match an Android emulator or device 100%. Note that the Robolectric simulator is highly experimental and is still largely in the proof-of-concept stage.

The following example sets up an Activity and subsequently starts the simulator to preview the Activity.

```kotlin
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [VANILLA_ICE_CREAM])
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class MainActivityTest {
    @Test
    fun simulateMainActivity() {
        Robolectric.setupActivity(MainActivity::class.java)
        Simulator().start()
    }
}
```

## SemanticsNodeInteraction.captureToImage

Captures the underlying semantics node's surface into an `ImageBitmap`.

```kotlin
@RequiresApi(value = 26)
fun SemanticsNodeInteraction.captureToImage(timeoutMillis: Long): ImageBitmap
```

`timeoutMillis: Long` The maximum time (in ms) to wait for the drawing to complete. Default is 2000 ms.

`captureToImage` can be used to capture nodes in a normal composable, as well as across multiple roots. Popups and Dialogs (if API >= 28) are specific cases of this, where they can be captured together with their anchor.

For example, selecting the root node (via `onRoot()`) when a popup or dialog is present will detect multiple roots. In this scenario, the resulting image is cropped to the combined bounding box of all nodes across the different roots. If a Dialog is present among the roots, the image is cropped to the window's visible display frame.

## Capturing Animation Frames

`ComposeTestRule` exposes its test clock as `mainClock`. You can set the `autoAdvance` property to false to control the clock in your test code. After initiating the animation you want to test, the clock can be moved forward with `advanceTimeBy`.

```kotlin
@get:Rule
val rule = createComposeRule()

@Test
fun testAnimationWithClock() {
    // Pause animations
    rule.mainClock.autoAdvance = false
    var enabled by mutableStateOf(false)
    rule.setContent {
        val color by animateColorAsState(
            targetValue = if (enabled) Color.Red else Color.Green,
            animationSpec = tween(durationMillis = 250)
        )
        Box(Modifier.size(64.dp).background(color))
    }

    // Initiate the animation.
    enabled = true

    // Let the animation proceed.
    rule.mainClock.advanceTimeBy(50L)

    // Compare the result with the image showing the expected result.
    // `assertAgainGolden` needs to be implemented in your code.
    rule.onRoot().captureToImage().assertAgainstGolden()
}
```

If, after any call to `advanceTimeBy`, you want to assert anything related to rendering (e.g. `SemanticsNodeInteraction.captureToImage`), you will need a call to `androidx.compose.ui.test.junit4.ComposeTestRule.waitForIdle` or `androidx.compose.ui.test.junit4.ComposeTestRule.runOnIdle` to make sure that any triggered draw pass has been completed.

If you change a state variable that is read during draw, calling `advanceTimeBy` will not produce the desired update to the UI. Use `androidx.compose.ui.test.junit4.ComposeTestRule.waitForIdle` for this case.

## Robolectric Versus Device Tests

Robolectric provides enough fidelity to run most UI tests but some cases will still require device tests, for example those related to system UI like edge-to-edge or picture-in-picture, or when relying on unsupported features, like `WebView`.

## Exceptions Thrown by captureToImage

| Throws | When |
| --- | --- |
| `ComposeTimeoutException` | if drawing does not complete within `timeoutMillis`. |
| `IllegalArgumentException` | if an attempt is made to capture a bitmap of a dialog before API 28. |

## Custom Semantics Properties for Visual Properties

Using custom Semantics properties to expose visual properties such as colors, font size or rounded corner radius is not recommended, as it can pollute production code and wrong implementations can lead to bugs that are hard to find.

## Related References

- [animations.md](animations.md) — driving the clock before a capture
- [clock-control.md](../advanced/clock-control.md) — `autoAdvance` and `advanceTimeBy`
- [runtime-modes.md](../core/runtime-modes.md) — `@GraphicsMode` and `@LooperMode`
- [device-configuration.md](../advanced/device-configuration.md) — font scale, dark mode, window size

## Sources

- https://developer.android.com/training/testing/local-tests/robolectric
- https://developer.android.com/develop/ui/compose/animation/testing
- https://developer.android.com/develop/ui/compose/testing/common-patterns
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/MainTestClock
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/SemanticsNodeInteraction
- https://robolectric.org/javadoc/4.18/org/robolectric/annotation/GraphicsMode.html
- https://robolectric.org/javadoc/4.18/org/robolectric/annotation/GraphicsMode.Mode.html
- https://robolectric.org/simulator/
- https://github.com/robolectric/robolectric/releases
