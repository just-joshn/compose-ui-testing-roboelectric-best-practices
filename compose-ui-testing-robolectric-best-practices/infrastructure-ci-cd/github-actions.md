# Run local Compose tests on GitHub Actions

Use this guide for pull request, main branch, scheduled, and reusable GitHub workflows.
The tests run inside Android Gradle local-unit-test tasks with Robolectric.
They do not require an emulator, browser installation, or display server.

## Table of contents

- [Choose a workflow](#choose-a-workflow)
- [Run a single job](#run-a-single-job)
- [Run shards without losing reports](#run-shards-without-losing-reports)
- [Separate variants and SDKs](#separate-variants-and-sdks)
- [Schedule wider regression](#schedule-wider-regression)
- [Extract a reusable workflow](#extract-a-reusable-workflow)
- [Protect secrets and cache writes](#protect-secrets-and-cache-writes)
- [Use a container when needed](#use-a-container-when-needed)
- [Avoid false-green workflows](#avoid-false-green-workflows)
- [Troubleshoot](#troubleshoot)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose a workflow

| Situation | Workflow | Check before adopting |
| --- | --- | --- |
| Small or new suite | One local-unit-test job | Named tests actually execute |
| Execution dominates setup | Class shards or independent modules | Complete, disjoint partition |
| Several product variants | Task matrix | Host and resources for each variant |
| Framework-dependent behavior | Runtime SDK matrix | JDK supports every selected SDK |
| Wider regression exceeds PR budget | Scheduled lane | PR lane still covers critical behavior |
| Multiple repositories share setup | `workflow_call` | Inputs do not become arbitrary shell commands |
| Native environment differs | Reviewed Android JVM container | Architecture and SDK inventory |

The examples are illustrative, not executed provider configurations.
They use `app`, debug local tests, JDK 17, and runtime SDK 35.
The host and resource setup must already pass locally.
Action major versions are explicit for readability. Pin reviewed action commits for
repositories that require immutable dependencies.

## Run a single job

Create `.github/workflows/compose-local.yml` in a consuming repository:

```yaml
name: Compose local
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: read
concurrency:
  group: compose-local-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
jobs:
  test:
    runs-on: ubuntu-24.04
    timeout-minutes: 25
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '17'
      - uses: gradle/actions/setup-gradle@v4
        with:
          cache-read-only: ${{ github.ref != 'refs/heads/main' }}
      - name: Inspect toolchain
        run: |
          java -version
          ./gradlew --version
      - name: Run Android local unit tests
        run: ./gradlew :app:testDebugUnitTest --stacktrace --console=plain
      - name: Preserve reports
        uses: actions/upload-artifact@v4
        if: ${{ !cancelled() }}
        with:
          name: compose-local-debug
          retention-days: 14
          path: |
            app/build/test-results/testDebugUnitTest/
            app/build/reports/tests/testDebugUnitTest/
```

The hosted image must contain the project's compile SDK and build tools.
If it does not, install those exact SDK packages using your reviewed provisioning
step before Gradle runs. A Java setup action does not install Android SDK packages.
Do not generate `local.properties` with a developer machine's absolute SDK path.

The expected result is a completed `testDebugUnitTest` task and matching JUnit XML.
An upload is not a result validator. Add your repository's inventory check when the
workflow must prove a bounded set of methods executed.

## Run shards without losing reports

Use the `uiTestClassList` and `uiTestForks` build properties defined in
[parallel sharding](parallel-sharding.md). They are not standard Gradle properties.
Replace the single job's `strategy`, test command, and artifact name with:

```yaml
strategy:
  fail-fast: false
  matrix:
    shard: [0, 1]
```

```yaml
- name: Run selected classes
  run: >-
    ./gradlew :app:testDebugUnitTest
    -PuiTestClassList=ci/ui-shard-${{ matrix.shard }}.txt
    -PuiTestForks=1 --stacktrace --console=plain
- uses: actions/upload-artifact@v4
  if: ${{ !cancelled() }}
  with:
    name: compose-debug-shard-${{ matrix.shard }}
    retention-days: 14
    path: |
      app/build/test-results/testDebugUnitTest/
      app/build/reports/tests/testDebugUnitTest/
```

Keep `fail-fast: false` so one assertion failure does not cancel evidence from other
shards. Cancellation of an obsolete entire workflow is still useful for PR feedback.
A cancelled run is incomplete, not a passing regression run.

A collector job can retain the separate shard directories:

```yaml
collect:
  needs: test
  if: ${{ !cancelled() }}
  runs-on: ubuntu-24.04
  timeout-minutes: 5
  steps:
    - uses: actions/download-artifact@v4
      with:
        pattern: compose-debug-shard-*
        path: collected
        merge-multiple: false
    - uses: actions/upload-artifact@v4
      with:
        name: compose-debug-collected
        path: collected/
        retention-days: 14
```

This collector archives results. It does not merge HTML, validate method coverage,
or turn a failed test matrix green. Keep the original `test` job required.
A true acceptance job must verify every expected artifact and JUnit identity.
Do not flatten XML files with identical filenames into one directory.

## Separate variants and SDKs

A variant matrix selects Gradle tasks, not Android runtime SDKs:

```yaml
strategy:
  fail-fast: false
  matrix:
    include:
      - task: testDemoDebugUnitTest
        label: demo-debug
      - task: testPaidDebugUnitTest
        label: paid-debug
```

Use `./gradlew :app:${{ matrix.task }}` only with fixed reviewed matrix values.
Publish `app/build/test-results/${{ matrix.task }}/` under a name containing the label.
Do not accept arbitrary task text from a PR title or issue body.

For SDK variation, use Robolectric's explicit test configuration or an intentionally
forwarded configuration property. A matrix `env` entry alone does not override
`@Config(sdk = [35])` in a class.
See [annotations](../core/annotations.md) for configuration ownership.

Robolectric 4.18 documents Java 17 for runtime SDK 35 and Java 21 for 36 and 37.
A Java 17 bytecode target does not choose the test-worker JVM.
Keep the runtime SDK in the artifact identity when one class runs at multiple SDKs.

## Schedule wider regression

Add these triggers to a separate full-suite workflow, using the single-job setup:

```yaml
on:
  schedule:
    - cron: '0 3 * * 1-5'
  workflow_dispatch:
```

Run the unfiltered local-unit-test task or the explicit wider matrix there.
Schedules run in the repository's default branch context and may start later than
the requested time. Do not use a nightly job as proof that a pending PR revision passed.

Keep notifications separate from the test command's exit status.
Include the actual run link and failed job identity.
Do not install an unpinned notification action or send test data to a public endpoint.

## Extract a reusable workflow

Prefer a fixed test command over a free-form shell input.
This illustrative reusable workflow varies only the Java version and keeps the
module and task under repository control:

```yaml
name: Reusable local UI tests
on:
  workflow_call:
    inputs:
      java-version:
        type: string
        default: '17'
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-24.04
    timeout-minutes: 25
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: ${{ inputs.java-version }}
      - uses: gradle/actions/setup-gradle@v4
      - run: ./gradlew :app:testDebugUnitTest --stacktrace --console=plain
      - uses: actions/upload-artifact@v4
        if: ${{ !cancelled() }}
        with:
          name: reusable-local-ui
          path: app/build/test-results/testDebugUnitTest/
          retention-days: 14
```

Call it from a workflow with the desired triggers:

```yaml
jobs:
  local-ui:
    uses: ./.github/workflows/reusable-local-ui.yml
    with:
      java-version: '17'
```

If callers invoke it several times, add a constrained artifact label input to avoid
name collisions. Do not inherit all secrets for a credential-free test lane.
For cross-repository reuse, pin the reusable workflow revision and review its permissions.

## Protect secrets and cache writes

Use `pull_request` for tests of untrusted contributions.
Do not use `pull_request_target` to check out and execute untrusted PR code with
write permissions or repository secrets.
The wrapper, build plugins, dependency scripts, and tests all execute code.

The local fake-driven lane normally needs no credentials.
Keep real integration credentials in a protected environment and separate workflow.
Do not upload Gradle credential files or dump all environment variables.
Semantics dumps can also contain sensitive data. Use synthetic accounts and payloads.

Use one maintained Gradle cache integration rather than overlapping cache actions
for the same directories. Avoid manual caches of whole module build directories.
A cache hit does not establish that the test methods ran at this revision.

## Use a container when needed

A container job needs an Android JVM image containing compatible Java and SDK tools.
Use the [container guide](docker.md) to build and publish a reviewed immutable image.
Do not substitute a Playwright image or assume a JDK-only image has `android.jar`.
Test non-root workspace and cache permissions with the selected Actions runner.
A container digest does not pin dependencies downloaded later by Gradle.

## Avoid false-green workflows

Bad:

```yaml
- run: ./gradlew :app:testDebugUnitTest || true
```

This reports success even when no UI assertion ran.
Keep the command unmodified and publish reports with `if: ${{ !cancelled() }}`.

Do not use `continue-on-error: true` for a required behavior lane.
Do not mark only the collector required while ignoring the failed matrix.
Do not add retries to conceal a hanging fake or shared singleton.
Retain first-attempt evidence when a separate diagnostic retry is justified.

## Troubleshoot

| Symptom | Inspect | Repair |
| --- | --- | --- |
| SDK package missing | Runner image inventory and SDK root | Provision the exact package |
| Worker Java differs from setup | Toolchain selection in Gradle output | Align the test launcher with the SDK requirement |
| No artifacts | Compilation or host setup failure before XML | Preserve logs and fix the first failure |
| Collector runs but matrix is red | Original shard outcomes | Keep failure visible, use collection only for evidence |
| Upload name collision | Matrix artifact names | Include shard, variant, and SDK |
| No PR annotations | Only raw JUnit artifacts were uploaded | Add a reviewed JUnit publisher with minimum permissions if needed |
| Test hangs only in CI | Fork count, memory, work owner | Reduce contention and fix synchronization, not global sleeps |

## Review checklist

- The workflow uses a fixed local-unit-test task and supported JDK.
- Untrusted code cannot access privileged secrets or writable caches.
- Every matrix dimension appears in report identity.
- Failed shards remain required failures after collection.
- Artifacts survive ordinary test failures with bounded retention.
- The scheduled lane names the revision it actually tested.
- Reusable workflows do not accept arbitrary shell commands.

## Related guides and sources

- [CI overview](ci-cd.md), [GitLab](gitlab.md), and [reporting](reporting.md).
- [Workflow syntax](https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions).
- [Workflow reuse](https://docs.github.com/en/actions/sharing-automations/reusing-workflows).
- [Gradle setup action](https://github.com/gradle/actions/tree/main/setup-gradle).
- [Artifact upload action](https://github.com/actions/upload-artifact).
- [Robolectric compatibility](https://robolectric.org/compatibility_table/).
