# SPDX-FileCopyrightText: 2025-2026 The OATS Authors
# SPDX-License-Identifier: Apache-2.0

import json
import re
import subprocess
import tomllib
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
SCHEMAS_DIR = REPO_ROOT / "schemas"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
PACKAGE_VERSION = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())["project"][
    "version"
]

Version = tuple[int, int, int]

X_VERSION_SINCE: Version = (0, 8, 0)
VERSION_PATTERN = r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
TAG_RE = re.compile(rf"v{VERSION_PATTERN}")
HEADING_RE = re.compile(rf"## v({VERSION_PATTERN}) \((\d{{4}}-\d{{2}}-\d{{2}})\)")


def parse_version(text: str) -> Version:
    major, minor, patch = (int(part) for part in text.split("."))
    return major, minor, patch


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key {key!r}")
        result[key] = value
    return result


def schema_violations(raw: bytes, version: str) -> list[str]:
    """Return why the site would refuse this schema file in release `version`."""
    try:
        schema = json.loads(
            raw.decode("utf-8"), object_pairs_hook=reject_duplicate_keys
        )
    except (UnicodeDecodeError, ValueError) as e:
        return [f"not valid UTF-8 JSON ({e})"]
    if not isinstance(schema, dict):
        return ["the schema is not a JSON object"]
    errors = []
    if parse_version(version) >= X_VERSION_SINCE:
        if schema.get("x-version") != version:
            errors.append(f"x-version is {schema.get('x-version')!r}, not {version!r}")
        if "version" in schema:
            errors.append("a top-level 'version' is not allowed; use 'x-version'")
    elif schema.get("version") != version:
        errors.append(f"version is {schema.get('version')!r}, not {version!r}")
    for key in ("title", "description"):
        if not isinstance(schema.get(key), str) or not schema[key]:
            errors.append(f"'{key}' must be a non-empty string")
    return errors


def parse_changelog(text: str) -> tuple[dict[Version, date], list[str]]:
    """Return each release's date and the reasons the site would refuse the changelog."""
    entries: dict[Version, date] = {}
    order: list[Version] = []
    errors: list[str] = []
    preamble = True
    for number, line in enumerate(text.splitlines(), start=1):
        if line.startswith("## "):
            preamble = False
            match = HEADING_RE.fullmatch(line)
            if match is None:
                errors.append(
                    f"line {number}: expected '## vX.Y.Z (YYYY-MM-DD)', got {line!r}"
                )
                continue
            version = parse_version(match.group(1))
            try:
                released = date.fromisoformat(match.group(5))
            except ValueError:
                errors.append(f"line {number}: invalid date {match.group(5)!r}")
                continue
            if version in entries:
                errors.append(f"line {number}: v{match.group(1)} is listed twice")
            entries[version] = released
            order.append(version)
        elif preamble and line.strip() and not line.startswith("# "):
            errors.append(f"line {number}: text before the first release heading")
    if order != sorted(order, reverse=True):
        errors.append("releases must be listed newest first")
    return entries, errors


def git(*args: str) -> bytes | None:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args], capture_output=True, check=False
    )
    return result.stdout if result.returncode == 0 else None


def release_tags() -> list[str]:
    listing = git("tag", "--list", "v*")
    if listing is None:
        return []
    return sorted(
        (tag for tag in listing.decode().split() if TAG_RE.fullmatch(tag)),
        key=lambda tag: parse_version(tag[1:]),
    )


def schemas_at(tag: str) -> dict[str, bytes]:
    listing = git("ls-tree", "-z", "--name-only", tag, "--", "schemas/")
    assert listing is not None, f"cannot list schemas/ at {tag}"
    files = {}
    for path in listing.decode().split("\0"):
        if path.endswith(".json"):
            raw = git("cat-file", "blob", f"{tag}:{path}")
            assert raw is not None, f"cannot read {path} at {tag}"
            files[Path(path).name] = raw
    return files


TAGS = release_tags()
CHANGELOG_ENTRIES, CHANGELOG_ERRORS = parse_changelog(CHANGELOG.read_text())


@pytest.mark.parametrize(
    "path", sorted(SCHEMAS_DIR.glob("*.json")), ids=lambda p: p.name
)
def test_working_schema_carries_the_package_version(path):
    errors = schema_violations(path.read_bytes(), PACKAGE_VERSION)
    assert not errors, f"{path.name}: " + "; ".join(errors)


def test_changelog_format():
    assert not CHANGELOG_ERRORS, f"{CHANGELOG.name}: " + "; ".join(CHANGELOG_ERRORS)


