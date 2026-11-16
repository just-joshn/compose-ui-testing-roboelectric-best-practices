# Prepare suite inputs without sharing live state

Use this guide for build-time seed generation, immutable database inputs, service provisioning boundaries, and teardown planning. Most Robolectric Compose tests need no global setup. Their activity, state, and fakes belong to each test.

## Contents

- [Choose the setup scope](#choose-the-setup-scope)
- [Generate an immutable suite input](#generate-an-immutable-suite-input)
- [Connect setup to test tasks](#connect-setup-to-test-tasks)
- [Handle database migrations and snapshots](#handle-database-migrations-and-snapshots)
- [Provision external environments separately](#provision-external-environments-separately)
- [Define teardown ownership](#define-teardown-ownership)
- [Account for workers and shards](#account-for-workers-and-shards)
- [Avoid global setup anti-patterns](#avoid-global-setup-anti-patterns)
- [Troubleshoot setup](#troubleshoot-setup)
- [Review checklist](#review-checklist)
- [Related guides and sources](#related-guides-and-sources)

## Choose the setup scope

| Need | Owner | Why |
| --- | --- | --- |
| Known UI state and pending request | Per-test fixture | Tests can mutate without collision |
| Read-only catalog data | Checked-in test resource or generated file | No live resource crosses workers |
| Database schema input | Build task or checked-in migration fixture | Preparation is independent of UI lifecycle |
| Open database connection | Per-test resource | A connection is mutable and process-bound |
| Dependency graph before activity launch | Ordered JUnit rule | Startup consumes the replacement |
| Service process and real accounts | Integration CI job | Local semantics tests should not require it |
| Shared expensive read-only artifact | Cache keyed by declared inputs | Reuse does not imply shared mutable state |

JUnit `@BeforeClass` runs for a test class. It is not a once-per-build hook. Gradle task execution, test-worker processes, Robolectric sandboxes, and CI shards have different lifetimes.

Do not use a class-level Compose rule as a global UI session. Activity state, semantics roots, and mutable fakes must not be shared between test methods.

## Generate an immutable suite input

For small data, a checked-in `src/test/resources/catalog.json` is usually enough. Use a build task when the input must be generated from declared configuration.

This illustrative Gradle Kotlin DSL fragment assumes an Android module and a debug local-unit-test task. It generates a plain read-only fixture, not a running service or a database connection:

```kotlin
import org.gradle.api.tasks.testing.Test

val catalogFile = layout.buildDirectory.file("generated/test-input/catalog.json")

val generateTestCatalog = tasks.register("generateTestCatalog") {
	inputs.property("catalogVersion", "1")
	outputs.file(catalogFile)
	doLast {
		val target = catalogFile.get().asFile
		target.parentFile.mkdirs()
		target.writeText("""{"version":1,"items":["Draft","Archive"]}""")
	}
}

tasks.withType<Test>().configureEach {
	dependsOn(generateTestCatalog)
	doFirst {
		systemProperty("test.catalog.path", catalogFile.get().asFile.absolutePath)
	}
}
```

All imports belong at the top of the build script. The fragment intentionally wires every local `Test` task in that module. Scope by the actual task name if only one suite needs the input.

A reading fragment inside test setup follows. It uses only JDK APIs:

```kotlin
import java.nio.file.Files
import java.nio.file.Path

val catalogPath = requireNotNull(System.getProperty("test.catalog.path")) {
	"Missing test.catalog.path; run the configured Gradle test task"
}
val catalogJson = Files.readString(Path.of(catalogPath))
```

Parse and validate the JSON with the consuming project's chosen parser before use. Copy its values into fresh mutable test models. Do not write test changes back into the generated file.

The expected observable build result is a declared output file before test workers start. The expected UI result still requires a separate test action and assertion. Merely reading the generated seed does not test application behavior.

## Connect setup to test tasks

`dependsOn` makes preparation part of the execution graph. `mustRunAfter` only orders tasks when both are already scheduled. It does not cause setup to run.

Use separate tasks for independent inputs. If input B needs input A, declare that dependency directly. Do not depend on alphabetical task names or the order in a shell invocation.

A setup task should fail with a concrete missing-input error before tests start. Do not return success after generating an empty file. Make outputs unique per module or variant when their contents differ.

Avoid environment-specific hidden defaults. For an integration task that needs a service URL, pass and validate it explicitly at that boundary. Do not let a local UI task silently fall back to production.

## Handle database migrations and snapshots

Keep migration correctness separate from screen behavior. A migration test opens a database with a known old schema, applies migrations, and checks the resulting schema and data. A screen test exercises a fresh repository backed by the schema it actually needs.

For a prebuilt database seed:

1. Record its schema version and generator inputs.
2. Keep the source seed immutable.
3. Copy the seed to a per-test temporary location.
4. Open that copy through the production database adapter under test.
5. Perform the user action and assert the visible result.
6. Close the database before deleting the owned temporary copy.

Do not reuse a mutable snapshot file between tests. Do not restore a database while another worker still has it open. Database-specific journal and lock files can outlive a connection if ownership is unclear.

A shared rollback transaction is not general isolation. Application work using another connection or coroutine can commit outside it. Use an isolated database for each test unless the test explicitly proves a transaction-sharing contract.

Keep large seed preparation outside every test when it is truly immutable. Do not move open connections, caches, or already-mutated repositories into global state to save startup time.

## Provision external environments separately

A fake repository needs no server readiness probe. If the claim concerns a real service, use a separately named integration job with its own environment owner.

That job needs a concrete contract:

| Input or result | Required evidence |
| --- | --- |
| Service endpoint | Validated scheme, expected environment, and bounded readiness response |
| Schema migration | Successful migration command and schema identity |
| Test identity | Run-specific namespace and restricted credentials |
| Seed completion | Created resource IDs or manifest |
| Test result | Named executed tests and process status |
| Cleanup | Ownership-scoped teardown outcome |

Use the existing service orchestration tooling. Do not launch a detached server from a JUnit test and hope an `@AfterClass` method finds its process later. Fail readiness after a bounded interval with the last response and logs.

A local fake session is not an exported authentication state comparable to browser storage state. Seed a fresh session model for each local test. Verify real authentication in its own integration and device layers.

Never commit real tokens, database URLs with passwords, or exported live sessions as fixtures.

## Define teardown ownership

Keep transient build outputs under the module's build directory. These can remain for diagnosis. Live processes, sockets, connections, and external accounts need explicit cleanup after both successful and failed runs.

Gradle finalizer tasks can run cleanup after a scheduled task, including failures, but they do not replace resource ownership. A killed worker or terminated CI job can bypass ordinary test teardown. Integration environments need an external expiry or janitor policy scoped to their run ID.

For per-test resources, prefer `use`, `try/finally`, or an ordered resource rule. For global immutable files, no test-side deletion is needed. Do not delete a seed while another test task is still reading it.

## Account for workers and shards

A Gradle invocation may contain several modules and variant tasks. CI may invoke it several times in parallel. A setup task runs within its build graph, not once across all CI.

Use separate output paths when configuration differs. Namespace external integration records by run, worker, and test. A fixed `test-user` created once globally invites collisions when tests update the same record.

Do not pass a Java object between workers through static state. Share immutable serialized inputs, then construct a fresh repository and state in each test.

## Avoid global setup anti-patterns

| Anti-pattern | Failure mechanism | Correction |
| --- | --- | --- |
| One signed-in repository for the suite | Mutations leak across tests | Fresh session fixture |
| `@BeforeClass` called global setup | Runs separately per class or worker | Choose build tasks or per-test rules explicitly |
| Migration command in every UI test | Slow repeated unrelated work | Separate migration coverage and immutable seed |
| Service wait without a deadline | CI hangs on failed startup | Bounded readiness with logs |
| Teardown deletes a shared database | Other runs lose their data | Delete only resources owned by this run |
| Setup outputs are undeclared | Stale or incorrectly reused inputs | Declare inputs, outputs, and task dependencies |

## Troubleshoot setup

| Symptom | Observe | Fix |
| --- | --- | --- |
| Tests pass only after another task | Missing dependency edge | Add `dependsOn`, not just ordering |
| Generated file is stale | Declared inputs and output path | Include every content-changing input |
| CI jobs overwrite seeds | Shared writable output directory | Use distinct run or module paths |
| Cleanup hides test failure | Original result and teardown logs | Preserve both statuses |
| Seeded UI shows old values | Shared mutable repository or cache | Reconstruct per-test state |

## Review checklist

- Global work produces immutable inputs rather than live UI state.
- Every prerequisite is an explicit dependency.
- Database copies and external records have narrow owners.
- Failed setup cannot produce an empty green suite.
- Readiness and cleanup have bounded, inspectable outcomes.
- Local UI tests remain independent of real service credentials.

## Related guides and sources

- [Fixtures and hooks](fixtures-hooks.md) covers per-test resource ownership.
- [Modules and variants](modules-variants.md) covers task and configuration matrices.
- [CI](../infrastructure-ci-cd/ci-cd.md) covers environment orchestration.
- [Gradle task dependencies](https://docs.gradle.org/current/userguide/controlling_task_execution.html) documents dependencies, ordering, and finalizers.
- [Robolectric best practices](https://robolectric.org/best-practices/) documents isolation constraints.
