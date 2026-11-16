# Summary child assertion failure

This is a selector/tree mismatch, not a missing UI element or a timing problem. `MergedLabel` sets `mergeDescendants = true` on the `summary` column. The default finder searches the merged semantics tree, where the supplied dump shows only the `summary` group with `Text = '[Draft, Ready]'`. Its `summary-child` descendant is not independently selectable there.

The actual unmerged dump shows one node tagged `summary-child` with `Text = '[Draft]'`. The corrected test therefore uses `onNodeWithTag("summary-child", useUnmergedTree = true)` and retains `.assert(hasText("Draft"))`. This checks the intended child's text, not merely the existence of a tagged node. A child still tagged `summary-child` but exposing `Published` instead would fail this assertion. Checking only the parent's merged text would not establish that the specific child exposes Draft.

The exception's suggestion spells the option `useUnmergedNode`; that is not the public finder parameter. The correct Compose 1.12.1 parameter is `useUnmergedTree`.

`DebuggingTaskTest.kt` supplies a complete JUnit 4 class in package `fixture`, with `RobolectricTestRunner`, runtime SDK 35, and `androidx.compose.ui.test.junit4.v2.createComposeRule`. It mounts the unchanged `MergedLabel` once. No sleeps, clock changes, dependency changes, or production UI edits are needed. The separate repeated-Open ambiguity in `failure.txt` is unrelated to this summary assertion.

This assertion proves the child's text in local unmerged semantics; it does not prove device rendering or accessibility-service traversal. Gradle and regression-control executions were not run, as requested. Compilation and runtime validation against the supplied Compose 1.12.1 / Robolectric 4.18 host remain for the evaluator.