def test_changelog_has_an_entry_for_the_package_version():
    assert parse_version(PACKAGE_VERSION) in CHANGELOG_ENTRIES, (
        f"{CHANGELOG.name} has no '## v{PACKAGE_VERSION} (YYYY-MM-DD)' entry"
    )


@pytest.mark.parametrize("tag", TAGS)
def test_released_schemas_carry_their_version(tag):
    files = schemas_at(tag)
    assert files, f"{tag} has no schemas/*.json"
    errors = [
        f"{name}: {error}"
        for name, raw in files.items()
        for error in schema_violations(raw, tag[1:])
    ]
    assert not errors, f"{tag}: " + "; ".join(errors)


@pytest.mark.parametrize("tag", TAGS)
def test_changelog_has_an_entry_for_every_release(tag):
    assert parse_version(tag[1:]) in CHANGELOG_ENTRIES, (
        f"{CHANGELOG.name} has no entry for {tag}"
    )


VALID_SCHEMA = {"title": "T", "description": "D"}


@pytest.mark.parametrize(
    "description, raw, version",
    [
        (
            "x-version differs",
            json.dumps({**VALID_SCHEMA, "x-version": "0.8.1"}),
            "0.9.0",
        ),
        ("x-version missing", json.dumps(VALID_SCHEMA), "0.9.0"),
        (
            "top-level version from 0.8.0",
            json.dumps({**VALID_SCHEMA, "x-version": "0.9.0", "version": "0.9.0"}),
            "0.9.0",
        ),
        (
            "x-version instead of version before 0.8.0",
            json.dumps({**VALID_SCHEMA, "x-version": "0.7.0"}),
            "0.7.0",
        ),
        (
            "version differs before 0.8.0",
            json.dumps({**VALID_SCHEMA, "version": "0.6.0"}),
            "0.7.0",
        ),
        (
            "empty title",
            json.dumps({"title": "", "description": "D", "x-version": "0.9.0"}),
            "0.9.0",
        ),
        (
            "duplicate key",
            '{"title": "T", "title": "T", "description": "D", "x-version": "0.9.0"}',
            "0.9.0",
        ),
        ("not an object", "[]", "0.9.0"),
    ],
)
def test_schema_check_rejects(description, raw, version):
    assert schema_violations(raw.encode(), version), (
        f"Release check accepted: {description}"
    )


@pytest.mark.parametrize(
    "raw, version",
    [
        (json.dumps({**VALID_SCHEMA, "x-version": "0.9.0"}), "0.9.0"),
        (json.dumps({**VALID_SCHEMA, "version": "0.7.0"}), "0.7.0"),
    ],
)
def test_schema_check_accepts(raw, version):
    assert schema_violations(raw.encode(), version) == []


VALID_CHANGELOG = "# Changelog\n\n## v0.9.0 (2026-11-02)\n\n### Added\n\n- x\n\n## v0.8.0 (2026-10-17)\n\n- y\n"


@pytest.mark.parametrize(
    "description, text",
    [
        (
            "missing date",
            VALID_CHANGELOG.replace("## v0.9.0 (2026-11-02)", "## v0.9.0"),
        ),
        (
            "unreleased instead of a date",
            VALID_CHANGELOG.replace("(2026-11-02)", "(unreleased)"),
        ),
        ("invalid date", VALID_CHANGELOG.replace("2026-11-02", "2026-13-02")),
        ("no v prefix", VALID_CHANGELOG.replace("## v0.9.0", "## 0.9.0")),
        ("leading zero", VALID_CHANGELOG.replace("v0.9.0", "v0.09.0")),
        ("two-part version", VALID_CHANGELOG.replace("v0.9.0", "v0.9")),
        ("text before the first heading", "Intro.\n\n" + VALID_CHANGELOG),
        (
            "oldest first",
            "# Changelog\n\n## v0.8.0 (2026-10-17)\n\n## v0.9.0 (2026-11-02)\n",
        ),
        (
            "duplicate release",
            VALID_CHANGELOG.replace("## v0.8.0 (2026-10-17)", "## v0.9.0 (2026-10-17)"),
        ),
    ],
)
def test_changelog_check_rejects(description, text):
    assert parse_changelog(text)[1], f"Changelog check accepted: {description}"


def test_changelog_check_accepts():
    entries, errors = parse_changelog(VALID_CHANGELOG)
    assert errors == []
    assert entries == {(0, 9, 0): date(2026, 11, 2), (0, 8, 0): date(2026, 10, 17)}
