---
name: compose-ui-testing-robolectric-best-practices
description: Workflow for Jetpack Compose UI tests with Robolectric. Given a goal, constraints, and a success check, it selects a playbook, investigates, makes a small change grounded in current official Compose testing and Robolectric documentation, verifies the real result, and returns evidence for review. Use when writing a new Compose UI test, debugging a failing test, fixing a flaky test, reviewing tests, setting up Robolectric, or migrating to the v2 Compose test APIs.
license: MIT
compatibility: Robolectric 4.18 supports Android API 24 → 37. Compose ui-test stable release 1.12.1, release candidate 1.13.0-rc01.
metadata:
  version: "4.0.0"
---

# Compose UI Testing with Robolectric

The user directs the outcome. This skill coordinates the process: it works like a disciplined Compose UI testing and Robolectric team that prefers a small, well-supported change with a clear explanation.

Follow the workflow below, taking the branch each decision points to. Each playbook supplies the task-specific part of the stages it names.

```mermaid
flowchart TD
    A[Goal, constraints, and success check] --> B[Select a playbook]
    B --> C[Investigate and establish evidence]
    C --> D{Requested outcome}
    D -- Explanation or plan --> E[Deliver supported findings]
    D -- Working change --> F[Design and implement]
    F --> G[Verify behavior and challenge findings]
    G --> H{Acceptance checks satisfied?}
    H -- No or inconclusive --> C
    H -- Yes --> I[Deliver the change and evidence]
    I --> J{Shipping authorized?}
    J -- Yes --> K[Manage review and land verified work]
    J -- No --> L[Hand back for review]
    K --> M[Capture useful lessons]
    L --> M
```

## Source of Truth

The only sources of truth are current official Compose UI testing and Robolectric documentation: the Compose testing docs and the Compose test API reference on developer.android.com, and robolectric.org.

- State facts about Compose testing or Robolectric only from the reference files this skill links to, or from those official pages. Each reference file lists its official sources.
- If neither covers a question, say it is not documented. Do not fill the gap from memory.
- Facts about the user's project come from the project itself: its code, build files, and test output. Comments in the project are evidence of what the project says, not documentation.

Reference files, each verified against the official pages it lists:

| Area | Reference files |
| --- | --- |
| Test structure and setup | [test-suite-structure.md](references/core/test-suite-structure.md), [configuration.md](references/core/configuration.md), [runtime-modes.md](references/core/runtime-modes.md) |
| Finding nodes and acting on them | [semantics-finders.md](references/core/semantics-finders.md), [assertions-actions.md](references/core/assertions-actions.md) |
| Waiting and time | [synchronization.md](references/core/synchronization.md), [clock-control.md](references/advanced/clock-control.md), [coroutines.md](references/testing-patterns/coroutines.md) |
| Debugging | [debugging.md](references/debugging/debugging.md), [flaky-tests.md](references/debugging/flaky-tests.md) |
| Test patterns | [component-testing.md](references/testing-patterns/component-testing.md), [accessibility.md](references/testing-patterns/accessibility.md), [animations.md](references/testing-patterns/animations.md), [state-restoration.md](references/testing-patterns/state-restoration.md), [visual-regression.md](references/testing-patterns/visual-regression.md) |
| Device and Android integration | [device-configuration.md](references/advanced/device-configuration.md), [interoperability.md](references/advanced/interoperability.md) |
| Architecture and CI | [test-architecture.md](references/architecture/test-architecture.md), [test-doubles.md](references/architecture/test-doubles.md), [ci-cd.md](references/infrastructure-ci-cd/ci-cd.md) |

## Goal, constraints, and success check

Start every task by writing down three things:

- **Goal**: the outcome the user wants.
- **Constraints**: what must not change, and any limits on time, scope, or tools.
- **Success check**: an observable result that shows the goal is met, such as a named test passing, or, for a review, every finding citing its evidence and source.

If the user gave all three, restate them and continue. If one is missing, propose it from the request and continue; ask only when the choice would change what you build.

## Select a playbook

Pick the playbook that matches the goal. If none fits exactly, use the closest one and say which one you chose.

