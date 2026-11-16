---
name: compose-ui-testing-robolectric-best-practices
description: Use when writing, reviewing, or debugging Jetpack Compose UI tests in Kotlin that run locally on the JVM with Robolectric. Covers Android local-unit-test setup, semantics selectors, merged and unmerged trees, ambiguous matches, observable assertions and interactions, Compose clock control, asynchronous work, test isolation, fakes, and failure diagnosis. Not a guide to screenshots, device fidelity, or general Android testing.
license: MIT
compatibility: Guidance targets Android Jetpack Compose and Robolectric, not Compose Desktop. Running the bundled validation project requires an Android SDK, a compatible JDK, Gradle, and dependency downloads.
metadata:
  version: "1.0.0"
---

# Compose UI testing with Robolectric

Write tests that exercise a user action and verify its observable result. Keep framework behavior, fake behavior, and real-device claims separate.

## Route by activity

Read every reference in the matching activity row before proposing code. Resolve these paths relative to this skill directory.

| Activity | Read |
| --- | --- |
| Set up a local JVM Compose test or repair a runner/resource error | [setup.md](references/setup.md) |
| Write a test | [behavior.md](references/behavior.md), [semantics.md](references/semantics.md) |
| Select repeated labels or inspect merged/unmerged nodes | [semantics.md](references/semantics.md) |
| Test loading, async completion, delay, or animation state | [synchronization.md](references/synchronization.md) |
| Choose a fake or prevent test pollution | [isolation.md](references/isolation.md) |
| Review or refactor tests | [behavior.md](references/behavior.md), [synchronization.md](references/synchronization.md), [isolation.md](references/isolation.md) |
| Debug missing nodes, ambiguous selectors, hangs, or timeouts | [diagnostics.md](references/diagnostics.md), then the reference for the failing subsystem |
| Check version-sensitive advice or device limitations | [evidence.md](references/evidence.md) |

## Before changing a test

1. Inspect the project's Gradle plugins, resolved Compose version, runner, SDK selection, rule imports, and test source set. Do not replace its setup with this fixture's versions without a reason.
2. Identify the observable behavior and which actor owns pending work. A clock, dispatcher, looper, and external service are not interchangeable.
3. Inspect the semantics tree before guessing why a selector fails. A merged parent's text can match even when its child is not separately exposed.
4. Keep one rule and one `setContent` call per test. Use fresh mutable state and fakes.
5. Run the narrow test. Introduce the relevant UI regression and confirm that the test fails at the intended assertion. A compile error is not mutation detection.

## Non-negotiable distinctions

- Compose assertions and actions synchronize with known idle work. They do not retry an arbitrary business condition until it becomes true. Use an explicit bounded wait for external work.
- A singular finder requires one node. Do not silence an ambiguous match with an index unless order is the behavior under test.
- Use the merged tree for user-facing groups. Use the unmerged tree when the test specifically needs a child. Do not enable it everywhere to make failures disappear.
- Advance the clock that owns the work. `mainClock` does not complete a parked fake, real I/O, or an unrelated coroutine scheduler.
- Assert the resulting text, enabled state, selection, or visible outcome. Node existence or a mock call alone may not prove the user's result.
- Do not use fixed sleeps, `returnDefaultValues`, or swallowed assertion failures to make tests green.

## Scope and proof

The [evidence reference](references/evidence.md) separates documented behavior, executable observations, and unverified claims. The [bundled examples](examples/) are the canonical Kotlin sources used by the repository validation project. They are examples, not an application architecture.

Robolectric runs Android code in a JVM environment. A passing test does not establish real-device rendering, TalkBack navigation, system UI, IME behavior, hardware behavior, or performance. Use device or emulator tests for claims that depend on those systems.

Report the command you ran, the versions it exercised, and what remains unverified. Do not describe compilation alone as a passing UI test.
