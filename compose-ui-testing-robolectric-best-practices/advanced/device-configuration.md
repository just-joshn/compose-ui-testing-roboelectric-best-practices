# Device Configuration

## Table of Contents

1. [DeviceConfigurationOverride](#deviceconfigurationoverride)
2. [Available Overrides](#available-overrides)
3. [Override Patterns](#override-patterns)
4. [Robolectric Qualifiers](#robolectric-qualifiers)
5. [Changing device configuration](#changing-device-configuration)
6. [Related References](#related-references)
7. [Sources](#sources)

## DeviceConfigurationOverride

Android apps need to adapt to many changing conditions: window sizes, locales, font sizes, dark and light themes, and more. Most of these conditions are derived from device-level values controlled by the user and exposed with the current `Configuration` instance. Testing different configurations directly in a test is difficult since the test must configure device-level properties.

`DeviceConfigurationOverride` is a test-only API that lets you simulate different device configurations in a localized way for the `@Composable` content under test. Artifact: `androidx.compose.ui:ui-test` Added in 1.7.0

To apply a specific override, wrap the content under test in a call to the `DeviceConfigurationOverride()` top-level function, passing the override to apply as a parameter.

`DeviceConfigurationOverride()` can be useful to locally test behavior in isolation that depends on properties that are normally device-wide, such as font scale, screen size and layout direction.

For example, the following code applies the `DeviceConfigurationOverride.ForcedSize()` override to change the density locally, forcing the `MyScreen` composable to be rendered in a large landscape window, even if the device the test is running on doesn't support that window size directly:

```kotlin
composeTestRule.setContent {
    DeviceConfigurationOverride(
        DeviceConfigurationOverride.ForcedSize(DpSize(1280.dp, 800.dp))
    ) {
        MyScreen() // Will be rendered in the space for 1280dp by 800dp without clipping.
    }
}
```

## Available Overrides

The companion object of `DeviceConfigurationOverride` has the following extension functions, which override device-level configuration properties:

| Override | Effect |
| --- | --- |
| `DeviceConfigurationOverride.Companion.DarkMode` | A `DeviceConfigurationOverride` that overrides the dark mode or light mode theme for the contained content. |
| `DeviceConfigurationOverride.Companion.FontScale` | A `DeviceConfigurationOverride` that overrides the font scale for the contained content. |
| `@RequiresApi(value = 31) DeviceConfigurationOverride.Companion.FontWeightAdjustment` | A `DeviceConfigurationOverride` that overrides the font weight adjustment for the contained content. |
| `DeviceConfigurationOverride.Companion.ForcedSize` | A `DeviceConfigurationOverride` that overrides the available size for the contained content. |
| `DeviceConfigurationOverride.Companion.Keyboard` | A `DeviceConfigurationOverride` that overrides the current keyboard type. |
| `DeviceConfigurationOverride.Companion.LayoutDirection` | A `DeviceConfigurationOverride` that overrides the layout direction for the contained content. |
| `DeviceConfigurationOverride.Companion.Locales` | A `DeviceConfigurationOverride` that overrides the locales for the contained content. |
| `DeviceConfigurationOverride.Companion.Navigation` | A `DeviceConfigurationOverride` that overrides the current navigation type and whether it is hidden. |
| `@RequiresApi(value = 23) DeviceConfigurationOverride.Companion.RoundScreen` | A `DeviceConfigurationOverride` that overrides whether the screen is round for the contained content. |
| `DeviceConfigurationOverride.Companion.Touchscreen` | A `DeviceConfigurationOverride` that overrides the current touchscreen type. |
| `DeviceConfigurationOverride.Companion.UiMode` | A `DeviceConfigurationOverride` that overrides the current ui mode type. |
| `DeviceConfigurationOverride.Companion.WindowInsets` | A `DeviceConfigurationOverride` that overrides the window insets for the contained content. |
| `DeviceConfigurationOverride.Companion.WindowSize` | A `DeviceConfigurationOverride` that overrides the window size for the contained content. |

## Override Patterns

### Font Scale

A `DeviceConfigurationOverride` that overrides the font scale for the contained content.

```kotlin
DeviceConfigurationOverride(DeviceConfigurationOverride.FontScale(1.5f)) {
    MyScreen() // will be rendered with a larger than default font scale
}
```

### DeviceConfigurationOverride.then

To apply multiple overrides together, use `DeviceConfigurationOverride.then()`:

```kotlin
composeTestRule.setContent {
    DeviceConfigurationOverride(
        DeviceConfigurationOverride.FontScale(1.5f) then
            DeviceConfigurationOverride.FontWeightAdjustment(200)
    ) {
        Text(text = "text with increased scale and weight")
    }
}
```

Combines this override with the other override into a single override, by applying this override as the outer override first, then the other override as an inner override, and then the content.

### Locales

`Locales()` will change resource resolution for the content under test, and also override the layout direction as specified by the locales.

```kotlin
DeviceConfigurationOverride(DeviceConfigurationOverride.Locales(LocaleList("es-ES"))) {
    MyScreen() // will be rendered with overridden locale
}
```

### Layout Direction

A `DeviceConfigurationOverride` that overrides the layout direction for the contained content.

```kotlin
DeviceConfigurationOverride(DeviceConfigurationOverride.LayoutDirection(LayoutDirection.Rtl)) {
    MyComponent() // will be rendered with a right-to-left layout direction
}
```

### Dark Mode

`isDarkMode: Boolean` if `true`, render content under test in dark mode.

```kotlin
DeviceConfigurationOverride(DeviceConfigurationOverride.DarkMode(true)) {
    isSystemInDarkTheme() // will be true
}
```

### Forced Size and Window Size

`DeviceConfigurationOverride.Companion.ForcedSize` is only suitable for tests, since this will override `LocalDensity` to ensure that the size is met (as opposed to `Modifier.requiredSize` which will result in clipping).

`WindowSize` is only suitable for tests, since this will override `LocalDensity` to ensure that the size is met (as opposed to `Modifier.requiredSize` which will result in clipping). Unlike `ForcedSize`, this override will override `LocalWindowInfo` and `LocalConfiguration` on Android to reflect the requested size.

```kotlin
DeviceConfigurationOverride(DeviceConfigurationOverride.WindowSize(DpSize(1280.dp, 800.dp))) {
    MyScreen() // will be rendered with an apparent window size of 1280dp by 800dp without
    // clipping
}
```

## Robolectric Qualifiers

Robolectric makes it easy to simulate a variety of device configurations. In particular, the properties that make up the Configuration class can be specified at the test method, test class, package, or suite level.

The Android device configuration can be specified using the qualifiers `@Config` argument:

```kotlin
@Test
@Config(qualifiers = "fr-rFR-w360dp-h640dp-xhdpi")
fun testItOnFrenchNexus5() {
}
```

The system's Configuration, Display and DisplayMetrics objects will all reflect the specified configuration, the locale will be set, and appropriate resources will be selected.

Specifying a resource qualifier is quite simple: simply add the desired qualifiers to the `@Config` annotation on your test case or test class, depending on whether you would like to change the resource qualifiers for the whole file, or simply one test.

### Default Values

For unspecified properties, Robolectric picks consistent values based on the properties that have been specified, or uses default values as follows:

| Property | Default |
| --- | --- |
| Language, region, and script (locale) | `en-rUS` |
| Width | `w320dp` |
| Height | `h470dp` |
| Screen orientation | `port` |
| Screen pixel density | `mdpi` |

If screen orientation is specified, width and height will be swapped as appropriate.

### Cumulative Qualifiers

By default, specifying qualifiers causes any previous specification of qualifiers to be ignored. For example, qualifiers at the test method level occlude qualifiers at the test class level. However, if the qualifiers config property starts with a + (plus sign), it is interpreted as an overlay to any higher-level qualifiers that have been specified:

```kotlin
@Config(qualifiers = "xlarge-port")
class MyTest {
  @Test
  fun testItWithXlargePort() {
    // Config is "xlarge-port"
  }

  @Test
  @Config(qualifiers = "+land")
  fun testItWithXlargeLand() {
    // Config is "xlarge-land"
  }

  @Test
  @Config(qualifiers = "land")
  fun testItWithLand() {
    // Config is "normal-land"
  }
}
```

Values for unspecified properties are calculated, and rules are applied, after all configs have been merged.

## Changing device configuration

The device configuration can be changed within a test using `RuntimeEnvironment.setQualifiers()`:

```kotlin
@Test
@Config(qualifiers = "+port")
fun testOrientationChange() {
  val controller = Robolectric.buildActivity(MyActivity::class)
  controller.setup()
  // assert that activity is in portrait mode
  RuntimeEnvironment.setQualifiers("+land")
  controller.configurationChange()
  // assert that activity is in landscape mode
}
```

The string parameter to `RuntimeEnvironment.setQualifiers()` has the same rules as `Config.qualifiers`.

`RuntimeEnvironment.setQualifiers()` updates the system and application resources with the new configuration, but does not trigger any action on extant activities or other components.

`ActivityController.configurationChange()` can be used to simulate the sequence of events that take place on a device when its configuration changes. If the Activity is configured to handle the configuration changes, `ActivityController.configurationChange()` will call the Activity's `onConfigurationChanged()` method. If not, `ActivityController` destroys and recreates the Activity.

Robolectric provides `Robolectric.setupActivity()` for the coarse-grained use case where you require a launched activity in the resumed state and visible for the user to interact with. Robolectric also provides `Robolectric.buildActivity()`, which returns an `ActivityController` that allows the developer to step through the Activity lifecycle. This has proved problematic as it requires developers to fully understand valid lifecycle transitions and possible valid states. `ActivityScenario` provides a replacement for both of these use cases, but places tighter restrictions around lifecycle transitions, namely that invalid or incomplete transitions are not possible.

### Simulating displays

Robolectric allows display properties to be changed during a test using setters on `ShadowDisplay`. Multiple displays can be simulated using APIs on `ShadowDisplayManager`.

## Related References

- [configuration.md](../core/configuration.md) for `@Config`
- [state-restoration.md](../testing-patterns/state-restoration.md) for `StateRestorationTester`
- [visual-regression.md](../testing-patterns/visual-regression.md) for screenshots on Robolectric
- [runtime-modes.md](../core/runtime-modes.md) for Robolectric runtime modes

## Sources

- https://developer.android.com/develop/ui/compose/testing/common-patterns
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/DeviceConfigurationOverride
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/DeviceConfigurationOverride.Companion
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/DeviceConfigurationOverride.composable
- https://robolectric.org/device-configuration/
- https://robolectric.org/using-qualifiers/
- https://robolectric.org/androidx_test/
