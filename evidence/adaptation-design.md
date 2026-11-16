# Complete adaptation design

## Goal and done predicate

Adapt Currents' Playwright best-practices skill faithfully and completely for Jetpack Compose UI testing with Robolectric. Match the source's structure, depth, and usability without asserting browser-to-Android API equivalence.

The completion predicate is a pinned 58-topic map with useful Android-native guides, direct activity routes to every guide, a working quick decision tree, preserved installability and attribution, passing structural negative tests, and passing real canonical fixture and regression controls. Editorial review checks depth and domain correctness separately. A checker pass does not certify prose quality or every illustrative snippet.

## Chosen structure

The installed skill contains eight categorized topic directories at its root, mirroring the source's organization. `android-apis/` replaces `browser-apis/`. Android-native filenames replace browser-specific filenames. `SKILL.md` owns activity routing, a symptom decision tree, and the validation loop.

`adaptation-map.json` is the source-to-target registry. A topic record contains `source`, `source_sha256`, `target`, `treatment`, `rationale`, and the original `source_sections`. The manifest identifies the source repository and full commit. The original section inventory is a review aid, not a claim that every heading translates directly.

The repository's `scripts/check_skill.py` remains the single structural validator. It reads the installed map and checks inventory, links, direct routing, and categorized topic discovery. Its existing `check(directory)` interface continues to serve copied-package and npm archive validation. No new documentation framework, dependency, or runtime service is introduced.

The seven existing foundation files remain stable entry routes with precise links into the library. Existing agent routing checks depend on those paths. They do not count as source-topic adaptations. Canonical Kotlin sources and the fixture/evidence machinery remain unchanged.

## Alternatives and review

Three models produced architecture sketches. A fresh Gemini reviewer scored them against source accountability, focused retrieval, domain boundaries, validator size/portability, and continuity with current callers.

| Candidate | Accountability | Retrieval | Boundaries | Validator | Continuity | Total |
| --- | --- | --- | --- | --- | --- | --- |
| GPT | 2 | 2 | 2 | 1 | 2 | 9 |
| Gemini | 2 | 2 | 2 | 1 | 1 | 8 |
| Grok | 2 | 2 | 2 | 2 | 1 | 9 |

These are design-review judgments, not measured skill quality scores. Candidate artifacts remain in the session's ignored `.work/` directory.

Use Grok's small installed-map plus existing-checker structure as the base. Graft GPT's stable foundation paths and exact inventory accountability. Use native names as all candidates recommend. Reject seven expanded handbooks because each would mix unrelated concerns and force agents to load too much context. Reject a literal browser-filename mirror because it would mislead retrieval and invite invalid API translation.

Do not adopt a generator for activity tables. They are editorial task routes, not one row per file. Direct-route and orphan checks enforce the actual invariant without making the map own a second navigation language. Do not adopt a new shipped Python checker or a per-heading concern schema. Source sections and independent full-source audits provide review accountability without a framework.

The independent reviewer flagged legacy-route masking, map/navigation drift, and unverified Markdown snippets. Recursive categorized discovery plus direct entry routes address the first two. Explicit illustrative-example labels and separate runtime evidence address the third, without claiming all guide code was executed.

## Execution and shared state

Capture baseline package and real JVM evidence before editing guidance. Author seven disjoint slices in parallel. Each reads full assigned upstream references and writes only its own target files under the common authoring contract. Workers use the current checkout because their source and documentation grounding is uncommitted. Path ownership prevents shared product writes. Only the coordinator edits the map, entry, foundation references, README, and evidence.

One implementation worker owns the two structural-checker files. Runtime drives serialize because Android SDK and Gradle caches are shared. Fresh review workers inspect completed artifacts rather than accepting author self-reports.

## Proof boundaries

Structural verification covers inventory, routes, links, packaging, and negative controls. Canonical runtime verification covers named local UI behavior, assigned mutations, and restoration. Fresh agent exercises cover explicit invocation and the specific supplied task, not automatic activation reliability. No run here establishes device rendering, accessibility-service navigation, actual provider transport, production security, or app performance.
