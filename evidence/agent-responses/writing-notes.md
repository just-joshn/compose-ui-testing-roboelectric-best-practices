# Test choices

- `WritingTaskTest.kt` uses JUnit 4, `RobolectricTestRunner`, SDK 35, explicit paused looper mode, and the Compose 1.12.1 v2 `createComposeRule` factory.
- The test uses the real merged semantics tree. It confirms there are two Open controls, then selects Open with the existing `draft`-tagged ancestor rather than relying on list order or an ambiguous text-only finder.
- `DraftActions` exposes its result through a callback, so a minimal test-only host renders that callback's value using fresh Compose state. The expected result is not preloaded: it must come from the real button click. Production `FixtureUi.kt` is unchanged.
- The test verifies that Draft opened is initially absent, then displayed after the click, while Archive opened does not exist. A no-op click or a click routed to the archive cannot satisfy the positive assertion.
- Compose interactions and assertions synchronize this synchronous state update; no sleeps, mock rules, or manual scheduler draining are needed.

## Validation limits

Reviewed the installed skill's setup, behavior, and semantics references and fetched the official Compose testing documentation through Context7 for hierarchical matchers and click actions. This directory has no Gradle build or wrapper, so compilation, execution against the supplied host versions, and mutation checks were not run. No device-rendering claim is made.
