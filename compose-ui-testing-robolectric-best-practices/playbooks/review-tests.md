# Review Existing Tests Against the Documentation

## When to use

Use when the goal is to check existing Compose UI tests against the official documentation and report which findings the documentation supports.

## Investigate and establish evidence

1. Read each test, the code under test, and the build files. Run the tests and record the exact command and result as the baseline.
2. Check the source set. Any UI test present in the `test` source set runs with Robolectric: [test-architecture.md](../architecture/test-architecture.md#source-sets).
3. Check the setup functions. The v1 APIs are deprecated, and it's strongly recommended to migrate to the new APIs: [test-suite-structure.md](../core/test-suite-structure.md#v2-apis).
4. Check for `createComposeRule` used together with `runTest`, which creates two separate clocks, one for Compose and one for the test coroutine scope: [test-suite-structure.md](../core/test-suite-structure.md#cautions).
5. Check for `androidx.compose.ui.test.junit4.ComposeTestRule` (for example `createComposeRule`) used inside `runAndroidComposeUiTest`, `runEmptyComposeUiTest`, or their variants. These APIs independently manage the test environment, so mixing them may lead to unexpected behavior: [test-suite-structure.md](../core/test-suite-structure.md#cautions).
6. Check how tests wait. In some cases, an external `CountDownLatch` used instead of the `waitUntil` APIs could behave unexpectedly, since the test clock won't be advanced: [synchronization.md](../core/synchronization.md#warnings).
7. Check the finders. The documentation says to use `onChild` only if the node has exactly one child, and `onSibling` only if the node has exactly one sibling: [semantics-finders.md](../core/semantics-finders.md#anti-patterns-to-avoid).
8. Check the actions. You cannot chain actions inside a perform function, and `performGesture` is deprecated and replaced by `performTouchInput`: [assertions-actions.md](../core/assertions-actions.md#anti-patterns-to-avoid).
9. Check the scroll actions. `performScrollTo` acts on a node that is part of the scrollable content, while `performScrollToIndex` and `performScrollToKey` act on a scrollable container: [assertions-actions.md](../core/assertions-actions.md#anti-patterns-to-avoid).
10. Check for mocks or spies of Android classes that will be acted on by other Android code, such as `Context` and `SharedPreferences`. The small exceptions are classes with very narrow responsibilities, such as event listeners. Stubbing is very brittle and can lead to breakages on Robolectric or Android Platform upgrades: [debugging.md](../debugging/debugging.md#anti-patterns-to-avoid).
11. Check for custom semantics properties that expose visual properties such as colors, font size or rounded corner radius. This is not recommended: [semantics-finders.md](../core/semantics-finders.md#anti-patterns-to-avoid).
12. Check what the tests rely on. System UI like edge-to-edge or picture-in-picture, and unsupported features like `WebView`, still require device tests: [test-architecture.md](../architecture/test-architecture.md#device-tests).
13. Check for `enableAccessibilityChecks` in tests that run on Robolectric. It requires API 34+ and is not supported on Robolectric: [runtime-modes.md](../core/runtime-modes.md#accessibility-checks-on-robolectric).
14. Check for `LooperMode.Mode.LEGACY`. It is deprecated and is not supported on Android SDKs > Baklava: [runtime-modes.md](../core/runtime-modes.md#looper-mode).

## Deliver supported findings

- Report each finding with the test and line, the documented statement it relies on, and the official page that states it.
- List separately anything you noticed that no official page covers, and mark it not documented. Do not present it as a finding.
- Give the baseline command and result, and say which tests were not run.
- If the request was only for a review, stop here.

## Design and implement

- Change only what a finding supports, and keep each change traceable to that finding.
- For v1 setup functions, follow [migrate-to-v2-apis.md](migrate-to-v2-apis.md).
- For `createComposeRule` used together with `runTest`, switch to `runComposeUiTest`. The `runComposeUiTest` API automatically executes the test block within its own `runTest` scope, and the test clock is synchronized with the Compose environment: [flaky-tests.md](../debugging/flaky-tests.md#migrate-to-runcomposeuitest).
- Replace `performGesture` with `performTouchInput`, and make multiple `perform...()` calls instead of chaining actions: [assertions-actions.md](../core/assertions-actions.md#anti-patterns-to-avoid).
- A condition that depends on external work, such as data loading or measure or draw external to Compose, should use `waitUntil()`: [debugging.md](../debugging/debugging.md#anti-patterns-to-avoid).
- Replace `LooperMode.Mode.LEGACY` with `LooperMode.PAUSED`: [runtime-modes.md](../core/runtime-modes.md#looper-mode).

## Verify behavior and challenge findings

- Run the baseline commands again and compare the results with the baseline.
- For each changed test, break the behavior it checks, confirm the failure, then restore it.
- Re-read every finding against its reference file or official page, and drop any finding you cannot tie to one.
- Before reporting a test as needing a device, note that Robolectric provides enough fidelity to run most UI tests, including behavior tests such as a Compose test that verifies the UI has changed after clicking a button: [test-suite-structure.md](../core/test-suite-structure.md#robolectric-versus-device-tests).
- Before reporting a test as too broad, note that the documentation says UI tests scoping larger parts of your UI are also very important: [test-suite-structure.md](../core/test-suite-structure.md#test-scope).

## Sources

- https://developer.android.com/develop/ui/compose/testing
- https://developer.android.com/develop/ui/compose/testing/migrate-v2
- https://developer.android.com/develop/ui/compose/testing/synchronization
- https://developer.android.com/develop/ui/compose/testing/semantics
- https://developer.android.com/develop/ui/compose/testing/apis
- https://developer.android.com/develop/ui/compose/testing/debug
- https://developer.android.com/training/testing/local-tests/robolectric
- https://robolectric.org/javadoc/4.18/org/robolectric/annotation/LooperMode.Mode.html
