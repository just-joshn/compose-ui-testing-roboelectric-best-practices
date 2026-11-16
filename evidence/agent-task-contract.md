# Agent task acceptance contract

These cases are acceptance checks for this skill, not a benchmark or a general estimate of agent reliability. Freeze the task inputs before running agents. Keep each response and its verification result. A response that merely repeats advice does not pass a code task.

## Writing

Give an agent the installed skill and the fixture UI. Ask it to write a Kotlin test that distinguishes duplicate action labels, interacts with one identified item, and asserts that only the intended item's visible state changes.

Accept only if the response routes through the writing and semantics references, compiles unchanged with the fixture, passes on the baseline, and fails when the action updates the wrong item. The evaluator, not the agent, applies the mutation. Do not include the acceptance test implementation in the task input.

## Review

Give an agent the installed skill and a flawed test containing an unscoped singular query for duplicate labels, a fixed sleep, and an assertion that only checks node existence after an action.

Accept only if the response identifies the ambiguity, distinguishes Compose idleness from external completion, and supplies a replacement test with an observable result assertion. Compile and run the replacement on the fixture. Verify that the no-op action mutation fails it. Record any missed issue even if the replacement passes.

## Debugging

Give an agent the installed skill, a failing test that assumes a merged child is selectable as a separate node, and the actual failure plus merged and unmerged semantics dumps.

Accept only if the response routes to diagnostics and semantics, explains the mismatch from the supplied tree, and supplies a test-only correction. Compile and run the correction. It must still fail when the user-facing semantics are removed. An application edit that exposes extra semantics only to make the test pass does not qualify.

## Execution record

Record the model, harness version, activation mode, files read, output paths, exact commands, exit codes, mutation results, and limitations. A tool-blocked response is inconclusive. Routing text alone does not demonstrate activation. Capture actual file-read events or equivalent loader evidence.
