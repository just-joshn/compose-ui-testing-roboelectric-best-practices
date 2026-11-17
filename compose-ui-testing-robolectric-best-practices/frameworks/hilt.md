# Hilt Testing Patterns

## Table of Contents

1. [Setup](#setup)
2. [When You Need Hilt](#when-you-need-hilt)
3. [Test Application on Robolectric](#test-application-on-robolectric)
4. [Rules and Rule Ordering](#rules-and-rule-ordering)
5. [Replacing Bindings](#replacing-bindings)
6. [Injecting Into the Test](#injecting-into-the-test)
7. [Custom Application](#custom-application)
8. [Common Issues & Solutions](#common-issues--solutions)
9. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
10. [Related References](#related-references)
11. [Sources](#sources)

> **When to use**: Compose UI tests that exercise screens using Hilt (`hiltViewModel()`, `@AndroidEntryPoint`) on Robolectric.
> **Prerequisites**: [test-suite-structure.md](../core/test-suite-structure.md), [configuration.md](../core/configuration.md)

## Setup

The Hilt testing guide lists these dependencies. "For Robolectric tests" use the `test` configurations. Versions are the page's examples (`2.57.1`); the Compose artifacts take their version from the BOM.

```kotlin
// build.gradle.kts
dependencies {
    // For Robolectric tests.
    testImplementation("com.google.dagger:hilt-android-testing:2.57.1")
    kspTest("com.google.dagger:hilt-android-compiler:2.57.1")

    // For instrumented tests.
    androidTestImplementation("com.google.dagger:hilt-android-testing:2.57.1")
    kspAndroidTest("com.google.dagger:hilt-android-compiler:2.57.1")

    // Compose UI test rule (BOM-managed, no version).
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}
```

The guide lists the Compose dependencies under `androidTestImplementation`. For the Robolectric (`testImplementation`) set, see [configuration.md](../core/configuration.md). If you use Jetpack integrations such as `hilt-navigation-compose` to get a ViewModel through `hiltViewModel()`, add their annotation processors to your test dependencies too.

## When You Need Hilt

| Test | Hilt needed? | How |
| --- | --- | --- |
| Class with constructor injection | No | Call the constructor with fakes |
| ViewModel obtained via `hiltViewModel()` | No (unit test) | Construct the ViewModel directly with fakes |
| Compose screen that calls `hiltViewModel()` | Yes | `@HiltAndroidTest` + rule + test application |
| Screen with its dependencies passed as parameters | No | Plain `createComposeRule()`; see [component-testing.md](../testing-patterns/component-testing.md) |

```kotlin
// Good: no Hilt for a unit test
class AnalyticsAdapterTest {
    @Test
    fun `Happy path`() {
        val adapter = AnalyticsAdapter(fakeAnalyticsService)
        assertEquals(/* ... */)
    }
}
```

## Test Application on Robolectric

Hilt tests must run in an `Application` that supports Hilt. The library provides `HiltTestApplication`. On Robolectric, set it in `robolectric.properties`:

```properties
application = dagger.hilt.android.testing.HiltTestApplication
```

Or per test with `@Config`:

```kotlin
@HiltAndroidTest
@Config(application = HiltTestApplication::class)
class SettingsScreenTest {
    @get:Rule
    var hiltRule = HiltAndroidRule(this)
    // Robolectric tests here.
}
```

`robolectric.properties` placement and precedence (`@Config` overrides properties; deeper packages override shallower ones) are in [configuration.md](../core/configuration.md). A custom `AndroidJUnitRunner` that returns `HiltTestApplication` is the instrumented-test approach and is not needed on Robolectric.

## Rules and Rule Ordering

Annotate every Hilt UI test with `@HiltAndroidTest` and add `HiltAndroidRule`. It manages component state and performs injection. Combine it with a Compose rule, and make sure `HiltAndroidRule` runs first.

```kotlin
@HiltAndroidTest
class SettingsScreenTest {
    @get:Rule(order = 0)
    val hiltRule = HiltAndroidRule(this)

    @get:Rule(order = 1)
    val composeRule = createAndroidComposeRule<HiltTestActivity>()

    @get:Rule(order = 2)
    val otherRule = SomeOtherRule()

    // Compose UI tests here.
}
```

```kotlin
// Alternative: RuleChain with HiltAndroidRule as the outer rule
@HiltAndroidTest
class SettingsScreenTest {
    @get:Rule
    var rule = RuleChain.outerRule(HiltAndroidRule(this))
        .around(SettingsScreenTestRule(/* ... */))
}
```

```kotlin
// Bad: no order; nothing guarantees HiltAndroidRule runs first
@get:Rule val composeRule = createAndroidComposeRule<HiltTestActivity>()
@get:Rule val hiltRule = HiltAndroidRule(this)
```

`HiltTestActivity` is "an empty activity ... in your `androidTest` source set" annotated with `@AndroidEntryPoint`. `createAndroidComposeRule` uses it as the host. The guide shows this for instrumented tests and does not say where the activity lives for Robolectric. In `src/test`, confirm the activity is resolvable by Robolectric before relying on it.

Add `@RunWith(AndroidJUnit4::class)` for `src/test`, as in [test-suite-structure.md](../core/test-suite-structure.md). The guide's snippets omit the runner.

## Replacing Bindings

Replace the module that holds the binding, so the composable picks up the fake through its ViewModel with no extra wiring. "Replacing the binding in Hilt is enough."

### For All Tests: `@TestInstallIn` (Recommended)

Create the module in the `test` source set for Robolectric tests (or `androidTest` for instrumented tests). All tests there get the fake.

```kotlin
@Module
@TestInstallIn(
    components = [SingletonComponent::class],
    replaces = [AnalyticsModule::class]
)
abstract class FakeAnalyticsModule {
    @Singleton
    @Binds
    abstract fun bindAnalyticsService(
        fakeAnalyticsService: FakeAnalyticsService
    ): AnalyticsService
}
```

### For One Test Class: `@UninstallModules`

```kotlin
@UninstallModules(AnalyticsModule::class)
@HiltAndroidTest
class SettingsScreenTest {
    @Module
    @InstallIn(SingletonComponent::class)
    abstract class TestModule {
        @Singleton
        @Binds
        abstract fun bindAnalyticsService(
            fakeAnalyticsService: FakeAnalyticsService
        ): AnalyticsService
    }
    // ...
}
```

Warnings from the guide:

- You cannot uninstall modules not annotated with `@InstallIn`. It is a compile error.
- `@UninstallModules` cannot uninstall `@TestInstallIn` modules. It is a compile error.
- `@UninstallModules` makes Hilt create new components, which "can significantly impact unit test build times". Prefer `@TestInstallIn` for bindings replaced in all test classes.

### Bind a Field: `@BindValue`

`@BindValue` binds a test field into the graph under its declared type and qualifiers, and lets you reference the fake in the test.

```kotlin
@UninstallModules(AnalyticsModule::class)
@HiltAndroidTest
class SettingsScreenTest {
    @BindValue @JvmField
    val analyticsService: AnalyticsService = FakeAnalyticsService()
    // ...
}
```

Use `@BindValueIntoSet` or `@BindValueIntoMap` for multibindings. The map form also needs a map key annotation. With a Mockito-style `@Mock`, `@BindValue @ExampleQualifier @Mock lateinit var ...` is shown for Robolectric tests, but the Android testing docs prefer fakes. See [test-doubles.md](../architecture/test-doubles.md).

## Injecting Into the Test

Use `@Inject` fields and call `hiltRule.inject()`.

```kotlin
@HiltAndroidTest
class SettingsScreenTest {
    @get:Rule(order = 0)
    val hiltRule = HiltAndroidRule(this)

    @get:Rule(order = 1)
    val composeRule = createAndroidComposeRule<HiltTestActivity>()

    @Inject
    lateinit var analyticsAdapter: AnalyticsAdapter

    @Before
    fun init() {
        hiltRule.inject()
    }

    @Test
    fun settingsScreen_showsTitle() {
        composeRule.setContent { SettingsScreen() }

        composeRule.onNodeWithText("Settings").assertIsDisplayed()
    }
}
```

## Custom Application

If the test application must extend another application, `@CustomTestApplication` generates one:

```kotlin
@CustomTestApplication(BaseApplication::class)
interface HiltTestApplication
```

Hilt generates `HiltTestApplication_Application` (the annotated name plus `_Application`) extending `BaseApplication`. Point Robolectric at the generated class through `robolectric.properties` or `@Config(application = ...)`. The IDE may show the generated class in red until you run the tests. `@EarlyEntryPoint` covers entry points needed before the singleton component exists. See the Hilt documentation.

## Common Issues & Solutions

| Issue | Cause | Fix |
| --- | --- | --- |
| Hilt setup misbehaves alongside other rules | `HiltAndroidRule` does not run first | `order = 0`, or `RuleChain.outerRule(HiltAndroidRule(this))` |
| App class is not Hilt-aware | Test application not set | `application = ...HiltTestApplication` in `robolectric.properties`, or `@Config(application = HiltTestApplication::class)` |
| Compile error uninstalling a module | Module lacks `@InstallIn`, or is a `@TestInstallIn` module | Uninstall only `@InstallIn` modules; replace with `@TestInstallIn` |
| Using Jetpack integrations such as `hilt-navigation-compose` | Their annotation processors must also be in test dependencies | Add the integration's annotation processors to test dependencies |
| Slower builds with many tests | `@UninstallModules` creates new components | Move shared fakes to `@TestInstallIn` |
| `HiltTestApplication_Application` unresolved | Generated at build time | Run the tests; ignore the IDE highlight |

The Robolectric custom-test-runner page also points Hilt users to the official Hilt integration guide.

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
| --- | --- | --- |
| Using Hilt in plain unit tests | Hilt is not necessary there | Call constructors with fakes |
| Real network or database modules in UI tests | Not hermetic (a hermetic test avoids all external dependencies) | Replace with `@TestInstallIn` fakes |
| `@UninstallModules` in every test class | Longer builds | `@TestInstallIn` for shared fakes |
| Mocking `Context` or `SharedPreferences` to avoid Hilt | Robolectric's best practices: stubbing is very brittle | Use a fake binding; do not mock Android classes |
| Several rules without `order` | `HiltAndroidRule` must run first | Set `order`, or use `RuleChain` |
| Copying instrumented runner setup onto Robolectric | Unneeded | Use `robolectric.properties` or `@Config(application)` |

## Related References

- **Test structure**: See [test-suite-structure.md](../core/test-suite-structure.md) for the Compose rule and `src/test` layout
- **Configuration**: See [configuration.md](../core/configuration.md) for `@Config` and `robolectric.properties`
- **Test doubles**: See [test-doubles.md](../architecture/test-doubles.md) for fakes over mocks and DI seams
- **ViewModels and coroutines**: See [coroutines-viewmodels.md](../testing-patterns/coroutines-viewmodels.md) for unit-testing ViewModels
- **Navigation**: See [navigation.md](navigation.md) for `NavHost` tests

## Sources

- https://developer.android.com/training/dependency-injection/hilt-testing
- https://developer.android.com/training/testing/fundamentals/test-doubles
- https://robolectric.org/configuring/
- https://robolectric.org/custom-test-runner/
