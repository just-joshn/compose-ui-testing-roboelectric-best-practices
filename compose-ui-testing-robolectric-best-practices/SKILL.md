---
name: compose-ui-testing-robolectric-best-practices
description: Use when writing, reviewing, or debugging Jetpack Compose UI tests that run locally on the JVM with Robolectric. Covers compose test rules (createComposeRule, createAndroidComposeRule, runComposeUiTest), semantics finders and matchers, merged vs unmerged trees, assertions and actions, synchronization and idling resources, waitUntil, the MainTestClock and animations, coroutines and ViewModels (runTest, test dispatchers), state restoration (StateRestorationTester), device configuration (DeviceConfigurationOverride, Robolectric qualifiers), accessibility and focus testing, View and Espresso interoperability, Navigation Compose testing, Hilt testing, test doubles, Robolectric @Config, robolectric.properties, LooperMode, GraphicsMode, SQLiteMode, screenshot testing, flaky tests, debugging with printToLog, test architecture, and CI.
license: MIT
compatibility: Grounded in official developer.android.com and robolectric.org documentation as read on 2026-11-17. Compose BOM 2026.09.00, ui-test 1.12.1 (v2 rules since 1.11.0-alpha03; ComposeUiTestConfig 1.13.0-alpha01+), Robolectric 4.18 (Android API 24-37).
metadata:
  version: "2.0.0"
---

# Compose UI Testing with Robolectric Best Practices

This skill provides guidance for Jetpack Compose UI tests that run in `src/test` on the JVM with Robolectric, from writing new tests to debugging and maintaining existing suites. Every reference file cites the official pages it is based on in its `Sources` section.

## Activity-Based Reference Guide

Consult these references based on what you're doing:

### Writing New Tests

**When to use**: Creating new test files, writing test cases, implementing test scenarios

| Activity | Reference Files |
| --- | --- |
| **Writing a Compose UI test** | [test-suite-structure.md](core/test-suite-structure.md), [semantics-finders.md](core/semantics-finders.md), [assertions-actions.md](core/assertions-actions.md) |
| **Testing a composable in isolation** | [component-testing.md](testing-patterns/component-testing.md), [test-suite-structure.md](core/test-suite-structure.md) |
| **Choosing a rule or `runComposeUiTest`** | [test-suite-structure.md](core/test-suite-structure.md) |
| **Finding nodes (text, testTag, content description)** | [semantics-finders.md](core/semantics-finders.md) |
| **Clicking, typing, scrolling, gestures** | [assertions-actions.md](core/assertions-actions.md) |
| **Testing ViewModels, StateFlow, coroutines** | [coroutines-viewmodels.md](testing-patterns/coroutines-viewmodels.md), [synchronization.md](core/synchronization.md) |
| **Testing animations** | [animations.md](testing-patterns/animations.md), [clock-control.md](advanced/clock-control.md) |
| **Testing time-dependent UI** | [clock-control.md](advanced/clock-control.md) |
| **Testing state survives recreation** | [state-restoration.md](testing-patterns/state-restoration.md) |
| **Screenshot / visual regression tests** | [visual-regression.md](testing-patterns/visual-regression.md), [runtime-modes.md](core/runtime-modes.md) |
| **Testing accessibility semantics** | [accessibility.md](testing-patterns/accessibility.md), [semantics-finders.md](core/semantics-finders.md) |
| **Testing keyboard focus navigation** | [accessibility.md](testing-patterns/accessibility.md) |
| **Locale and RTL (i18n)** | [device-configuration.md](advanced/device-configuration.md) |

### Screen Sizes & Device Configuration

**When to use**: Testing font scale, dark mode, locale, window sizes, orientation

| Activity | Reference Files |
| --- | --- |
| **Overriding configuration per composable** | [device-configuration.md](advanced/device-configuration.md) |
| **Robolectric qualifiers (`@Config(qualifiers)`)** | [device-configuration.md](advanced/device-configuration.md), [configuration.md](core/configuration.md) |
| **Testing different window sizes** | [device-configuration.md](advanced/device-configuration.md) |
| **Testing configuration changes** | [state-restoration.md](testing-patterns/state-restoration.md), [device-configuration.md](advanced/device-configuration.md) |

### Android Integration

**When to use**: Testing Compose alongside Views, navigation, or dependency injection

| Activity | Reference Files |
| --- | --- |
| **Compose inside Views / Views inside Compose** | [interoperability.md](advanced/interoperability.md) |
| **Using Espresso with a Compose rule** | [interoperability.md](advanced/interoperability.md), [synchronization.md](core/synchronization.md) |
| **Testing Navigation Compose** | [navigation.md](frameworks/navigation.md) |
| **Testing with Hilt** | [hilt.md](frameworks/hilt.md), [configuration.md](core/configuration.md) |

### Debugging & Troubleshooting

**When to use**: Test failures, node not found, idle timeouts, unexpected behavior

