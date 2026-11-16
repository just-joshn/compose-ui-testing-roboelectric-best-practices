## ISSUES

The goal is a complete, usable Compose and Robolectric adaptation of the pinned Playwright skill. I read all 15 assigned source guides and all 15 mapped targets in full. The adaptations preserve most topic distinctions and avoid false device or service claims. Several important workflows remain instructions to build an example rather than worked examples comparable to the source.

All target paths below are relative to `compose-ui-testing-robolectric-best-practices/`.

### Acceptance findings

| Priority | Location | Proven gap | Minimal correction |
| --- | --- | --- | --- |
| High | `testing-patterns/visual-regression.md:35-55`, `:105-126`, `:180` | The visual-regression guide never captures or compares an image. It deliberately omits the capture call, leaves tooling unspecified, and supplies an environment-variable placeholder instead of an actual verification task. The source supplies screenshot assertions, comparator configuration, verification, recording, and CI commands. The target’s baseline-review guidance is substantive, but readers cannot execute its central workflow. | Add one explicitly optional, version-scoped screenshot integration with dependencies, a capture-and-compare example, actual record and verify tasks, and failure-artifact paths. Keep its rendering limits and unverified status explicit until tested. |
| High | `testing-patterns/repository-contracts.md:35-49`, `:108-132`, `:171-183` | The real HTTP boundary is never demonstrated. The only operation example calls an abstract `ItemRepository`; server creation, client construction, request inspection, authentication, and multipart assertions remain prose or tables. The source demonstrates these mechanisms directly. This loses practical API-testing depth even though the layer selection is correct. | Add one concrete local-server test using a named client stack. Show dependency setup, production-client construction, queued response, execution, recorded method/path/header/body assertions, decoded result, and cleanup. Add a small multipart variation or a concrete linked example. |
| Medium | `testing-patterns/graphql.md:165-187` | The sole executable-looking GraphQL test depends on an undefined `clientHarness.enqueueJson` and undefined repository implementation. Query and mutation examples are wire JSON, not examples of executing a client and inspecting its response. The guide correctly preserves partial data, errors, null propagation, and authorization distinctions, but its client-integration recipe stops before the difficult wiring. | Define one minimal real-client harness or link to a complete concrete example. Demonstrate a query’s recorded variables and authentication, then decode a schema-consistent partial response through the real client and mapper. |
| Medium | `testing-patterns/forms-validation.md:131-195` | Dropdowns, toggles, dates, dependent fields, and wizard progression are described, but none has worked Kotlin action-and-assertion code. The only complete form test enters one text field and clicks submit. The source’s practical value includes actual control interactions and a complete multistep path. The target has coverage plans rather than equivalent worked scenarios for these controls. | Add a compact worked example that selects a dropdown option, toggles a control, asserts resulting state, and advances and returns through a wizard. Include one actual picker selection with unambiguous day identity or a concrete linked picker example. |
| Medium | `testing-patterns/custom-drawing.md:134` and `testing-patterns/gestures.md` | The drawing guide sends readers to `gestures.md` for detailed multi-pointer input construction, but that guide contains only single-pointer construction. Neither guide demonstrates pinch input. The source contains a pinch scenario, so this is both a missing worked scenario and an inaccurate handoff. | Add a two-pointer pinch example with pointer identities, movement, release, and an observable zoom assertion. Alternatively, link to a concrete example that actually supplies those steps. |
| Medium | `testing-patterns/file-operations.md:135-163` | The only complete export-content example writes its own expected CSV bytes and reads them back. It does not execute an exporter or the UI action. The caveat accurately labels the limitation, but the example cannot detect an export regression and does not provide the source’s action-to-artifact workflow. | Replace the inline `writeText` with a small defined exporter or a real application exporter. Show how the action’s destination is injected and inspect bytes produced by that operation. Include quoted-field parsing when claiming general CSV verification. |

These are usability and depth findings. I am not treating the explicitly labeled illustrative fragments as falsely claimed runtime evidence.

### Topics examined

