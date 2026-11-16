# Compose Robolectric verification map

The maintained verification surface is the installable Compose UI testing skill and its library fixture, not a standalone mobile app. Read the matching feature recipe before driving. Commands below run from the repository root.

## Baseline preconditions

- Follow Launch in [SKILL.md](../SKILL.md): Python 3.10+, JDK 17, API 37 compile SDK, Build Tools 36.0.0, accepted licenses, and dependency access.
- Save the absolute `RUN` returned at setup. Each shell/tool call must restore that variable.
- Only drive the disposable project created by `verify.py launch`; require `verify.py doctor "$RUN"` to print HEALTHY first.
- Tests create fresh UI/fakes. No auth, data seeding, backend, device, ports, or external delivery service exists.
- Do not run concurrent drivers. Shared SDK/caches are not isolated.
- Current saved-response filenames are `WritingTaskTest.kt`, `ReviewTaskTest.kt`, and `DebuggingTaskTest.kt`.

## Driving conventions

Use `.pi/skills/verify-compose-robolectric/verify.py drive "$RUN" <journey>` with a literal journey from the feature recipe. Use tmux_run for long commands and record its job ID. Each journey can run once per RUN; a repeat needs a new run.

Selectors are real Compose text/test-tag semantics: `Open` scoped to `draft` or `archive`, `Message`, `Send`, `summary`, and `summary-child`. Do not substitute coordinates, node indices, callbacks, or internal delivery setters.

## Proof and skip reporting

Artifacts go to `$RUN/evidence/<journey>/`, with source snapshots and manifest at `$RUN/evidence/`. Preserve commands, exit codes, logs, actual JUnit cases, assertions and mutation failures. Record the feature ID and entry point in `proof.md`. Cleanup removes only the workspace, not these artifacts.

Saved-output replay proves previously authored test behavior. It does not prove fresh model activation, reference routing, unaided discovery, or an actual skills-CLI installation. Report those separately. Do not count compilation, NO-SOURCE, skipped tests, or setup errors as behavioral success.

## Feature entry contract

Each entry uses the four H2s below: Sub-features; How to get to it (user POV); Driving it with Python/Gradle; Gotchas. List every known entry, including one that lacks an executable journey. Missing preconditions are reported, never removed from a journey to make it pass.

## Features

- [Package portability and setup](package.md): copied installation structure, malformed-package rejection, hosted test setup.
- [Write a test](writing.md): scoped duplicate-label action, wrong-target negative control, fresh-agent contract.
- [Review a test](review.md): correct target, observable delivery, no-op negative control, fresh-agent contract.
- [Debug a missing node](debugging.md): merged/unmerged diagnosis and label regression detection.
- [Exercise the Compose examples](fixture.md): summary semantics, Draft/Archive actions, sending, delay ownership, disposal, and diagnostic/effect probes.