| Activity | Reference Files |
| --- | --- |
| **Debugging test failures** | [debugging.md](debugging/debugging.md), [semantics-finders.md](core/semantics-finders.md) |
| **Printing the semantics tree** | [debugging.md](debugging/debugging.md) |
| **Node not found or matched multiple nodes** | [semantics-finders.md](core/semantics-finders.md), [debugging.md](debugging/debugging.md) |
| **Fixing flaky tests** | [flaky-tests.md](debugging/flaky-tests.md), [synchronization.md](core/synchronization.md) |
| **Idle timeouts and infinite animations** | [synchronization.md](core/synchronization.md), [clock-control.md](advanced/clock-control.md) |
| **Async work the test doesn't wait for** | [synchronization.md](core/synchronization.md), [coroutines-viewmodels.md](testing-patterns/coroutines-viewmodels.md) |
| **Robolectric behaves differently from a device** | [runtime-modes.md](core/runtime-modes.md), [test-architecture.md](architecture/test-architecture.md) |

### Architecture Decisions

**When to use**: Choosing test layers, deciding on fakes, planning the suite

| Activity | Reference Files |
| --- | --- |
| **Robolectric vs device vs pure JVM test** | [test-architecture.md](architecture/test-architecture.md) |
| **Fakes vs mocks vs real dependencies** | [test-doubles.md](architecture/test-doubles.md) |
| **Sharing tests between JVM and device** | [test-suite-structure.md](core/test-suite-structure.md), [test-architecture.md](architecture/test-architecture.md) |

### Refactoring & Maintenance

**When to use**: Improving existing tests, code review

| Activity | Reference Files |
| --- | --- |
| **Replacing brittle finders** | [semantics-finders.md](core/semantics-finders.md) |
| **Removing `Thread.sleep` and manual waits** | [synchronization.md](core/synchronization.md), [flaky-tests.md](debugging/flaky-tests.md) |
| **Migrating to the v2 test APIs** | [synchronization.md](core/synchronization.md), [test-suite-structure.md](core/test-suite-structure.md) |
| **Replacing mocks of Android classes** | [test-doubles.md](architecture/test-doubles.md) |

### Infrastructure & Configuration

**When to use**: Setting up the project, Robolectric config, CI

| Activity | Reference Files |
| --- | --- |
| **Gradle dependencies and test options** | [configuration.md](core/configuration.md) |
| **`@Config` and `robolectric.properties`** | [configuration.md](core/configuration.md) |
| **Looper, graphics, and SQLite modes** | [runtime-modes.md](core/runtime-modes.md) |
| **Running in CI, android-all downloads** | [ci-cd.md](infrastructure-ci-cd/ci-cd.md) |
| **JDK and SDK compatibility** | [configuration.md](core/configuration.md), [ci-cd.md](infrastructure-ci-cd/ci-cd.md) |

## Quick Decision Tree

```
What are you doing?
│
├─ Writing a new test?
│  ├─ Screen or flow test → core/test-suite-structure.md, core/semantics-finders.md, core/assertions-actions.md
│  ├─ One composable → testing-patterns/component-testing.md
│  ├─ ViewModel / coroutines → testing-patterns/coroutines-viewmodels.md
│  ├─ Animation → testing-patterns/animations.md, advanced/clock-control.md
│  ├─ State restoration → testing-patterns/state-restoration.md
│  ├─ Screenshot → testing-patterns/visual-regression.md
│  ├─ Accessibility / focus → testing-patterns/accessibility.md
│  ├─ Font scale, locale, dark mode, size → advanced/device-configuration.md
│  ├─ Navigation → frameworks/navigation.md
│  ├─ Hilt → frameworks/hilt.md
│  └─ Views or Espresso involved → advanced/interoperability.md
│
├─ Test is failing?
│  ├─ Node not found / multiple nodes → core/semantics-finders.md, debugging/debugging.md
│  ├─ Idle timeout / never settles → core/synchronization.md, advanced/clock-control.md
│  ├─ Passes sometimes → debugging/flaky-tests.md
│  └─ Differs from device → core/runtime-modes.md, architecture/test-architecture.md
│
├─ Setting up?
│  ├─ Gradle, @Config, SDK, JDK → core/configuration.md
│  ├─ Looper / graphics / SQLite mode → core/runtime-modes.md
│  └─ CI → infrastructure-ci-cd/ci-cd.md
│
└─ Deciding approach?
   ├─ Which test layer → architecture/test-architecture.md
   └─ What to fake → architecture/test-doubles.md
```

## Test Validation Loop

After writing or modifying tests:

1. **Run the tests**: `./gradlew test`
2. **On failure, print the tree**: `composeTestRule.onRoot().printToLog("TAG")`, or `printToString()` → [debugging.md](debugging/debugging.md)
3. **Check finders**: merged vs unmerged tree → [semantics-finders.md](core/semantics-finders.md)
4. **Check synchronization**: no `Thread.sleep`, let the rule idle or use `waitUntil` → [synchronization.md](core/synchronization.md)
5. **Repeat** until the tests pass
