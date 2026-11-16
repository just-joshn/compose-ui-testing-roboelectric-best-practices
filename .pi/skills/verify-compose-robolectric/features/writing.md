# Write a behavior test

A user asks the skill to write a Kotlin Compose test that chooses the correct item when two actions share the visible name Open, and verifies the resulting visible state.

## Sub-features

- `writing-scoped-open`: select the Draft Open action without relying on position.
- `writing-outcome`: show Draft opened and do not show Archive opened.
- `writing-negative`: the generated test rejects a wrong-item implementation.
- `writing-routing`: a fresh agent reads behavior and semantics guidance before proposing the test.

## How to get to it (user POV)

- Explicitly invoke `/skill:compose-ui-testing-robolectric-best-practices` and ask for a test of the duplicate Open buttons.
- Ask to write a Compose/Robolectric test and let a skill-capable agent select the skill. Automatic discovery depends on the host and is a distinct, unproven entry point.
- The fixture journey starts at DraftActions, where Draft and Archive each have an Open button.

## Driving it with Python/Gradle

Preconditions:

- Launch and doctor succeeded.
- The saved response `evidence/agent-responses/WritingTaskTest.kt` exists in the checkout snapshot.
- For a fresh-agent proof, use the frozen task in `evidence/agent-prompts/writing.md` and the acceptance contract in `evidence/agent-task-contract.md`. Preserve actual output and the new session transcript.

- **Replay the written journey.** Run `.pi/skills/verify-compose-robolectric/verify.py drive "$RUN" writing`. The saved test checks two Open nodes, then performs `onNode(hasText("Open") and hasAnyAncestor(hasTestTag("draft"))).performClick()`. Require Draft opened displayed and Archive opened absent.
- **Negative control.** The same command changes the Draft action to the Archive result in a nested disposable copy. Require `agent-writing-wrong-item/result.json` to show the authored test failing with an AssertionError, then `agent-writing-wrong-item-restored/result.json` passing. Baseline and restored runs must execute tests; a compiler failure is not detection.
- **Fresh response entry.** In the disposable project run `python3 scripts/verify_agent_outputs.py --responses "$RESPONSES" --case writing`, where RESPONSES is the absolute directory holding the new `WritingTaskTest.kt`. Keep the command/log and copy `.work/fixture-results/` to a new evidence subdirectory before cleanup. Do not substitute this path for saved replay without identifying which response was used.
- **Fresh routing entry.** Run `python3 scripts/check_agent_routing.py "writing=$TRANSCRIPT" --output "$RUN/evidence/writing-routing.json"` from the original checkout, with TRANSCRIPT set to the actual Pi session JSONL. Require successful reads of SKILL.md, behavior.md and semantics.md. Record activation mode and model. Missing transcript/response is an unmet precondition; replay cannot fill it.
- **Proof.** Keep `evidence/source/evidence/agent-responses/WritingTaskTest.kt`, the baseline/mutation/restored logs and XML, and a summary naming `writing-scoped-open` and the Draft entry.

## Gotchas

- A global singular Open query is ambiguous. Index 0 is not an acceptable substitute for item identity.
- Directly assigning the opened state would bypass the user action.
- Saved responses only demonstrate replay. Neither fresh activation nor unaided discovery is certified by this command.
- A static code review cannot overrule a compilation or runtime failure.
