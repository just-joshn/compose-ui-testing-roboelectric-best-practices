# Source inspection and adaptation contract

The source is [Currents' Playwright best-practices skill](https://github.com/currents-dev/playwright-best-practices-skill/tree/0b75b5835a87de1fdd202ba965f3bc5a27738fdf) at commit `0b75b5835a87de1fdd202ba965f3bc5a27738fdf`. This revision has 58 topic guides across eight categories, plus `SKILL.md`. The source was cloned and inspected on 2026-11-16.

## Correct the earlier scope

The earlier version of this package deliberately reduced the source to seven short references. It kept one activity table but omitted the second navigation path, broad topic library, CI guides, and many worked scenarios. That was a smaller introductory skill, not a complete adaptation. This refactor replaces that scope decision.

The seven existing reference paths remain stable foundation entries because the repository's writing, review, and debugging routing checks consume them. Each now links to the corresponding detailed guides. They do not count toward the 58 adapted topic guides.

## Preserve the source structure and usability

The installed entry has task-rich Agent Skills frontmatter, grouped activity tables, a quick decision tree, inspect-before-changing rules, and a test validation loop. Detailed guidance lives in individually routed topic files.

| Source category | Android adaptation | Guides |
| --- | --- | --- |
| `core/` | Hosted test setup, semantics, assertions, rules, robots, data, selection, and Gradle variants | 11 |
| `advanced/` | Authentication, clocks, adaptive UI, roots, users, network fakes, and external SDKs | 8 |
| `architecture/` | Test layers, abstraction ownership, and fake boundaries | 3 |
| `browser-apis/` | `android-apis/` with system services, View interop, background work, and reactive streams | 4 |
| `debugging/` | Failure classification, flakes, errors, logs, and exceptions | 4 |
| `frameworks/` | Android dependency injection, navigation, state/ViewModels, and design systems | 4 |
| `infrastructure-ci-cd/` | Android JVM CI, containers, providers, sharding, costs, artifacts, and coverage | 9 |
| `testing-patterns/` | Component behavior, forms, gestures, accessibility, locale, contracts, files, rendering, and external boundaries | 15 |

The installed [adaptation map](../compose-ui-testing-robolectric-best-practices/adaptation-map.json) is the complete correspondence. Each record has the original path, original file hash, original section inventory, native target, treatment, and rationale. Reproduce the source inventory with:

```bash
git clone https://github.com/currents-dev/playwright-best-practices-skill /path/to/source
git -C /path/to/source checkout 0b75b5835a87de1fdd202ba965f3bc5a27738fdf
find /path/to/source/playwright-best-practices -mindepth 2 -name '*.md' -type f | sort
```

## Adapt the testing objective, not the browser API

The treatment values describe editorial choices. None means omit the topic.

- `adapt` keeps the testing concern and teaches Compose, JUnit, Gradle, or Robolectric mechanisms.
- `reframe` replaces the browser mechanism with the relevant Android boundary or workflow.
- `boundary` teaches a useful local test and separates the external claim that needs another test environment.

DOM selectors become semantics matchers, including merge behavior and singular-query cardinality. Browser waiting does not become an assertion-retry promise. Compose synchronizes registered idle work, while external completion needs a controlled boundary or bounded wait.

Browser contexts become Android host and semantics-root concerns. WebSockets become controlled incoming stream behavior plus separate protocol verification. Service workers become offline-cache and Android background-work concerns without claiming those mechanisms are equivalent.

Web-framework references become Android integration references. React's reactive-state concerns map to Compose state and ViewModels. Angular's dependency ownership maps to Android test injection. Route concerns map to Navigation Compose. Component environment concerns map to themes and design systems. The guides do not claim to run those web frameworks on Robolectric.

Electron and browser extensions have no Android Robolectric execution equivalent. Their adapted guides cover Android host and external-system contracts, then identify the original host or device evidence that remains necessary. They are not exclusion-only placeholders.

Visual regression, performance, accessibility services, and security keep explicit proof boundaries. A local semantics assertion cannot certify pixels, TalkBack navigation, device timing, backend authorization, or browser security. Screenshot tools can supply renderer-specific evidence, but not an automatic device-fidelity guarantee.

## Check depth separately from inventory

The source topic count is an accountability mechanism, not a quality score. A mapped filename or a long guide does not prove a faithful adaptation.

The authoring contract requires full assigned source reads, practical decision rules, worked examples, an anti-pattern and correction, topic-specific synchronization/isolation advice, troubleshooting, review checks, related guides, and primary sources. The coordinator reviews actual artifacts. Independent audits compare source concerns and Android correctness. The [authoring contract](adaptation-authoring.md) and [decision trail](adaptation-decisions.tsv) retain those choices.

The package checker verifies the pinned inventory, direct routes, safe local links, legal files, examples, and copied-install portability. It cannot judge prose depth or compile Markdown fences. The existing Gradle fixture establishes behavior only for canonical Kotlin sources and explicitly exercised agent responses. Newly authored snippets do not inherit that proof.

## Preserve distribution and attribution

The repository still has one discoverable named skill directory. It remains self-contained when copied or packed. The Gradle fixture and repository verification scripts are not required application dependencies and are not part of the npm skill payload.

The source's MIT notice remains inside the installed skill. Attribution now describes the full topic adaptation rather than only packaging inspiration. Browser example code is not copied.
