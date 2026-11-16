# Complete adaptation verification

The goal is a faithful, complete adaptation of Currents' Playwright best-practices skill for Android Jetpack Compose UI testing with Robolectric. The completed library preserves the source's topic granularity and practical workflows. Structural checks, content review, canonical behavior, supplemental examples, and fresh agent tasks have separate evidence.

## Source and installed structure

The source is pinned to `0b75b5835a87de1fdd202ba965f3bc5a27738fdf`. Its exact 58 topic paths and every original SHA-256 match the installed `adaptation-map.json`. A comparison against the local clone confirmed both. [The final source inventory](results/adaptation-source.json) records the installed file hashes and unchanged canonical source hashes.

The entry has grouped activity tables, a quick decision tree, a mandatory task-foundation table, and a run/debug loop. Every topic has a direct entry route. The library contains 11 core, eight advanced, four Android API, three architecture, four debugging, four framework, nine infrastructure, and 15 testing-pattern guides. Seven stable foundation paths remain separate from these 58 adaptations.

[Source inspection](reference-inspection.md), [the design](adaptation-design.md), and [the authoring contract](adaptation-authoring.md) explain the correspondence and Android replacements. [The decision trail](adaptation-decisions.tsv) records the selected structure, rejected alternatives, corrections, and verification checkpoints.

## Pre-refactor baseline

Before guidance changed, copied-package validation and all eight canonical fixture methods passed without skips. The result, original sources, and logs remain at `.work/verify-compose-robolectric.BZjdBq/evidence/`. Its disposable project was cleaned after exit.

The first launch supplied a fresh `.work/baseline-compose.*` directory. The helper rejected that prefix with `Use a fresh .work/verify-compose-robolectric.* directory` before testing. Earlier decision-log rows 3 and 10 incorrectly described an unset variable or empty argument. A superseding correction preserves those rows and states the actual failure. This was not a product defect or behavioral result.

## Structural checks and npm installation

These commands passed against the completed files:

```bash
python3 scripts/check_skill.py
python3 scripts/test_check_skill.py
python3 scripts/test_verify_npm_package.py
python3 scripts/verify_npm_package.py
```

The real package and a standalone copied install each passed all 58 guide routes, seven foundation routes, relative links, Markdown fragments, legal files, and two canonical Kotlin examples. The structural test suite passed 14 tests. Its controls reject missing or duplicate mappings, unknown source paths, unsafe or duplicate targets, orphan guides, broken fragments, missing routes, and malformed package metadata. Its synthetic positive package does not depend on the real library.

All four npm archive negative controls passed. The final archive and disposable consumer installation passed with 75 files. [The package result](results/adaptation-package.json) records its SHA-256. The archive remains at `.work/npm-package-uuju5vc3/compose-ui-testing-robolectric-best-practices-skill-1.0.0.tgz`. Nothing was published to npm.

These checks establish package structure and installability. They do not establish source fidelity or snippet behavior.

## Independent source-to-target review

Four independent reviews read all 58 mapped source and target guides in full:

- [Core and advanced review](adaptation-audits/core-advanced.md) covered 19 topics.
- [Architecture and platform review](adaptation-audits/architecture-platform.md) covered 15 topics.
- [Initial testing-pattern review](adaptation-audits/testing-patterns-initial.md) covered 15 topics and rejected six incomplete worked workflows.
- [Infrastructure and checker review](adaptation-audits/infrastructure.md) covered nine topics and the structural checker.

The reviews found a repeated incorrect clearing-semantics claim. A real pinned probe showed that `clearAndSetSemantics` replaces merged descendant information without erasing unmerged test inspection. The corrected statements appear in the semantics foundation, selectors, multiple roots, debugging, design systems, and reporting. [The probe source and JUnit XML](adaptation-probes/README.md) retain the actual merged and unmerged trees. The one named method passed without failures, errors, or skips.

Fresh correction workers replaced the six prose-only or disconnected workflows with concrete examples. These cover authenticated HTTP and multipart requests, GraphQL partial results, dropdown and toggle selection, full-date picker selection and wizard back navigation, two-pointer pinch and cancellation, operation-produced CSV bytes, and optional screenshot capture and comparison.

