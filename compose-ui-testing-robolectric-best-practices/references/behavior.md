# Test the user's result

## Continue with the topic guides

For a complete writing workflow, read [suite structure](../core/test-suite-structure.md), [assertions and waiting](../core/assertions-waiting.md), and [component testing](../testing-patterns/component-testing.md). Use [forms and validation](../testing-patterns/forms-validation.md) for editable state and [screen robots](../core/screen-robots.md) for repeated interactions. This foundation remains the stable writing and review entry point.

## Choose the claim first

Name the behavior before writing the finder. "Submitting a message displays the returned receipt" is stronger than "Send exists". "Opening the draft leaves the archive unchanged" specifies which repeated action matters.

Use `setContent` to mount the smallest real UI that owns that behavior. A stateless component test can prove state rendering and callback delivery. It cannot prove a screen's loading-to-result orchestration if the test supplies the final state itself.

Keep one `setContent` call per test. Create fresh state before it. Use the [canonical examples](../examples/) as executable patterns, not a shared base class.

## Drive actions and assert outcomes

Select the intended editable node, enter a concrete value, perform the action, and assert the rendered result. Assert important preconditions such as a disabled action or a loading state when those are part of the contract.

Prefer these API pairs according to the claim:

| Claim | Action and assertion |
| --- | --- |
| User input is accepted | `performTextInput` or `performTextReplacement`, then `assertTextEquals` on the editable semantics |
| A click changes the UI | `performClick`, then assert the expected text or state |
| An action is unavailable | `assertIsNotEnabled`, plus a valid-input case that enables it |
| One item changes | Scope the action to that item, then assert its new state and the other item's unchanged state |
| A group exists exactly once | A singular finder and an assertion, not an arbitrary first match |
| No matches are expected | `assertDoesNotExist`, not a caught generic exception |

`assertExists` checks semantics presence. `assertIsDisplayed` checks visibility according to the test framework. Neither alone proves a click produced the correct content. Inspect the semantics when text-field labels and editable text share a node. Supply the right `assertTextEquals` values for that node instead of weakening the assertion.

Bad:

```kotlin
rule.onNodeWithText("Send").performClick()
rule.onNodeWithText("Send").assertExists()
```

The second line can pass if the click handler does nothing.

A useful test asserts the visible receipt supplied by a controlled fake. A separate failure-path test supplies a failure and asserts the user-facing error if that behavior is in scope. Do not invent retry or error handling solely to demonstrate a testing pattern.

## Keep negative proof

Temporarily remove the state update, make the click a no-op, or route the action to the wrong item. The intended test must fail at a behavior assertion. Restore the UI and rerun.

Do not count a compilation error, failed dependency download, or broken test host as detection of a UI regression. Inspect the named test and the JUnit failure before recording a mutation as killed.

Review a test against two edits. It must fail when the promised behavior breaks. It should keep passing when internal helpers change without changing that behavior.

## Review checklist

- Does the finder uniquely identify the intended control in the chosen tree?
- Does the test drive the real action-to-state path rather than inject its expected final state?
- Is an external request assertion part of the public contract, or only an internal call-count preference?
- Does synchronization follow the actual work owner?
- Would a no-op action still pass?
- Are important wrong-target or unchanged-state cases covered?
- Does the test claim device behavior that Robolectric cannot establish?

Use [semantics.md](semantics.md) for selection and [synchronization.md](synchronization.md) for intermediate states and async results. The [official testing guide](https://developer.android.com/develop/ui/compose/testing) defines finders, assertions, and actions.
