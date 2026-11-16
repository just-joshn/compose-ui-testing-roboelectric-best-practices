# Select the intended semantics node

## Continue with the topic guides

Read [semantics selectors](../core/semantics-selectors.md) for matcher decisions, duplicate labels, merged and unmerged trees, and lazy items. Read [accessibility](../testing-patterns/accessibility.md) for roles, states, descriptions, and the device-service boundary. Use [gestures](../testing-patterns/gestures.md) when the target must first scroll into view.

## Start with the merged tree

Compose tests query semantics, not the composable call hierarchy. A layout without semantics may not create a queryable node. `clickable` and components such as buttons can merge descendant semantics into a user-facing group.

Use the tree that expresses the behavior you need. A text matcher can find a merged parent because that parent contains the child's text. It does not prove the child exists as a separate merged node.

Inspect both trees when that distinction matters:

```kotlin
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.printToString

val merged = rule.onRoot().printToString()
val unmerged = rule.onRoot(useUnmergedTree = true).printToString()
println(merged)
println(unmerged)
```

For a deliberately merged row with two text children, prove the group and child separately. The canonical [example tests](../examples/) show the exact compiled version. Match the parent by its group identity and text. Use `useUnmergedTree = true` only for the child-specific assertion.

[`clearAndSetSemantics`](https://developer.android.com/develop/ui/compose/accessibility/merging-clearing) replaces descendant information in the merged tree. The unmerged tree can still expose child nodes for test inspection. That does not mean accessibility services receive the child's original semantics. Inspect both trees before adding tags or changing production semantics.

## Resolve ambiguity by identity

`onNode` and its singular convenience finders require exactly one node when you operate on the result. They fail for zero or multiple matches. Finding text and immediately clicking does not choose one match for you.

Bad:

```kotlin
rule.onNodeWithText("Open").performClick()
rule.onAllNodesWithText("Open")[0].performClick()
```

The first is ambiguous if two items say Open. The second hides the ambiguity and couples the test to order.

Prefer an observable label plus a meaningful group when labels repeat. A test tag is appropriate for stable identity that visible semantics do not uniquely express. It is not a substitute for accessible text or an outcome assertion.

```kotlin
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.hasAnyAncestor
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.performClick

rule.onAllNodesWithText("Open").assertCountEquals(2)
rule.onNode(hasText("Open") and hasAnyAncestor(hasTestTag("draft")))
    .performClick()
```

This ancestor pattern assumes the tagged group remains an ancestor in the selected tree. If the clickable group itself owns the merged text and tag, combine `hasText("Open") and hasTestTag("draft")` instead. The tree decides which structure exists.

Use an index when list order is itself the contract. Assert the order first. For an arbitrary collection, assert its size or match by stable identity.

## Check match defaults

In Compose 1.12.1, `onNodeWithText` defaults to exact, case-sensitive matching. `substring = true` and `ignoreCase = true` are explicit changes. `onNodeWithTag` matches an exact tag. It has no substring option.

Do not broaden a matcher until a test passes. First distinguish wrong data, wrong tree, missing node, duplicate node, and a genuine label change.

## Evidence

The [official testing APIs guide](https://developer.android.com/develop/ui/compose/testing/apis) demonstrates merged and unmerged text. The [semantics guide](https://developer.android.com/develop/ui/compose/accessibility/semantics) explains merging and clearing. Published `ui-test:1.12.1` source defines finder defaults and singular-count errors. See [evidence.md](evidence.md) for provenance and executable observations.
