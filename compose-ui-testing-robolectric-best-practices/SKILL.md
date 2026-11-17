---
name: compose-ui-testing-robolectric-best-practices
description: Use when writing, reviewing, or debugging Jetpack Compose UI tests that run locally on the JVM with Robolectric. Covers compose test rules (createComposeRule, createAndroidComposeRule, runComposeUiTest), semantics finders and matchers, merged vs unmerged trees, assertions and actions, synchronization and idling resources, waitUntil, the MainTestClock and animations, coroutines in the v2 test APIs, state restoration (StateRestorationTester), device configuration (DeviceConfigurationOverride, Robolectric qualifiers), accessibility checks and focus tests, View, Espresso and UiAutomator interoperability, shadows and mocks, Robolectric @Config, robolectric.properties, LooperMode, GraphicsMode, SQLiteMode, screenshots, flaky tests, debugging with printToLog, choosing Robolectric or device tests, and CI.
license: MIT
compatibility: Robolectric 4.18 supports Android API 24 → 37. Compose ui-test stable release 1.12.1, release candidate 1.13.0-rc01.
metadata:
  version: "3.0.0"
---

# Compose UI Testing with Robolectric Best Practices

This skill provides guidance for Jetpack Compose UI tests that run on the JVM with Robolectric. It uses only the official Compose UI testing and Robolectric documentation. Every statement in the reference files is backed by a quote from those pages, recorded in the repository's `verification/` ledgers.

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
| **Clicking, typing, scrolling, gestures, keys** | [assertions-actions.md](core/assertions-actions.md) |
| **Coroutines and the v2 test dispatcher** | [coroutines.md](testing-patterns/coroutines.md), [synchronization.md](core/synchronization.md) |
| **Testing animations** | [animations.md](testing-patterns/animations.md), [clock-control.md](advanced/clock-control.md) |
| **Controlling the test clock** | [clock-control.md](advanced/clock-control.md) |
| **Testing state restoration** | [state-restoration.md](testing-patterns/state-restoration.md) |
| **Screenshots of composables** | [visual-regression.md](testing-patterns/visual-regression.md), [runtime-modes.md](core/runtime-modes.md) |
| **Accessibility checks and semantics** | [accessibility.md](testing-patterns/accessibility.md), [semantics-finders.md](core/semantics-finders.md) |
| **Testing keyboard focus navigation** | [accessibility.md](testing-patterns/accessibility.md), [assertions-actions.md](core/assertions-actions.md) |

### Device Configuration

**When to use**: Testing font scale, locale, layout direction, dark mode, sizes, and Robolectric qualifiers

| Activity | Reference Files |
| --- | --- |
| **Overriding configuration for a composable** | [device-configuration.md](advanced/device-configuration.md) |
| **Robolectric qualifiers (`@Config(qualifiers)`)** | [device-configuration.md](advanced/device-configuration.md), [configuration.md](core/configuration.md) |
| **Changing configuration during a test** | [device-configuration.md](advanced/device-configuration.md) |

### Android Integration

**When to use**: Testing Compose alongside Views, Espresso, or UiAutomator

| Activity | Reference Files |
| --- | --- |
| **Compose and Views in one test** | [interoperability.md](advanced/interoperability.md) |
| **Using Espresso with a Compose rule** | [interoperability.md](advanced/interoperability.md), [synchronization.md](core/synchronization.md) |
| **Finding composables from UiAutomator** | [interoperability.md](advanced/interoperability.md) |

### Debugging & Troubleshooting

**When to use**: Test failures, node not found, timeouts, unexpected behavior

| Activity | Reference Files |
| --- | --- |
| **Debugging test failures** | [debugging.md](debugging/debugging.md), [semantics-finders.md](core/semantics-finders.md) |
| **Printing the semantics tree** | [debugging.md](debugging/debugging.md) |
| **Node not found or matched multiple nodes** | [semantics-finders.md](core/semantics-finders.md), [debugging.md](debugging/debugging.md) |
| **Fixing flaky tests** | [flaky-tests.md](debugging/flaky-tests.md), [synchronization.md](core/synchronization.md) |
| **Timeouts and waiting for conditions** | [synchronization.md](core/synchronization.md), [clock-control.md](advanced/clock-control.md) |
| **Work the test doesn't wait for** | [synchronization.md](core/synchronization.md), [coroutines.md](testing-patterns/coroutines.md) |
| **Robolectric behaves differently from a device** | [runtime-modes.md](core/runtime-modes.md), [test-architecture.md](architecture/test-architecture.md), [ci-cd.md](infrastructure-ci-cd/ci-cd.md) |

### Architecture Decisions

**When to use**: Choosing between Robolectric and device tests, or deciding what to replace

| Activity | Reference Files |
| --- | --- |
| **Robolectric or device test** | [test-architecture.md](architecture/test-architecture.md) |
| **Shadows and mocking Android classes** | [test-doubles.md](architecture/test-doubles.md) |

### Refactoring & Maintenance

**When to use**: Improving existing tests, code review

| Activity | Reference Files |
| --- | --- |
| **Choosing finders and matchers** | [semantics-finders.md](core/semantics-finders.md) |
| **Replacing manual waits with conditions** | [synchronization.md](core/synchronization.md), [flaky-tests.md](debugging/flaky-tests.md) |
| **Migrating to the v2 test APIs** | [coroutines.md](testing-patterns/coroutines.md), [test-suite-structure.md](core/test-suite-structure.md) |

### Infrastructure & Configuration

**When to use**: Setting up the project, Robolectric config, CI

| Activity | Reference Files |
| --- | --- |
| **Gradle dependencies** | [configuration.md](core/configuration.md) |
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
│  ├─ Coroutines → testing-patterns/coroutines.md
│  ├─ Animation → testing-patterns/animations.md, advanced/clock-control.md
│  ├─ State restoration → testing-patterns/state-restoration.md
│  ├─ Screenshot → testing-patterns/visual-regression.md
│  ├─ Accessibility / focus → testing-patterns/accessibility.md
│  ├─ Font scale, locale, dark mode, size → advanced/device-configuration.md
│  └─ Views, Espresso, or UiAutomator involved → advanced/interoperability.md
│
├─ Test is failing?
│  ├─ Node not found / multiple nodes → core/semantics-finders.md, debugging/debugging.md
│  ├─ Timeout waiting for a condition → core/synchronization.md, advanced/clock-control.md
│  ├─ Passes sometimes → debugging/flaky-tests.md
│  └─ Differs from device → core/runtime-modes.md, architecture/test-architecture.md
│
├─ Setting up?
│  ├─ Gradle, @Config, SDK, JDK → core/configuration.md
│  ├─ Looper / graphics / SQLite mode → core/runtime-modes.md
│  └─ CI → infrastructure-ci-cd/ci-cd.md
│
└─ Deciding approach?
   ├─ Robolectric or device → architecture/test-architecture.md
   └─ Shadows and mocks → architecture/test-doubles.md
```

## Test Validation Loop

After writing or modifying tests:

1. **Run the tests**.
2. **Look at the semantics tree**, the main way to solve problems in your tests: `composeTestRule.onRoot().printToLog()` → [debugging.md](debugging/debugging.md)
3. **Match unmerged nodes when needed**: set `useUnmergedTree` to `true` → [semantics-finders.md](core/semantics-finders.md)
4. **Conditions that depend on external work**: use a more general concept such as `waitUntil()` → [synchronization.md](core/synchronization.md)
5. **Repeat** until the tests pass.
