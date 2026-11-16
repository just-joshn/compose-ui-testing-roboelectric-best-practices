# Review of `current.kt`

`CurrentFlow.openAndSend` does not prove either behavior it appears to cover. A no-op click and a send that never finishes would still pass.

## Draft action

- `DraftActions` renders two buttons whose text is `Open` (draft and archive). `onNodeWithText("Open")` is a singular finder and requires exactly one match, so the click is ambiguous. It does not choose the draft.
- `onAllNodesWithText("Open")[0]` would only hide that ambiguity and couple the test to order. The draft control is the node with text `Open` that has an ancestor tagged `draft`.
- After the click, the test asserts that `Open` still exists. Both buttons remain in the tree whether or not `onOpen` runs, so a no-op handler passes. The observable result is the text `Draft opened`, and `Archive opened` must stay absent.
- `Thread.sleep(1_000)` waits on the wall clock. Opening the draft is a synchronous click and recomposition. Sleep does not select a node, does not own Compose work, and adds a fixed delay.

## Pending send to receipt

- `MessagePanel` starts with an empty field, and Send is enabled only when delivery is `Editing` and the message is not blank. The test never enters text, so `performClick` on Send does not start a send.
- `Sender { receipt.await() }` suspends on a `CompletableDeferred` that the test never completes. The receipt text therefore cannot appear.
- `waitForIdle()` returns while that deferred is still pending. It does not wait for an arbitrary business result, and it cannot finish a fake the test has not completed.
- Asserting that `Send` still exists does not prove a receipt. The button stays in the composition while the panel shows `Sending` and after it shows a receipt.
- Both flows share one `setContent` call, so a failure in the draft finder prevents the message path from running, and the two claims are not isolated.

The replacement is `ReviewTaskTest`: one test scopes the draft Open action and asserts `Draft opened` without `Archive opened`; the other enters text, asserts `Sending` while a controlled sender is pending, completes that sender, and asserts the receipt.
