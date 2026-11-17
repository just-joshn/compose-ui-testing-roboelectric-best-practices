# Migrate to v2 Testing APIs

## When to use

Use when the goal is to move existing tests from the deprecated v1 Compose test APIs to the v2 APIs.

## Delegate

- Delegate the survey by module: each read-only subagent lists the old setup functions and patterns in its module, with file and line.
- Keep for yourself: the edits, one file at a time, running that file's tests after each.
- After verification, delegate the challenge to a fresh reviewer: compare the migrated files with the migration reference and the baseline results.

## Investigate and design

### Investigate

1. Run the tests and record the exact command and result as the baseline.
2. Find every use of the v1 APIs in [test-suite-structure.md](../references/core/test-suite-structure.md#api-mappings). Only the APIs that establish the test environment have been updated: [coroutines.md](../references/testing-patterns/coroutines.md#dispatchers-in-the-v1-and-v2-apis).
3. Check the module's Compose UI test dependency versions. The v2 testing API changes are included in `androidx.compose.ui:ui-test-junit4:1.11.0-alpha03+` and `androidx.compose.ui:ui-test:1.11.0-alpha03+`: [flaky-tests.md](../references/debugging/flaky-tests.md#coroutine-timing-v1-vs-v2).
4. Find tests that depend on when a launched coroutine runs. The v1 APIs used `UnconfinedTestDispatcher`, which executed a launched coroutine immediately. The v2 APIs use `StandardTestDispatcher` by default for the running composition, which queues it until the test explicitly advances the virtual clock: [coroutines.md](../references/testing-patterns/coroutines.md#dispatchers-in-the-v1-and-v2-apis).
5. Find tests that use Compose test APIs alongside the Kotlin `runTest` API: [flaky-tests.md](../references/debugging/flaky-tests.md#migrate-to-runcomposeuitest).
6. Find calls of overloads that accept individual configuration parameters such as `effectContext`, `runTestContext`, or `testTimeout`. Several of these overloads are deprecated: [configuration.md](../references/core/configuration.md#deprecations).
7. Find code that creates an instance of `AndroidComposeUiTestEnvironment` by its constructor or subclasses it. Its default test dispatcher switched from `UnconfinedTestDispatcher` to `StandardTestDispatcher`: [coroutines.md](../references/testing-patterns/coroutines.md#api-mappings).
8. Find tests that rely on non-touch input modes configured through instrumentation APIs before the test starts. They can fail during migration: [configuration.md](../references/core/configuration.md#input-mode).

### Design

- Make one kind of change at a time, and run the tests after each.
- Update the package imports to the replacements in the mappings. You can generally use Find + Replace for this: [coroutines.md](../references/testing-patterns/coroutines.md#dispatchers-in-the-v1-and-v2-apis).
- If an assertion fails right after launching a task, use `waitForIdle` or `runOnIdle` to execute queued tasks before asserting: [flaky-tests.md](../references/debugging/flaky-tests.md#failures-after-upgrading-to-v2).
- In scenarios involving manual synchronization, such as when auto-advancing is disabled, use `runCurrent()` to execute queued tasks without advancing the virtual clock: [flaky-tests.md](../references/debugging/flaky-tests.md#run-queued-coroutines-without-advancing-time).
- For tests that use Compose test APIs alongside `runTest`, switch to `runComposeUiTest`: [flaky-tests.md](../references/debugging/flaky-tests.md#migrate-to-runcomposeuitest).
- Replace the deprecated individual parameters with `ComposeUiTestConfig`: [configuration.md](../references/core/configuration.md#compose-test-environment).
- Specify the required input mode in `ComposeUiTestConfig`, for a test class through the rule or for one test through `runComposeUiTest`: [configuration.md](../references/core/configuration.md#input-mode).
- While migrating, `AndroidComposeUiTestFlags.isInputModeSetForDeviceTests = false` temporarily retains the legacy input mode behavior. The flag will be removed in the future, so if only a small number of tests fail, it is recommended to change their configuration instead: [configuration.md](../references/core/configuration.md#deprecations).

## Implement and clean

- Migrate one file at a time, in the order the design lists.
- Remove temporary code added during the migration.

## Verify actual behavior

- Run the baseline commands again. Every test that passed before the change must still pass.
- Confirm the setup functions resolve to `androidx.compose.ui.test.junit4.v2` for the rule functions and `androidx.compose.ui.test.v2` for the `run...` functions: [test-suite-structure.md](../references/core/test-suite-structure.md#api-mappings).
- For each test that failed after the change, check whether it launches a task and its assertion fails immediately, because with the v2 APIs coroutines are queued rather than executed immediately, so the task never actually ran before the result was checked: [flaky-tests.md](../references/debugging/flaky-tests.md#failures-after-upgrading-to-v2).
- When a migrated test newly fails, check whether v1 immediate execution had inadvertently masked a real timing issue or race condition that would occur in a live application, and report it as such if so: [coroutines.md](../references/testing-patterns/coroutines.md#dispatchers-in-the-v1-and-v2-apis).
- For each changed test, break the behavior it checks, confirm the failure, then restore it.
- Re-read every statement against its reference file or official page.

## Deliver artifact and evidence

- List each v1 use with its file and line and its replacement from the API mappings, and say which of the cases above apply to it.
- Most tests relying on standard Compose test APIs, such as `waitForIdle()`, should continue to work with no changes. Name the tests you expect to need changes and the reason: [flaky-tests.md](../references/debugging/flaky-tests.md#coroutine-timing-v1-vs-v2).
- Give the baseline command and result.

## Sources

- https://developer.android.com/develop/ui/compose/testing/migrate-v2
- https://developer.android.com/develop/ui/compose/testing/synchronization
- https://developer.android.com/develop/ui/compose/testing
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/ComposeUiTestConfig
