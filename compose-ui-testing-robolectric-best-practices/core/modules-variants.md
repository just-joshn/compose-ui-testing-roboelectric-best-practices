# Choose modules, variants, and test dependencies

Use this guide when a repository has several Android modules, product flavors, runtime SDKs, or test layers. Gradle projects and Android variants are not browser projects. Choose dimensions that correspond to actual Android behavior and declare their build dependencies explicitly.

## Contents

- [Choose a matrix dimension](#choose-a-matrix-dimension)
- [Run the intended task](#run-the-intended-task)
- [Share configuration without sharing state](#share-configuration-without-sharing-state)
- [Declare preparation dependencies](#declare-preparation-dependencies)
- [Separate sessions from variants](#separate-sessions-from-variants)
- [Choose SDK and qualifier coverage](#choose-sdk-and-qualifier-coverage)
- [Keep reports and teardown distinct](#keep-reports-and-teardown-distinct)
- [Troubleshoot matrix failures](#troubleshoot-matrix-failures)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose a matrix dimension

| Difference under test | Mechanism | Example |
| --- | --- | --- |
| Feature ownership or dependency boundary | Android Gradle module | `:feature:messages` |
| Build-time configuration or resources | Flavor and build-type variant | `demoDebug` |
| Android framework behavior | Robolectric runtime SDK | API 35 versus a justified second API |
| Locale, resource size, orientation | Robolectric qualifiers or narrow test configuration | Explicit locale-specific case |
| User role or session status | Fresh fixture input | Signed out, member, admin |
| Repository failure or success | Controlled fake | Pending, success, recoverable failure |
| Real device behavior | Instrumentation suite | IME, TalkBack, permissions, performance |
| Real transport behavior | Repository or service integration suite | Serialization and HTTP contract |

Do not create a product flavor for each fake response or user role. Those are runtime scenario inputs, not alternate application builds.

Do not multiply every test across every dimension. Select representative behavior checks and add cross-product cases only where the interaction is a requirement.

## Run the intended task

These illustrative commands assume the named modules and variants already exist:

```bash
./gradlew :feature:messages:tasks --all
./gradlew :feature:messages:testDebugUnitTest
./gradlew :app:testDemoDebugUnitTest
./gradlew :app:testDemoDebugUnitTest \
  --tests 'example.messages.MessageTest.sendShowsReceipt'
```

`testDemoDebugUnitTest` runs local tests. A `connected...AndroidTest` task targets a connected device or emulator. Do not report one as evidence for the other.

For multiple local modules, request their concrete tasks:

```bash
./gradlew :feature:messages:testDebugUnitTest :feature:profile:testDebugUnitTest
```

An aggregate task can make the intended PR lane explicit. This root Gradle Kotlin DSL fragment assumes both tasks exist:

```kotlin
tasks.register("localUiChecks") {
	dependsOn(
		":feature:messages:testDebugUnitTest",
		":feature:profile:testDebugUnitTest",
	)
}
```

A dependency failure prevents successful completion of that lane. It does not prove the other module's tests ran. Read reports per task.

## Share configuration without sharing state

Use the repository's convention plugin or version catalog for common Android resources, dependency alignment, test logging, and worker settings. Keep the host declaration and scenario-specific dependencies in the module that actually uses them.

A shared test helper module can contain immutable data builders and robots. It must expose only the necessary test dependencies and must not hold a shared Compose rule, Android context, or mutable fake singleton.

Place variant-specific tests and resources in the source sets supported by the existing Android build. Verify discovery with the actual task before relying on a directory name. A helper under an unconfigured source directory can silently compile nowhere.

The default host dependency `debugImplementation("androidx.compose.ui:ui-test-manifest")` affects debug. Do not assume a release local test gets that host automatically. A real activity still needs its own manifest declaration.

Check resolved dependencies for the specific variant:

```bash
./gradlew :app:dependencies \
  --configuration demoDebugUnitTestRuntimeClasspath
```

The compile SDK is a build input. The Robolectric runtime SDK is the simulated Android version. A single compile SDK does not establish runtime coverage across every Android API.

## Declare preparation dependencies

Use build tasks for immutable preparation. Use per-test rules for live dependencies that must exist before activity launch. Do not order test classes as setup projects.

The following illustrative module-level Gradle Kotlin DSL fragment assumes an existing `generateCatalog` task:

```kotlin
import org.gradle.api.tasks.testing.Test

val generateCatalog = tasks.named("generateCatalog")

tasks.withType<Test>().configureEach {
	dependsOn(generateCatalog)
}
```

When one generated artifact depends on another, connect the generating tasks directly. `mustRunAfter` does not schedule the prerequisite. See [global setup](global-setup.md) for declared input and output examples.

A passing `LoginTest` must not be a prerequisite that leaves a signed-in singleton for `SettingsTest`. Seed SettingsTest's own session instead. Each test must be runnable through its own method filter.

For a real service lane, its setup and teardown belong to the integration job. Do not make fast local UI checks depend on an unrelated production login task.

## Separate sessions from variants

A role matrix belongs in scenario construction:

| Local scenario | Fixture input | Expected visible behavior |
| --- | --- | --- |
| Signed out | Empty fresh session store | Sign-in prompt |
| Member | Member session in a fresh store | Member content, no admin action |
| Admin | Admin session in a fresh store | Admin action available |
| Expired | Expired session result from a controlled boundary | Session-expired UI |

These are client behavior claims. A fake admin session does not establish server authorization. Add service authorization tests that reject unauthorized requests without relying on whether the client hides a button.

Store immutable role data in builders. Construct mutable stores per test. Avoid exported live authentication files and shared accounts in a local UI suite.

## Choose SDK and qualifier coverage

For a framework-sensitive test, apply `@Config(sdk = [34, 35])` to the existing behavior method. Import `org.robolectric.annotation.Config`. Robolectric then runs that method at both declared SDKs. Keep its actual action and outcome assertions unchanged. The class still needs the Robolectric runner and its own rule when testing Compose.

Do not add a second API merely to increase the matrix size. Name the framework difference that makes the second runtime useful, such as a resource or service contract used by the screen. Pure business rules can remain on one local runtime or in a framework-free unit test.

A runtime matrix increases executed cases and can need different JDKs. Consult the pinned Robolectric compatibility table. The fixture's API 35/JDK 17 observation does not validate API 36 or 37 on that JDK.

For resources, choose qualifiers that isolate the requirement. Test a translation with an explicit locale and assert its actual wording. Test an adaptive layout at representative widths and assert available actions. Do not label a Robolectric qualifier as physical device emulation.

Make required matrix cases visible in CI metadata and report paths. Conditional omission of an expensive lane should be an explicit pipeline policy, not an environment check inside every test that silently skips it.

## Keep reports and teardown distinct

Archive results under module, variant, SDK, and shard identity. Two jobs writing `results.xml` to the same destination can overwrite evidence.

Track the expected cases for each lane. A filtered run that executes zero tests must not count as green. SDK-expanded methods may have runner-decorated names, so inspect the actual JUnit report before matching a strict expected-method contract.

Do not merge all layers into one success label. Local UI success, service contract success, and device success carry different claims.

Teardown must close resources owned by each test. Any integration environment shared across tasks needs a run-scoped owner and cleanup after all consumers finish. Do not delete shared seeds after the first module completes.

## Troubleshoot matrix failures

| Symptom | Observe | Fix |
| --- | --- | --- |
| One variant has no activity | Its merged manifest and dependency graph | Supply the intended host for that variant |
| Test disappears in CI | Actual task, source set, and filter | Verify discovery and expected test count |
| Works only after login suite | Shared session singleton | Seed session per test |
| SDK case fails before UI | Worker JDK and Robolectric support | Select compatible runtime infrastructure |
| All tests run for a tiny change | Aggregate task and filter scope | Choose the concrete affected tasks without losing required lanes |
| Reports overwrite each other | Artifact destination naming | Include module, variant, and shard identity |

Anti-patterns include duplicate copy-pasted build configuration, hidden inter-test setup dependencies, and an unreviewed Cartesian product of flavors, roles, locales, and APIs. Share configuration at the build layer and keep scenario variation local.

## Review checklist

- Each matrix dimension corresponds to a real requirement.
- The invoked task targets the intended module and variant.
- Setup dependencies are explicit and tests remain independent.
- Shared helpers contain no mutable test session.
- Worker JDKs support the selected runtime SDKs.
- Reports identify and execute all required cases without skips.

## Related guides and sources

- [Configuration](configuration.md) covers the minimal local host.
- [Test filtering](test-filtering.md) covers method and category selection.
- [Adaptive layouts](../advanced/adaptive-layouts.md) covers width and resource cases.
- [Android build variants](https://developer.android.com/build/build-variants) describes variant composition.
- [Android local unit tests](https://developer.android.com/training/testing/local-tests) describes source sets and tasks.
- [Robolectric configuration](https://robolectric.org/configuring/) describes SDK and qualifier configuration.
