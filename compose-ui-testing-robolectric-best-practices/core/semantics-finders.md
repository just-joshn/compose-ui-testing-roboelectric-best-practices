# Semantics & Finders

## Table of Contents

1. [Semantics Tree](#semantics-tree)
2. [Finders](#finders)
3. [Matchers](#matchers)
4. [Merged and Unmerged Trees](#merged-and-unmerged-trees)
5. [Selectors](#selectors)
6. [Test Tags](#test-tags)
7. [Custom Semantics Properties](#custom-semantics-properties)
8. [Scope Compose Searches to Views](#scope-compose-searches-to-views)
9. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
10. [Related References](#related-references)
11. [Sources](#sources)

## Semantics Tree

UI tests in Compose use *semantics* to interact with the UI hierarchy. The *semantics tree* is generated alongside the UI hierarchy and describes the hierarchy.

The semantics framework is primarily used for accessibility, so tests take advantage of the information exposed by semantics about the UI hierarchy. Developers decide what and how much to expose.

Testing a Compose UI is different from testing a view-based UI. In Compose, because only some composables *emit* UI into the UI hierarchy, you need a different approach to matching UI elements.

Given a button that consists of an icon and a text element, the default semantics tree only contains the text label "Like". This is because some composables, such as `Text`, already expose some properties to the semantics tree. You can add properties to the semantics tree by using a `Modifier`.

```kotlin
MyButton(
    modifier = Modifier.semantics { contentDescription = "Add to favorites" }
)
```

## Finders

Finders let you select one or multiple elements (or *nodes* in the semantics tree) to make assertions or perform actions on them.

Some of these APIs accept a `SemanticsMatcher` to refer to one or more *nodes* in the semantics tree.

You can use `onNode` and `onAllNodes` to select one or multiple nodes respectively, but you can also use convenience finders for the most common searches, such as `onNodeWithText`, and `onNodeWithContentDescription`.

Select a single node:

```kotlin
composeTestRule
    .onNode(hasText("Button")) // Equivalent to onNodeWithText("Button")
```

Select multiple nodes:

```kotlin
composeTestRule
    .onAllNodes(hasText("Button")) // Equivalent to onAllNodesWithText("Button")
```

- `onNodeWithTag` finds a semantics node identified by the given tag. The tag to search for looks for an exact match only.
- `onRoot` finds the root semantics node of the Compose tree.
- A `SemanticsNodeInteractionCollection` has `filter`, which returns all the nodes matching the given matcher, and `filterToOne`, which expects to return exactly one node matching the given matcher.
- `onFirst` returns the first node in a collection and `onLast` returns the last node in a collection.
- `get(index)` retrieves the node at the given index of a collection. Any subsequent operation on its result will expect exactly one element found and will throw `AssertionError` if none or more than one element is found.

## Matchers

Hierarchical matchers let you go up or down the semantics tree and perform matching.

```kotlin
fun hasParent(matcher: SemanticsMatcher): SemanticsMatcher
fun hasAnySibling(matcher: SemanticsMatcher): SemanticsMatcher
fun hasAnyAncestor(matcher: SemanticsMatcher): SemanticsMatcher
fun hasAnyDescendant(matcher: SemanticsMatcher):  SemanticsMatcher
```

Here are some examples of these matchers being used:

```kotlin
composeTestRule.onNode(hasParent(hasText("Button")))
    .assertIsDisplayed()
```

- `hasText` returns whether the node's text contains the given text. In the merged semantics tree there can be a list of text items that got merged from the child nodes.
- `hasTextExactly` returns whether the node's text contains exactly the given values and nothing else. The order does not matter.
- `hasContentDescription` returns whether the node's content description contains the given value.
- `hasTestTag` returns whether the node is annotated by the given test tag.
- `hasClickAction` returns whether the node has a semantics click action defined.

`SemanticsMatcher` is a wrapper for semantics matcher lambdas that allows to build string explaining to the developer what conditions were being tested. Its constructor and its `and`, `or`, and `not` functions are:

```kotlin
SemanticsMatcher(description: String, matcher: (SemanticsNode) -> Boolean)
infix fun and(other: SemanticsMatcher): SemanticsMatcher
infix fun or(other: SemanticsMatcher): SemanticsMatcher
operator fun not(): SemanticsMatcher
```

- `SemanticsMatcher.expectValue` builds a predicate that tests whether the value of the given key is equal to the expected value.
- `SemanticsMatcher.keyIsDefined` builds a predicate that tests whether the given key is defined in semantics.
- `SemanticsMatcher.keyNotDefined` builds a predicate that tests whether the given key is NOT defined in semantics.

## Merged and Unmerged Trees

Some nodes merge the semantics information of their children. For example, a button with two text elements merges the text element labels:

```kotlin
MyButton {
    Text("Hello")
    Text("World")
}
```

From a test, use `printToLog()` to show the semantics tree:

```kotlin
composeTestRule.onRoot().printToLog("TAG")
```

This code prints the following output:

```
Node #1 at (...)px
 |-Node #2 at (...)px
   Role = 'Button'
   Text = '[Hello, World]'
   Actions = [OnClick, GetTextLayoutResult]
   MergeDescendants = 'true'
```

If you need to match a node of what would be the *unmerged* tree, you can set `useUnmergedTree` to `true`:

```kotlin
composeTestRule.onRoot(useUnmergedTree = true).printToLog("TAG")
```

This code prints the following output:

```
Node #1 at (...)px
 |-Node #2 at (...)px
   OnClick = '...'
   MergeDescendants = 'true'
    |-Node #3 at (...)px
    | Text = '[Hello]'
    |-Node #5 at (83.0, 86.0, 191.0, 135.0)px
      Text = '[World]'
```

The `useUnmergedTree` parameter is available in all finders. For example, here it's used in an `onNodeWithText` finder.

```kotlin
composeTestRule
    .onNodeWithText("World", useUnmergedTree = true).assertIsDisplayed()
```

`useUnmergedTree` is for tests with a special need to inspect implementation detail within children.

## Selectors

An alternative way to create tests is to use *selectors* which can make some tests more readable.

```kotlin
composeTestRule.onNode(hasTestTag("Players"))
    .onChildren()
    .filter(hasClickAction())
    .assertCountEquals(4)
    .onFirst()
    .assert(hasText("John"))
```

- `onChildren` returns children of this node at the moment of invocation, it only captures nodes that are currently present in the semantic tree.
- `onChild` returns exactly one child of this node. Use this only if this node has exactly one child.
- `onChildAt` returns child of this node at the given index.
- `onParent` returns a parent of this node.
- `onSibling` returns exactly one sibling of this node. Use this only if this node has exactly one sibling.
- `onSiblings` returns all siblings of this node.
- `onAncestors` returns all the ancestors of this node.
- `onDescendants` returns all the descendants of this node in Depth-First Search order.

## Test Tags

By default, composables are accessible from UiAutomator only by their convenient descriptors (displayed text, content description, etc.). If you want to access any composable that uses `Modifier.testTag`, you need to enable the semantic property `testTagsAsResourceId` for the particular composable's subtree.

Enable the semantic property only once high in your composables hierarchy to ensure all nested composables with `Modifier.testTag` are accessible from UiAutomator.

```kotlin
Scaffold(
    // Enables for all composables in the hierarchy.
    modifier = Modifier.semantics {
        testTagsAsResourceId = true
    }
){
    // Modifier.testTag is accessible from UiAutomator for composables nested here.
    LazyColumn(
        modifier = Modifier.testTag("myLazyColumn")
    ){
        // Content
    }
}
```

This feature is available in Jetpack Compose version 1.2.0-alpha08 and higher.

## Custom Semantics Properties

You can create custom semantics properties to expose information to tests. To do this, define a new `SemanticsPropertyKey` and make it available using the `SemanticsPropertyReceiver`.

```kotlin
// Creates a semantics property of type Long.
val PickedDateKey = SemanticsPropertyKey<Long>("PickedDate")
var SemanticsPropertyReceiver.pickedDate by PickedDateKey
```

Now use that property in the `semantics` modifier:

```kotlin
val datePickerValue by remember { mutableStateOf(0L) }
MyCustomDatePicker(
    modifier = Modifier.semantics { pickedDate = datePickerValue }
)
```

From tests, use `SemanticsMatcher.expectValue` to assert the value of the property:

```kotlin
composeTestRule
    .onNode(SemanticsMatcher.expectValue(PickedDateKey, 1445378400)) // 2015-10-21
    .assertExists()
```

You should only use custom Semantics properties when it's hard to match a specific item using the given finders and matchers.

## Scope Compose Searches to Views

The `onRootWithViewInteraction` API is included in `androidx.compose.ui:ui-test-junit4:1.12.0-alpha01+` and `androidx.compose.ui:ui-test:1.12.0-alpha01+`. This API is experimental and subject to change.

When migrating complex UIs to Compose, you might encounter identical Compose elements nested inside multiple traditional Android Views---such as within a `RecyclerView` or a `ViewPager`. In these scenarios, a standard Compose search like `onNodeWithText("Save")` might fail with a "Multiple nodes found" error.

Use the `onRootWithViewInteraction` API on your test rule. This function accepts an Espresso `ViewInteraction`, allowing you to leverage Espresso to isolate a specific container View and perform Compose interactions exclusively within that scoped hierarchy.

This API is specifically designed for testing Compose components nested inside Views. To test Views nested inside Compose, continue using standard Espresso interactions.

```kotlin
// Select the "Header" View container
val headerInteraction = onView(withId(header_id))

// Scope the Compose interaction to only the Header
composeTestRule
    .onRootWithViewInteraction(headerInteraction)
    .onNodeWithContentDescription("Settings")
    .performClick()
```

## Anti-Patterns to Avoid

- Using custom Semantics properties to expose visual properties such as colors, font size or rounded corner radius is not recommended, as it can pollute production code and wrong implementations can lead to bugs that are hard to find.
- Instead of modifying your production code to inject dynamic test tags to distinguish these elements, you can scope your Compose test directly to a specific Android View.

## Related References

- **Assertions and actions**: See [assertions-actions.md](assertions-actions.md)
- **Debugging the tree**: See [debugging.md](../debugging/debugging.md)
- **Compose inside Views**: See [interoperability.md](../advanced/interoperability.md)

## Sources

- https://developer.android.com/develop/ui/compose/testing/semantics
- https://developer.android.com/develop/ui/compose/testing/apis
- https://developer.android.com/develop/ui/compose/testing/common-patterns
- https://developer.android.com/develop/ui/compose/testing/interoperability
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/SemanticsNodeInteraction
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/SemanticsNodeInteractionCollection
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/SemanticsMatcher
- https://developer.android.com/reference/kotlin/androidx/compose/ui/test/package-summary
