# Problems in `current.kt`

`openAndSend` does not prove either behavior it appears to cover. Both assertions can pass when the clicks do nothing.

## Draft action

`DraftActions` renders two buttons whose merged text is `Open`, under tags `draft` and `archive`. `onNodeWithText("Open")` is a singular finder, so the click is ambiguous: it does not select the draft, and indexing `[0]` would only hide that. The test never checks `Draft opened` or that `Archive opened` stays absent. `onNodeWithText("Open").assertExists()` is true before the click, so a no-op handler still passes.

## Pending send to receipt

`MessagePanel` enables `Send` only while editing a non-blank message. The test never enters text, so the click does not start `sender.send`. The `Sender` lambda parks on a `CompletableDeferred` that the test never completes, so a receipt cannot appear. `Thread.sleep(1_000)` waits on wall time; it is not the Compose clock (`LaunchedEffect`'s `delay` that reveals `Still sending`) and it does not resume the fake. `waitForIdle()` returns while that deferred is still suspended. `onNodeWithText("Send").assertExists()` does not show `Sending` or the returned receipt, so a disabled or no-op `Send` still passes.

The two flows also share one `setContent` and one test, so a failure does not say which behavior broke.
