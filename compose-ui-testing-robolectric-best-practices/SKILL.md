---
name: compose-ui-testing-robolectric-best-practices
description: Use when writing, reviewing, debugging, or organizing Jetpack Compose UI tests in Kotlin that run locally on the JVM with Robolectric. Covers semantics selectors, merged and unmerged trees, assertions, synchronization, clocks, coroutine work, rules, fakes, test data, screen robots, forms, gestures, accessibility, localization, authentication, reactive streams, navigation, ViewModels, dependency injection, Android interop, files, error states, Gradle setup, CI, parallel execution, reporting, and coverage. Includes local test strategies and explicit handoffs for screenshots, performance, security, system UI, and external integrations. Not a device-fidelity or Compose Desktop testing guide.
license: MIT
compatibility: Targets Android Jetpack Compose local unit tests with Robolectric. Running the bundled examples requires an Android SDK, a compatible JDK, Gradle, and dependency downloads. Read the consuming project's versions before choosing APIs.
metadata:
  version: "1.0.0"
---

# Compose UI testing with Robolectric best practices

Write, review, and debug Android Compose UI tests through semantics and observable behavior. Use real Compose execution with controlled dependencies. Keep local JVM evidence separate from transport, system, rendering, and device evidence.

This skill adapts the activity-based structure and topic library of Currents' Playwright best-practices skill. The [adaptation map](adaptation-map.json) records every source topic at the pinned upstream revision. Android-native mechanisms replace browser mechanisms. A replacement is not an API equivalence.

## Activity-based reference guide

Read the foundation row for your task first. Then choose the matching topic rows and read their linked guides before proposing code. Resolve paths relative to this skill directory. Read only the required foundation and relevant topics, not the whole library. A specific topic row supplements its task foundation rather than replacing it.

### Start with the task foundation

| Task | Required foundation |
| --- | --- |
| Write a new test, including a selector-focused test | [Behavior](references/behavior.md), [semantics](references/semantics.md) |
| Review or refactor an existing test | [Behavior](references/behavior.md), [synchronization](references/synchronization.md), [isolation](references/isolation.md) |
| Debug a failing test, including a missing node | [Diagnostics](references/diagnostics.md), [semantics](references/semantics.md) |
| Set up a project or repair its test host | [Setup](references/setup.md), [evidence and limits](references/evidence.md) |

### Write new tests

Use these routes when creating test classes, cases, or scenarios.

| Activity | Reference files |
| --- | --- |
| Write a hosted UI behavior test | [Behavior](references/behavior.md), [semantics](references/semantics.md), [suite structure](core/test-suite-structure.md), [assertions and waiting](core/assertions-waiting.md) |
| Test one composable | [Component testing](testing-patterns/component-testing.md), [fixtures and rules](core/fixtures-hooks.md) |
| Select repeated labels or lazy-list items | [Semantics selectors](core/semantics-selectors.md), [gestures and scrolling](testing-patterns/gestures.md) |
| Test a repository or API contract | [Repository contracts](testing-patterns/repository-contracts.md), [when to fake](architecture/when-to-fake.md) |
| Test GraphQL-backed UI | [GraphQL](testing-patterns/graphql.md), [network fakes](advanced/network-fakes.md) |
| Organize repeated interactions | [Screen robots](core/screen-robots.md), [robots versus fixtures](architecture/robots-vs-fixtures.md) |
| Create data and lifecycle fixtures | [Test data](core/test-data.md), [fixtures and hooks](core/fixtures-hooks.md), [isolation](references/isolation.md) |
| Test forms and validation | [Forms and validation](testing-patterns/forms-validation.md), [error states](debugging/error-testing.md) |
| Test touch input, scrolling, or drag behavior | [Gestures](testing-patterns/gestures.md), [semantics selectors](core/semantics-selectors.md) |
| Test accessible semantics | [Accessibility](testing-patterns/accessibility.md), [semantics](references/semantics.md) |
| Test locale, plurals, or RTL | [Internationalization](testing-patterns/i18n.md), [adaptive layouts](advanced/adaptive-layouts.md) |
| Test local files or exported content | [File operations](testing-patterns/file-operations.md), [file transfers](testing-patterns/file-transfers.md) |
| Test custom drawing or screenshot-related state | [Custom drawing](testing-patterns/custom-drawing.md), [visual regression](testing-patterns/visual-regression.md) |
| Check sensitive-data UI and prohibited actions | [Security testing](testing-patterns/security-testing.md), [authentication](advanced/authentication.md) |
| Choose annotations or a runnable subset | [Annotations](core/annotations.md), [test filtering](core/test-filtering.md) |

