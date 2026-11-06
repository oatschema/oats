# SPDX-FileCopyrightText: 2025-2026 The OATS Authors
# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path

import jsonschema_rs
import pytest

SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "entity-extraction.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
VALIDATOR = jsonschema_rs.Draft202012Validator(SCHEMA, validate_formats=True)
MAX_INTEGER = 9007199254740991
BOX = {
    "type": "block",
    "block_type": "box",
    "page_number": 1,
    "box": {"x": 0, "y": 0, "width": 1, "height": 1},
}


def block_range(**fields):
    return {
        "type": "block_range",
        "start_block_id": "a",
        "end_block_id": "b",
        **fields,
    }


def record(*locations, **fields):
    return {"entities": [{"label": "X", "location": list(locations)}], **fields}


def location_branch(title):
    location = SCHEMA["properties"]["entities"]["items"]["properties"]["location"]
    return next(b for b in location["items"]["oneOf"] if b["title"] == title)


@pytest.mark.parametrize(
    "location",
    [
        block_range(),
        block_range(start=6),
        block_range(end=4),
        block_range(start=6, end=4),
        block_range(start=0, end=0),
        block_range(start=MAX_INTEGER, end=MAX_INTEGER),
        block_range(start_block_id="a", end_block_id="a", start=2, end=9),
        block_range(start_block_id="x" * 128, end_block_id="y" * 128),
    ],
    ids=[
        "whole-blocks",
        "start-only",
        "end-only",
        "end-less-than-start-across-blocks",
        "lowest-offsets",
        "highest-offsets",
        "same-block",
        "longest-ids",
    ],
)
def test_accepts_range(location):
    assert VALIDATOR.is_valid(record(location))


@pytest.mark.parametrize(
    "location",
    [
        {"type": "block_range", "end_block_id": "b"},
        {"type": "block_range", "start_block_id": "a"},
        {"type": "block_range", "start": 1, "end": 2},
        {"type": "block_range", "block_id": "a", "start": 1, "end": 2},
        block_range(block_id="a"),
        block_range(page_number=1),
        block_range(start_block_id=1),
        block_range(end_block_id=1),
        block_range(start_block_id="x" * 129),
        block_range(end_block_id="x" * 129),
        block_range(start=-1),
        block_range(end=-1),
        block_range(start=1.5),
        block_range(end=1.5),
        block_range(start="1"),
        block_range(end="1"),
        block_range(start=None),
        block_range(end=None),
        block_range(start=MAX_INTEGER + 1),
        block_range(end=MAX_INTEGER + 1),
        {**block_range(), "type": "range"},
    ],
    ids=[
        "no-start-block",
        "no-end-block",
        "no-blocks",
        "block-id-instead-of-ends",
        "extra-block-id",
        "extra-field",
        "numeric-start-block",
        "numeric-end-block",
        "long-start-block",
        "long-end-block",
        "negative-start",
        "negative-end",
        "fractional-start",
        "fractional-end",
        "string-start",
        "string-end",
        "null-start",
        "null-end",
        "start-too-large",
        "end-too-large",
        "unknown-type",
    ],
)
def test_rejects_range(location):
    assert not VALIDATOR.is_valid(record(location))


@pytest.mark.parametrize(
    "location",
    [
        {"type": "span", "start": 6, "end": 4, "block_id": "a", "end_block_id": "b"},
        {"type": "span", "start": 6, "end": 4, "end_block_id": "b"},
        {"type": "span", "start": 6, "end": 9, "start_block_id": "a"},
        {"type": "block_ref", "block_id": "a", "end_block_id": "b"},
        {"type": "block_ref", "block_id": "a", "start_block_id": "a"},
        {"type": "block_ref", "block_id": "a", "start": 1},
        {"type": "block_ref", "block_id": "a", "end": 1},
        {**BOX, "start_block_id": "a"},
        {**BOX, "end_block_id": "b"},
        {**BOX, "start": 1},
        {**BOX, "end": 1},
    ],
    ids=[
        "span-with-block",
        "span-without-block",
        "span-start-block",
        "block-ref-end-block",
        "block-ref-start-block",
        "block-ref-start",
        "block-ref-end",
        "geometry-start-block",
        "geometry-end-block",
        "geometry-start",
        "geometry-end",
    ],
)
def test_other_locations_cannot_cross_blocks(location):
    assert not VALIDATOR.is_valid(record(location, unit="pt"))


@pytest.mark.parametrize(
    "location",
    [
        {"type": "span", "start": 0, "end": 9},
        {"type": "span", "start": 0, "end": 9, "block_id": "a"},
        {"type": "block_ref", "block_id": "a"},
    ],
    ids=["span-in-source-text", "span-in-block", "block-ref"],
)
def test_existing_locations_stay_valid(location):
    assert VALIDATOR.is_valid(record(location))


def test_limit_counts_ranges_with_other_locations():
    assert VALIDATOR.is_valid(record(*[block_range()] * 10))
    assert VALIDATOR.is_valid(record(*[block_range()] * 9, BOX, unit="pt"))
    assert not VALIDATOR.is_valid(record(*[block_range()] * 11))
    assert not VALIDATOR.is_valid(record(*[block_range()] * 10, BOX, unit="pt"))


def test_range_is_not_geometry():
    assert VALIDATOR.is_valid(record(block_range()))
    for unit in ("px", "pt", "normalized", "per_mille"):
        assert VALIDATOR.is_valid(record(block_range(start=5000, end=5000), unit=unit))


def test_geometry_beside_a_range_still_needs_a_unit():
    assert VALIDATOR.is_valid(record(block_range(), BOX, unit="pt"))
    assert not VALIDATOR.is_valid(record(block_range(), BOX))


@pytest.mark.parametrize(
    "phrase",
    [
        "identified outside this record",
        "order of its 'blocks' array",
        "need not be reading order",
        "both ids name the same block",
        "no text has length 0 and adds no characters",
        "nothing is added between blocks",
        "must not be resolved",
        "the extraction is not known",
        "a named block is missing",
        "an id matches more than one block",
        "the end block comes before the start block",
        "an offset breaks its rule",
        "must not guess or swap",
    ],
)
def test_range_rules_validation_cannot_check_are_stated(phrase):
    assert phrase in location_branch("Block Range")["description"]


@pytest.mark.parametrize(
    "field, phrase",
    [
        ("start", "must not be greater than the length of that text"),
        ("start", "if omitted, the range starts at the beginning of the start block"),
        ("end", "must not be greater than the length of that text"),
        ("end", "must not be less than start"),
        ("end", "may be less than start when the range ends in a different block"),
        ("end", "if omitted, the range ends at the end of the end block"),
    ],
)
def test_offset_rules_validation_cannot_check_are_stated(field, phrase):
    branch = location_branch("Block Range")
    assert phrase in branch["properties"][field]["description"].lower()


@pytest.mark.parametrize(
    "branch, field",
    [
        ("Text Span", "start"),
        ("Text Span", "end"),
        ("Block Range", "start"),
        ("Block Range", "end"),
    ],
)
def test_offsets_count_code_points(branch, field):
    description = location_branch(branch)["properties"][field]["description"]
    assert "Unicode code points" in description
