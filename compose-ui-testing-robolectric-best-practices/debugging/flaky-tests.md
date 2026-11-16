# Reproduce and fix flaky local UI tests

Use this guide when the same test sometimes passes and sometimes fails without an intentional code change. It covers Compose UI tests run locally with Robolectric. A failure that always occurs in CI is an environment-specific defect until evidence establishes intermittency.

## Table of contents

- [Classify the variation](#classify-the-variation)
- [Repeat actual executions](#repeat-actual-executions)
- [Build a root-cause timeline](#build-a-root-cause-timeline)
- [Fix synchronization by work owner](#fix-synchronization-by-work-owner)
- [Fix identity and animation assumptions](#fix-identity-and-animation-assumptions)
- [Remove shared state and leaked work](#remove-shared-state-and-leaked-work)
- [Compare the CI environment](#compare-the-ci-environment)
- [Quarantine without hiding the defect](#quarantine-without-hiding-the-defect)
- [Confirm stability and prevent recurrence](#confirm-stability-and-prevent-recurrence)
- [Troubleshooting table](#troubleshooting-table)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Classify the variation

| Category | Typical symptom | First experiment |
| --- | --- | --- |
| Work ownership | Loading sometimes remains or transient UI disappears | Hold the external completion deterministically |
| UI identity | Wrong row activated after list order changes | Match by meaningful item identity |
| Clock ownership | Delay advances in one scope but UI never changes | Identify the scheduler that owns the delay |
| Test order | Method passes alone and fails after another method | Compare fake, global, and storage ownership |
| Worker sharing | Failure appears with concurrent workers | Isolate mutable paths and external records |
| Environment | Consistent CI failure, local pass | Match versions, JDK, SDK, locale, and resource configuration |
| External dependency | Failures correlate with network or service state | Replace only that boundary for local UI coverage |
| Resource exhaustion | Worker terminates or hangs under suite load | Inspect memory limits and owned thread cleanup |

Do not begin by increasing a global timeout. A timeout is an observation that the required condition did not occur within a bound. It does not identify why.

Use one change per diagnostic experiment. If both concurrency and waiting change, a pass cannot identify which assumption was wrong.

## Repeat actual executions

Gradle has no built-in Playwright `--repeat-each` equivalent in this workflow. Force the selected test task to run and retain each result before the next run overwrites it.

This illustrative shell loop runs from a checkout with a Gradle wrapper and the fixture task. It uses a fresh evidence directory, continues after test failures, and reports failure if any attempt fails. It records repeated task executions, not independent machine environments.

```bash
RUN="$(mktemp -d "$PWD/flaky-evidence.XXXXXX")"
failed=0
for attempt in $(seq 1 10); do
  destination="$RUN/$attempt"
  mkdir -p "$destination"
  status=0
  ./gradlew :fixture:testDebugUnitTest \
    --tests 'fixture.FixtureUiTest.sendShowsReceiptAfterCompletion' \
    --console=plain --no-daemon --rerun-tasks \
    > "$destination/gradle.log" 2>&1 || status=$?
  printf '%s\n' "$status" > "$destination/exit-code.txt"
  if [ -d fixture/build/test-results/testDebugUnitTest ]; then
    cp -R fixture/build/test-results/testDebugUnitTest "$destination/junit"
  fi
  if [ "$status" -ne 0 ]; then
    failed=1
  fi
done
printf 'Evidence directory %s\n' "$RUN"
exit "$failed"
```

Use the project's real module, variant, and method. Run long loops in a managed job rather than an untracked background shell. An existing Gradle workspace must not be driven concurrently by separate commands that write the same reports.

Inspect every attempt's exit code and JUnit testcase. If compilation or dependency resolution failed, report that attempt as infrastructure or setup failure, not as an intermittent UI assertion. If no selected testcase exists, the attempt is not a pass.

Compare these execution scopes:

1. Suspect method alone.
2. Its complete class.
3. The relevant suite containing likely predecessors.
4. The suite under the CI worker configuration.

A serial pass suggests a concurrency hypothesis. It does not prove concurrency is the cause. Run the original failing configuration again after fixing the suspected sharing.

## Build a root-cause timeline

Collect events at meaningful boundaries rather than printing every frame:

```text
user action selected Draft/Open
state owner started request for draft-7
fake received request draft-7
test completed request draft-7
state owner published receipt
semantics displayed Draft opened
```

This is an illustrative event sequence, not a measured fixture log. Assign each event to a real observation before using it to diagnose a run. Keep request identifiers sanitized and include the selected item identity.

The first absent event narrows the investigation:

| Last observed event | Inspect next |
| --- | --- |
| Action selected | Enabled state and actual click callback |
| Request started | Correct fake instance and dependency installation order |
| Fake completed | Cancellation, scheduler, and state collector |
| State published | Lifecycle collection and recomposition |
| Semantics changed | Matcher identity, merged tree, and display bounds |

Capture the failing selector and both semantics trees when synchronization permits. Preserve exceptions with their cause chains. Do not replace a primary failure with a second exception from diagnostic collection.

The recorded canonical JUnit ambiguity diagnostic begins:

```text
Failed to inject touch input.
Reason: Expected exactly '1' node but found '2' nodes that satisfy: (Text + InputText + EditableText contains 'Open' (ignoreCase: false))
```

This is evidence of an ambiguous target. It is not evidence that the click was too fast. Inspecting the matching nodes is more useful than adding a delay.

## Fix synchronization by work owner

Faulty illustrative test body:

```kotlin
compose.onNodeWithText("Send").performClick()
Thread.sleep(500)
compose.onNodeWithText("Delivered Hello").assertIsDisplayed()
```

A sleep assumes a completion deadline that the test does not control. It can be too short under load and still waste time when the operation finishes sooner.

Correct the boundary. This illustrative fragment assumes the canonical `MessagePanel` and a fresh sender equivalent to the canonical private `ControlledSender`. It needs `performTextInput`, `performClick`, `onNodeWithText`, and `assertIsDisplayed` from `androidx.compose.ui.test`.

```kotlin
val sender = ControlledSender()
compose.setContent { MessagePanel(sender) }
compose.onNodeWithText("Message").performTextInput("Hello")
compose.onNodeWithText("Send").performClick()
compose.onNodeWithText("Sending").assertIsDisplayed()
compose.runOnIdle { sender.complete("Delivered Hello") }
compose.onNodeWithText("Delivered Hello").assertIsDisplayed()
compose.onNodeWithText("Sending").assertDoesNotExist()
```

The test can now inspect the pending state before the request finishes. A final receipt assertion proves the result, not merely the fake's call count.

If work is genuinely external and cannot be completed directly, observe a bounded condition. This fragment additionally needs `onAllNodesWithText`:

```kotlin
compose.waitUntil(timeoutMillis = 2_000) {
	compose.onAllNodesWithText("Delivered Hello").fetchSemanticsNodes().size == 1
}
compose.onNodeWithText("Delivered Hello").assertIsDisplayed()
```

Do not wrap arbitrary assertions in catch-and-retry loops. A collection query represents zero matches naturally. The final assertion establishes display state after the bounded observation.

Keep time owners separate:

| Owner | Correct action | Wrong substitute |
| --- | --- | --- |
| Composition delay or animation | Advance `mainClock` after establishing its start | `Thread.sleep` |
| Composition task queued now | `mainClock.scheduler.runCurrent()` where needed | Advancing an unrelated test scope |
| Injected coroutine scheduler | Advance that scheduler | Assuming Compose drives it |
| Deferred request | Complete its pending result | Advancing virtual time indefinitely |
| Wall-clock expiry | Inject application time source | Assuming `Instant.now()` follows Compose time |
| Android looper callback | Target that looper when required by the tested adapter | Globally draining every queue |

With automatic clock advancement, synchronized operations can skip transient animation states. Disable it before triggering the transition when the intermediate state is the contract. Establish the start frame, advance deliberately, and assert the intended state. Do not add an unexplained large duration until the test happens to pass.

## Fix identity and animation assumptions

Faulty repair for duplicate labels:

```kotlin
compose.onAllNodesWithText("Open")[0].performClick()
```

List order can vary, so the first match can target the wrong item. Correct the selector with a stable item identity and observable action label. The canonical example uses `hasText("Open") and hasAnyAncestor(hasTestTag("draft"))`.

Assert both the intended result and an important unchanged result. The canonical test requires `Draft opened` and absence of `Archive opened`. Its recorded wrong-item mutation failed the visible-result assertion and passed after restoration.

Use an index only when order itself is the behavior under test. Establish the expected order before acting. Do not use index zero to hide a singular finder's ambiguity.

Do not disable all animations to conceal a state bug. For settled-state behavior, ordinary Compose synchronization is usually enough. For animation timing, explicitly control the Compose clock. Device animation and rendering performance remain separate claims.

## Remove shared state and leaked work

Faulty ownership:

```kotlin
companion object {
	val sender = ControlledSender()
}
```

Its deferred and request history survive between test methods. Once completed, later tests can skip loading or display a stale receipt.

Prefer a local fake in each test. JUnit's test instance lifecycle also permits instance fields, but local values make ownership clearest. Keep databases, file paths, preference names, and external record IDs independent where writes can overlap.

Use an explicit owner for cleanup:

- The Compose rule disposes its test-owned composition.
- Composition-owned scopes cancel with disposal.
- Test-owned scopes must be cancelled and joined by their fixture.
- Executors must shut down and owned threads must terminate.
- Registered idling resources must be unregistered.
- Global dispatcher or service overrides must be restored after failures too.

Robolectric does not clean up arbitrary rogue threads for you. A test can pass while leaked work corrupts the next method.

For late-result bugs, start a request, dispose its owner, mount a fresh screen, and complete the stale request. Assert the stale receipt never appears. The canonical `disposalCancelsPendingSendAndFreshPanelIsIsolated` test exercises this local ownership boundary. It does not prove process-death behavior.

## Compare the CI environment

Record rather than assume parity:

| Difference | Evidence | Response |
| --- | --- | --- |
| JDK or runtime SDK | Worker Java version and `@Config` | Use a supported combination |
| Compose v1 versus v2 | Resolved artifact and factory import | Account for dispatcher ordering explicitly |
| Missing Android resources | Selected variant's test configuration and manifest | Restore required host setup |
| Locale, density, font scale | Effective resource configuration | Declare the scenario's required configuration |
| Dependency availability | Download exception and repository settings | Fix cache or network setup, not UI waits |
| Worker memory pressure | Worker exit diagnostics and runner limits | Bound parallelism and eliminate leaks |
| Files shared across workers | Actual path and ownership | Allocate per-test or per-worker directories |

The fixture's recorded v1/v2 probe produced `events=[effect, apply]` for v1 and `events=[apply, effect]` for v2. These are observations for that probe, not a universal ordering contract for application code. A migration that exposes hidden immediate-execution assumptions needs synchronization, not a version downgrade by guesswork.

Match the CI toolchain and run command locally. Setting `CI=true` alone does not recreate its JDK, resource limits, or dependency cache. A headless-versus-headed comparison is a browser concern, not a Robolectric UI mode switch.

## Quarantine without hiding the defect

A quarantine is a temporary reporting and ownership decision. It is not a fix.

If the team must separate a known flaky test, keep its source and dedicated execution visible. Record the issue, owner, observed failure signature, expiry, and condition for returning to the normal suite.

Use the project's JUnit category or dedicated task convention. Do not silently exclude the test via a method-name filter or blanket `@Ignore`. A skipped test is not a passing test.

Retain every retry attempt. A failed first attempt followed by a pass must remain classified as flaky in reporting. Do not make retry-until-green the acceptance criterion.

If retries are enabled by an existing Gradle plugin, keep their budget small and document the policy in the CI guide. This guide does not assume an installed retry plugin or invent a Gradle retry DSL.

## Confirm stability and prevent recurrence

After the repair, run the named method and its class repeatedly under the original failing configuration. Report the actual number of executed attempts and their outcomes. Ten passes are evidence for ten attempts, not proof that no race exists.

Add a negative control for the broken assumption:

- Route the click to the wrong item to check identity assertions.
- Remove the result state update to check outcome coverage.
- Leave the fake pending to check that the test does not fabricate success.
- Deliver a stale result after disposal to check ownership.

Require compilation and host startup to succeed before counting a negative control as a detected regression. Preserve the intended named assertion failure, restore the change, and rerun.

Prefer deterministic tests that hold and release meaningful work over repeated burn-in alone. Keep visible preconditions that identify the first incorrect transition. Do not add unrelated assertions solely to increase the assertion count.

## Troubleshooting table

| Symptom | Root-cause observation to seek | Repair |
| --- | --- | --- |
| Loading skipped intermittently | Reused completion or automatic timer advancement | Fresh pending fake and deliberate clock mode |
| Wrong row opens | Selector matches multiple items or depends on order | Scope by meaningful identity |
| Passes alone only | Shared mutable state, persisted data, or leaked job | Fix lifecycle and cleanup |
| Timeout unaffected by larger values | Work has no producer or wrong scheduler is advanced | Control the real owner |
| Passes only on retry | First-attempt seed, startup, or state leak differs | Preserve and investigate first attempt |
| CI worker exits without assertion | Resource or environment failure | Inspect worker diagnostics separately from UI results |

## Review checklist

- Is intermittency established by executed named tests?
- Are failed attempts retained with their JUnit evidence?
- Does each experiment change one suspected cause?
- Are clocks and pending requests controlled separately?
- Is selector identity independent of incidental order?
- Are fake state, files, and asynchronous work isolated?
- Does the corrected test reject the original broken behavior?
- Is any quarantine visible, owned, and time-bounded?

## Related guides and sources

- [Debugging](debugging.md) preserves first-failure evidence.
- [Logs and exceptions](logs-exceptions.md) records causes without swallowing them.
- [Fixtures and hooks](../core/fixtures-hooks.md) defines cleanup ownership.
- [Parallel execution](../infrastructure-ci-cd/parallel-sharding.md) isolates workers.
- [Synchronization reference](../references/synchronization.md) separates clock domains.
- [Compose synchronization](https://developer.android.com/develop/ui/compose/testing/synchronization) documents waiting and idling resources.
- [Compose v2 migration](https://developer.android.com/develop/ui/compose/testing/migrate-v2) documents dispatcher changes.
- [Robolectric best practices](https://robolectric.org/best-practices/) documents rogue-thread hazards.
