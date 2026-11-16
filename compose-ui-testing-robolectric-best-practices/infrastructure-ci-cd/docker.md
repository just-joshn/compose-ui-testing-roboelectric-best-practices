# Run Android JVM UI tests in containers

Use this guide when a container helps reproduce the JDK, Android SDK, or native
runtime used by local Compose tests. Robolectric runs on the JVM inside the container.
An Android emulator and browser binaries are not required for this lane.

## Table of contents

- [Choose a container strategy](#choose-a-container-strategy)
- [Define the image contract](#define-the-image-contract)
- [Build a project test image](#build-a-project-test-image)
- [Run and retain reports](#run-and-retain-reports)
- [Use a development bind mount](#use-a-development-bind-mount)
- [Use Compose for the test runner](#use-compose-for-the-test-runner)
- [Separate real service dependencies](#separate-real-service-dependencies)
- [Use the image in CI and development](#use-the-image-in-ci-and-development)
- [Keep state and credentials out](#keep-state-and-credentials-out)
- [Avoid browser-container assumptions](#avoid-browser-container-assumptions)
- [Troubleshoot](#troubleshoot)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose a container strategy

| Situation | Approach | Tradeoff |
| --- | --- | --- |
| Hosted runner already has the right SDK | Run Gradle directly | Fewer image maintenance tasks |
| Repeated SDK provisioning costs time | Organization-owned Android JVM base | Own image updates and license policy |
| Need exact source and toolchain reproduction | Copy checkout into a test image | Rebuild source layer on changes |
| Interactive local edits | Bind mount source with matching UID | Host filesystem and build-output costs |
| Need real backend integration | Separate service job or Compose stack | Readiness and data isolation required |
| Need real Android system behavior | Device lane outside this image | Containerized JVM is not a device |

Do not choose a Playwright image because the upstream guide uses one.
Do not claim a universal official Compose Robolectric image exists.
Use an image whose Java, Android SDK packages, libc, and CPU architecture you control.

## Define the image contract

The examples use an organization-provided `ANDROID_JVM_IMAGE` build argument.
Set it to a reviewed immutable digest in your registry before running the commands.
No registry name or digest below is presented as a published artifact.

For the repository reproduction target, the base image contract is:

- Linux with native libraries needed by the selected Robolectric rendering path.
- A compatible JDK, Java 17 for runtime SDK 35 with Robolectric 4.18.
- Android SDK platform 37 and the build tools required by the consuming build.
- `ANDROID_HOME` pointing to the readable SDK installation.
- SDK licenses accepted according to your organization's policy.
- `bash`, `git`, `unzip`, and certificate authorities for wrapper and dependency access.
- A non-root user named `tester` with UID and GID 1000.
- Writable `/home/tester` and permission to read and execute the SDK tools.

SDKs 36 and 37 as Robolectric runtime targets require Java 21 in 4.18.
Compile SDK and runtime SDK are separate choices.
Pin Android command-line tools by their downloaded version and verified checksum in
the base-image build. Do not fetch an unversioned archive during every test run.

This guide does not supply an unverified SDK bootstrap Dockerfile.
Validate the base through one hosted test and record its installed package inventory.
A JDK-only base is insufficient for an Android Gradle module.

## Build a project test image

These are illustrative consuming-project files, not installed skill files.
They assume the base-image contract above and an Android module named `app`.
The image is a test runner, not a production application runtime.
A multi-stage slim application image would not help when Gradle and the SDK are needed
at test execution time.

Create `.dockerignore` before building:

```text
.git
.idea
.gradle
.gradle-user-home
.container-home
container-results
**/build
local.properties
**/local.properties
.env
.env.*
**/*.jks
**/*.keystore
**/credentials.properties
**/secrets.properties
```

Keep project `gradle.properties` only if it contains nonsecret build settings.
Do not copy user-home Gradle credentials into the context.
Review the complete context for custom secret paths before using `COPY . .`.

Create `Dockerfile`:

```dockerfile
# syntax=docker/dockerfile:1
ARG ANDROID_JVM_IMAGE
FROM ${ANDROID_JVM_IMAGE} AS tests
WORKDIR /workspace
USER root
RUN mkdir -p /workspace /home/tester/.gradle \
    && chown -R 1000:1000 /workspace /home/tester/.gradle
COPY --chown=1000:1000 . .
USER tester
ENV HOME=/home/tester
ENV GRADLE_USER_HOME=/home/tester/.gradle
RUN chmod +x ./gradlew
CMD ["./gradlew", ":app:testDebugUnitTest", "--stacktrace", "--console=plain"]
```

Use the Gradle wrapper committed by the project.
Do not install an unrelated global Gradle version in the image.
Do not run the tests in a Dockerfile `RUN` step when a failure would prevent the image
from being created and make its reports harder to retrieve.

Build after setting the real immutable base reference:

```bash
: "${ANDROID_JVM_IMAGE:?Set a reviewed Android JVM image digest}"
docker build --build-arg ANDROID_JVM_IMAGE="$ANDROID_JVM_IMAGE" \
  -t local-compose-tests:dev .
```

The `dev` tag names this locally built source snapshot. It is not an immutable release
reference. Publish and use the resulting digest for shared CI jobs.
The base digest does not lock Maven dependencies fetched by Gradle later.
Use dependency verification and locking where the consuming build supports them.

## Run and retain reports

Precreate host report directories with permissions matching UID 1000.
On a Linux host whose current user has UID 1000, this example retains outputs directly:

```bash
mkdir -p container-results/xml container-results/html
docker run --rm \
  --mount type=bind,src="$PWD/container-results/xml",dst=/workspace/app/build/test-results \
  --mount type=bind,src="$PWD/container-results/html",dst=/workspace/app/build/reports/tests \
  local-compose-tests:dev
```

The ephemeral container and its unmounted writable layer disappear after execution.
The bind-mounted reports remain on the host.
The process exit status is the Gradle test command's status.
Do not append `|| true` in CI to force artifact collection.
Use the CI provider's unconditional upload step instead.

After a successful debug run, expect XML under
`container-results/xml/testDebugUnitTest/` and HTML under
`container-results/html/testDebugUnitTest/`.
If the build fails before the test task, preserve its console log because XML may not exist.

For persistent dependency downloads, use a dedicated cache mount with verified
ownership. Do not share a writable Gradle user home between concurrently running
containers without understanding Gradle's locking and filesystem support.
A per-job cache or a provider-managed cache is safer than a global writable volume.

## Use a development bind mount

A bind mount over `/workspace` hides the source copied into the image.
Use this only when you deliberately want to run the current host checkout:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env HOME=/workspace/.container-home \
  --env GRADLE_USER_HOME=/workspace/.container-home/gradle \
  --mount type=bind,src="$PWD",dst=/workspace \
  --workdir /workspace \
  local-compose-tests:dev
```

This assumes the SDK is readable by the supplied UID and the checkout is writable.
Ignore `.container-home/` in the consuming repository and exclude it from image contexts.
Do not commit its caches or credentials.

Do not reuse host-generated native build outputs indiscriminately across architectures.
Use a clean container workspace or separate build directory policy for reproducibility.
On Docker Desktop, bind-mounted filesystem I/O can dominate test startup.
Compare a copied-source image before changing test synchronization.

## Use Compose for the test runner

A one-service `compose.yaml` can make image and report mounts repeatable:

```yaml
services:
  tests:
    build:
      context: .
      target: tests
      args:
        ANDROID_JVM_IMAGE: ${ANDROID_JVM_IMAGE:?Set a reviewed image digest}
    user: "1000:1000"
    volumes:
      - ./container-results/xml:/workspace/app/build/test-results
      - ./container-results/html:/workspace/app/build/reports/tests
```

Create the host directories with matching ownership before use.
Validate and run the configuration:

```bash
docker compose config --quiet
docker compose up --build --abort-on-container-exit --exit-code-from tests
```

`--exit-code-from tests` makes the selected test service determine the command's result.
Without it, a successful service startup can be mistaken for a passing test run.
Do not add a restart policy to this one-shot test service.
Do not delete shared volumes as a routine test cleanup step.

## Separate real service dependencies

For ordinary UI behavior, inject a fake instead of adding a database and server.
A container network does not make a shared backend deterministic.
A fake-driven screen test proves client behavior, not transport integration.

When a separate integration test genuinely needs services:

1. Give each service a pinned image and a bounded health check.
2. Use `depends_on` with `condition: service_healthy` for readiness dependencies.
3. Address a sibling service by its Compose service name, not `localhost`.
4. Isolate data and allocated ports per run.
5. Keep real credentials out of `compose.yaml` and artifacts.
6. Assert the real protocol outcome in that integration suite.

The JVM container's `localhost` means the container itself.
A local server started inside the same test process can use a dynamically allocated
loopback port. It does not need a published host port.
Do not expose unauthenticated databases to the host merely for the UI lane.

## Use the image in CI and development

For GitLab Docker executors, set the job image to the published test-toolchain digest.
For GitHub container jobs, check workspace ownership and runner action prerequisites.
For Jenkins, choose a configured Docker agent or an equivalent preprovisioned node.
Provider-specific examples are in [GitHub Actions](github-actions.md),
[GitLab](gitlab.md), and [other providers](other-providers.md).

A development container can use the same reviewed toolchain image and non-root user.
Run `./gradlew --version` and one hosted smoke test after creation.
No forwarded web port is needed for a local Compose semantics test.
Keep IDE extensions and optional device tooling outside the minimum CI image contract.

## Keep state and credentials out

Do not bake private Maven credentials into `ARG`, `ENV`, or copied Gradle files.
For build-time resolution, use BuildKit secrets with narrowly scoped credentials.
For runtime test commands, use the provider's secret mechanism and avoid logging values.
A copied credential remains in an image layer even if a later instruction deletes it.

Keep mutable fakes, Compose state, deferred completions, and test-owned scopes per test.
Container isolation does not reset a static singleton between methods in one JVM.
Close servers and executors and restore globals after failures.
Do not advance every scheduler to compensate for slower virtualized execution.

## Avoid browser-container assumptions

| Anti-pattern | Failure mechanism | Correct approach |
| --- | --- | --- |
| Use a Playwright image | No guaranteed Android SDK or compatible Java | Reviewed Android JVM base |
| Add `--privileged` or mount Docker socket | Expands host access without helping local semantics | Ordinary non-root execution |
| Run everything as root | Hides workspace permission problems and creates root-owned reports | Match UID and writable paths |
| Pin only the base tag | Mutable inputs still change the environment | Digest plus wrapper and dependency policy |
| Accept architecture emulation silently | Native code behavior and timing differ | Record and verify the actual architecture |
| Build tests into the image with secrets copied | Credentials persist in layers | Secret mounts and context review |

## Troubleshoot

| Symptom | Inspect | Fix |
| --- | --- | --- |
| SDK not found | `ANDROID_HOME` and readable platform directories | Correct the base image contract |
| Native library load error | Architecture, libc, Robolectric artifact | Select a supported environment, do not fake success |
| Permission denied for reports | Host UID and mount ownership | Precreate directories with matching ownership |
| Wrapper cannot execute | Executable bit and line endings | Preserve Unix executable mode and LF endings |
| Empty report mount | Task failed before tests or wrong module path | Preserve logs and align paths |
| Offline run downloads SDK jars | Robolectric runtime artifacts not provisioned | Warm verified inputs before enforcing offline mode |
| Works on host, not in image | Toolchain and native environment differences | Reproduce the same class and inspect the first exception |

## Review checklist

- The base image digest and installed SDK packages are recorded.
- The worker JDK supports the declared Robolectric runtime SDK.
- Non-root cache and report paths are writable.
- No credential file enters the build context.
- Container exit status reflects the test process.
- Reports remain accessible after the container exits.
- A hosted smoke test validates the actual image and architecture.

## Related guides and sources

- [CI overview](ci-cd.md), [reporting](reporting.md), and [test speed](performance.md).
- [Robolectric native graphics](https://robolectric.org/graphics/).
- [Robolectric compatibility](https://robolectric.org/compatibility_table/).
- [Docker build guidance](https://docs.docker.com/build/building/best-practices/).
- [Docker secrets](https://docs.docker.com/build/building/secrets/).
- [Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/).
