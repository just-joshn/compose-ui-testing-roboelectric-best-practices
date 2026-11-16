# Reproduce the focused adaptation probes

These checks support specific guide corrections. They are separate from the canonical eight-test fixture and do not expand its bounded evidence contract.

## Reproduce clearing-semantics inspection

`ClearingSemanticsProbeTest.kt` executed with the canonical fixture's Compose UI 1.12.1, Robolectric 4.18, API 35, and JDK 17. Its one named test passed without skips. `clearing-semantics.xml` retains both trees.

In a disposable copy of the repository, copy the probe into the directory compiled by the fixture:

```bash
cp evidence/adaptation-probes/ClearingSemanticsProbeTest.kt \
  compose-ui-testing-robolectric-best-practices/examples/
./gradlew :fixture:testDebugUnitTest \
  --tests fixture.ClearingSemanticsProbeTest.unmergedTreeRetainsClearedDescendant \
  --console=plain --no-daemon --rerun-tasks
```

Require exactly that one passing method and inspect both dumps. The merged tree exposes the replacement description without the child. The unmerged tree exposes `cleared-child` and its original text.

Run this only in the disposable copy. Leaving the extra test in the canonical example directory changes the suite inventory. This probe does not establish accessibility-service exposure.

The first direct Gradle attempt failed when the sandbox prevented a compiler temporary-file write. The retry used a writable JVM temporary directory and the verification helper's writable caches. That environmental failure is not a semantics result.

## Reproduce the concrete HTTP and GraphQL contracts

The complete code blocks in `repository-contracts.md` and `graphql.md` executed in a standalone Kotlin/JVM project. All five methods passed with zero failures, errors, or skips. `http-contracts/proof.json` records the executed source hashes. The two JUnit XML files record the actual method names.

The tested combination was Gradle 9.4.1, Kotlin 2.2.10, JDK 17, JUnit 4.13.2, OkHttp and MockWebServer 4.12.0, and JSON-java 20240303. This is not Android `org.json` or production backend evidence.

From this repository root, extract the authoritative guide blocks into a fresh standalone project:

```bash
mkdir -p .work
RUN="$(mktemp -d "$PWD/.work/guide-http.XXXXXX")"
cp evidence/adaptation-probes/http-contracts/build.gradle.kts "$RUN/"
printf '%s\n' 'rootProject.name = "guide-http-contracts"' > "$RUN/settings.gradle.kts"
python3 - "$RUN" <<'PY'
import re
import sys
from pathlib import Path

output = Path(sys.argv[1]) / "src/test/kotlin"
output.mkdir(parents=True)
for filename, class_name in (
    ("repository-contracts.md", "ItemHttpContractTest"),
    ("graphql.md", "GraphQlHttpContractTest"),
):
    guide = Path("compose-ui-testing-robolectric-best-practices/testing-patterns") / filename
    blocks = re.findall(r"```kotlin\n(.*?)\n```", guide.read_text(), re.DOTALL)
    source = next(block for block in blocks if "class " + class_name in block)
    (output / (class_name + ".kt")).write_text(source + "\n")
PY
```

Set `JAVA_HOME` to JDK 17. Then execute the extracted sources:

```bash
mkdir -p "$RUN/tmp"
export JAVA_TOOL_OPTIONS="${JAVA_TOOL_OPTIONS:-} -Djava.io.tmpdir=$RUN/tmp"
./gradlew -p "$RUN" test --console=plain --no-daemon --rerun-tasks
find "$RUN/build/test-results/test" -name 'TEST-*.xml' -type f
```

Require three methods in `ItemHttpContractTest` and two in `GraphQlHttpContractTest`, with no failures, errors, or skips. The requests cross real loopback HTTP. They test the defined example client and decoder, not a live service or a consuming application's production client.

The full original build logs, extracted sources, and dedicated cache remain in the authoring job's retained temporary project. The main adaptation report records that path. An initial sandbox temporary-directory failure remains in those logs; the explicit writable JVM temporary directory fixed the environment.
