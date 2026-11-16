#!/usr/bin/env python3

import json
import shutil
import tempfile
from pathlib import Path

from verify_npm_package import NAME, ROOT, verify


def main():
    (ROOT / ".work").mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="npm-package-tests-", dir=ROOT / ".work"))
    print(f"Artifacts: {work}", flush=True)
    cases = {
        "missing-license": "LICENSE",
        "missing-reference": "Broken link",
        "unwanted-payload": "Archive inventory mismatch",
        "broken-pi-path": "Broken pi.skills path",
    }
    for case, message in cases.items():
        directory = work / case
        source = directory / "source"
        source.mkdir(parents=True)
        for name in ("package.json", "README.md", "LICENSE"):
            shutil.copy2(ROOT / name, source / name)
        shutil.copytree(ROOT / NAME, source / NAME)
        manifest_path = source / "package.json"
        manifest = json.loads(manifest_path.read_text())
        if case == "missing-license":
            (source / "LICENSE").unlink()
        elif case == "missing-reference":
            (source / NAME / "references" / "evidence.md").unlink()
        elif case == "unwanted-payload":
            (source / "unwanted.txt").write_text("repository-only payload\n")
            manifest["files"].append("unwanted.txt")
        elif case == "broken-pi-path":
            manifest["pi"]["skills"] = ["./missing-skill"]
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        try:
            verify(source, directory / "verification")
        except (AssertionError, FileNotFoundError) as error:
            assert message in str(error), f"{case} failed for the wrong reason: {error}"
            (directory / "rejection.log").write_text(f"{type(error).__name__}: {error}\n")
            print(f"PASS rejects {case}")
        else:
            raise AssertionError(f"Accepted {case}")
    print(f"PASS {len(cases)} npm package negative controls")


if __name__ == "__main__":
    main()