| Goal | Playbook |
| --- | --- |
| Write a new Compose UI test that runs on Robolectric | [write-a-compose-ui-test.md](playbooks/write-a-compose-ui-test.md) |
| A test fails and the cause is unknown | [debug-a-failing-test.md](playbooks/debug-a-failing-test.md) |
| A test passes and fails without code changes | [fix-a-flaky-test.md](playbooks/fix-a-flaky-test.md) |
| Review existing tests against the documentation | [review-compose-ui-tests.md](playbooks/review-compose-ui-tests.md) |
| Set up or configure Robolectric, the JDK, or CI | [configure-robolectric.md](playbooks/configure-robolectric.md) |
| Migrate tests to the v2 testing APIs | [migrate-to-v2-testing-apis.md](playbooks/migrate-to-v2-testing-apis.md) |

## Investigate and establish evidence

Follow the playbook's investigation steps. In every playbook:

- Read the code under test and the existing tests before proposing anything.
- Run the narrowest test command that covers the goal, confirm it targets the project's actual test task, and record the exact command and its result.
- Record each piece of evidence with where it came from: a command and its output, a file and line, or an official page.
- Split independent investigations across subagents when the harness supports them. Keep a single owner for edits.
- When a needed piece of evidence cannot be obtained, such as a result that needs a device or access you lack, stop and report the check, why it is unresolved, and the proof that would settle it. Do not continue as if it were settled.

## Requested outcome

Decide what the user asked for:

- **Explanation or plan**: go to Deliver supported findings.
- **Working change**: go to Design and implement.

## Deliver supported findings

Report in this order, using the playbook's guidance for what to include:

1. Goal, constraints, and success check.
2. Playbook used.
3. Findings, each with its project evidence and the reference section behind it. The reference section's Sources list holds the official pages.
4. Unresolved findings, each with the proof it is missing.
5. Open questions.

This ends the workflow.

## Design and implement

- Make the smallest change that meets the success check within the constraints.
- Use only the APIs and patterns in the playbook's reference files.
- Keep each change traceable to a piece of evidence from the investigation.

## Verify behavior and challenge findings

- Run the success check itself, not a proxy, and record the command and output.
- For each test the change adds or modifies, show that it can fail: break the behavior it checks, confirm the failure, then restore it.
- Re-read every technical statement in your explanation against its reference file or official page.
- Ask an independent reviewer, such as a fresh subagent, to challenge the change and the explanation when the harness supports it.
- Give each acceptance check exactly one result:
  - **Pass**: direct evidence shows the check is met, such as the command output.
  - **Fail**: direct evidence shows the check is not met.
  - **Unresolved**: there is no direct evidence either way. Record the proof that is missing.
- Never count an unresolved check as a pass, and never describe it as likely to pass.

## Acceptance checks satisfied?

- **Yes**: every acceptance check is Pass. Go to Deliver the change and evidence.
- **No or inconclusive**: any check is Fail or Unresolved. Return to Investigate and establish evidence to obtain the missing proof or find the cause. If the same check fails twice for the same reason, or its proof cannot be obtained, stop and report each Fail and Unresolved check with its evidence and the missing proof. Do not deliver the change as verified.

## Deliver the change and evidence

Report in this order:

1. Goal, constraints, and success check.
2. Playbook used.
3. What changed, by file.
4. Evidence: each acceptance check with its result and the commands and output behind it, before and after.
5. The reference section behind each technical statement.
6. Risks and open questions.

## Shipping authorized?

Shipping means committing, pushing, opening a pull request, or merging. It is authorized only when the user said so for this task.

- **Yes**: go to Manage review and land verified work.
- **No**: go to Hand back for review.

## Manage review and land verified work

Commit only the verified change, open a pull request whose description carries the evidence report, wait for CI, and answer review comments. Merge only if the user authorized merging. Then go to Capture useful lessons.

## Hand back for review

Leave the change uncommitted, or on its own branch if one was already in use, and present the evidence report. Then go to Capture useful lessons.

## Capture useful lessons

List what you learned that would help next time, such as a documented behavior that surprised you or a check that caught a mistake. Add a lesson to the project's agent instructions only with the user's approval.
