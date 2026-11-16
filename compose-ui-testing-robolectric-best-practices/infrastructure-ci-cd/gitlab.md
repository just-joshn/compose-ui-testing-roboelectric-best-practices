# Run local Compose tests in GitLab CI

Use this guide to run Android local-unit-test tasks on merge requests, the default
branch, and scheduled GitLab pipelines. The Compose UI uses a Robolectric activity host.
The lane does not launch an emulator or validate a deployed backend.

## Table of contents

- [Choose a job model](#choose-a-job-model)
- [Provision the runner](#provision-the-runner)
- [Run the basic pipeline](#run-the-basic-pipeline)
- [Publish JUnit and HTML](#publish-junit-and-html)
- [Run checked shards](#run-checked-shards)
- [Add variants and scheduled runs](#add-variants-and-scheduled-runs)
- [Separate service integration](#separate-service-integration)
- [Handle variables and caches](#handle-variables-and-caches)
- [Avoid false-green pipelines](#avoid-false-green-pipelines)
- [Troubleshoot](#troubleshoot)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose a job model

| Need | GitLab mechanism | Android-specific check |
| --- | --- | --- |
| One local suite | One test job | SDK, JDK, resources, host manifest |
| Class partitions | `parallel: N` | Explicit nonempty class lists |
| Independent variants | `parallel:matrix` | Each matrix value maps to a real task |
| Native environment consistency | Docker executor image | Compatible architecture and SDK packages |
| Test dashboard | `artifacts:reports:junit` | Real executed method evidence |
| Browsable HTML | `artifacts:paths` | Upload the whole report directory |
| Wider regression | Scheduled pipeline rules | Do not accidentally exclude scheduled jobs |
| Real server checks | Separate integration job | Readiness, credentials, cleanup, transport assertions |

Examples below are illustrative. They assume a registered runner tagged `android-jvm`
with JDK 17, the project's Android SDK, and a writable workspace.
Use the tag your administrators actually provisioned.
A shell executor ignores Docker `image:` settings. A Docker executor needs a reviewed
Android JVM image such as the one described in [containers](docker.md).

## Provision the runner

For the repository reproduction target, provision Gradle wrapper support, compile SDK
37, and Java 17 for runtime SDK 35. Robolectric 4.18 needs Java 21 for runtime SDKs
36 and 37. Keep worker Java distinct from source bytecode settings.

Verify one hosted test before tuning the pipeline:

```bash
java -version
./gradlew --version
./gradlew :app:testDebugUnitTest --tests 'com.example.ui.HostSmokeTest' \
  --stacktrace --console=plain
```

Replace `app` and the class with your real module and test.
Expect a named test case, not only `BUILD SUCCESSFUL`.
Resources and the declared host must be present in the selected variant.
Do not make `returnDefaultValues` hide an unsupported or missing test environment.

## Run the basic pipeline

This complete illustrative `.gitlab-ci.yml` uses a preprovisioned runner rather than
inventing a public Android image tag:

```yaml
stages:
  - test

workflow:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_PIPELINE_SOURCE == "schedule"'
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'

variables:
  GRADLE_USER_HOME: "$CI_PROJECT_DIR/.gradle-user-home"

local-ui:
  stage: test
  tags: [android-jvm]
  timeout: 25 minutes
  interruptible: true
  cache:
    key:
      files:
        - gradle/wrapper/gradle-wrapper.properties
        - gradle/libs.versions.toml
    paths:
      - .gradle-user-home/caches/
      - .gradle-user-home/wrapper/
    policy: pull
  script:
    - java -version
    - ./gradlew --version
    - ./gradlew :app:testDebugUnitTest --stacktrace --console=plain
  artifacts:
    when: always
    expire_in: 14 days
    reports:
      junit: app/build/test-results/testDebugUnitTest/TEST-*.xml
    paths:
      - app/build/test-results/testDebugUnitTest/
      - app/build/reports/tests/testDebugUnitTest/
```

Replace `gradle/libs.versions.toml` if the project does not use a version catalog.
Choose a real dependency-definition file for the cache key.
Do not create a dummy catalog solely to satisfy the example.

The cache is read-only in this job. Populate it through a trusted default-branch job
under your runner's cache policy if worthwhile. Running without a warm cache remains
correct. Cache availability must not decide which assertions execute.

`interruptible: true` allows configured redundant-pipeline cancellation.
It does not itself configure automatic cancellation for the project.
A cancelled job is incomplete evidence.

## Publish JUnit and HTML

`artifacts:reports:junit` feeds GitLab's test result UI.
It does not run tests or create reports from console text.
`artifacts:paths` preserves files for download, including HTML assets.
Keep both paths aligned with the actual task's output.

A flavor task such as `testDemoDebugUnitTest` uses a different result directory.
Update all report paths with the task rather than globbing unrelated historic outputs.
The job must fail if Gradle fails, even when GitLab successfully ingests XML.

Check the expected methods and skip policy in a repository-specific acceptance step.
A dashboard with no failures can still be missing a class, a shard, or every test.
Fresh checkout isolation prevents a previous job's XML from appearing as current proof.

## Run checked shards

Use the build fragment in [parallel sharding](parallel-sharding.md) first.
It defines `uiTestClassList` and validates a nonempty class list.
GitLab's `parallel` keyword creates jobs. It does not partition Gradle tests for you.

Replace the basic job's test command and report paths with this job pattern.
It assumes `ci/ui-shard-0.txt` and `ci/ui-shard-1.txt` exist and cover the suite:

```yaml
local-ui-shards:
  stage: test
  tags: [android-jvm]
  timeout: 25 minutes
  parallel: 2
  script:
    - SHARD_INDEX=$((CI_NODE_INDEX - 1))
    - >-
      ./gradlew :app:testDebugUnitTest
      -PuiTestClassList=ci/ui-shard-${SHARD_INDEX}.txt
      -PuiTestForks=1 --stacktrace --console=plain
  after_script:
    - mkdir -p "shard-${CI_NODE_INDEX}"
    - cp -R app/build/test-results "shard-${CI_NODE_INDEX}/" 2>/dev/null || true
    - cp -R app/build/reports "shard-${CI_NODE_INDEX}/" 2>/dev/null || true
  artifacts:
    when: always
    name: "local-ui-${CI_COMMIT_SHORT_SHA}-${CI_NODE_INDEX}"
    expire_in: 14 days
    reports:
      junit: shard-*/test-results/testDebugUnitTest/TEST-*.xml
    paths:
      - shard-*/
```

GitLab's `CI_NODE_INDEX` is one-based. The class-list convention here is zero-based.
The subtraction is a filename conversion, not a Robolectric API.
Keep the unsharded job out of the same required lane unless duplicate execution is intended.

The best-effort copies in `after_script` preserve partial evidence after a failure.
They must not wrap or replace the Gradle test command.
Keep the Gradle exit status authoritative. Missing copied files remain an evidence gap.
The unique top-level directory prevents collisions if artifacts from parallel jobs
are downloaded into one report job.

A report collector can use `needs` on the parallel job, but must check all expected
shard directories. Do not claim a combined HTML report by copying several `index.html`
files into one directory. Keep separate reports or use a tested JUnit aggregation tool.

## Add variants and scheduled runs

For a fixed variant matrix, replace the task with a reviewed matrix value:

```yaml
parallel:
  matrix:
    - UNIT_TASK: [testDemoDebugUnitTest, testPaidDebugUnitTest]
script:
  - ./gradlew ":app:${UNIT_TASK}" --stacktrace --console=plain
artifacts:
  when: always
  expire_in: 14 days
  reports:
    junit: app/build/test-results/$UNIT_TASK/TEST-*.xml
  paths:
    - app/build/test-results/$UNIT_TASK/
    - app/build/reports/tests/$UNIT_TASK/
```

This is a job fragment, not a second complete pipeline.
Only use task names that exist in your Android module.
A variant matrix does not override the runtime SDK declared by a test class.

For a scheduled-only full regression job, add a rule:

```yaml
rules:
  - if: '$CI_PIPELINE_SOURCE == "schedule"'
```

Keep the workflow-level schedule rule so the pipeline itself can exist.
Configure the schedule through GitLab's pipeline schedules UI with an explicit branch.
Name the revision and matrix in the regression result.
Do not omit critical behavior from merge requests merely because a nightly suite exists.

## Separate service integration

Most local Compose tests should inject repository or session fakes.
A fake can prove loading, error, and result rendering without a database or service.
Fresh fake instances and deferred completions belong to one test.

If a separate repository integration job needs a containerized backend, pin its image,
use the GitLab service alias rather than `localhost`, and poll a bounded readiness
endpoint. A started service is not necessarily ready for requests.
Use unique data per test or job and clean up only the data that job owns.
Do not add shared production accounts to parallel UI tests.

A local fake test does not prove HTTP, GraphQL, OAuth, or backend authorization.
Keep those claims in the service job's assertions and reports.

## Handle variables and caches

Set nonsecret build controls as CI variables.
Use masked and protected variables for real integration credentials where available.
Protected variables may be unavailable in an untrusted merge request pipeline.
That is a security boundary, not a reason to expose them to every contributor.

Do not log secrets through `set -x`, full environment dumps, or HTTP request bodies.
Do not store credential-bearing `gradle.properties` in cache artifacts.
Use synthetic data in semantics dumps and limit artifact retention.

A pipeline variable does not automatically become a test-worker JVM system property.
Forward only explicit allowlisted values when the test reads system properties.
For ordinary fake-driven behavior, prefer constructor inputs in the test instead.

## Avoid false-green pipelines

Bad:

```yaml
script:
  - ./gradlew :app:testDebugUnitTest || true
allow_failure: true
```

Both mechanisms can let a broken required suite stop blocking the pipeline.
Keep the test command's exit status and publish evidence with `artifacts:when:always`.
Do not retry assertion failures until they disappear.
For runner failures, use a narrowly scoped infrastructure retry policy and retain
attempt identity so the first failure remains diagnosable.

## Troubleshoot

| Symptom | Observe | Fix |
| --- | --- | --- |
| `image:` seems ignored | Runner executor type | Use a Docker executor or provision the shell runner |
| XML missing in MR view | Artifact glob and actual task directory | Align paths and inspect compile failures |
| Zero tests on shard 1 | Index conversion and list contents | Repair the class partition |
| Combined artifacts lose classes | Download directory collisions | Preserve unique shard directories |
| Scheduled pipeline has no test job | Workflow and job rules | Allow the schedule at both levels |
| Tests need unavailable protected variables | Credential use in the local lane | Replace with fakes or move to protected integration |
| CI-only hangs | Fork limits, pending work, leaked globals | Reproduce and fix ownership before increasing timeouts |

## Review checklist

- Runner executor, JDK, and SDK inventory are explicit.
- Merge requests run without privileged credentials.
- JUnit and HTML paths match the selected task.
- Every shard list and actual method inventory is checked.
- Artifact publication cannot mask Gradle failure.
- Scheduled pipelines test a named revision and intended wider set.
- Shared state and external resource names are isolated.

## Related guides and sources

- [CI overview](ci-cd.md), [sharding](parallel-sharding.md), and [reporting](reporting.md).
- [GitLab YAML reference](https://docs.gitlab.com/ci/yaml/).
- [GitLab unit test reports](https://docs.gitlab.com/ci/testing/unit_test_reports/).
- [GitLab predefined variables](https://docs.gitlab.com/ci/variables/predefined_variables/).
- [GitLab cache](https://docs.gitlab.com/ci/caching/).
- [Robolectric configuration](https://robolectric.org/configuring/).
