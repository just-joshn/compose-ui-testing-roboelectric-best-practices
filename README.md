# Compose UI Testing with Robolectric Best Practices Skill

A skill that gives the AI specialized guidance for writing, debugging, and maintaining **Jetpack Compose UI tests** that run locally on the JVM with **Robolectric**, in **Kotlin**. It follows the format of [currents-dev/playwright-best-practices-skill](https://github.com/currents-dev/playwright-best-practices-skill).

Every reference file is grounded only in official documentation from developer.android.com and robolectric.org, read on 2026-11-17. Each file ends with a `Sources` section listing the pages it is based on.

## Installation

```bash
npx skills add https://github.com/just-joshn/compose-ui-testing-robolectric-best-practices-skill
```

The skill is activity-based. The AI is directed to the right reference for what you're doing, so it gets focused advice without loading everything at once.

## When the Skill Is Used

The skill triggers when the AI infers you need help with things like:

- Writing Compose UI tests in `src/test` with `createComposeRule`, `createAndroidComposeRule`, or `runComposeUiTest`
- Finding nodes by semantics, text, test tags, and the unmerged tree
- Synchronization, idling resources, `waitUntil`, and the Compose test clock
- Testing animations, ViewModels, StateFlow, and coroutines
- State restoration and configuration changes
- Font scale, locale, RTL, dark mode, and window sizes
- Accessibility semantics and focus navigation
- Compose and View interop, Espresso, Navigation Compose, and Hilt
- Robolectric `@Config`, `robolectric.properties`, looper, graphics, and SQLite modes
- Screenshot testing options
- Fixing flaky tests, debugging failures, and running tests in CI

## What's Inside

**22 reference documents** organized into 7 categories:

### Core (`core/`)

| Topic | Reference | Use for |
| --- | --- | --- |
| Test structure | `test-suite-structure.md` | Test anatomy, rules, `src/test`, shared JVM/device tests |
| Configuration | `configuration.md` | Gradle dependencies, `@Config`, `robolectric.properties`, SDK and JDK |
| Semantics & finders | `semantics-finders.md` | Finders, matchers, merged vs unmerged trees, test tags |
| Assertions & actions | `assertions-actions.md` | Assertions, collections, clicks, text input, gestures |
| Synchronization | `synchronization.md` | Auto-sync, idling resources, `waitUntil`, v2 dispatcher |
| Runtime modes | `runtime-modes.md` | Robolectric looper, graphics, and SQLite modes |

### Debugging (`debugging/`)

| Topic | Reference | Use for |
| --- | --- | --- |
| Debugging | `debugging.md` | Printing the semantics tree, failure artifacts |
| Flaky tests | `flaky-tests.md` | Stability causes and fixes |

### Testing Patterns (`testing-patterns/`)

| Topic | Reference | Use for |
| --- | --- | --- |
| Component testing | `component-testing.md` | Testing composables in isolation, edge cases |
| Accessibility | `accessibility.md` | Accessibility semantics, checks, focus navigation |
| Animations | `animations.md` | Driving animations with the test clock |
| State restoration | `state-restoration.md` | `StateRestorationTester`, `rememberSaveable` |
| Visual regression | `visual-regression.md` | Screenshot testing options and limits |
| Coroutines & ViewModels | `coroutines-viewmodels.md` | `runTest`, test dispatchers, ViewModel state |

### Advanced (`advanced/`)

| Topic | Reference | Use for |
| --- | --- | --- |
| Clock control | `clock-control.md` | `MainTestClock`, `autoAdvance`, frame stepping |
| Device configuration | `device-configuration.md` | `DeviceConfigurationOverride`, Robolectric qualifiers |
| Interoperability | `interoperability.md` | Views, Espresso, UiAutomator with Compose |

### Architecture (`architecture/`)

| Topic | Reference | Use for |
| --- | --- | --- |
| Test architecture | `test-architecture.md` | Robolectric vs device vs pure JVM |
| Test doubles | `test-doubles.md` | Fakes, mocks, hermetic tests |

### Frameworks (`frameworks/`)

| Topic | Reference | Use for |
| --- | --- | --- |
| Navigation | `navigation.md` | Navigation Compose, `TestNavHostController` |
| Hilt | `hilt.md` | Hilt on Robolectric, `HiltTestApplication` |

### Infrastructure (`infrastructure-ci-cd/`)

| Topic | Reference | Use for |
| --- | --- | --- |
| CI/CD | `ci-cd.md` | Running local tests in CI, android-all downloads |

## Not Covered

The Playwright skill covers these topics, but no official Compose or Robolectric documentation does, so this skill leaves them out: page objects, test tags, test data factories, authentication and multi-user flows, network mocking, GraphQL, WebSockets, file upload and download, security testing, performance budgets, CI provider recipes (GitHub Actions, GitLab, Docker), sharding, coverage, and reporting.

## Validation

`sources.txt` lists every official page the skill may cite. The check script verifies frontmatter, links, anchors, required sections, and that every cited URL is on that list:

```bash
python3 scripts/check_skill.py
```

## License

MIT
