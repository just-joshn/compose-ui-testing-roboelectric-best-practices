# Run Compose Robolectric tests in CI

Use this guide to establish the local JVM test lane for an Android module.
This lane tests Compose behavior with Robolectric, not an installed application.
Keep device rendering, TalkBack, system UI, and real service checks in separate jobs.

## Table of contents

- [Choose the lane](#choose-the-lane)
- [Establish the build contract](#establish-the-build-contract)
- [Run the first CI job](#run-the-first-ci-job)
- [Partition pull request and scheduled work](#partition-pull-request-and-scheduled-work)
- [Manage environments and secrets](#manage-environments-and-secrets)
- [Cache inputs without hiding failures](#cache-inputs-without-hiding-failures)
- [Add containers and shards](#add-containers-and-shards)
- [Preserve failure evidence](#preserve-failure-evidence)
- [Troubleshoot](#troubleshoot)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the lane

| Claim | CI lane | Inputs |
| --- | --- | --- |
| A user action changes a Compose screen | Android local unit tests with Robolectric | Resources, host manifest, controlled dependencies |
| Repository serialization or HTTP contract works | Repository integration tests | Local server and real client |
| TalkBack traverses controls correctly | Device accessibility tests | Installed application and accessibility service |
| A layout has correct device pixels | Device or dedicated screenshot tests | Explicit renderer and baseline policy |
| Startup or scrolling meets a budget | Android benchmarks | Release-like build and controlled device |
| Multiple runtime SDK models behave correctly | Robolectric SDK matrix | Supported SDK and compatible worker JDK |

Do not replace the first row with `connectedDebugAndroidTest`.
That task belongs to a different test layer and requires a device.
Do not add staging credentials to a UI suite whose dependencies are fakes.

## Establish the build contract

Before adding provider YAML, make one hosted test pass locally.
Inspect the Android module's wrapper, AGP version, test-worker JDK, Compose artifacts,
Robolectric version, and chosen runtime SDK.

The repository's reproduction target uses Gradle 9.4.1, AGP 9.2.0,
JDK 17, Compose UI 1.12.1, and Robolectric 4.18 with runtime SDK 35.
Compile SDK 37 does not mean that the tests run at SDK 37.
Robolectric 4.18 requires Java 21 for runtime SDKs 36 and 37.
Do not upgrade a consuming project just to match this example.

The module needs these pieces before CI can run a meaningful assertion:

- Tests in `src/test`, with `testImplementation` dependencies.
- Android resources enabled for local unit tests.
- A Robolectric-aware JUnit runner.
- An explicit supported runtime SDK.
- A declared activity host, including `ui-test-manifest` when using the default host.
- The version-correct Compose rule factory.

For UI 1.12.1, use `androidx.compose.ui.test.junit4.v2.createComposeRule`.
Do not copy the 1.13-only `ComposeUiTestConfig` into this combination.
See [setup](../references/setup.md) and the [canonical tests](../examples/FixtureUiTest.kt).

These commands illustrate a consuming Android module named `app`:

```bash
./gradlew --version
./gradlew :app:tasks --all
./gradlew :app:testDebugUnitTest --tests 'com.example.ui.HostSmokeTest' \
  --stacktrace --console=plain
```

Expect a completed named test, a JUnit XML file, and an HTML report.
A successful Gradle configuration or `NO-SOURCE` task is not the expected result.
For this repository, substitute `:fixture:testDebugUnitTest` and `fixture.FixtureUiTest`.

## Run the first CI job

The following GitHub Actions example is illustrative.
It assumes an Android SDK on the hosted Ubuntu runner, compile SDK 37 available,
and the reproduction target described above.
Check your selected runner image inventory before adopting it.
The action major versions are explicit. Pin reviewed commit SHAs in a hardened repository.

```yaml
name: Local Compose tests
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
      - name: Run local UI tests
        run: ./gradlew :app:testDebugUnitTest --stacktrace --console=plain
      - uses: actions/upload-artifact@v4
        if: ${{ !cancelled() }}
        with:
          name: local-compose-debug
          retention-days: 14
          path: |
            app/build/test-results/testDebugUnitTest/
            app/build/reports/tests/testDebugUnitTest/
```

A test failure must remain a failed job even when artifact publication succeeds.
An upload warning can indicate failure before any test ran.
Treat the Gradle log as necessary evidence in that case.
See [GitHub Actions](github-actions.md) for matrices and reusable workflows.

## Partition pull request and scheduled work

Choose the partition from risk and measured feedback time, not an arbitrary test count.

| Trigger | Typical work | Required evidence |
| --- | --- | --- |
| Pull request | All fast behavior tests for the selected variant | Named tests and no unexpected skips |
| Main branch | Same lane plus module or variant integration | Distinct reports per variant |
| Scheduled | Additional runtime SDKs, locales, larger regression set | Expected matrix and test inventory |
| Protected manual workflow | Real service or device smoke tests | Credentials, cleanup, and environment identity |

A package filter is a concrete way to select an intentional smoke suite:

```bash
./gradlew :app:testDebugUnitTest --tests 'com.example.smoke.*'
```

Run the unfiltered task in the scheduled lane:

```bash
./gradlew :app:testDebugUnitTest
```

A naming convention is not automatic JUnit tagging.
Document the package's intended coverage and check that every requested class runs.
Do not silently exclude a flaky class. Record its owner, failure evidence,
repair deadline, and the checks that remain required.

## Manage environments and secrets

Construct fresh fakes and mutable state per test.
Do not use the pipeline environment to share a logged-in singleton between methods.
A fake session can test authenticated rendering without a real password.
It does not test OAuth or server authorization.

Keep real integration credentials in provider-managed secrets with minimum permissions.
Do not grant secrets to untrusted pull request code.
Do not echo environment dumps, tokens, or real user data into semantics artifacts.
Separate protected integration jobs from the credential-free local UI lane.

Gradle process environment and test-worker system properties are different channels.
If a test reads a JVM property, explicitly forward an allowlisted value in the build.
Do not assume an arbitrary `-D` on the Gradle command reaches the test worker.
For runtime SDK selection, prefer explicit test configuration or documented Robolectric
properties that the build deliberately forwards.

## Cache inputs without hiding failures

Cache dependency downloads and supported Gradle caches.
Keep the wrapper checksum and dependency verification policy in version control.
Restore caches from trusted contexts and avoid publishing privileged caches from forks.

| Input | Cache policy | What still runs |
| --- | --- | --- |
| Gradle distributions and dependency artifacts | Use a provider's maintained Gradle integration | Dependency resolution and task graph |
| Android SDK packages | Preprovision or install exact packages | SDK availability check |
| Robolectric runtime artifacts | Allow the supported dependency cache to retain downloads | First hosted test for the selected SDK |
| Test reports | Publish as artifacts, not dependency caches | Fresh result validation |
| Module `build/` tree | Do not blindly restore as a shared cache | Gradle's own input-aware mechanisms |

A cache hit is not test evidence.
Gradle may legitimately reuse task outputs under its input model.
For a diagnostic execution that must rerun tests, use `--rerun-tasks` and preserve the log.
Distinguish an executed result from a reused result in any verification report.

## Add containers and shards

Use [containers](docker.md) when the toolchain or native runtime differs across runners.
The image must contain a compatible JDK and Android SDK, not browser binaries.
Do not add a display server or emulator to the local JVM lane without a specific need.

Gradle has no general Playwright-style `--shard=1/4` switch.
Use an explicit class partition, a tested distribution product, or module jobs.
See [parallel execution](parallel-sharding.md) for a checked class-list approach.
Name every artifact with its module, variant, SDK, and shard identity as needed.
Never let two shards overwrite `TEST-ExampleTest.xml` in one destination.

## Preserve failure evidence

Always retain JUnit XML and the entire HTML report directory when available.
Keep the command, source revision, tool versions, runner identity, and shard selection
with the result. Collect a semantics dump at the point of failure when possible.
Robolectric does not produce Playwright traces or automatic action videos.

Do not use `./gradlew ... || true` to reach the upload step.
Use the provider's unconditional publication mechanism instead.
A report parser must reject missing, malformed, stale, empty, or unexpectedly skipped
results rather than convert an infrastructure failure into a green badge.
See [reporting](reporting.md) for the acceptance checklist.

## Troubleshoot

| Symptom | Observe first | Corrective action |
| --- | --- | --- |
| SDK location not found | Runner SDK path and installed platforms | Provision the required compile SDK and set the SDK environment |
| Unsupported runtime SDK | `@Config`, worker Java version, Robolectric version | Select a supported combination |
| Activity cannot launch | Merged manifest and resource inclusion | Restore the host declaration or resources |
| Class passes locally, fails in CI | Full exception, dependencies, worker limits | Reproduce the same task and toolchain before changing timeouts |
| UI assertion times out | Work owner and pending fake | Complete the fake or advance its actual scheduler |
| Green job with no tests | Task outcomes and JUnit methods | Fail the acceptance check and repair selection |
| Report missing after a compiler error | Gradle log before the test task | Fix compilation, do not diagnose semantics |

## Review checklist

- The job runs an Android local-unit-test task.
- The JDK supports the selected runtime SDK.
- The host smoke test executes before broader async tests are trusted.
- Fakes and pending work belong to one test.
- Publication does not suppress the test command's failure.
- Every expected shard and method contributes evidence.
- Device and service claims have separate verification lanes.

## Related guides and sources

- [GitLab](gitlab.md) and [other providers](other-providers.md).
- [Reporting](reporting.md), [coverage](test-coverage.md), and [test speed](performance.md).
- [Android local tests](https://developer.android.com/training/testing/local-tests/robolectric).
- [Robolectric setup](https://robolectric.org/getting-started/) and [compatibility](https://robolectric.org/compatibility_table/).
- [Gradle test filtering](https://docs.gradle.org/9.4.1/userguide/java_testing.html).
- [GitHub workflow syntax](https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions).
