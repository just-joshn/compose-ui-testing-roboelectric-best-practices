# Adapt the complete Playwright skill

The goal is a faithful, complete adaptation of Currents' Playwright best-practices skill to Jetpack Compose UI testing with Robolectric. Match its activity-based structure, topic depth, and practical usability. Do not translate browser APIs literally or use exclusions instead of useful Android guidance.

## Ground each guide

Read the corresponding FULL upstream guide before writing. The local source is `.work/playwright-source/playwright-best-practices/` at commit `0b75b5835a87de1fdd202ba965f3bc5a27738fdf`. The mapping in `compose-ui-testing-robolectric-best-practices/adaptation-map.json` names the source and target of every guide. Read existing `references/*.md`, canonical examples, and `fixture/build.gradle.kts` for established version-specific facts. `.work/context7-testing.txt` and `.work/context7-environment.txt` contain fresh official documentation excerpts.

Use current official Android and Robolectric documentation links for claims. The installed `references/evidence.md` lists versioned primary sources and known contradictions. Do not invent API signatures, dependencies, compatibility ranges, test results, or source consultation. Label illustrative snippets and name their required imports, dependencies, and surrounding types. Put imports at the top of complete Kotlin examples. Do not imply illustrative fragments compiled in this fixture.

## Write a usable reference

Each target is a focused, substantive how-to guide, normally 200 to 400 lines for directly applicable topics. Length is not acceptance. Match the source's range of decisions and worked scenarios. Boundary topics can be shorter when they still give a concrete local workflow and a device or integration handoff. Avoid one-paragraph stubs, repetitive warnings, and padding.

Give each guide one H1, a linked table of contents, and the following sections or more precise task-specific equivalents:

- When to use this guide and the test layer it covers.
- A decision table that chooses APIs, boundaries, or approaches.
- Worked Kotlin, Gradle, shell, or pipeline examples with assumptions and expected observable results.
- At least one explicit anti-pattern and corrected approach. Explain the failure mechanism.
- Test isolation and synchronization considerations specific to that topic.
- Troubleshooting that maps symptoms to observations and fixes.
- A short review checklist.
- Related guides with valid relative links and official sources.

Use sentence case headings and direct prose. No long dashes, decorative emojis, filler, or phase-narrating code comments. Code comments explain only a non-obvious reason. Do not copy TypeScript code or browser assertions. Cross-reference canonical runnable examples where applicable.

## Preserve domain distinctions

- Tests run in Android `src/test`, not `src/androidTest`, with `testImplementation`, Android resources, a Robolectric runner, and a declared activity host.
- The existing validated fixture uses Compose UI 1.12.1 and v2 `androidx.compose.ui.test.junit4.v2.createComposeRule`. Do not use 1.13-only `ComposeUiTestConfig`. Do not rewrite consuming projects to the fixture's versions without a reason.
- Compose actions and assertions synchronize known work. They are not Playwright-style retrying assertions for arbitrary business state.
- A singular finder requires exactly one node. Scope duplicate labels by meaningful identity. Do not use index zero as a repair.
- Distinguish `mainClock`, coroutine schedulers, Android loopers, wall clock, and external work. Do not recommend arbitrary sleeps or globally draining everything.
- Use one owner of content. `createAndroidComposeRule` may launch an activity which sets its own content. Do not add another `setContent` in that case.
- Assert user-visible state after a user action. A callback count or fake payload may supplement, not replace, the UI result.
- Use fresh fakes and state per test. Do not share mutable state between test workers.
- A fake proves client behavior, not HTTP, GraphQL, OAuth, permissions, backend authorization, or service integration.
- Semantics do not prove TalkBack traversal. JVM drawing does not prove device pixels or performance. Local disposal does not prove process death.
- For browser-only source topics, explain the Android analogue, give a useful local test strategy, and specify the separate test layer for the original kind of integration claim. Do not manufacture a one-to-one API equivalence.

## Ownership and verification

Each worker owns only the exact paths in its brief. Do not edit `SKILL.md`, the map, legacy top-level references, scripts, fixture, examples, README, other workers' files, or TODO.md. Other workers are writing disjoint directories in this checkout because they require uncommitted source grounding. Do not commit or stage shared files. Do not spawn more workers.

Before returning, inspect every owned file, verify every relative link to an existing or mapped target, and report file paths, source guides read, assumptions, and any gaps. Use PASS, ISSUES, or BLOCKED. A self-report is not final acceptance. The coordinator reviews content and runs package and runtime checks.
