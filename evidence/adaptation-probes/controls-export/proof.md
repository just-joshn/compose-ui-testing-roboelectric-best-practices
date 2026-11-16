# Focused controls and export proof

Goal. Replace missing worked form and pinch interactions and tautological CSV output checks in four owned adaptation guides.

The three new complete Kotlin examples were extracted verbatim from the guides into a private copy of the existing fixture configuration. Gradle and Maven caches were cloned into this worker's private temporary directory. No shared fixture, build configuration, or cache was changed. The ordinary verification helper does not accept extra guide snippets, so this is supplemental example verification rather than certification of the full skill or canonical fixture.

## Entry points and outcomes

- BookingControlsTest.selectionsSurviveBackAndReachBookingCallback opens the room dropdown, selects Suite, toggles breakfast, opens a fixed June calendar, selects the full-date identity 2026-06-15, progresses to review, goes back, checks retained selections, and confirms. It asserts the visible completion and the submitted BookingDraft.
- PinchZoomTest.pinchOutChangesDisplayedZoom injects pointer IDs 0 and 1 through a real transformable canvas, updates both positions before each move, releases both, and asserts the visible percentage exceeds 125.
- PinchZoomTest.cancellationRetainsLiveZoomAndAllowsAnotherGesture cancels an actual multi-pointer sequence, asserts retained live zoom, starts another pinch, and verifies an additional visible zoom change. Both tests have finally-based pointer cleanup.
- CsvExportOperationTest invokes the defined ContactCsvExporter with Contact input and an injected fresh destination. It checks exact UTF-8 bytes, record order, empty fields, an empty export header, and rejection of unsupported delimiters before opening the output.

The baseline and restored runs each executed six tests with zero failures, errors, or skipped tests. Each command and JUnit case is recorded in results.json. The restored source matches the current guides' extracted snippets exactly.

## Negative controls

- Replacing the room-selection update with Unit caused the booking test to fail with AssertionError.
- Replacing zoom updates with an unchanged factor caused both pinch tests to fail with AssertionError.
- Omitting contact rows while retaining the CSV header caused the produced-bytes test to fail with ArrayComparisonFailure.

These were assertion failures after successful compilation, not setup failures. Mutated source files and JUnit XML are retained. All original snippet sources were restored before the final six-test pass.

## Version evidence

Tests used the existing fixture's pinned Compose 1.12.1 artifacts, Robolectric 4.18, JDK 17, and runtime API 35. The private build used offline Gradle dependency resolution. TouchInjectionScope and TransformableStateKt signatures were also inspected with javap against the cached official 1.12.1 AARs. The snippet uses the four-parameter centroid-aware rememberTransformableState overload, while intentionally ignoring centroid, pan, and rotation for this centered-circle zoom contract.

## Limits

The calendar is a deliberately limited, real June 2026 picker, not a Material DatePicker integration. The booking callback is in memory. The CSV contract rejects commas, quotes, and newlines rather than claiming general CSV support. Operation tests do not establish Export button wiring or provider grants. Local touch tests establish recognition and visible state, not pixels, device multitouch fidelity, GPU behavior, or performance.

The Android metrics warning about read-only ~/.android/analytics.settings is a sandbox permission observation. It did not prevent compilation or test execution. Robolectric warnings about API 36 and 37 requiring Java 21 do not apply to the explicitly selected API 35 cases.

Final guide copies and SHA-256 hashes are retained in guides/ and guide-hashes.json. Non-code gesture introduction, decision-table, and checklist wording was updated after the baseline snapshot. Exact snippet identity was checked again after the restored run. All owned local links and heading fragments passed a separate filesystem and heading check.
