# Run local Compose tests on Jenkins, CircleCI, and Azure

Use this guide when the CI provider is not GitHub Actions or GitLab.
The shared contract is an Android local-unit-test task, a compatible Java worker,
Android SDK packages, and retained JUnit evidence.
The provider does not change Compose synchronization or Robolectric's limits.

## Table of contents

- [Choose provider mechanisms](#choose-provider-mechanisms)
- [Establish the shared command](#establish-the-shared-command)
- [Configure Jenkins](#configure-jenkins)
- [Configure CircleCI](#configure-circleci)
- [Configure Azure Pipelines](#configure-azure-pipelines)
- [Partition tests across jobs](#partition-tests-across-jobs)
- [Preserve result identity](#preserve-result-identity)
- [Handle secrets and isolation](#handle-secrets-and-isolation)
- [Avoid false-green jobs](#avoid-false-green-jobs)
- [Troubleshoot](#troubleshoot)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose provider mechanisms

| Concern | Jenkins | CircleCI | Azure Pipelines |
| --- | --- | --- | --- |
| Provisioned Android worker | Node label | Self-hosted resource class or Android image | Agent pool or hosted image |
| Test command | `sh` | `run` | `bash` |
| Native JUnit display | `junit` step | `store_test_results` | `PublishTestResults@2` |
| HTML archive | `archiveArtifacts` | `store_artifacts` | `PublishPipelineArtifact@1` |
| Shards | Parallel stages | `parallelism` and node variables | Matrix variables |
| Secrets | Credentials binding | Context or project variables | Secret variables or variable groups |
| Timeout | Pipeline `timeout` | Job and run-step limits | `timeoutInMinutes` |

Examples are illustrative configurations, not evidence of hosted execution.
Replace administrator-owned worker labels and resource classes with actual values.
Do not invent a public container image tag for an Android SDK toolchain.

## Establish the shared command

These examples assume an Android module named `app`, a debug variant, and tests in
`src/test`. Resolve dependencies and validate the host before creating provider YAML.

```bash
java -version
./gradlew --version
./gradlew :app:testDebugUnitTest --stacktrace --console=plain
```

Expected outputs are:

```text
app/build/test-results/testDebugUnitTest/TEST-*.xml
app/build/reports/tests/testDebugUnitTest/index.html
```

A compiler failure may produce neither. Preserve its console exception.
Check the actual named methods rather than accepting `NO-SOURCE` or an empty dashboard.

For the reproduction target, runtime SDK 35 with Robolectric 4.18 uses Java 17.
Runtime SDKs 36 and 37 need Java 21. The compile SDK is a separate Android SDK package.
A Java setup step does not install the Android SDK.

## Configure Jenkins

This declarative `Jenkinsfile` assumes an administrator-provisioned node labeled
`android-jvm`, a compatible JDK and SDK on its path, and the JUnit plugin installed.
Use a clean workspace for each revision. Do not reuse old XML as current evidence.

```groovy
pipeline {
    agent { label 'android-jvm' }
    options {
        timeout(time: 25, unit: 'MINUTES')
        disableConcurrentBuilds()
        skipDefaultCheckout(true)
    }
    environment {
        GRADLE_USER_HOME = "${WORKSPACE}/.gradle-user-home"
    }
    stages {
        stage('Checkout') {
            steps {
                deleteDir()
                checkout scm
            }
        }
        stage('Local UI tests') {
            steps {
                sh 'java -version'
                sh './gradlew --version'
                sh './gradlew :app:testDebugUnitTest --stacktrace --console=plain'
            }
            post {
                always {
                    junit testResults: 'app/build/test-results/testDebugUnitTest/TEST-*.xml',
                          allowEmptyResults: false
                    archiveArtifacts artifacts: 'app/build/reports/tests/testDebugUnitTest/**',
                                     allowEmptyArchive: true
                }
            }
        }
    }
}
```

`deleteDir()` clears this job's allocated workspace before checkout.
Do not point the job workspace at a shared developer checkout or persistent data directory.
This is an example configuration, not a command to clean an existing workspace now.
Set build and artifact retention in the job policy.

`allowEmptyResults: false` rejects a run with no XML.
It does not detect a partially missing class set or stale report in a dirty workspace.
The shell failure remains authoritative even if Jenkins marks JUnit failures unstable.
Do not publish only a successful archive stage as the required status.

For Docker agents, use the reviewed Android JVM image contract in [containers](docker.md).
Do not set `args '-u root'` as a generic repair for permissions.
Provision a writable workspace and cache for the intended user.

## Configure CircleCI

This `.circleci/config.yml` assumes a configured self-hosted machine resource class
`your-namespace/android-jvm`. Replace it with the actual administrator-created class.
It must provide Java, Android SDK packages, Git, and a writable home.
A managed Android image is another option when its version and inventory match your build.

```yaml
version: 2.1
jobs:
  local-ui:
    machine: true
    resource_class: your-namespace/android-jvm
    working_directory: ~/project
    steps:
      - checkout
      - run:
          name: Inspect Java and Gradle
          command: |
            java -version
            ./gradlew --version
      - run:
          name: Run Android local tests
          no_output_timeout: 15m
          command: ./gradlew :app:testDebugUnitTest --stacktrace --console=plain
      - store_test_results:
          path: app/build/test-results/testDebugUnitTest
      - store_artifacts:
          path: app/build/reports/tests/testDebugUnitTest
          destination: local-ui-html
workflows:
  local-ui:
    jobs:
      - local-ui
```

Store the result directory, not a path to a nonexistent merged `junit.xml`.
CircleCI result ingestion and artifacts serve different purposes.
Keep the HTML assets together.
Check that failed run steps still reach the platform's result-publication behavior
in your executor and cancellation policy.
Hard termination can prevent uploads. Such a run is incomplete evidence.

Cache dependency downloads with a key based on real wrapper and dependency-definition
files if setup dominates. Do not cache the whole checkout's result directories.
If using an orb to provision Java or Android, pin a reviewed orb version rather than
`latest`. Avoid adding an orb when the runner already supplies the required toolchain.

## Configure Azure Pipelines

This `azure-pipelines.yml` assumes a self-hosted pool named `AndroidJvm` with the
required Java and SDK installed. Replace it with your configured pool.
A Microsoft-hosted image is usable after checking its current SDK inventory.

```yaml
trigger:
  branches:
    include: [main]
pr:
  branches:
    include: [main]
pool:
  name: AndroidJvm
jobs:
  - job: LocalUi
    timeoutInMinutes: 25
    workspace:
      clean: all
    steps:
      - checkout: self
        clean: true
      - bash: |
          java -version
          ./gradlew --version
        displayName: Inspect toolchain
      - bash: ./gradlew :app:testDebugUnitTest --stacktrace --console=plain
        displayName: Run Android local tests
      - task: PublishTestResults@2
        condition: always()
        inputs:
          testResultsFormat: JUnit
          testResultsFiles: app/build/test-results/testDebugUnitTest/TEST-*.xml
          failTaskOnFailedTests: true
          failTaskOnMissingResultsFile: true
          testRunTitle: Compose local debug
      - task: PublishPipelineArtifact@1
        condition: always()
        inputs:
          targetPath: app/build/reports/tests/testDebugUnitTest
          artifact: local-ui-debug-html
```

If reports never exist because compilation failed, the artifact task can also fail.
Keep the earlier Gradle failure visible and diagnose that first.
Do not create a fake passing XML file to satisfy publication.
Azure Repos Git uses branch policies for PR validation rather than the YAML `pr`
trigger used by supported external repository types. Configure the repository's
actual validation mechanism.

## Partition tests across jobs

First implement the checked class-list build fragment from
[parallel sharding](parallel-sharding.md). The following property is project-defined:

```bash
./gradlew :app:testDebugUnitTest \
  -PuiTestClassList=ci/ui-shard-0.txt -PuiTestForks=1
```

Provider parallel jobs alone run duplicate suites unless the command selects a partition.
Use the provider's index to select a reviewed list.

For CircleCI, set `parallelism: 2` and use its zero-based node index directly:

```yaml
- run:
    name: Run selected classes
    command: >-
      ./gradlew :app:testDebugUnitTest
      -PuiTestClassList=ci/ui-shard-${CIRCLE_NODE_INDEX}.txt
      -PuiTestForks=1 --stacktrace --console=plain
```

Check that `CIRCLE_NODE_TOTAL` matches the list count.
Unlike Playwright, this convention does not need a one-based conversion.
The partition belongs to your build, not CircleCI's test splitter.
A timing-based CircleCI splitter needs its own tested class-name mapping before use.

For Azure, define a fixed matrix under the job:

```yaml
strategy:
  matrix:
    shard0:
      CLASS_LIST: ci/ui-shard-0.txt
      ARTIFACT_LABEL: shard-0
    shard1:
      CLASS_LIST: ci/ui-shard-1.txt
      ARTIFACT_LABEL: shard-1
```

Run the property with `-PuiTestClassList=$(CLASS_LIST)` and include
`$(ARTIFACT_LABEL)` in artifact names and `testRunTitle`.
Use only fixed reviewed matrix values in shell commands.

For Jenkins, use parallel stages with distinct allocated workspaces or separate agents.
Check out the same revision in each workspace and run a different class list.
Do not run two Gradle invocations concurrently against one module's `build/` directory.
Archive each stage under its own shard identity.

After all jobs finish, compare the actual method union with the unsharded inventory.
Reject missing shards, duplicate methods, unexpected skips, and empty lists.
Balance by observed class duration, not only method count.

## Preserve result identity

Record source revision, module, variant, runtime SDK, shard, and attempt when relevant.
Do not flatten files named `TEST-com.example.UiTest.xml` across those dimensions.
Publish separate HTML reports or a tested aggregate, not a directory assembled by
overwriting multiple `index.html` files.

JUnit dashboards do not validate the whole acceptance contract for you.
The process must exit successfully, the intended methods must execute, and the files
must belong to the current run. See [reporting](reporting.md).

## Handle secrets and isolation

The local fake-driven suite normally needs no staging password or token.
Use provider-managed credentials only in separate real integration lanes.
Restrict secret exposure for untrusted contributions and artifact access for sensitive data.
Do not cache user credential files or emit full environment dumps.

Create fresh fakes, pending completions, state, temporary files, and test-owned scopes
per test. Close local servers and executors after failures.
Use allocated ports and unique external data names across workers.
A separate CI machine does not isolate a shared backend account.

For synchronization, complete the fake that owns external work or advance its actual
scheduler. A slower runner does not justify sleeping before every assertion.
Compose clock advancement does not advance wall clock or arbitrary network work.

## Avoid false-green jobs

| Anti-pattern | Failure mechanism | Correct approach |
| --- | --- | --- |
| `allowEmptyResults: true` everywhere | No-test runs look acceptable | Reject missing results in required suites |
| Shell `|| true` around Gradle | Compilation and assertion failures disappear | Unconditional publication after an ordinary failed command |
| Parallel jobs with no partition | Duplicate cost, no shorter critical path | Explicit complete class lists |
| Shared writable workspace | Competing tasks overwrite outputs | Separate workspaces or agents |
| Retry until green | First failure vanishes from the decision | Preserve attempts and fix the cause |
| Cache entire `build/` without input tracking | Stale reports can be uploaded | Cache dependencies through supported mechanisms |

## Troubleshoot

| Symptom | First observation | Fix |
| --- | --- | --- |
| Jenkins cannot find `junit` | Installed pipeline plugins | Install and configure the supported JUnit plugin |
| CircleCI resource class unavailable | Organization runner registration | Use the real registered class or reviewed managed executor |
| Azure reports show no tests | Task output path and publish glob | Align the selected task and reject missing results |
| Java class-file mismatch | Actual worker JVM, not only compiler target | Select the JDK required by the runtime SDK |
| Shards all contain the same methods | Actual class-list property wiring | Add tested filtering before increasing parallelism |
| Worker hangs after tests | Leaked servers, executors, scopes | Close owned resources in cleanup |
| Reports missing after timeout | Job cancellation and upload timing | Preserve logs and treat the run as incomplete |

## Review checklist

- The worker's JDK and SDK are provisioned rather than assumed.
- The command targets local tests and preserves nonzero exits.
- Native JUnit publication rejects missing results.
- HTML assets and shard identities remain intact.
- Every shard runs a checked partition in a separate workspace.
- Secrets remain outside the local fake-driven lane.
- Actual method inventory, not dashboard color, determines completeness.

## Related guides and sources

- [CI overview](ci-cd.md), [containers](docker.md), and [reporting](reporting.md).
- [Jenkins pipeline syntax](https://www.jenkins.io/doc/book/pipeline/syntax/).
- [Jenkins JUnit step](https://www.jenkins.io/doc/pipeline/steps/junit/).
- [CircleCI configuration](https://circleci.com/docs/configuration-reference/).
- [CircleCI test data](https://circleci.com/docs/collect-test-data/).
- [Azure test result task](https://learn.microsoft.com/en-us/azure/devops/pipelines/tasks/reference/publish-test-results-v2).
- [Azure repository triggers](https://learn.microsoft.com/en-us/azure/devops/pipelines/repos/azure-repos-git).
