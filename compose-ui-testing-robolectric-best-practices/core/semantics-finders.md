# Semantics & Finders

## Table of Contents

1. [Semantics Tree](#semantics-tree)
2. [Selector Priority](#selector-priority)
3. [Finders](#finders)
4. [Matchers](#matchers)
5. [Merged and Unmerged Trees](#merged-and-unmerged-trees)
6. [Hierarchy and Selectors](#hierarchy-and-selectors)
7. [Test Tags](#test-tags)
8. [Custom Semantics Properties](#custom-semantics-properties)
9. [Common Issues & Solutions](#common-issues--solutions)
10. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
11. [Related References](#related-references)
12. [Sources](#sources)

## Semantics Tree

Compose UI tests find nodes in the semantics tree, which is generated alongside the UI hierarchy. There are no view IDs: "only some composables emit UI into the UI hierarchy", so you match on semantics.

The framework exists mainly for accessibility, and "developers decide what and how much to expose". A button with an icon and a `Text` exposes only the text by default. Add properties with a modifier:

```kotlin
MyButton(
    modifier = Modifier.semantics { contentDescription = "Add to favorites" }
)
```

## Selector Priority

The docs do not rank finders; this order is the skill's own, based on their point that tests reuse what semantics already expose for accessibility:

1. **Text**: `onNodeWithText` (users read it; `Text` already exposes it)
2. **Content description**: `onNodeWithContentDescription` (what accessibility services read)
3. **Matchers**: `onNode(hasClickAction() and hasText("Save"))` for state and role-like properties
4. **Test tags**: `onNodeWithTag` when no user-visible semantics distinguish the node
5. **Custom semantics property**: only when "it's hard to match a specific item using the given finders and matchers"

```kotlin
// Good: user-facing semantics
composeTestRule.onNodeWithText("Continue").performClick()
composeTestRule.onNodeWithContentDescription("Add to favorites").assertIsDisplayed()

// Fallback: stable tag for an item with no distinguishing text
composeTestRule.onNodeWithTag("cart-count").assertTextEquals("1")
```

When the text is a string resource, read it from the activity (`composeTestRule.activity.getString(R.string.next)`) so the test follows copy changes. See [test-suite-structure.md](test-suite-structure.md).

## Finders

Every finder is a method on the rule (or on `ComposeUiTest` inside `runComposeUiTest`). `onNode` returns one `SemanticsNodeInteraction`; `onAllNodes` returns a `SemanticsNodeInteractionCollection`.

```kotlin
// General form
composeTestRule.onNode(matcher, useUnmergedTree = false)
composeTestRule.onAllNodes(matcher)

// Convenience finders
composeTestRule.onNodeWithText("Button")                 // same as onNode(hasText("Button"))
composeTestRule.onNodeWithContentDescription("Beatle")
composeTestRule.onNodeWithTag("Players")
composeTestRule.onAllNodesWithText("Button")
composeTestRule.onAllNodesWithContentDescription("Beatle")
composeTestRule.onAllNodesWithTag("row")
composeTestRule.onRoot()                                 // the root node
```

The full list of convenience finders is in the Compose testing cheat sheet, which is an image or PDF download and not extractable as text.

A finder that matches several nodes fails when you act on it. Narrow it or select from a collection:

```kotlin
// Bad: fails with several "Save" nodes
composeTestRule.onNodeWithText("Save").performClick()

// Good: choose explicitly from the collection
composeTestRule.onAllNodesWithText("Save").onFirst().performClick()
composeTestRule.onAllNodesWithText("Save")[1].performClick()
```

`onFirst()` and `onLast()` expect exactly one element in the result of any later operation, and throw `AssertionError` if none is found. For Compose nested inside View rows or pagers, `onRootWithViewInteraction` (experimental, `ui-test-junit4:1.12.0-alpha01+`) scopes a finder to one View; see [interoperability.md](../advanced/interoperability.md).

## Matchers

A `SemanticsMatcher` is what `onNode` and `assert` take.

```kotlin
hasText("Button")                    // matches one item in the node's text list; substring = true, ignoreCase = true are opt-in
hasTextExactly("Hello", "World")     // the text list contains exactly these values (order does not matter)
hasContentDescription("Add to favorites")
hasTestTag("Drummer")
hasClickAction()
isEnabled()
isNotEnabled()
```

Combine with `and`, `or`, `not()`:

```kotlin
composeTestRule.onNode(hasText("Save") and hasClickAction())
composeTestRule.onNode(hasText("Button") or hasText("Button2"))
composeTestRule.onNode(!hasClickAction())
```

Build your own with `SemanticsMatcher(description: String, matcher: (SemanticsNode) -> Boolean)` when no built-in fits. The description appears in failure messages.

`SemanticsMatcher` also has `expectValue(key, expected)`, `keyIsDefined(key)`, and `keyNotDefined(key)` for custom properties.

## Merged and Unmerged Trees

Some nodes merge their children's semantics. A button holding two `Text` elements shows one node:

```
Node #2 at (...)px
  Role = 'Button'
  Text = '[Hello, World]'
  MergeDescendants = 'true'
```

Finders use the merged tree by default. Pass `useUnmergedTree = true` to match the children:

```kotlin
composeTestRule.onNodeWithText("World", useUnmergedTree = true).assertIsDisplayed()
composeTestRule.onRoot(useUnmergedTree = true).printToLog("TAG")
```

`useUnmergedTree` is available on all finders. Print the tree before guessing; see [debugging.md](../debugging/debugging.md).

Use the unmerged tree when you need the child node itself, for example to assert on one child of a merged button. Use `hasTextExactly(...)` when the merged text list must match completely.

## Hierarchy and Selectors

Hierarchical matchers walk the tree: `hasParent`, `hasAnySibling`, `hasAnyAncestor`, `hasAnyDescendant`, each `(SemanticsMatcher) -> SemanticsMatcher`.

```kotlin
composeTestRule.onNode(hasParent(hasText("Button"))).assertIsDisplayed()
composeTestRule.onNode(hasAnyAncestor(hasTestTag("settings")) and hasText("Save"))
```

Selectors make chains read in order:

```kotlin
composeTestRule.onNode(hasTestTag("Players"))
    .onChildren()
    .filter(hasClickAction())
    .assertCountEquals(4)
    .onFirst()
    .assert(hasText("John"))
```

Other selectors on `SemanticsNodeInteraction`: `onChild()`, `onChildAt(index)`, `onParent()`, `onSibling()`, `onSiblings()`, `onAncestors()`, `onDescendants()`.

## Test Tags

```kotlin
import androidx.compose.ui.platform.testTag

LazyColumn(modifier = Modifier.testTag("myLazyColumn")) { /* ... */ }

composeTestRule.onNodeWithTag("myLazyColumn").performScrollToIndex(20)
```

Tags do not reach UI Automator by default. Setting `Modifier.semantics { testTagsAsResourceId = true }` once high in the hierarchy exposes them there.

## Custom Semantics Properties

Expose a value a test cannot otherwise read:

```kotlin
// Production code
val PickedDateKey = SemanticsPropertyKey<Long>("PickedDate")
var SemanticsPropertyReceiver.pickedDate by PickedDateKey

MyCustomDatePicker(modifier = Modifier.semantics { pickedDate = datePickerValue })

// Test
composeTestRule
    .onNode(SemanticsMatcher.expectValue(PickedDateKey, 1445378400)) // 2015-10-21
    .assertExists()
```

Warning from the docs: do not expose visual properties such as colors, font size, or corner radius this way. It "can pollute production code and wrong implementations can lead to bugs that are hard to find."

## Common Issues & Solutions

| Issue                                              | Solution                                                                  |
| -------------------------------------------------- | ------------------------------------------------------------------------- |
| Node not found                                     | `onRoot().printToLog("TAG")`; check merged vs unmerged                    |
| "Multiple nodes found" error                       | Use `onAllNodes...()` with `onFirst()`, `[index]`, or a narrower matcher  |
| Child text not matched                             | Add `useUnmergedTree = true`                                              |
| Icon-only control has no semantics to match        | Give it `contentDescription` in production code                           |
| Item has no distinguishing text                    | Add `Modifier.testTag(...)`                                               |
| `isDisplayed()` result silently ignored            | It returns a Boolean; use `assertIsDisplayed()` to assert (`@CheckResult` since 1.13.0-alpha01) |

## Anti-Patterns to Avoid

| Anti-Pattern                                        | Problem                              | Solution                                           |
| --------------------------------------------------- | ------------------------------------ | -------------------------------------------------- |
| `onNodeWithTag` for everything                      | Ignores what users and accessibility see | Prefer text or content description first      |
| Hard-coded copy of a string resource                | Breaks when copy changes             | `activity.getString(R.string.x)`                   |
| Custom semantics keys for colors or sizes           | Pollutes production code             | Docs: not recommended; use custom properties only when finders and matchers cannot match the item |
| Dynamic test tags injected into production code to tell apart identical Compose elements in View rows | Production code churn | Scope with `onRootWithViewInteraction` |
| Calling `isDisplayed()` as if it asserted           | Test can never fail                  | `assertIsDisplayed()`                              |

## Related References

- **Assertions and actions**: See [assertions-actions.md](assertions-actions.md)
- **Debugging the tree**: See [debugging.md](../debugging/debugging.md)
- **Compose inside Views**: See [interoperability.md](../advanced/interoperability.md)
- **Waiting for nodes to appear**: See [synchronization.md](synchronization.md)

## Sources

- https://developer.android.com/develop/ui/compose/testing/semantics
- https://developer.android.com/develop/ui/compose/testing/apis
- https://developer.android.com/develop/ui/compose/testing/common-patterns
- https://developer.android.com/develop/ui/compose/testing/interoperability
- https://developer.android.com/develop/ui/compose/testing/testing-cheatsheet
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/SemanticsMatcher
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/package-summary
- https://developer.android.com/jetpack/androidx/releases/compose-ui