### Test adaptive layouts and input

Use these routes for configuration changes, window constraints, fonts, and input modes.

| Activity | Reference files |
| --- | --- |
| Change orientation, density, font scale, or available width | [Adaptive layouts](advanced/adaptive-layouts.md), [configuration](core/configuration.md) |
| Verify touch-driven UI state | [Gestures](testing-patterns/gestures.md) |
| Verify editable text and IME action callbacks | [Forms and validation](testing-patterns/forms-validation.md) |
| Decide whether a claim needs a device | [Test architecture](architecture/test-architecture.md), [evidence and limits](references/evidence.md) |

### Test Android services and reactive updates

Use these routes when UI depends on platform capabilities, external hosts, or asynchronous events.

| Activity | Reference files |
| --- | --- |
| Model permission, location, clipboard, or capability state | [System services](android-apis/system-services.md) |
| Test AndroidView, ComposeView, or embedded WebView boundaries | [View interop](android-apis/view-interop.md) |
| Test cached, offline, or background-work UI | [Background work](android-apis/background-work.md), [error states](debugging/error-testing.md) |
| Test streams, incoming messages, reconnects, or event ordering | [Reactive streams](android-apis/reactive-streams.md), [network fakes](advanced/network-fakes.md) |
| Test dialogs, popups, and multiple semantics roots | [Multiple roots](advanced/multiple-roots.md) |
| Test payment, email, SMS, or external SDK outcomes | [Third-party integrations](advanced/third-party.md), [file transfers](testing-patterns/file-transfers.md) |
| Test notifications, widgets, or another app's UI | [System surfaces](testing-patterns/system-surfaces.md), [host integration](testing-patterns/host-integration.md) |

### Debug and troubleshoot

Use these routes for failed queries, unexpected states, timeouts, and test pollution.

| Activity | Reference files |
| --- | --- |
| Classify a test failure | [Diagnostics](references/diagnostics.md), [debugging](debugging/debugging.md) |
| Diagnose a missing or ambiguous node | [Semantics](references/semantics.md), [semantics selectors](core/semantics-selectors.md), [debugging](debugging/debugging.md) |
| Investigate an idle timeout or frozen animation | [Synchronization](references/synchronization.md), [assertions and waiting](core/assertions-waiting.md), [clock control](advanced/clock-control.md) |
| Fix flaky tests or race conditions | [Flaky tests](debugging/flaky-tests.md), [clock control](advanced/clock-control.md), [fixtures and hooks](core/fixtures-hooks.md) |
| Diagnose failures only in the whole suite or parallel runs | [Flaky tests](debugging/flaky-tests.md), [isolation](references/isolation.md), [parallel execution](infrastructure-ci-cd/parallel-sharding.md) |
| Inspect uncaught exceptions or Android logs | [Logs and exceptions](debugging/logs-exceptions.md), [debugging](debugging/debugging.md) |
| Separate a resource/runner failure from a selector failure | [Setup](references/setup.md), [configuration](core/configuration.md), [debugging](debugging/debugging.md) |

### Test errors and edge cases

Use these routes for loading, empty, partial, denied, failed, and retry states.

