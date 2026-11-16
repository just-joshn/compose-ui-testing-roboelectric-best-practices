# Review an unreliable test

A user submits a test with an ambiguous selector, a fixed sleep, and weak existence-only checks. The skill should identify those issues and produce a replacement that verifies the correct item and asynchronous delivery result.

## Sub-features

- `review-target`: scoped Open selects Draft rather than Archive.
- `review-send`: enter Hello, click Send, observe Sending, then Delivered Hello.
- `review-negative`: reject wrong-item and no-op-send mutations.
- `review-routing`: a fresh review reads behavior, synchronization, and isolation guidance.

## How to get to it (user POV)

- Invoke the installed skill explicitly and ask it to review the unreliable test.
- Or ask for a Compose/Robolectric test review through automatic selection, which is a separate discovery path.
- The sample UI paths are Draft's Open button and the Message field followed by Send.

## Driving it with Python/Gradle

Preconditions:

- Launch and doctor succeeded; `ReviewTaskTest.kt` is in saved responses.
- For a fresh review, retain the input `evidence/agent-inputs/review.kt`, task `evidence/agent-prompts/review.md`, response text, replacement Kotlin file, and session transcript.

- **Replay reviewed tests.** Run `.pi/skills/verify-compose-robolectric/verify.py drive "$RUN" review`. Require both baseline tests to pass. Draft Open must display Draft opened, not Archive opened. `onNodeWithText("Message").performTextInput("Hello")` followed by `onNodeWithText("Send").performClick()` must display Sending before completion.
- **Payload and completion.** The existing Sender boundary fake must receive exactly Hello before its controlled completion. Delivered Hello must be absent before completion, then displayed afterward with Sending absent. Completing the fake is permitted; directly assigning UI delivery state is not.
- **Negative controls.** The command runs wrong-item and no-op-send separately. Each must reach JUnit and fail an outcome assertion, followed by a passing restored response. Preserve `agent-review-*/result.json`, logs, and XML.
- **Fresh replacement entry.** From the disposable project run `python3 scripts/verify_agent_outputs.py --responses "$RESPONSES" --case review`, with RESPONSES containing the new `ReviewTaskTest.kt`. Archive new results outside project before cleanup. Also read the response to check it actually explains the ambiguity, sleep/scheduler problem, and weak assertion; the execution script does not judge prose.
- **Fresh routing entry.** From the checkout run `python3 scripts/check_agent_routing.py "review=$TRANSCRIPT" --output "$RUN/evidence/review-routing.json"`, using the actual new Pi transcript. Require behavior.md, synchronization.md and isolation.md plus SKILL.md. Record any missed issue even if replacement code passes.

## Gotchas

- The fake's successful send is not backend delivery and does not exercise network/IME/device behavior.
- Advancing Compose time does not complete a deferred Sender. Fixed sleeps are rejected, not increased.
- A previous initial review had an invalid top-level onNode import. Compile the exact replacement unchanged; intent alone is insufficient.
- Missing new agent output/transcript means fresh review is NOT VERIFIED. Saved replay is still a separate valid, narrower check.
