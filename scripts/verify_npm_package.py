#!/usr/bin/env python3

import json
import os
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

from check_skill import LINK, NAME, check


ROOT = Path(__file__).resolve().parents[1]


def run(command, cwd, work, label):
    environment = dict(os.environ, npm_config_cache=str(work / "npm-cache"))
    result = subprocess.run(command, cwd=cwd, env=environment, text=True, capture_output=True)
    (work / f"{label}.log").write_text(
        f"$ {' '.join(command)}\nexit {result.returncode}\n{result.stdout}\n{result.stderr}"
    )
    assert result.returncode == 0, f"{label} failed. See {work / (label + '.log')}"
    return result.stdout


def verify(root, work):
    root, work = root.resolve(), work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    paths = [root / name for name in ("package.json", "README.md", "LICENSE")]
    paths.extend(path for path in (root / NAME).rglob("*") if path.is_file())
    assert all(not path.is_symlink() for path in paths), "Source payload must not contain symlinks"
    expected = {path.relative_to(root).as_posix(): path.read_bytes() for path in paths}
    packed = json.loads(run(
        ["npm", "pack", "--json", "--ignore-scripts", "--pack-destination", str(work)],
        root, work, "pack",
    ))
    assert len(packed) == 1, "Expected one npm archive"
    filename = packed[0]["filename"]
    assert Path(filename).name == filename, "Unsafe npm archive filename"
    tarball = work / filename
    extracted = work / "extracted"
    extracted.mkdir()
    actual = {}
    with tarfile.open(tarball, "r:gz") as archive:
        for member in archive.getmembers():
            path = PurePosixPath(member.name)
            assert member.isfile(), f"Non-regular archive entry: {member.name}"
            assert (path.parts[0] == "package" and len(path.parts) > 1
                    and ".." not in path.parts and not path.is_absolute()), \
                f"Unsafe archive entry: {member.name}"
            name = path.relative_to("package").as_posix()
            assert name not in actual, f"Duplicate archive entry: {name}"
            actual[name] = archive.extractfile(member).read()
    assert actual.keys() == expected.keys(), (
        f"Archive inventory mismatch. Missing {sorted(expected.keys() - actual.keys())}; "
        f"unexpected {sorted(actual.keys() - expected.keys())}"
    )
    assert actual == expected, "Archive bytes differ from canonical source"
    for name, content in actual.items():
        destination = extracted / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    manifest = json.loads((extracted / "package.json").read_text())
    assert manifest["pi"]["skills"] == [f"./{NAME}"], "Broken pi.skills path"
    assert "pi-package" in manifest["keywords"], "Missing pi-package keyword"
    frontmatter = (extracted / NAME / "SKILL.md").read_text().split("---", 2)[1]
    version = re.search(r'^  version: "([^"]+)"$', frontmatter, re.MULTILINE)
    assert version and version[1] == manifest["version"], "Package and skill versions differ"
    check(extracted / NAME)
    for target in LINK.findall((extracted / "README.md").read_text()):
        if re.match(r"[a-z]+://", target) or target.startswith("#"):
            continue
        resolved = (extracted / target.split("#", 1)[0]).resolve()
        assert resolved.is_relative_to(extracted) and resolved.exists(), f"Broken README link: {target}"
    consumer = work / "consumer"
    consumer.mkdir()
    (consumer / "package.json").write_text('{"name":"package-verification-consumer","private":true}')
    run(["npm", "install", "--ignore-scripts", "--no-audit", "--no-fund", str(tarball)],
        consumer, work, "install")
    installed = consumer / "node_modules" / manifest["name"]
    installed_files = {
        path.relative_to(installed).as_posix(): path.read_bytes()
        for path in installed.rglob("*") if path.is_file()
    }
    assert installed_files == expected, "Installed payload differs from verified archive"
    check(installed / NAME)
    result = {"status": "PASS", "tarball": str(tarball), "files": len(actual),
              "version": manifest["version"]}
    (work / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    (ROOT / ".work").mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="npm-package-", dir=ROOT / ".work"))
    print(f"Artifacts: {work}", flush=True)
    try:
        print(json.dumps(verify(ROOT, work), indent=2))
    except Exception as error:
        (work / "result.json").write_text(json.dumps({"status": "FAIL", "error": str(error)}, indent=2) + "\n")
        raise


if __name__ == "__main__":
    main()
