# Fixture design decision

The goal is a small executable fixture that supports the Compose/Robolectric skill, not an application architecture.

Two independent candidates were inspected. A third runner was stopped after producing no artifact during the bounded design phase. Independent judge `spacex-cursor/grok-4.7-fast` agreed with the coordinator on candidate 1. Scores used the six criteria in the local design rubric, each scored from 0 to 2.

| Criterion | Stateful composable and controlled sender | Stateless board, host, reducer, scheduler |
| --- | --- | --- |
| Executable Android JVM scope | 2 | 1 |
| Behavioral strength | 2 | 1 |
| Time ownership | 2 | 1 |
| Semantics and diagnosis | 2 | 2 |
| Smallness and packaging | 1 | 1 |
| Rerunnable proof | 2 | 2 |

These scores compare proposals. They are not runtime measurements.

## Chosen shape

A stateful `MessagePanel(sender)` owns its UI state and composition-owned coroutine. A test-local `ControlledSender` suspends until the test supplies a receipt. `Delivery` represents editing, sending, and sent states. A second tiny composable exposes duplicate actions in distinguishable item groups. Tests use Compose APIs directly.

The installed skill's `examples/` directory holds the canonical Kotlin files. The repository's Android library test source set compiles those files. This avoids divergent documentation copies while keeping the installed skill self-contained. Root Gradle files and scripts run the validation project.

The selected candidate's signatures are a sketch, not an API promise. Implementation may narrow them when the first executable test exposes an invalid assumption.

## Grafts and corrections

The second candidate contributes a stronger merge check. It must show that a child is not a separate merged node but is present in the unmerged tree. It also contributes a structural gate for routed reference files.

Fresh source research overrides both candidates' older rule imports. Use the stable `androidx.compose.ui.test.junit4.v2.createComposeRule` in Compose 1.12.1. Include the manifest artifact. `createComposeRule()` still hosts an Android activity. Reject the second candidate's no-activity claim, extra host/reducer architecture, and independent scheduler in the canonical example.

Use one API 35 run on JDK 17, stable Compose BOM 2026.09.00, and Robolectric 4.18. This is one tested combination, not a compatibility matrix. AGP 9.2.0 and Gradle 9.4.1 follow the official AGP 9.2 compatibility table. Its KGP default is 2.2.10. Execution must establish whether this combination compiles the current Compose artifacts.

## Verification contract

Establish one passing hosted semantics test before expanding the fixture. Run the complete fixture, remove Android-resource inclusion in an isolated throwaway copy, and compare the same test. Then restore and rerun. Compare v1 and v2 effect-start ordering only if it materially changes the guidance. Record commands and output, not predictions.

Mutations must remove a visible effect, target the wrong item, and break merged semantics. The evaluator must reject nonzero builds that never reached the named assertion. Agent-generated test corrections must compile, pass the baseline, and fail the corresponding mutation.
