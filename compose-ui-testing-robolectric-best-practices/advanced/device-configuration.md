# Device Configuration

## Table of Contents

1. [DeviceConfigurationOverride](#deviceconfigurationoverride)
2. [Robolectric Qualifiers](#robolectric-qualifiers)
3. [Changing Configuration Mid-Test](#changing-configuration-mid-test)
4. [Window Testing Library](#window-testing-library)
5. [Related References](#related-references)
6. [Sources](#sources)

## DeviceConfigurationOverride

Android apps need to adapt to many changing conditions: window sizes, locales, font sizes, dark and light themes, and more. Testing different configurations directly in a test is difficult since the test must configure device-level properties.

`DeviceConfigurationOverride` is a test-only API that lets you simulate different device configurations in a localized way for the `@Composable` content under test.

The release notes for 1.7.0-alpha01 say: adds `DeviceConfigurationOverride` API to `ui-test` to allow locally overriding the behavior of content under test, such as to specify an available size, locale, layout direction, font scale, or theme.

The companion object of `DeviceConfigurationOverride` has the following extension functions, which override device-level configuration properties:

- `DeviceConfigurationOverride.DarkMode()`: Overrides the system to dark theme or light theme.
- `DeviceConfigurationOverride.FontScale()`: Overrides the system font scale.
- `DeviceConfigurationOverride.FontWeightAdjustment()`: Overrides the system font weight adjustment.
- `DeviceConfigurationOverride.ForcedSize()`: Forces a specific amount of space regardless of device size.
- `DeviceConfigurationOverride.LayoutDirection()`: Overrides the layout direction (left-to-right or right-to-left).
- `DeviceConfigurationOverride.Locales()`: Overrides the locale.
- `DeviceConfigurationOverride.RoundScreen()`: Overrides if the screen is round.

The `androidx.compose.ui.test` API reference also lists `Keyboard`, `Navigation`, `Touchscreen`, `UiMode`, `WindowInsets`, and `WindowSize` overrides.

To apply a specific override, wrap the content under test in a call to the `DeviceConfigurationOverride()` top-level function, passing the override to apply as a parameter.

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

`then` combines the override with the other override into a single override, by applying this override as the outer override first, then the other override as an inner override, and then the content.

The `ForcedSize` reference says it is only suitable for tests, since it overrides `LocalDensity` to ensure that the `ForcedSize` is met (as opposed to `Modifier.requiredSize` which will result in clipping).

The `WindowSize` reference says that, unlike `ForcedSize`, this override will override `LocalWindowInfo` and `LocalConfiguration` on Android to reflect the requested size.

```kotlin
DeviceConfigurationOverride(DeviceConfigurationOverride.Locales(LocaleList("es-ES"))) {
    MyScreen() // will be rendered with overridden locale
}
```

`Locales` will change resource resolution for the content under test, and also override the layout direction as specified by the locales.

```kotlin
DeviceConfigurationOverride(DeviceConfigurationOverride.DarkMode(true)) {
    isSystemInDarkTheme() // will be true
}
```

`FontWeightAdjustment` is annotated `@RequiresApi(value = 31)` and `RoundScreen` is annotated `@RequiresApi(value = 23)`.

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

Multiple qualifiers should be separated by dashes.

For unspecified properties, Robolectric picks consistent values based on the properties that have been specified, or uses default values. Some of the defaults:

| Property | Default |
| --- | --- |
| Language, region, and script (locale) | `en-rUS` |
| Width | `w320dp` |
| Height | `h470dp` |
| Screen orientation | `port` |
| Screen pixel density | `mdpi` |

If screen orientation is specified, width and height will be swapped as appropriate.

Specifying a resource qualifier is quite simple: simply add the desired qualifiers to the `@Config` annotation on your test case or test class, depending on whether you would like to change the resource qualifiers for the whole file, or simply one test.

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

## Changing Configuration Mid-Test

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

Note that `RuntimeEnvironment.setQualifiers()` updates the system and application resources with the new configuration, but does not trigger any action on extant activities or other components.

`ActivityController.configurationChange()` can be used to simulate the sequence of events that take place on a device when its configuration changes. If the Activity is configured to handle the configuration changes, `ActivityController.configurationChange()` will call the Activity's `onConfigurationChanged()` method. If not, `ActivityController` destroys and recreates the Activity.

Robolectric allows display properties to be changed during a test using setters on `ShadowDisplay`. Multiple displays can be simulated using APIs on `ShadowDisplayManager`.

The AndroidX Test page on Robolectric.org says Robolectric provides `Robolectric.setupActivity()` for the coarse-grained use case where you require a launched activity in the resumed state and visible for the user to interact with, and `Robolectric.buildActivity()`, which returns an `ActivityController` that allows the developer to step through the Activity lifecycle. It says `buildActivity()` has proved problematic as it requires developers to fully understand valid lifecycle transitions and possible valid states, and that `ActivityScenario` provides a replacement for both of these use cases, but places tighter restrictions around lifecycle transitions, namely that invalid or incomplete transitions are not possible.

## Window Testing Library

A Robolectric blog post that calls itself an outside read of the code, not an official AndroidX position, says of `window-testing` that the fakes are pure JUnit and that Robolectric only provides the JVM Android types (`Rect`, `WindowLayoutInfo`) so the tests can build them off-device.

## Related References

- [configuration.md](../core/configuration.md) for `@Config`
- [state-restoration.md](../testing-patterns/state-restoration.md) for `StateRestorationTester`
- [visual-regression.md](../testing-patterns/visual-regression.md) for screenshots on Robolectric
- [runtime-modes.md](../core/runtime-modes.md) for Robolectric runtime modes

## Sources

- https://developer.android.com/develop/ui/compose/testing/common-patterns
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/package-summary
- https://developer.android.com/jetpack/androidx/releases/compose-ui
- https://robolectric.org/device-configuration/
- https://robolectric.org/using-qualifiers/
- https://robolectric.org/androidx_test/
- https://robolectric.org/blog/2026/07/03/designing-local-testing-libraries/