| Activity | Reference files |
| --- | --- |
| Verify loading, failure, recovery, and retry | [Error testing](debugging/error-testing.md), [network fakes](advanced/network-fakes.md) |
| Verify offline and stale-cache behavior | [Background work](android-apis/background-work.md), [error testing](debugging/error-testing.md) |
| Verify validation errors and repeated submissions | [Forms and validation](testing-patterns/forms-validation.md) |
| Verify partial GraphQL data and operation errors | [GraphQL](testing-patterns/graphql.md) |
| Verify cancellation and late completions | [Reactive streams](android-apis/reactive-streams.md), [clock control](advanced/clock-control.md), [fixtures and hooks](core/fixtures-hooks.md) |

### Test authentication and multiple actors

Use these routes for session-dependent behavior, user roles, and controlled remote updates.

| Activity | Reference files |
| --- | --- |
| Render signed-in, signed-out, expired, and revoked sessions | [Authentication](advanced/authentication.md) |
| Test login, MFA, reset, expiry, or onboarding flows | [Authentication flows](advanced/authentication-flows.md), [third-party integrations](advanced/third-party.md) |
| Verify role-dependent controls and independent users | [Multiple users](advanced/multi-user.md), [security testing](testing-patterns/security-testing.md) |
| Model collaboration, conflicts, and remote events | [Multiple users](advanced/multi-user.md), [reactive streams](android-apis/reactive-streams.md) |
| Separate client session behavior from real OAuth/backend proof | [Authentication flows](advanced/authentication-flows.md), [test architecture](architecture/test-architecture.md) |

### Make architecture decisions

Use these routes before choosing a test layer, dependency boundary, or shared abstraction.

| Activity | Reference files |
| --- | --- |
| Choose pure JVM, Robolectric UI, transport, or device testing | [Test architecture](architecture/test-architecture.md) |
| Choose screen robots, fixtures, or direct test code | [Robots versus fixtures](architecture/robots-vs-fixtures.md), [screen robots](core/screen-robots.md) |
| Decide which dependencies to fake | [When to fake](architecture/when-to-fake.md), [repository contracts](testing-patterns/repository-contracts.md) |
| Design module, flavor, or variant test dependencies | [Modules and variants](core/modules-variants.md) |
| Define suite prerequisites without shared mutable UI | [Global setup](core/global-setup.md), [fixtures and hooks](core/fixtures-hooks.md) |

### Test Compose integrations

These Android topics replace the source skill's web-framework integration guides. They do not describe React, Angular, Vue, or Next.js execution in Robolectric.

| Activity | Reference files |
| --- | --- |
| Test state hoisting, effects, ViewModels, and StateFlow | [State and ViewModels](frameworks/state-viewmodels.md), [reactive streams](android-apis/reactive-streams.md) |
| Install test dependencies before creating the host | [Dependency injection](frameworks/dependency-injection.md), [fixtures and hooks](core/fixtures-hooks.md) |
| Test Navigation Compose, route inputs, and back behavior | [Navigation](frameworks/navigation.md), [multiple roots](advanced/multiple-roots.md) |
| Mount the production theme and test Material components | [Design systems](frameworks/design-systems.md), [component testing](testing-patterns/component-testing.md) |

### Review, refactor, and maintain tests

Use these routes when improving existing tests or reviewing a proposed change.

| Activity | Reference files |
| --- | --- |
| Review a test for useful behavioral proof | [Behavior](references/behavior.md), [synchronization](references/synchronization.md), [isolation](references/isolation.md), [assertions and waiting](core/assertions-waiting.md) |
| Replace brittle selectors | [Semantics selectors](core/semantics-selectors.md) |
| Remove sleeps and broad retry wrappers | [Assertions and waiting](core/assertions-waiting.md), [flaky tests](debugging/flaky-tests.md) |
| Extract repeated actions without hiding assertions | [Screen robots](core/screen-robots.md), [robots versus fixtures](architecture/robots-vs-fixtures.md) |
| Extract lifecycle setup or deterministic data | [Fixtures and hooks](core/fixtures-hooks.md), [test data](core/test-data.md) |
| Organize or quarantine tests without losing coverage | [Suite structure](core/test-suite-structure.md), [annotations](core/annotations.md), [test filtering](core/test-filtering.md) |
| Review version-sensitive claims and evidence | [Evidence and limits](references/evidence.md), [test architecture](architecture/test-architecture.md) |

