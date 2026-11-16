# Test choices

- `WritingTaskTest.kt` uses JUnit 4, the real v2 Compose rule, Robolectric's runner, SDK 35, and paused looper mode for the supplied Compose 1.12.1 / Robolectric 4.18 host.
- The default merged semantics tree exposes each Button's Open label. Matching `Open` with an ancestor tagged `draft` selects the intended button without relying on layout order or an ambiguous global text query. The test also verifies there are two Open controls.
- `DraftActions` only emits an `onOpen` payload; it does not render a result itself. A small test-owned wrapper stores the actual callback payload in observable Compose state and displays it as Text under MaterialTheme. Production `FixtureUi.kt` is unchanged. This proves the component interaction and emitted payload, not a separate production screen's orchestration.
- One `setContent` call creates fresh state. Initial absence checks and the final displayed Draft result detect a no-op; the Archive absence assertion checks the wrong-target outcome. Normal Compose synchronization is sufficient for this synchronous callback and recomposition; no sleeps, mocked rules, or extra clocks are needed.
- Read the installed SKILL.md and the matching hosted behavior, component, and repeated-label reference rows before writing.
- Per the task constraints, Gradle and regression mutations were not run. Compilation and runtime execution remain for the evaluator; no passing execution is claimed.