| Source topic | Mapped target | Assessment |
| --- | --- | --- |
| Accessibility | `accessibility.md` | Roles, labels, toggle state, keyboard focus, startup shortcuts, dialog restoration, live regions, contrast, motion, and device handoff examined. No additional proven correctness issue. |
| API testing | `repository-contracts.md` | CRUD, HTTP contracts, authenticated fixtures, decoding, errors, seeding, uploads, chained workflows, and cleanup examined. Concrete transport recipe missing as above. |
| Browser extensions | `system-surfaces.md` | Native notification, widget, tile, shortcut, background-work, permission, persistence, and registration alternatives examined. Native reframing is appropriate. |
| Canvas and WebGL | `custom-drawing.md` | Geometry, semantics, drawing, selection, rendering, simulation, GPU lifecycle, and chart boundaries examined. Pinch recipe missing as above. |
| Component testing | `component-testing.md` | Hosting, theme, controlled state, callbacks, slots, providers, dependency replacement, disposal, and restoration examined. No additional proven correctness issue. |
| Drag and drop | `gestures.md` | Coordinate conversion, long press, incremental movement, membership, order, previews, cancellation, multiselect, resize, accessible alternatives, persistence, and undo examined. Multi-pointer handoff gap noted above. |
| Electron | `host-integration.md` | Activity ownership, launch timing, intent routing, callbacks versus IPC, native features, recreation, multiple windows, and packaged artifacts examined. Reframing is appropriate. |
| File operations | `file-operations.md` | Picker registry, cancellation, URI access, imports, exports, multiple documents, formats, grants, and cleanup examined. Export example weakness noted above. |
| Advanced file transfers | `file-transfers.md` | Progress, unknown totals, cancellation, late completion, retry identity, validation, previews, downloads, authentication, and partial artifacts examined. No additional proven correctness issue. |
| Forms | `forms-validation.md` | Required-field recovery, formatting, control types, debounce, stale responses, dependencies, wizards, pending submission, rejection, and reset examined. Worked-control depth gap noted above. |
| GraphQL | `graphql.md` | Operation identity, variables, mutations, envelopes, error metadata, partial results, nullability, validation, authorization, cache policies, and helper design examined. Contract distinctions are strong; concrete client wiring is missing. |
| Internationalization | `i18n.md` | Resources, independent expected translations, locale switching, persistence, RTL, formatting, plurals, fallback, overflow, fonts, and bidirectional content examined. No additional proven correctness issue. |
| Performance | `performance-testing.md` | Local work counts, loading, Macrobenchmark startup, frames, memory, budgets, baselines, missing metrics, and CI evidence examined. Device-timing separation is correct. |
| Security | `security-testing.md` | Native text versus XSS, link policy, expiry, reset tokens, roles, IDOR, database input, CSRF boundaries, WebView, TLS, exported components, and URI grants examined. No additional proven correctness issue. |
| Visual regression | `visual-regression.md` | Capture scope, deterministic inputs, animations, adaptive layouts, thresholds, CI, and baseline promotion examined. Actual screenshot workflow missing as above. |

### Verification and limits

- Upstream checkout HEAD matches `0b75b5835a87de1fdd202ba965f3bc5a27738fdf`.
- All relative file links in the 15 targets resolve to existing files. This check did not validate heading anchors or external URLs.
- No files were modified. No workers were spawned.
- I did not compile the illustrative snippets or execute device, screenshot, network, or benchmark examples. Their API compatibility remains unverified, not a proven defect.
- The initial shell here-document failed with `Operation not permitted`. This was a sandbox restriction. The read-only checks succeeded using `python3 -c`.
- **Prove It Works** shaped the audit by requiring inspection of actual target contents rather than author summaries or map declarations.

### Slice identities

Both hashes were computed twice and remained unchanged during the audit.

The algorithm sorts slice-relative paths, creates a record of `path + " " + SHA256(file bytes) + "\n"` for each file, concatenates the records, and hashes the UTF-8 concatenation.

```text
Records: 15 source files and 15 target files

Source SHA256:
ae2a4e74ebc581bb817ea25fc494292c3e025308f232dd5079fe39b87bea7594

Target SHA256:
3ff33ed249c8c7c3eb8423b100b8964557d3a5ef3350e87e64b7dce7999d33d8
```
