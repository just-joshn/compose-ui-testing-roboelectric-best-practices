# Visual Regression Testing

## Table of Contents

1. [Screenshots on Robolectric](#screenshots-on-robolectric)
2. [Native Graphics](#native-graphics)
3. [Capturing a Compose Node](#capturing-a-compose-node)
4. [Related References](#related-references)
5. [Sources](#sources)

## Screenshots on Robolectric

You can run other UI tests with Robolectric, such as screenshot tests. However the fidelity is lower as different devices render screens slightly differently.

You must decide whether Robolectric's implementation is good enough for each use case. Android's recommendation for screenshots: use Robolectric to take screenshots when the pixel accuracy is not critical. For example, to test how a component reacts to different font sizes or themes.

Robolectric can take screenshots natively, but you need a third-party library to perform screenshot testing with it.

## Native Graphics

`@GraphicsMode` is a Configurer annotation for controlling which graphics shadow implementation is used for the android.graphics package. Its modes:

- `GraphicsMode.Mode.NATIVE`: use graphics shadows libraries backed by native Android graphics code.
- `GraphicsMode.Mode.LEGACY`: use legacy graphics shadows that are no-ops and fakes.

The Robolectric simulator page's example test class is annotated with `@GraphicsMode(GraphicsMode.Mode.NATIVE)`.

Robolectric 4.10 added support for native Android graphics. The 4.10 release notes say it can be enabled using `@GraphicsMode(NATIVE)`. When native graphics is enabled, interactions with Android graphics classes use real native Android graphics code and are much higher fidelity.

The Robolectric blog post "Designing local testing libraries" describes itself as "an outside read of the code as it stands in mid-2026, not an official AndroidX position". In its section on Jetpack Compose UI test, the post says screenshot tests use Robolectric's native-graphics PixelCopy shadow.

Robolectric 4.12.2 release notes: in order to use HW rendering with PixelCopy, you must set the `robolectric.pixelCopyRenderMode=hardware` system property.

Robolectric 4.13 release notes: better support for HW rendering in Robolectric Native Graphics (RNG), and HW rendering is now supported all the way down to Android P.

## Capturing a Compose Node

`SemanticsNodeInteraction.captureToImage` captures the underlying semantics node's surface into an `ImageBitmap`. Its signature:

```kotlin
@RequiresApi(value = 26)
fun SemanticsNodeInteraction.captureToImage(timeoutMillis: Long): ImageBitmap
```

`timeoutMillis` is the maximum time (in ms) to wait for the drawing to complete. Default is 2000 ms.

The release notes list: added a `timeoutMillis` parameter (defaulting to 2000 ms) to `SemanticsNodeInteraction.captureToImage()` to allow configuring a custom timeout when waiting for redraw passes.

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

In that sample, the comment says `assertAgainGolden` needs to be implemented in your code.

The `MainTestClock` page says that if, after any call to `advanceTimeBy`, you want to assert anything related to rendering (for example `SemanticsNodeInteraction.captureToImage`), you will need a call to `ComposeTestRule.waitForIdle` or `ComposeTestRule.runOnIdle`.

## Related References

- [animations.md](animations.md) — driving the clock before a capture
- [clock-control.md](../advanced/clock-control.md) — `autoAdvance` and `advanceTimeBy`
- [runtime-modes.md](../core/runtime-modes.md) — `@GraphicsMode` and `@LooperMode`
- [device-configuration.md](../advanced/device-configuration.md) — font scale, dark mode, window size

## Sources

- https://developer.android.com/training/testing/local-tests/robolectric
- https://developer.android.com/develop/ui/compose/animation/testing
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/MainTestClock
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/SemanticsNodeInteraction
- https://developer.android.com/jetpack/androidx/releases/compose-ui
- https://robolectric.org/blog/2026/07/03/designing-local-testing-libraries/
- https://robolectric.org/javadoc/4.18/org/robolectric/annotation/GraphicsMode.html
- https://robolectric.org/javadoc/4.18/org/robolectric/annotation/GraphicsMode.Mode.html
- https://robolectric.org/simulator/
- https://github.com/robolectric/robolectric/releases
