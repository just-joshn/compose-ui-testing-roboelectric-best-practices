# Device Configuration & Screen Sizes

## Table of Contents

1. [Choosing a Mechanism](#choosing-a-mechanism)
2. [DeviceConfigurationOverride](#deviceconfigurationoverride)
3. [Robolectric Qualifiers](#robolectric-qualifiers)
4. [Changing Configuration Mid-Test](#changing-configuration-mid-test)
5. [Testing Screen and Window Sizes](#testing-screen-and-window-sizes)
6. [Configuration Changes and State](#configuration-changes-and-state)
7. [Device-Only Tools](#device-only-tools)
8. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
9. [Related References](#related-references)
10. [Sources](#sources)

## Choosing a Mechanism

Two JVM-friendly mechanisms exist: a Compose-level override scoped to the content under test, and Robolectric qualifiers that configure the whole simulated device.

| Need | Use | Scope |
| --- | --- | --- |
| Font scale, dark mode, locale, layout direction, round screen, size for one composable | `DeviceConfigurationOverride` | Content wrapped in the override only |
| Resource qualifiers (`values-fr`, `layout-land`), density, orientation, `Configuration`/`DisplayMetrics` | `@Config(qualifiers = ...)` | Method, class, package, or suite |
| Change device configuration between steps of one test | `RuntimeEnvironment.setQualifiers()` | Rest of the test |
| Fold postures, real display resizing | Espresso Device, Gradle-managed devices, Firebase Test Lab | Documented for instrumented tests only |

## DeviceConfigurationOverride

`DeviceConfigurationOverride` is a test-only API (`androidx.compose.ui:ui-test`, since 1.7.0) that simulates device conditions locally "for the `@Composable` content under test", without configuring the whole device.

```kotlin
import androidx.compose.ui.test.DeviceConfigurationOverride
import androidx.compose.ui.test.ForcedSize
import androidx.compose.ui.unit.DpSize
import androidx.compose.ui.unit.dp

// Good: render a tablet layout regardless of the device the test runs on
composeTestRule.setContent {
    DeviceConfigurationOverride(
        DeviceConfigurationOverride.ForcedSize(DpSize(1280.dp, 800.dp))
    ) {
        MyScreen() // Rendered in 1280dp x 800dp without clipping
    }
}
```

The companion object provides these overrides (signatures from the `androidx.compose.ui.test` API reference):

| Override | Parameter | Effect |
| --- | --- | --- |
| `DarkMode(isDarkMode: Boolean)` | `Boolean` | Overrides the dark or light theme for the contained content |
| `FontScale(fontScale: Float)` | `Float` | Overrides the font scale for the contained content |
| `FontWeightAdjustment(fontWeightAdjustment: Int)` | `Int` | `@RequiresApi(31)` |
| `ForcedSize(size: DpSize)` | `DpSize` | Overrides the available size for the contained content, applied by changing density locally; renders without clipping |
| `LayoutDirection(layoutDirection: LayoutDirection)` | `LayoutDirection` | Left-to-right or right-to-left |
| `Locales(locales: LocaleList)` | `LocaleList` | Overrides the locales for the contained content |
| `RoundScreen(isScreenRound: Boolean)` | `Boolean` | `@RequiresApi(23)` |

The reference also lists `Keyboard`, `Navigation`, `Touchscreen`, and `UiMode` overrides.

Each override needs its own import from `androidx.compose.ui.test` (for example `androidx.compose.ui.test.FontScale`).

### Combine Overrides with `then`

```kotlin
import androidx.compose.ui.test.DeviceConfigurationOverride
import androidx.compose.ui.test.FontScale
import androidx.compose.ui.test.FontWeightAdjustment
import androidx.compose.ui.test.then

composeTestRule.setContent {
    DeviceConfigurationOverride(
        DeviceConfigurationOverride.FontScale(1.5f) then
            DeviceConfigurationOverride.FontWeightAdjustment(200)
    ) {
        Text(text = "text with increased scale and weight")
    }
}
```

`a then b` applies `a` as the outer override first, then `b` as the inner override.

### Locale

```kotlin
import androidx.compose.ui.test.Locales
import androidx.compose.ui.text.intl.LocaleList

DeviceConfigurationOverride(DeviceConfigurationOverride.Locales(LocaleList("es-ES"))) {
    MyScreen() // Rendered with the overridden locale
}
```

### Dark Mode

```kotlin
import androidx.compose.ui.test.DarkMode

DeviceConfigurationOverride(DeviceConfigurationOverride.DarkMode(true)) {
    MyScreen() // Rendered with the dark theme override
}
```

Runtime support: the Android docs show these overrides with the standard Compose rule. The Robolectric blog (2026-07-03) states the same `createAndroidComposeRule<ComponentActivity>()` / `runComposeUiTest { }` code runs on a device and on the JVM. No source lists per-override Robolectric limits. Verify an override on the JVM before relying on it.

## Robolectric Qualifiers

Set the simulated device with `qualifiers` in `@Config`. Robolectric builds the system `Configuration`, `Display`, and `DisplayMetrics` from it, sets the locale, and selects matching resources.

```kotlin
@RunWith(AndroidJUnit4::class)
@Config(qualifiers = "fr-rFR-w360dp-h640dp-xhdpi")
class FrenchNexus5ScreenTest {
    @get:Rule val composeTestRule = createComposeRule()
    // ...
}
```

Rules:

- Separate qualifiers with dashes, in the order of the Android resource qualifier list.
- Unspecified properties get consistent calculated values or defaults. Locale defaults to `en-rUS`, width to `w320dp`, height to `h470dp`, density to `mdpi`, orientation to `port`.
- Specifying width and height derives screen size, aspect, and orientation. Specifying orientation swaps width and height.
- Resource resolution follows Android rules. With `values/`, `values-en/`, and `values-en-port/` string files, `@Config(qualifiers = "en-port")` selects the most specific match.
- Put `@Config` on a class or a method. The method wins. Package-level defaults and global settings are in [configuration.md](../core/configuration.md).

### Cumulative Qualifiers

By default, new qualifiers replace higher-level ones. A leading `+` overlays them.

```kotlin
@Config(qualifiers = "xlarge-port")
class MyTest {
    @Test fun xlargePort() { /* xlarge-port */ }

    @Test @Config(qualifiers = "+land")
    fun xlargeLand() { /* xlarge-land: overlays the class qualifiers */ }

    @Test @Config(qualifiers = "land")
    fun normalLand() { /* normal-land: replaces the class qualifiers */ }
}
```

## Changing Configuration Mid-Test

`RuntimeEnvironment.setQualifiers()` takes the same string rules as `@Config(qualifiers)`.

```kotlin
import org.robolectric.RuntimeEnvironment

// Good: same string rules as @Config(qualifiers)
RuntimeEnvironment.setQualifiers("w1000dp-h1000dp-480dpi")
```

It "updates the system and application resources with the new configuration but does not trigger any action on extant activities or other components." To simulate the sequence of events on a real configuration change, Robolectric documents `ActivityController.configurationChange()`. It calls `onConfigurationChanged()` if the activity handles the change, or destroys and recreates the activity if not.

```kotlin
// Bad: assume running activities react to setQualifiers
RuntimeEnvironment.setQualifiers("+land")
// activity still holds the old configuration

// Good: drive the change through the controller (Robolectric's documented pattern)
val controller = Robolectric.buildActivity(MyActivity::class.java).setup()
RuntimeEnvironment.setQualifiers("+land")
controller.configurationChange()
```

`ActivityController` is shown on the Robolectric page. The AndroidX Test page recommends `ActivityScenario` over `Robolectric.buildActivity()` and says `ActivityController` "has proved problematic". For Compose tests, prefer the state-restoration approaches in [state-restoration.md](../testing-patterns/state-restoration.md). I found no source showing `configurationChange()` combined with a Compose rule.

Displays: setters on `ShadowDisplay` change display properties during a test, and `ShadowDisplayManager` simulates multiple displays.

## Testing Screen and Window Sizes

Test compact, medium, and expanded widths and heights, and the state preserved across size changes. Android's guidance for local Compose UI tests:

- Use `DeviceConfigurationOverride` with `ForcedSize` to "run any UI test on any screen size". You can use a small phone form factor for all UI tests, including big phones, foldables, and tablets.
- Use Robolectric to run Compose or view-based UI tests on the JVM with no device or emulator. Now in Android sets a very large qualifier so the content fits without clipping or scaling.

```kotlin
// Good: large simulated screen, then force sizes per case
@RunWith(AndroidJUnit4::class)
@Config(qualifiers = "w1000dp-h1000dp-480dpi")
class ScreenSizesTest {
    @get:Rule val composeTestRule = createComposeRule()

    @Test
    fun expandedWidth_showsListAndDetail() {
        composeTestRule.setContent {
            DeviceConfigurationOverride(
                DeviceConfigurationOverride.ForcedSize(DpSize(840.dp, 480.dp))
            ) {
                MyApp()
            }
        }
        composeTestRule.onNodeWithTag("detail_pane").assertIsDisplayed()
    }
}
```

The Android page shows `@RunWith(RobolectricTestRunner::class)` with the same `@Config`. This skill uses `AndroidJUnit4` per the AndroidX Test page. The `840.dp` by `480.dp` size and the test tags are illustrative.

To parameterize sizes in the test body, as in the Now in Android example:

```kotlin
val (width, height, dpi) = spec
RuntimeEnvironment.setQualifiers("w${width}dp-h${height}dp-${dpi}dpi")
```

The Android docs say screenshot tests on Robolectric have lower fidelity, and recommend Robolectric screenshots when pixel accuracy is not critical, for example font sizes or themes. See [visual-regression.md](../testing-patterns/visual-regression.md).

## Configuration Changes and State

Compose tests do not need a real device change to verify state restoration:

- `StateRestorationTester` simulates a configuration change without recreating the activity. See [state-restoration.md](../testing-patterns/state-restoration.md).
- In any UI test, `Activity.recreate()` simulates one.
- Resizing the screen in a test does not cover foldable posture logic, "as posture changes don't trigger a configuration change".

## Device-Only Tools

These are documented for instrumented tests only. No source states they work on Robolectric.

| Tool | Purpose |
| --- | --- |
| Espresso Device (alpha) | `onDevice().setTabletopMode()`, `setDisplaySize()`, `@RequiresDeviceMode`, `@RequiresDisplay`, `DisplaySizeRule`. Requires AGP 8.3+, emulator 33.1.10+, API 24+ |
| Gradle-managed devices | `ManagedVirtualDevice` definitions, for example `systemImageSource = "aosp-atd"` |
| Firebase Test Lab | Real devices and emulators |

`androidx.window.testing.layout` (`FoldingFeature`, `TestWindowLayoutInfo`, `WindowLayoutInfoPublisherRule`) emulates display features with `createAndroidComposeRule<ComponentActivity>()`. The Robolectric blog (2026-07-03) says `window-testing` fakes such as `WindowLayoutInfoPublisherRule` are pure JUnit and Robolectric only supplies JVM Android types (`Rect`, `WindowLayoutInfo`), so tests can build them off-device. The Android page gives no artifact version.

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
| --- | --- | --- |
| Testing only the default device (`w320dp`, `en-rUS`) | Misses tablet, locale, and font scale bugs | Cover compact, medium, and expanded sizes with `ForcedSize` or qualifiers |
| Expecting `setQualifiers()` to update live activities | It only updates resources | Trigger the change explicitly, or recreate content |
| Qualifiers in the wrong order | Not parsed per the resource list | Follow the Android qualifier order |
| Class-level `@Config` unintentionally replaced on a method | Method qualifiers replace class qualifiers | Prefix with `+` to overlay |
| Exposing colors or sizes through custom semantics to check config effects | Pollutes production code | Wrap content in an override and assert visible behavior |
| Asserting fold postures with `setQualifiers()` | Postures are not configuration changes | Use device tools or the Window testing library |

## Related References

- **Configuration**: See [configuration.md](../core/configuration.md) for `@Config`, `robolectric.properties`, and SDK selection
- **State restoration**: See [state-restoration.md](../testing-patterns/state-restoration.md) for `StateRestorationTester`
- **Screenshots**: See [visual-regression.md](../testing-patterns/visual-regression.md) for rendering fidelity on Robolectric
- **Test scope**: See [test-architecture.md](../architecture/test-architecture.md) for what belongs on a device

## Sources

- https://developer.android.com/develop/ui/compose/testing/common-patterns
- https://developer.android.com/training/testing/different-screens
- https://developer.android.com/training/testing/different-screens/tools
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/package-summary
- https://robolectric.org/device-configuration/
- https://robolectric.org/using-qualifiers/
- https://robolectric.org/configuring/
- https://robolectric.org/androidx_test/
- https://robolectric.org/blog/2026/07/03/designing-local-testing-libraries/