### Configure infrastructure

Use these routes for local setup, build workers, CI, artifacts, and suite execution costs.

| Activity | Reference files |
| --- | --- |
| Configure Android local UI tests | [Setup](references/setup.md), [configuration](core/configuration.md), [modules and variants](core/modules-variants.md) |
| Set up a portable CI job | [CI/CD](infrastructure-ci-cd/ci-cd.md), [reporting](infrastructure-ci-cd/reporting.md) |
| Configure GitHub Actions | [GitHub Actions](infrastructure-ci-cd/github-actions.md) |
| Configure GitLab CI | [GitLab](infrastructure-ci-cd/gitlab.md) |
| Adapt another CI provider | [Other providers](infrastructure-ci-cd/other-providers.md) |
| Run in a container | [Docker](infrastructure-ci-cd/docker.md) |
| Configure forks, shards, and result aggregation | [Parallel execution](infrastructure-ci-cd/parallel-sharding.md), [test data](core/test-data.md) |
| Diagnose suite startup, memory, or build costs | [Suite performance](infrastructure-ci-cd/performance.md) |
| Collect JUnit, HTML reports, logs, and semantics dumps | [Reporting](infrastructure-ci-cd/reporting.md) |
| Assess code coverage and missing behavioral cases | [Test coverage](infrastructure-ci-cd/test-coverage.md) |
| Filter a method, class, category, or variant | [Test filtering](core/test-filtering.md), [modules and variants](core/modules-variants.md) |

### Evaluate rendering, performance, and external claims

Use these routes when the requested assertion is larger than a local semantics test can establish.

| Activity | Reference files |
| --- | --- |
| Plan screenshot baselines and renderer-specific comparisons | [Visual regression](testing-patterns/visual-regression.md), [custom drawing](testing-patterns/custom-drawing.md) |
| Verify startup, jank, frame time, or a performance budget | [Performance testing](testing-patterns/performance-testing.md) |
| Verify security beyond client UI behavior | [Security testing](testing-patterns/security-testing.md) |
| Verify external windows, widgets, or platform behavior | [Host integration](testing-patterns/host-integration.md), [system surfaces](testing-patterns/system-surfaces.md) |
| Determine what a passing local test actually proves | [Evidence and limits](references/evidence.md), [test architecture](architecture/test-architecture.md) |

## Quick decision tree

Use this shorter route when you know the symptom or boundary. The activity tables above provide the full topic inventory.

