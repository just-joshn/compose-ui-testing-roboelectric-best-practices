# PASS

The goal is a faithful, complete adaptation of Currents' infrastructure guidance for Compose UI testing with Robolectric. The nine reviewed adaptations preserve the substantive decisions and scenarios without inventing browser API equivalents. I found no proven acceptance-blocking issue in this slice.

I audited the actual uncommitted files against base `5dd17596f8f172e7008bfe21cdb28904196f2922`. I made no changes and spawned no workers.

## Topics examined

Every source and target below was read in full. Paths are relative to their respective source and target roots.

| Source and target path | Assessment |
| --- | --- |
| `infrastructure-ci-cd/ci-cd.md` | Covers build prerequisites, first job, PR versus scheduled selection, secrets, caches, containers, shards, and failure evidence. Distinguishes compile SDK from Robolectric runtime SDK. |
| `infrastructure-ci-cd/docker.md` | Provides a concrete image contract, Dockerfile, report mounts, development bind mounts, Compose runner, service handoff, permissions, and credential guidance. Does not promise a nonexistent public Android image. |
| `infrastructure-ci-cd/github-actions.md` | Covers single jobs, checked shards, collection, variants, SDK selection, schedules, reusable workflows, permissions, and failure propagation. Clearly states that Java setup does not install Android SDK packages. |
| `infrastructure-ci-cd/gitlab.md` | Covers provisioned runners, pipeline rules, caching, JUnit and HTML, one-based node conversion, variant matrices, schedules, variables, and service boundaries. Best-effort artifact copies do not swallow the Gradle command's failure. |
| `infrastructure-ci-cd/other-providers.md` | Provides usable Jenkins, CircleCI, and Azure configurations, plus provider-specific partitioning and report publication. Names the required administrator-provisioned infrastructure. |
| `infrastructure-ci-cd/parallel-sharding.md` | Implements actual class selection with `Test.filter.includeTestsMatching`. Distinguishes forks, module parallelism, shards, and SDK expansion. Requires complete, disjoint partitions and method-level result comparison. |
| `infrastructure-ci-cd/performance.md` | Covers equivalent-work measurement, setup costs, forks, resource limits, fakes, work ownership, cleanup, sharding costs, and diagnostic overhead. Does not mislabel JVM timings as device performance. |
| `infrastructure-ci-cd/reporting.md` | Covers Gradle output, in-lifetime semantics diagnostics, artifact identity, failure-preserving publication, bounded passing evidence, retries, summaries, notifications, and screenshot boundaries. |
| `infrastructure-ci-cd/test-coverage.md` | Respects Android plugin boundaries. Uses explicit custom JaCoCo tasks and production-class inputs rather than assuming standard JVM report tasks exist. Covers denominators, thresholds, compatible shard data, changed files, publication, and instrumentation limits. |

The separate integration and device handoffs are appropriate adaptations of source-only mechanisms. They are not used as substitutes for the local workflows.

## Checker audit

I fully inspected `scripts/check_skill.py` and `scripts/test_check_skill.py`.

- The checker verifies the exact pinned set of 58 source paths, not merely a row count. Duplicate and unknown source substitutions are rejected.
- Target discovery is recursive and must equal the manifest targets. Unmanifested guides and duplicate targets are rejected.
- Every adaptation target must have a direct entry route.
- Local links, fragments, installation boundaries, canonical references, legal files, and copied-install portability are checked.
- Negative tests exercise source inventory substitutions, missing mappings, metadata, unsafe targets, missing routes, nested guides, fragments, and structural damage.
- The existing `check(directory)` API remains intact.
- The implementation is small and traceable. I found no maintainability defect warranting a correction.

The checker does **not** verify substantive topic depth, snippet execution, or source-content hash authenticity. That matches its documented structural scope in `README.md`. Its acceptance of synthetic minimal guides is therefore not a source-coverage false green. I separately checked all nine recorded source hashes against the pinned files; all matched.

## Fresh verification

Both commands passed:

```text
python3 scripts/test_check_skill.py
Ran 14 tests
OK

python3 scripts/check_skill.py
PASS 58 routed adaptation guides, 7 references and 2 Kotlin example files
PASS standalone copied install
```

I checked Gradle filtering and JaCoCo behavior against current documentation through Context7. I also inspected Gradle 9.4.1's `JacocoPlugin.java`. Its `applyToDefaultTasks` configures every `Test` task with the agent extension, supporting the guide's custom Android report approach without requiring a Java-plugin-owned `jacocoTestReport` task.

**Verification limit.** I did not execute the illustrative provider pipelines, container examples, sharding fragment, or coverage fragment. This PASS establishes acceptance of the guidance, not hosted execution certification. No unresolved API concern was identified.

## Content identities

Each slice digest uses UTF-8 records sorted by relative path:

```text
relative-path<TAB>sha256(file-bytes)<NEWLINE>
```

The digest is SHA256 of those concatenated records.

| Slice | Files | SHA256 |
| --- | ---: | --- |
| Pinned infrastructure source | 9 | `6c4939f470475ea6fadcd6abbe30022cc459081a7ffc01f93738a5a4bcd91d02` |
| Uncommitted infrastructure targets | 9 | `a348905caa31f3694907382e619f686719608033503f6ef7f17e842cc21eb88b` |

Additional audited file identities:

```text
scripts/check_skill.py
196a365997f4ee827a500ef3349c86f22f21a580e8a9276104eb50ce73ee02f4

scripts/test_check_skill.py
45552ddb8e20bbdc52052e8ab75bc76a106bd205c350bfe070b518bd90a4e43b
```

**Principle applied.** Prove It Works changed the evidence standard. I read the actual source and targets, ran both structural checks, and verified the relevant Gradle behavior rather than relying on author summaries or manifest entries.
