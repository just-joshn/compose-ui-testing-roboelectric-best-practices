# Exercise the Compose examples

The fixture demonstrates a summary, repeated Open actions, and a message panel with pending/delivered states. There is no navigation shell: tests mount each composable directly and then interact through its real semantics.

## Sub-features

- `fixture-summary`: merged Draft label and separately addressable unmerged child.
- `fixture-draft-open`: Draft Open changes visible result to Draft opened.
- `fixture-archive-open`: Archive Open changes visible result to Archive opened; currently lacks an executable test.
- `fixture-send`: typing and submitting produces pending state, records payload, then displays receipt.
- `fixture-delay`: delayed Still sending is independent from external completion.
- `fixture-disposal`: removed panel cancels its pending work; a fresh panel has no stale result.
- `fixture-diagnostics`: capture failure text and both semantics trees; compare isolated rule effect probes.

## How to get to it (user POV)

- Read the installable skill's bundled examples, or run the README fixture commands.
- Summary path: view the Draft/Ready summary (no click action).
- DraftActions paths: click Open within Draft, or Open within Archive.
- MessagePanel path: type into Message and click Send. An empty/blank message disables Send, but that enabled-state path also lacks an existing assertion.
- Disposal/remount and rule probes are lifecycle/test-harness paths, not user-accessible navigation buttons.

## Driving it with Python/Gradle

Preconditions:

- Launch and doctor succeeded; each test supplies fresh UI state.
- Use the test methods below verbatim. Every direct method drive must produce exactly one passing JUnit case, not NO-SOURCE or a skipped case.

- **Summary.** Run `.pi/skills/verify-compose-robolectric/verify.py drive "$RUN" mergedLabelAndUnmergedChild`. Require summary to display Draft, the merged child lookup to be absent, and summary-child displayed with useUnmergedTree.
- **Draft Open.** Run `.pi/skills/verify-compose-robolectric/verify.py drive "$RUN" scopedOpenSelectsDraft`. It demonstrates that a global Open click is ambiguous, then clicks `hasText("Open") and hasAnyAncestor(hasTestTag("draft"))`. Require Draft opened visible and Archive opened absent.
- **Archive Open.** The stable selector is `hasText("Open") and hasAnyAncestor(hasTestTag("archive"))`; the required outcome is Archive opened visible and Draft opened absent. No existing test drives this action. Report NOT VERIFIED / missing executable journey rather than claiming the Draft negative assertion covers it. Add a dedicated semantics-action test before certifying this entry.
- **Send.** Run `.pi/skills/verify-compose-robolectric/verify.py drive "$RUN" sendShowsReceiptAfterCompletion`. The test types Hello into Message and clicks Send. Require Sending before completion, exactly one Hello received by the Sender fake, no premature Delivered Hello, then Delivered Hello visible and Sending absent.
- **Delayed feedback.** Run `.pi/skills/verify-compose-robolectric/verify.py drive "$RUN" composeClockDoesNotCompleteSender`. Require Sending first, Still sending after 1,200ms of controlled Compose time, and no Clock delivered until the fake completes; then require Clock delivered visible.
- **Dispose/remount.** Run `.pi/skills/verify-compose-robolectric/verify.py drive "$RUN" disposalCancelsPendingSendAndFreshPanelIsIsolated`. Require cancellation of First, Ready to send on remount, no Stale receipt, Second recorded once by the new sender, and Second delivered visible after completion. This is test-controlled lifecycle, not an app navigation path.
- **Diagnostics.** Run `.pi/skills/verify-compose-robolectric/verify.py drive "$RUN" selectorFailureIncludesTreeDiagnostics`. Keep original missing-node assertion and MERGED/UNMERGED output.
- **Full suite and rule probes.** Run `.pi/skills/verify-compose-robolectric/verify.py drive "$RUN" suite`. Require all 6 FixtureUiTest cases plus one effectStartOrder case from each V1EffectOrderTest and V2EffectOrderTest, total 8 without skips. Preserve the printed events, but do not turn their observed order into a universal contract.
- **Regression sensitivity.** Run `.pi/skills/verify-compose-robolectric/verify.py drive "$RUN" mutations`. Require no-op Send, wrong-item and removed-merge to fail their assigned assertion tests, then every restoration and final baseline to pass.

## Gotchas

- Archive Open and blank-message disabled-state paths are known coverage gaps, not seed-data problems. Report them explicitly for a whole-feature proof.
- Some tests mount state and lifecycle controls through setContent. That is fixture setup; input/action/result must still use semantics rather than internal setters.
- Fresh state and a controlled Sender exist per test. There is no seed database and no production transport.
- Cancellation/remount does not establish activity recreation or process-death recovery.
- Tests assert JVM semantics, not pixels, physical touch, TalkBack, or real IME behavior.
- One method passing certifies only its entry point. A full suite still does not cover the two known missing action paths.