1. Does the test fail before content starts? Read [configuration](core/configuration.md) and [debugging](debugging/debugging.md). Inspect runner, resources, host declaration, resolved versions, and worker JDK first.
2. Does a node query fail? Read [semantics selectors](core/semantics-selectors.md). Inspect merged and unmerged trees. Check cardinality, root, lazy composition, and cleared semantics before changing the selector.
3. Does the correct action produce the wrong or missing result? Read [assertions and waiting](core/assertions-waiting.md) and [error testing](debugging/error-testing.md). Identify the pending work's owner and assert the observable transition.
4. Does advancing time do nothing? Read [clock control](advanced/clock-control.md). Separate Compose time, coroutine time, Android looper work, business time, and parked external dependencies.
5. Does the test pass alone but fail with other tests? Read [fixtures and hooks](core/fixtures-hooks.md) and [flaky tests](debugging/flaky-tests.md). Look for shared state, unfinished jobs, global replacements, and resource reuse.
6. Does the UI depend on a ViewModel, navigation, dependency injection, or theme? Choose the matching [Compose integration](#test-compose-integrations) row before adding a second host or fake layer.
7. Does the claim concern a transport, real service, pixels, accessibility service, OS UI, hardware, or timing? Read [test architecture](architecture/test-architecture.md) and the matching external-claim guide. Test the local UI contract here and collect integration or device evidence separately.
8. Is the problem test organization or CI? Choose [maintenance](#review-refactor-and-maintain-tests) or [infrastructure](#configure-infrastructure). Do not fix missing or skipped test execution with a green build banner.

## Before changing a test

1. Inspect Gradle plugins, resolved Compose artifacts, runner, selected runtime SDK, rule imports, and source set. Do not replace the project's setup with this fixture's versions without a reason.
2. Name the user-visible behavior, the action that causes it, and the boundary this test can prove.
3. Identify the actor that owns each pending operation. A clock, dispatcher, looper, and external service are not interchangeable.
4. Use one content owner. For rule-hosted examples, create one rule and call `setContent` once. If a production activity sets its own content, do not set it again.
5. Create fresh mutable state and fakes for each test. Restore owned globals and release pending work even when assertions fail.
6. Inspect the semantics tree before guessing why a selector fails. Merged parent text can match without exposing a separately selectable child.

## Non-negotiable distinctions

- Compose assertions and actions synchronize with known idle work. They do not retry an arbitrary business condition until it becomes true. Use a bounded condition wait or a controlled dependency for external work.
- A singular finder requires one node. Scope repeated labels by meaningful identity. Use an index only when order is the behavior under test.
- Use merged semantics for user-facing groups. Use the unmerged tree only when the test needs a particular child or diagnoses merging.
- Advance the clock that owns the work. `mainClock` does not complete parked fakes, real I/O, or unrelated coroutine schedulers.
- Assert the resulting text, enabled state, selection, or visible outcome after an interaction. A mock call or node existence alone can miss a broken user result.
- Do not hide failures with fixed sleeps, `returnDefaultValues`, swallowed assertions, broad retry wrappers, or blanket test skips.
- Match imports to the resolved artifact. The canonical fixture uses Compose UI 1.12.1 and the v2 rule factory. Online examples may use older imports or 1.13-only APIs.

## Test validation loop

After writing or changing a test:

1. Run the consuming module's narrow local-unit-test task. Substitute its actual module, variant, and test name. For this repository's [canonical examples](examples/FixtureUiTest.kt), use:

```bash
./gradlew :fixture:testDebugUnitTest \
  --tests fixture.FixtureUiTest.scopedOpenSelectsDraft \
  --console=plain --rerun-tasks
```

2. Inspect the process exit code, named JUnit method, failure details, and skipped count. Compilation, `NO-SOURCE`, an empty report, or an unrelated passing method is not a passing UI test.
3. If the test fails, classify setup, compilation, selector, synchronization, state, or assertion failure. Capture relevant trees and logs. Correct the cause and rerun the same method.
4. Introduce a relevant behavior regression in a disposable copy. Require the intended assertion to fail. A compiler or host error is not successful mutation detection.
5. Restore the production behavior and rerun. Run the owning class and full relevant suite to catch isolation errors.
6. For a suspected flake, repeat the same scenario and compare isolated and suite runs. Record every failure. Repetition can expose a race; it does not prove its absence.
7. Report the command, dependency/runtime versions, named test results, regression control, and unverified claims. Only proceed when the required checks pass.

The repository includes scripts for package validation, fixture mutations, setup comparison, and saved agent-output replay. Those scripts are not installed application dependencies. Consult the source repository README when maintaining this skill.

## Scope and proof

The [evidence reference](references/evidence.md) separates documented behavior, fixture observations, and unverified claims. The [canonical Kotlin sources](examples/) are executable in the repository fixture. Other snippets are illustrative unless their guide records a separate execution result.

Robolectric executes Android code in a JVM environment. Local UI tests do not establish real-device rendering, TalkBack navigation, system UI, IME integration, hardware behavior, app performance, real service integration, or process death. Optional screenshot tools have their own renderer and baseline contracts. Use device, transport, security, or service tests for claims owned by those systems.
