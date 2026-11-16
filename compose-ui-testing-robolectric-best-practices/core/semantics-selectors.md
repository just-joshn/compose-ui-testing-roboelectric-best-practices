# Select Compose semantics nodes

Use this guide when a local Robolectric UI test must identify a control, disambiguate repeated labels, or inspect merged content. Queries operate on semantics, not the composable call hierarchy or Android View IDs.

## Contents

- [Choose a selector](#choose-a-selector)
- [Match visible and accessible information](#match-visible-and-accessible-information)
- [Scope repeated controls](#scope-repeated-controls)
- [Choose the semantics tree](#choose-the-semantics-tree)
- [Handle lists and changing content](#handle-lists-and-changing-content)
- [Inspect other roots and View content](#inspect-other-roots-and-view-content)
- [Troubleshoot selection](#troubleshoot-selection)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose a selector

| Intent | Start with | Boundary |
| --- | --- | --- |
| Read or activate a labeled control | `hasText`, `onNodeWithText` | Text can belong to a merged parent |
| Find an icon's accessible purpose | `onNodeWithContentDescription` | Do not add descriptions solely for tests |
| Identify an editable control | Text or tag combined with `hasSetTextAction()` | Placeholder text may disappear after input |
| Distinguish repeated controls | Identity plus `hasAnyAncestor` or a group matcher | Inspect whether the group merges descendants |
| Find a stable nontext identity | `hasTestTag`, `onNodeWithTag` | A tag is not an accessibility label |
| Verify individual merged children | `useUnmergedTree = true` | Diagnostic child visibility is not accessibility-service exposure |
| Test ordering | A collection and an explicit order assertion | Indexing is not an ambiguity repair |

Prefer information the user can perceive. Use tags when a stable identity cannot otherwise be expressed. A decorative layout node need not become queryable merely because the test knows it exists.

## Match visible and accessible information

These illustrative fragments assume a `rule` created by the v2 factory and content mounted by the test. They need `ui-test-junit4` through `testImplementation`. The snippets are not additional fixture-compiled tests.

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput

rule.onNodeWithText("Continue").performClick()
rule.onNodeWithText("Welcome").assertIsDisplayed()
rule.onNodeWithContentDescription("Close settings").performClick()
rule.onNode(hasText("Email") and hasSetTextAction())
	.performTextInput("reader@example.test")
```

The control must expose those properties in the selected tree. Compose does not have an HTML label association API that automatically maps every nearby `Text` to a field.

In Compose 1.12.1, `onNodeWithText` defaults to exact, case-sensitive matching. Make relaxed matching explicit:

```kotlin
import androidx.compose.ui.test.onNodeWithText

rule.onNodeWithText("Welcome", substring = true, ignoreCase = true)
	.assertExists()
```

Use a relaxed match only when partial or case-insensitive text is the requirement. It can introduce duplicates. `onNodeWithTag` uses an exact tag and has no substring option.

Role semantics can supplement a match, but do not impose a browser role hierarchy on Compose. Inspect the actual component semantics before combining a role with text or an action.

## Scope repeated controls

A singular finder must resolve to exactly one node when you act or assert. It does not select the first node automatically.

Anti-pattern:

```kotlin
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.performClick

rule.onAllNodesWithText("Open")[0].performClick()
```

This can activate the archive after a layout reorder even though the test intended the draft.

Correct the identity rather than the index. This fragment uses the canonical `DraftActions` component's unmerged group boundaries:

```kotlin
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasAnyAncestor
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick

rule.onAllNodesWithText("Open").assertCountEquals(2)
rule.onNode(hasText("Open") and hasAnyAncestor(hasTestTag("draft")))
	.performClick()
rule.onNodeWithText("Draft opened").assertIsDisplayed()
rule.onNodeWithText("Archive opened").assertDoesNotExist()
```

The result assertions detect both a no-op action and a wrong target. If the tagged group itself owns the merged text, use `hasTestTag("draft") and hasText("Open")` instead. An ancestor matcher cannot match the node itself.

Use `and`, `or`, and negated matchers to state the intended contract. Do not keep adding exclusions until only one arbitrary node remains.

## Choose the semantics tree

Inspect both trees before changing production semantics:

```kotlin
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.printToString

println(rule.onRoot().printToString())
println(rule.onRoot(useUnmergedTree = true).printToString())
```

The default merged tree often represents a clickable group as one node. A child text can contribute to that parent's text without remaining an independent node.

For the canonical `MergedLabel`, verify the group in the merged tree and the child only in the unmerged tree:

```kotlin
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.onNodeWithTag

rule.onNodeWithTag("summary").assert(hasText("Draft"))
rule.onNodeWithTag("summary-child").assertDoesNotExist()
rule.onNodeWithTag("summary-child", useUnmergedTree = true)
	.assertIsDisplayed()
```

`clearAndSetSemantics` replaces descendant information in the merged tree. The unmerged tree can still expose child nodes. Match the replacement semantics when testing the group's public contract. Use unmerged inspection for a child-specific test, without treating that visibility as accessibility-service exposure.

For example, mount a `Column` with `Modifier.testTag("cleared").clearAndSetSemantics { contentDescription = "Replacement" }` and a child `Text("Original child", Modifier.testTag("cleared-child"))`. With the same mounted UI, these assertions distinguish the contracts:

```kotlin
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.hasContentDescription
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.onNodeWithTag

rule.onNodeWithTag("cleared").assert(hasContentDescription("Replacement"))
rule.onNodeWithTag("cleared-child").assertDoesNotExist()
rule.onNodeWithTag("cleared-child", useUnmergedTree = true)
	.assert(hasText("Original child"))
```

The mounted example also requires `Column`, `Text`, `Modifier`, `testTag`, `clearAndSetSemantics`, and `contentDescription` from their normal Compose packages. A separate probe executed this exact merged-versus-unmerged distinction with Compose UI 1.12.1 and Robolectric 4.18. It does not establish accessibility-service behavior. See [evidence and limits](../references/evidence.md).

Keep the tree choice consistent across a matcher and its structural assumptions. An ancestor visible in one tree may disappear or own the text in the other.

## Handle lists and changing content

`onAllNodes` returns a queryable collection. Assert cardinality when the number of semantic items is the requirement. Do not equate the number of currently composed lazy-list items with total repository size.

For a lazy list, first locate its container and scroll to the semantic item. An illustrative fragment assumes an existing `LazyColumn` tagged `orders`:

```kotlin
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performScrollToNode

rule.onNodeWithTag("orders").performScrollToNode(hasText("Order 42"))
rule.onNodeWithText("Order 42").assertIsDisplayed()
```

A collection snapshot is not a live inventory of every possible item. Re-query after a state transition. Do not cache fetched `SemanticsNode` objects as durable UI handles.

Compose finder assertions synchronize known Compose work. They do not repeatedly retry a business result. When external work controls item creation, complete the fake or use a bounded wait as described in [assertions and waiting](assertions-waiting.md).

## Inspect other roots and View content

Dialogs and popups may create another Compose root. Scope by dialog semantics or a meaningful identity instead of assuming there is one universal root. See [multiple roots](../advanced/multiple-roots.md).

An `AndroidView` can expose a View hierarchy that is not fully searchable as Compose semantics. Test the Compose wrapper's contract locally, then use the appropriate View testing API for the embedded content. A WebView document is not a Compose semantics subtree. See [View interoperability](../android-apis/view-interop.md).

No selector here proves TalkBack traversal or actual touch hit testing on a device.

## Troubleshoot selection

| Symptom | Observe | Correct |
| --- | --- | --- |
| Zero matches | Dump both trees and check mounted content | Fix text, tree, or missing content ownership |
| Multiple matches | Inspect every matching group's identity | Add meaningful scope, not index zero |
| Child missing | Check merge and clearing boundaries | Assert the group or intentionally use unmerged search |
| Match vanishes after typing | Inspect editable semantics | Select stable field identity rather than the placeholder |
| List item absent | Check whether it is composed and scrollable | Scroll the correct container before asserting |
| Tag exists but click has no effect | Inspect click action and final UI | Select the actionable group and assert its result |

## Review checklist

- The matcher selects exactly the intended semantic identity.
- Any use of the unmerged tree has a child-specific reason.
- Repeated labels remain safe after reorder.
- The action ends with a visible result assertion.
- External work has an explicit owner and completion strategy.
- Tags do not replace accessible labels.

## Related guides and sources

- [Screen robots](screen-robots.md) centralize reusable selectors.
- [Canonical selection tests](../examples/FixtureUiTest.kt) contain compiled merged-tree and duplicate-label examples.
- [Testing APIs](https://developer.android.com/develop/ui/compose/testing/apis) documents matchers and actions.
- [Merging and clearing semantics](https://developer.android.com/develop/ui/compose/accessibility/merging-clearing) explains tree boundaries.
- [Evidence and version limits](../references/evidence.md) records the inspected 1.12.1 sources.
