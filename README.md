# Compose UI Testing with Robolectric Best Practices Skill

A skill that gives the AI specialized guidance for writing, debugging, and maintaining **Jetpack Compose UI tests** that run locally on the JVM with **Robolectric**, in **Kotlin**. It follows the format of [currents-dev/playwright-best-practices-skill](https://github.com/currents-dev/playwright-best-practices-skill).

## Sources of Truth

The skill uses only current official Compose UI testing and Robolectric documentation. [`sources.txt`](sources.txt) defines that boundary:

- **Compose UI testing**: the Testing section of the Compose docs on developer.android.com, the `androidx.compose.ui.test` API reference, and the Compose UI release notes for the current stable and newer releases.
- **Robolectric**: robolectric.org guides and javadoc, the latest Robolectric release notes, and Android's Robolectric page. Blog posts are excluded, because they are dated or describe themselves as unofficial.

Every paragraph, list item, table row, and code block in the reference files has an entry in [`verification/`](verification) that quotes the official page supporting it. A script checks that each quote appears word for word in the current text of that page.

## Installation

```bash
npx skills add https://github.com/just-joshn/compose-ui-testing-robolectric-best-practices-skill
```

The skill is activity-based. The AI is directed to the right reference for what you're doing, so it gets focused advice without loading everything at once.

## When the Skill Is Used

The skill triggers when the AI infers you need help with things like:

- Writing Compose UI tests with `createComposeRule`, `createAndroidComposeRule`, or `runComposeUiTest`
- Finding nodes by semantics, text, test tags, and the unmerged tree
- Synchronization, idling resources, `waitUntil`, and the Compose test clock
- Testing animations and coroutines with the v2 test APIs
- State restoration with `StateRestorationTester`
- Font scale, locale, layout direction, dark mode, and Robolectric qualifiers
- Accessibility checks and focus navigation
- Compose with Views, Espresso, and UiAutomator
- Robolectric `@Config`, `robolectric.properties`, looper, graphics, and SQLite modes
- Fixing flaky tests, debugging failures, and running tests in CI

## What's Inside

**20 reference documents** organized into 6 categories:

### Core (`core/`)

| Topic | Reference | Use for |
| --- | --- | --- |
| Test structure | `test-suite-structure.md` | Test anatomy, rules, v2 APIs, running on Robolectric |
| Configuration | `configuration.md` | Dependencies, `@Config`, `robolectric.properties`, JDK, system properties |
| Semantics & finders | `semantics-finders.md` | Finders, matchers, merged vs unmerged trees, test tags |
| Assertions & actions | `assertions-actions.md` | Assertions, actions, touch, key, and text input, scrolling |
| Synchronization | `synchronization.md` | Auto-sync, idling resources, `waitUntil`, main thread |
| Runtime modes | `runtime-modes.md` | Robolectric looper, graphics, and SQLite modes |

### Debugging (`debugging/`)

| Topic | Reference | Use for |
| --- | --- | --- |
| Debugging | `debugging.md` | Printing the semantics tree, failure artifacts, Robolectric logging |
| Flaky tests | `flaky-tests.md` | Synchronization, coroutine, looper, and thread causes |

### Testing Patterns (`testing-patterns/`)

| Topic | Reference | Use for |
| --- | --- | --- |
| Component testing | `component-testing.md` | Testing composables in isolation, custom semantics |
| Accessibility | `accessibility.md` | Accessibility checks, focus navigation tests |
| Animations | `animations.md` | Driving animations with the test clock |
| State restoration | `state-restoration.md` | `StateRestorationTester`, activity recreation |
| Visual regression | `visual-regression.md` | Native graphics and capturing a node |
| Coroutines | `coroutines.md` | v1 and v2 dispatchers, `runComposeUiTest`, coroutine contexts |

### Advanced (`advanced/`)

| Topic | Reference | Use for |
| --- | --- | --- |
| Clock control | `clock-control.md` | `MainTestClock`, `autoAdvance`, frame stepping |
| Device configuration | `device-configuration.md` | `DeviceConfigurationOverride`, Robolectric qualifiers |
| Interoperability | `interoperability.md` | Views, Espresso, UiAutomator with Compose |

### Architecture (`architecture/`)

| Topic | Reference | Use for |
| --- | --- | --- |
| Test architecture | `test-architecture.md` | Robolectric or device tests, source sets |
| Test doubles | `test-doubles.md` | Shadows, mocking and spying on Android classes |

### Infrastructure (`infrastructure-ci-cd/`)

| Topic | Reference | Use for |
| --- | --- | --- |
| CI/CD | `ci-cd.md` | Java versions, android-all downloads, mirrors and proxies |

## Not Covered

These topics are in the Playwright skill, but the official Compose UI testing and Robolectric docs don't cover them, so this skill leaves them out:

- Page objects, test tags, test data factories
- Authentication and multi-user flows
- Network mocking, GraphQL, WebSockets
- File upload and download
- Security testing and performance budgets
- CI provider recipes (GitHub Actions, GitLab, Docker), sharding, coverage, and reporting

Topics documented only outside that boundary are also left out: Hilt, Navigation, ViewModel and `kotlinx-coroutines-test` guidance, the Compose BOM, and Android Studio's screenshot testing tool.

## Validation

```bash
python3 scripts/check_skill.py      # frontmatter, links, anchors, sections, official-only URLs
python3 scripts/fetch_sources.py    # download the current text of every cited page into .cache/
python3 scripts/verify_claims.py    # every unit has quotes found word for word on those pages
```

`verify_claims.py` also checks that every API name in the code examples appears on an official page or is declared in the same example, and that advice (should, avoid, prefer, ...) is quoted from a page that gives that advice. It can't judge whether a quote fully supports its unit. That part was reviewed by hand.

## License

MIT