[The final correction review](adaptation-audits/corrections.md) compared the seven changed testing-pattern guides to their full mapped sources. It accepted all six findings as resolved. It also accepted all six clearing-semantics corrections and the mandatory foundation routing. The coordinator checked all 32 hashes recorded by that reviewer against the actual files. [The final no-comments review](adaptation-audits/no-comments.txt) found no actionable comments in the new checker code, all 58 guides' fenced examples, or the specified probe files.

The optional screenshot workflow passed source and usability review only. Its capture and comparison did not run.

## Supplemental example execution

These checks are separate from the canonical eight-test contract:

| Example | Executed result | Retained evidence |
| --- | --- | --- |
| Clearing-semantics inspection | One method passed and printed both trees. | [Probe instructions and evidence](adaptation-probes/README.md) |
| HTTP and multipart client | Three methods passed. The current guide block matches the executed source hash. | [Source hashes](adaptation-probes/http-contracts/proof.json) and [JUnit XML](adaptation-probes/http-contracts/TEST-ItemHttpContractTest.xml) |
| GraphQL client, decoder, and mapper | Two methods passed. The current guide block matches the executed source hash. | [JUnit XML](adaptation-probes/http-contracts/TEST-GraphQlHttpContractTest.xml) |
| Booking controls, pinch, and CSV export | Six methods passed in baseline and restored runs. The current three guide blocks exactly match the executed sources. | [Proof](adaptation-probes/controls-export/proof.md), [results](adaptation-probes/controls-export/results.json), and baseline, mutation, and restored XML in the same directory. |

Removing room selection failed the booking assertion. Disabling zoom updates failed both pinch assertions. Omitting exported records failed the produced-byte comparison. The coordinator inspected actual XML and confirmed assertion failures after compilation, with no errors or skips.

HTTP and GraphQL used Kotlin 2.2.10, JDK 17, OkHttp and MockWebServer 4.12.0, JSON-java 20240303, and JUnit 4.13.2 in a standalone JVM project. Controls and pinch used the pinned Compose 1.12.1, Robolectric 4.18, API 35 fixture configuration in a private copy. The exporter tests exercise its operation, not an Export button or document provider. The date picker deliberately supports June 2026 only. The CSV exporter deliberately rejects quoted-field delimiters.

The complete private HTTP build remains at `/Users/josh-desktop/.pi/agent/pstack-v2/jobs/deepen-http-graphql-39af7b/tmp/http-contracts.DJuA1k/`. The controls build and mutation sources remain at `/Users/josh-desktop/.pi/agent/pstack-v2/jobs/deepen-controls-export-def356/tmp/controls-verification/`. The copied evidence is portable. Those full build directories are local artifacts. Initial sandbox temporary-file failures remain in the logs and are not counted as behavior failures.

## Final canonical runtime and regression controls

The final verification snapshot is `.work/verify-compose-robolectric.RspOEv/evidence/`. Cleanup removed only the owned disposable project after a final healthy doctor check. Logs, JUnit XML, result records, response copies, and source snapshots remain. Launch compiled the fixture. Doctor confirmed the disposable snapshot matched the checkout before every drive. Drives ran serially in this order:

```text
package
suite
mutations
setup
writing
review
debugging
```

[The retained runtime results](results/adaptation-runtime.json) contain the original result records for every drive and the fresh-response replay. The coordinator compared all 37 records to their actual JUnit method inventories and failure counts. Every command wrapper exited successfully. Expected negative test runs remain nonzero in their underlying result records.

The canonical suite passed all eight methods without failures, errors, or skips. The full final baseline passed again after mutations. Removing merge behavior, routing Open to the wrong item, and making Send a no-op each failed the assigned named method through `AssertionError`. Each filtered restoration passed. Independent clock, disposal/isolation, and diagnostic cases also passed alone.

The setup comparison changed only Android-resource inclusion. The enabled and restored cases passed. The disabled case failed at the expected unresolved activity host. This is setup sensitivity, not a detected UI mutation.

