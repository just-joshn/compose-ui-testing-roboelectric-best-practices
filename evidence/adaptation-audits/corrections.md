# PASS

The goal is a faithful source-to-Compose/Robolectric adaptation with comparable depth and practical usability. **All six original missing-workflow findings are closed in the reviewed files.** The clearing-semantics corrections and mandatory foundation routing also pass this acceptance review.

This verdict covers the named corrections, not every guide in the 58-topic adaptation. I made no edits and started no workers.

## Original findings

Paths below are relative to `compose-ui-testing-robolectric-best-practices/`.

| Original finding | Resolution | Evidence and limits |
|---|---|---|
| Real HTTP workflow, including multipart | **Closed.** `testing-patterns/repository-contracts.md` supplies dependencies, a complete OkHttp client, local-server lifecycle, JSON creation, multipart upload, recorded-request assertions, response decoding, and HTTP-error handling. | The three named HTTP tests passed in retained JUnit XML. The extracted current Kotlin block matches its recorded source hash. Multipart assertions cover field name, filename, MIME type, and transferred text bytes. Arbitrary binary multipart parsing remains explicitly outside this small example. |
| Real GraphQL client/parser for partial results | **Closed.** `testing-patterns/graphql.md` defines a complete operation-specific HTTP client, envelope decoder, typed error paths, repository mapping, and partial-result test. No undefined harness or mapper is required. | The two named GraphQL tests passed in retained XML. The current extracted block matches its recorded source hash. The nullable reviews schema makes the partial-data fixture coherent. The guide correctly distinguishes this implementation from a generated client, schema execution, and production integration. |
| Dropdown, toggle, date, and wizard actions | **Closed.** `testing-patterns/forms-validation.md` opens and selects a dropdown, toggles breakfast, opens a calendar dialog, selects a full-date identity, advances, navigates back, checks retained selections, and confirms. | The booking test passed in baseline and restored evidence. Removing the room update produced an assertion failure on `Room: Suite`. The calendar is explicitly a limited June 2026 implementation, not an asserted Material DatePicker integration. |
| Two-pointer pinch | **Closed.** `testing-patterns/gestures.md` mounts a real `transformable` recognizer, moves two pointer IDs through shared move events, checks visible zoom, releases or cancels input, and exercises another gesture after cancellation. `testing-patterns/custom-drawing.md` links directly to this worked example. | Both pinch methods passed in baseline and restored XML. Disabling zoom updates failed both at their zoom assertions. The sample explicitly excludes centroid-aware editor behavior, rendered-pixel proof, and hardware multitouch fidelity. |
| Produced CSV export bytes | **Closed.** `testing-patterns/file-operations.md` invokes an actual exporter against a fresh destination and compares its produced UTF-8 bytes with an independent expected literal. | Three export methods passed in baseline and restored XML. Omitting rows failed the byte comparison, with expected length 64 and actual length 12. The restricted unquoted-field contract is explicit. Export-button wiring and document-provider integration are not claimed. |
| Actual optional screenshot capture, record, compare, and verify workflow | **Closed at the requested source/usability level.** `testing-patterns/visual-regression.md` supplies a pinned Roborazzi integration, project configuration, complete capture test, baseline paths, record/verify/compare commands, thresholds, CI artifacts, and baseline-review procedure. | The guide labels the workflow source-checked and unexecuted. I independently checked the tagged 1.29.0 capture signature, comparison constructor/default comparator, and registered task names. Screenshot execution and mutation detection remain unverified, rather than being represented as canonical-fixture evidence. |

I compared the seven complete corrected guides with their mapped full upstream guides. Their upstream bytes match the SHA-256 entries in `adaptation-map.json`. Closure above rests on executable or fully specified workflows, not heading counts, document length, or structural-check results.

## Clearing-semantics corrections

**PASS across all six requested references.**

- `references/semantics.md`.
- `core/semantics-selectors.md`.
- `advanced/multiple-roots.md`.
- `debugging/debugging.md`.
- `frameworks/design-systems.md`.
- `infrastructure-ci-cd/reporting.md`.

The corrections consistently distinguish merged-tree replacement from unmerged test inspection. None treats an unmerged child's presence as proof that accessibility services receive its original semantics.

I inspected both the actual probe source and `evidence/adaptation-probes/clearing-semantics.xml`. The XML records one passing method, zero failures, errors, or skips, and both trees:

- The merged tree contains `cleared`, description `Replacement`, and `ClearAndSetSemantics = true`. It has no child node.
- The unmerged tree additionally contains `cleared-child` with text `Original child`.

That directly supports the corrected claim for the pinned probe. It does not establish TalkBack behavior or every modifier-order arrangement.

## Foundation routing

**PASS.** `SKILL.md` now explicitly requires the task foundation first and states that topic rows supplement rather than replace it.

The earlier selector ambiguity is addressed directly. Writing a selector-focused test requires behavior and semantics. Debugging a missing node requires diagnostics and semantics. Review/refactoring requires behavior, synchronization, and isolation.

## Proven new issues

**None found within this correction scope.**

The optional screenshot example's older, isolated toolchain is clearly distinguished from the canonical Compose 1.12.1 fixture. That is a documented adoption limit, not an unsupported compatibility claim.

## Evidence boundaries

