`MergedLabel` puts `testTag("summary")` and `semantics(mergeDescendants = true)` on the same column. In the default merged tree that column is one node: tag `summary`, text `[Draft, Ready]`. The child tagged `summary-child` is not a separate node there, so `onNodeWithTag("summary-child")` finds nothing and `assert` fails at `assertExists`.

The unmerged tree still has that child, with text `[Draft]`, under the merged parent. The failure text suggests `useUnmergedNode = true`. On Compose 1.12.1 the finder parameter is `useUnmergedTree`.

The check stays on the `summary-child` node in the unmerged tree and still requires its text to be `Draft`. Matching `Draft` on the merged `summary` parent would pass because the parent already contains both labels, and would no longer prove the child exposes `Draft`.