The existing saved writing, review, and debugging responses passed unchanged. All four assigned response mutations failed through their intended assertions, and restorations passed. No canonical example or fixture build configuration changed.

To rerun the canonical drives, set JDK 17 and the Android SDK environment described in the setup reference. Then run:

```bash
mkdir -p .work
RUN="$(mktemp -d "$PWD/.work/verify-compose-robolectric.XXXXXX")"
python3 .pi/skills/verify-compose-robolectric/verify.py launch "$RUN"
for journey in package suite mutations setup writing review debugging; do
	python3 .pi/skills/verify-compose-robolectric/verify.py doctor "$RUN"
	python3 .pi/skills/verify-compose-robolectric/verify.py drive "$RUN" "$journey"
done
```

## Fresh explicit skill invocations

The first fresh round exposed a routing defect. Writing and debugging followed specialized topic rows without reading required foundations. The entry now requires task foundations before specialized routes. A second round passed routing but predated some later corrections. Those earlier transcripts, failed routing results, and copied skill snapshots remain under `.work/fresh-agents/` and `.work/fresh-agents-round2/`.

The final round used three new isolated sessions and exact copies of the completed skill. Each invoked the skill explicitly with `openai/gpt-6.1-sol` at low thinking. The [input and response hashes](results/adaptation-agent-inputs.json) identify the transcripts and generated files. [The routing result](results/adaptation-routing.json) confirms the required foundation reads for all three tasks.

The final outputs are preserved unchanged in [the fresh-response corpus](adaptation-agent-responses/). Writing produced one Draft-action test. Review produced a scoped Draft-action test and a pending-to-receipt test. Debugging produced one unmerged-child assertion. All four methods compiled and passed against the actual UI. Wrong-item, no-op Send, and wrong-summary-label mutations failed through the assigned assertions. Every restoration passed. The coordinator confirmed byte identity between the generated responses and the replayed copies.

Rerun that corpus separately from the earlier saved responses:

```bash
python3 scripts/verify_agent_outputs.py --responses evidence/adaptation-agent-responses
```

The exact final invocation copies, prompts, transcripts, notes, and original outputs remain under `.work/fresh-agents-final/`. This verifies explicit invocation for the three supplied tasks. It does not measure unaided automatic activation, performance, or reliability across models and repeated samples.

## Decision-trail review

[The cross-model trail review](adaptation-audits/trail.md) ran on `spacex-cursor/grok-4.7-fast`. It repeated the source-hash checks, all 37 JSON-to-JUnit comparisons, final skill-copy comparisons, and generated-source comparisons against the invocation write payloads. It confirmed the main verification claims and reported no high or medium finding.

The reviewer reported two low bookkeeping findings. The coordinator briefly rewrote the two incorrect baseline-history rows, then restored the original rows and appended the correct prefix explanation. The coordinator also initially expected eight cases in each filtered mutation restoration. That parent aggregation stopped. A corrected aggregation required one case in each filtered restoration and eight in each full baseline, then matched all 37 XML results. The trail now records both events. Neither changed product code, generated responses, test results, or the eight-test canonical contract.

The raw review calls the input-hash artifact `evidence/adaptation-agent-inputs.json`. Its actual path is [the result artifact](results/adaptation-agent-inputs.json). The review is retained unchanged.

## Remaining limits

The optional Roborazzi workflow uses an explicitly separate, older pinned toolchain. Tagged source checks confirm its API and task names. Capture, record, compare, verification failures, and CI rendering remain unexecuted. It is not a compatibility claim for the canonical Compose 1.12.1 fixture.

Most Markdown examples remain illustrative. The named supplemental runs above establish only their defined example clients and components. They do not validate a consuming app's production implementation. CI provider examples, category filtering, custom idling resources, provider integrations, and many project-specific snippets were not executed here.

No local run establishes actual device pixels, TalkBack traversal, OS UI, real IME behavior, hardware multitouch, production identity or transport services, backend authorization, process death, or app runtime performance. The guides retain separate integration and device checks for those claims.
