# Debug a missing semantics node

A user sees a missing summary-child node even though Draft is visible through its merged parent. The skill should explain the tree mismatch and correct only the test while preserving a meaningful label assertion.

## Sub-features

- `debug-tree`: compare merged summary with the unmerged summary-child.
- `debug-correction`: select the child with useUnmergedTree and assert Draft.
- `debug-negative`: reject a UI label changed to Wrong.
- `debug-routing`: a fresh diagnostic task reads diagnostics and semantics guidance.

## How to get to it (user POV)

- Invoke the installed skill and provide the missing-node assertion plus actual merged/unmerged tree dumps.
- Or request missing-node debugging through automatic skill selection, a distinct discovery path.
- In the sample, inspect the Draft/Ready summary rather than the separate Message panel.

## Driving it with Python/Gradle

Preconditions:

- Launch and doctor succeeded.
- Saved `DebuggingTaskTest.kt` is available.
- A fresh task uses `evidence/agent-prompts/debugging.md`, `evidence/agent-inputs/debugging.kt`, and the actual captured `evidence/agent-inputs/failure.txt`.

- **Capture current diagnostics.** Run `.pi/skills/verify-compose-robolectric/verify.py drive "$RUN" selectorFailureIncludesTreeDiagnostics`. Require the merged dump to expose summary text Draft/Ready and the unmerged dump to expose summary-child text Draft. The expected missing-node assertion is caught inside this passing diagnostic test; retain its original failure text.
- **Replay corrected test.** Run `.pi/skills/verify-compose-robolectric/verify.py drive "$RUN" debugging`. The correction is `onNodeWithTag("summary-child", useUnmergedTree = true).assert(hasText("Draft"))`. Require a passing baseline.
- **Negative control.** The same command changes Draft to Wrong in the UI. Require the corrected test to fail an AssertionError, then pass on restoration. Merely asserting existence would not qualify.
- **Fresh correction entry.** From the disposable project run `python3 scripts/verify_agent_outputs.py --responses "$RESPONSES" --case debugging`, with RESPONSES containing the new `DebuggingTaskTest.kt`. Retain results outside project. Check the response explains the supplied trees and changes tests only, not the UI to expose extra semantics.
- **Fresh routing entry.** Run `python3 scripts/check_agent_routing.py "debugging=$TRANSCRIPT" --output "$RUN/evidence/debugging-routing.json"` from the checkout with the actual new transcript. Require diagnostics.md, semantics.md and SKILL.md reads.

## Gotchas

- The observed framework hint says useUnmergedNode, but the API parameter used here is useUnmergedTree.
- Do not enable unmerged lookup everywhere or remove descendant merging merely to obtain green.
- The saved correction asserts child text, not visibility or device accessibility. Do not broaden that proof claim.
- Without new response and transcript inputs, fresh diagnostic activation is NOT VERIFIED.