- I inspected retained evidence; I did not rerun Gradle in this acceptance session.
- The five HTTP/GraphQL methods, six controls/export methods, and one clearing-semantics probe are separate from the canonical eight-test contract.
- Controls/export XML confirms baseline passes, assertion-level mutation failures, and restored passes. Its recorded guide hashes match the current four guides.
- Screenshot capture and comparison remain unexecuted.
- No conclusion here establishes production backend enforcement, Android provider grants, device pixels, TalkBack traversal, hardware input, or performance.
- Context7 returned no indexed Roborazzi library. Screenshot API checks used the guide's tagged upstream sources instead.
- **Prove It Works** shaped this review by requiring actual code, JUnit cases, tree output, and hash comparisons rather than accepting structural checks or author summaries.

## SHA-256 pins

These hashes pin every requested current guide, routing file, and the actual clearing-semantics probe artifacts. Guide paths are relative to `compose-ui-testing-robolectric-best-practices/`.

```text
7d71a4f2834e37aab61b3c69685887e74c4ab6bb6869f7baee09dd5df71c07bd  testing-patterns/repository-contracts.md
1ff6454eb66ccf28782888b52b4f3ab6fcccd3c589357b2997ebfcb557add175  testing-patterns/graphql.md
1ad0eda902e6900a598ec7dcca5b8cbe2f9660019c0988792f1d9ccbf4b8f6d8  testing-patterns/forms-validation.md
fa647fc104801f8faad9e0f5b181b06adcf32a2f3a60ea61a493cb9249ee54dc  testing-patterns/gestures.md
91e5f1af2bb57124fd54f0b8f114f572c560ff873c9087244d82a642294b571e  testing-patterns/custom-drawing.md
72814019ff0dbbdbde15b82daa714fd4c6309ce04f4b8660b5a9feef93cbfffb  testing-patterns/file-operations.md
0e177bf285e17a763240410f47b57a0ab05b8acae435af276ea81c02b80c9c08  testing-patterns/visual-regression.md
59b9109432947b547209c388520da01dab37d483b0c989ca4054a042d495f83b  references/semantics.md
2ab236a85e546ac60d455daa2775cf250a15e9b7054f4843ef88e8e16c771fc9  core/semantics-selectors.md
6628db6f9f12da80269b9edd03cb30e272da6170594763a2dd16815898561814  advanced/multiple-roots.md
4476edba1b1d197c1f7e790adc8b6520c0cb05ede96782f9b990560a9c1fef7c  debugging/debugging.md
edbf0f10ce8cc15c81ff5bd10c62fe7ace44a906a55733bf94c8ddfb80283a2a  frameworks/design-systems.md
ff473f076eaa256b33241074ffb7c97a4a2f73de0c5690f0e9f45f7ae06fcb1b  infrastructure-ci-cd/reporting.md
96b181d0256eedd5e46045ceb192c79bcefddfb6735575aea3d3201a31f71f6e  SKILL.md
```

Probe and supporting execution-evidence paths are relative to `evidence/adaptation-probes/`.

```text
8f1c0e9e30d3a592b76d6650c38e6330115a1c0c07ad89e9558001c172d1515d  ClearingSemanticsProbeTest.kt
7a0ab7846c0a6bd7c8f9953338a1fff114630bbf11de817b71910825c27765cc  clearing-semantics.xml
74854fd07e72800f7564b1da2179a766430a7fc5eb5ce5c8fc38ad95b03f787d  README.md
adf52442ad98efdf2dfb7f7a519631564d5207d9c4b11f178fdafb4974a8ced9  http-contracts/proof.json
357e1404f3dafaa70798996e4bb35793cd367265308cfe1ead1f0003cb399a14  http-contracts/TEST-ItemHttpContractTest.xml
0adc492b2c6013aef4b54fd6f339e5743ae2074e69b316441d3884df157141dc  http-contracts/TEST-GraphQlHttpContractTest.xml
54bbf28f6c5cacee9fd1a9fca239a9754423935f4bbaeaf52e89bf76e90c8505  controls-export/proof.md
de81d4e987e717bfbd3088d9070a1da8a81ebb49fa4681a6ffd8232da6e13209  controls-export/results.json
f811f66ce6f66ceeac5ed4fd53d5342657f04699b01cb9785ea2ed523a5693fb  controls-export/guide-hashes.json
cdf62b341b723082b250e69759e545cb45016d8f6f969cff509764b9279468f6  controls-export/baseline/TEST-BookingControlsTest.xml
231d101e254064d2cca6d346cccdc28ef8b472cee5aee89ffc7ca098b62e0309  controls-export/baseline/TEST-CsvExportOperationTest.xml
eb9344ef52fd547172086650858c94cf0e515b219c08556b45bce77c4ce83681  controls-export/baseline/TEST-PinchZoomTest.xml
7254071a1d1eea839dd3b5eb2f5e8194677fbaa8c5d622f3603a40933fcf461f  controls-export/mutation-BookingControlsTest/TEST-BookingControlsTest.xml
e1ccb0bf73cd5075a30ff9bf8965c6536a0cc41bcf6f2f8d35343f8694fa1a86  controls-export/mutation-CsvExportOperationTest/TEST-CsvExportOperationTest.xml
e3b10fe541402de340f41a758d02f283f88466046c52b4e5eb7b07316ce0f35a  controls-export/mutation-PinchZoomTest/TEST-PinchZoomTest.xml
68dd3b0681b2a7efab14c0b3f43a7457c487c1846d2dc14d6e62baf7c5cb9709  controls-export/restored/TEST-BookingControlsTest.xml
f51880b46f0e5d6b61d4e0bdc5c7e99f5151952065b2a08af128bd2ae51fc3d4  controls-export/restored/TEST-CsvExportOperationTest.xml
b043cc772d95ff0a285d8e20d883502b9405f956ee04be4ee38b2e8ab1b1b891  controls-export/restored/TEST-PinchZoomTest.xml
```
