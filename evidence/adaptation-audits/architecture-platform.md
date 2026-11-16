## ISSUES

The goal is a complete, usable Compose/Robolectric adaptation of Currents' skill. I read all fifteen assigned source guides and their actual target guides. `frameworks/design-systems.md` was present and included in the audit. No files were modified.

### Actionable finding

**The guidance incorrectly states that unmerged-tree searches cannot expose descendants beneath `clearAndSetSemantics`.**

Affected locations, relative to `compose-ui-testing-robolectric-best-practices/`:

- `debugging/debugging.md:121` says that `clearAndSetSemantics` can remove descendant information entirely and that unmerged search cannot reconstruct it.
- `frameworks/design-systems.md:139` says that clearing semantics cannot be undone by searching the unmerged tree.

The published [`clearAndSetSemantics` API documentation](https://developer.android.com/reference/kotlin/androidx/compose/ui/semantics/clearAndSetSemantics.modifier), fetched through Context7 during this audit, explicitly distinguishes the trees. Descendant information is cleared in the merged tree. In the unmerged tree, the node is marked `isClearingSemantics`, but nothing is actually cleared.

These statements can send a reader away from a useful diagnostic and incorrectly conflate merged accessibility semantics with unmerged test inspection.

**Minimal correction for both locations:**

> `clearAndSetSemantics` replaces descendant information in the merged tree. Inspect the unmerged tree for child-specific test diagnostics. Finding a child there does not mean accessibility services receive that child's original semantics.

This is a documentation-backed correctness finding. I did not compile or execute a new clearing-semantics probe against Compose 1.12.1.

### Coverage examined

| Source | Target | Topics examined |
|---|---|---|
| `architecture/pom-vs-fixtures.md` | `architecture/robots-vs-fixtures.md` | Robots, fixtures, pure helpers, rule ordering, cleanup, combined organization, abstraction failures |
| `architecture/test-architecture.md` | Same path | Domain, component, screen, adapter, service and device claims; layered inventory coverage |
| `architecture/when-to-mock.md` | `architecture/when-to-fake.md` | Boundary selection, held completions, cancellation, real adapters, replay, hybrid tests and contract drift |
| `browser-apis/browser-apis.md` | `android-apis/system-services.md` | Location, permission denial, clipboard, notifications, camera, microphone and hardware handoffs |
| `browser-apis/iframes.md` | `android-apis/view-interop.md` | Hierarchy ownership, `AndroidView` updates, callbacks, reuse, disposal, WebView/provider boundaries and stale results |
| `browser-apis/service-workers.md` | `android-apis/background-work.md` | Worker results, initialization, constraints, offline queues, cache persistence, retry, unique work and push boundaries |
| `browser-apis/websockets.md` | `android-apis/reactive-streams.md` | State versus events, readiness, conflation, incoming/outgoing messages, reconnect, lifecycle and transport contracts |
| `debugging/console-errors.md` | `debugging/logs-exceptions.md` | Log capture, throwable preservation, scoped error policy, rule ordering, uncaught failures and report retention |
| `debugging/debugging.md` | Same path | Reproduction, semantics diagnostics, cardinality, clock ownership, host setup, CI and negative controls |
| `debugging/error-testing.md` | Same path | Recoverable states, pending work, retry, timeout ownership, offline recovery, validation and cancellation |
| `debugging/flaky-tests.md` | Same path | Forced repetitions, retained attempts, timelines, identity, shared state, CI parity, quarantine and recurrence |
| `frameworks/angular.md` | `frameworks/dependency-injection.md` | Explicit injection, route/screen separation, Hilt prerequisites, replacement timing, scopes, variants and lazy dependencies |
| `frameworks/nextjs.md` | `frameworks/navigation.md` | NavHost wiring, arguments, nested graphs, Back, authentication return routes, deep links and data loading |
| `frameworks/react.md` | `frameworks/state-viewmodels.md` | Hoisted state, ViewModel scheduling, forms, effects, stale responses, shared state and restoration |
| `frameworks/vue.md` | `frameworks/design-systems.md` | Providers, controlled components, slots, semantics, overlays, transitions, adaptive variants and theme configuration |

Apart from the finding above, I found no additional proven actionable defect. The guides contain substantive worked examples and topic-specific workflows rather than boundary disclaimers alone. Browser-only mechanisms are generally handed off to appropriate integration or device evidence without inventing direct Compose equivalents.

### Verification and limits

- `python3 scripts/check_skill.py` passed package checks and the standalone copied-install check. This establishes structure and links, not content completeness.
- The local upstream checkout reported commit `0b75b5835a87de1fdd202ba965f3bc5a27738fdf`.
- All fifteen source content hashes matched their map records.
- Illustrative snippets were reviewed, not newly compiled. Hilt, WorkManager, Navigation, interop and ShadowLog examples therefore do not receive a fresh runtime-compatibility certification from this audit.
- The sandbox refused an initial shell here-document with `cannot create temp file for here document: Operation not permitted`. A read-only `python3 -c` invocation succeeded instead. This was an environment restriction, not a product finding.

### Reviewed identity

For each side, I sorted the relative paths and concatenated UTF-8 records in this exact format:

```text
relative-path<TAB>sha256(file-bytes)<NEWLINE>
```

The SHA256 of each concatenation was:

| Slice | Digest |
|---|---|
| Fifteen source files | `aba077f96ed37e3faafc1e1df7d71043bb8fee1fc3eaad2b5f864b8219adbe9b` |
| Fifteen target files | `87bc8133f83ce42fbdeff9de8caffc9a3d7e17a0017b42d2aab67ddbf2176723` |

**Principle applied.** Prove It Works shaped the audit. I inspected the actual source and target content and ran the package checker, rather than treating author summaries or a structural pass as acceptance evidence.
