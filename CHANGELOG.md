# Changelog

## v0.8.0 (2026-10-17)

The launch release of OATS (Open Annotation Task Schemas).

### Breaking changes

- Every schema's top-level `version` keyword is renamed `x-version`. The stable JSON Schema specification only permits non-standard keywords with the `x-` prefix; draft 2020-12 ignores unknown keywords either way, so this eases the move to the stable specification. Records are unaffected. Tools that read a schema's version should read `x-version`, and fall back to `version` for releases up to 0.7.0, which keep it.
- `regression`: `points` must hold at least one point. A regression with no points made no prediction.

### Added

- `ranking`: an ordered list of items related to a query, such as search results, retrieved passages, reranker output, recommendations and near-duplicate matches. Each result has a `rank` (tied items share one), an `id` of up to 2048 characters (so it can hold a URI; the second exception to the 128-character identifier rule), and an optional normalized `score`.
- `entity-extraction`: optional `relations` record directed links between entities, such as which price belongs to which line item. Relation labels can come from `relation_vocabulary` or `relation_vocabulary_url`. When `relations` is not empty, every entity requires an `id`.

### Changed

- An empty main list no longer needs other fields alongside it. In `classification`, `entity-extraction`, `object-detection` and `temporal-segmentation`, an empty list previously required `vocabulary`, `vocabulary_url` or `producer`. An empty list should mean "checked and found nothing".
- The `x-license` notice is "Copyright 2025-2026 The OATS Authors". Copyright is held by the contributors listed in `AUTHORS`. The licence is still Apache-2.0.

### Fixed

- `document-extraction`: the `page_width` and `page_height` descriptions no longer imply that page sizes must be in `px` or `pt` when `unit` is `normalized` or `per_mille`.
- Descriptions no longer assume a record is attached to a file or annotation: `classification.labels`, `object-detection.objects` (and an object's `id` and `score`), and `track_id` in `audio-transcription` and `temporal-segmentation`.

## v0.7.0 (2026-10-14)

The first release under the OATS name, and the first served from oatschema.org.

### Breaking changes

- Every schema's `$id` is now `https://oatschema.org/0.7.0/<name>`, so each version has its own identifier. Earlier releases keep their `https://dorsalhub.com/schemas/open/<name>` identifiers.
- `audio-transcription`: `track_id` and `speaker.id` must be strings of at most 128 characters. Numeric identifiers are written as strings, such as `"0"`.

### Added

- `temporal-segmentation`: labelled time intervals in a media source, such as chapters, scenes, shots, speaker turns and detected events. Segments may overlap, may nest, and need not cover the whole source.

### Changed

- Identifier fields (`id` and names ending in `_id`) are strings of at most 128 characters in every schema. The one exception is the GeoJSON feature `id` in `geolocation`.
- `x-license.url` points to the licence in [oatschema/oats](https://github.com/oatschema/oats).

## v0.6.0 (2026-10-14)

### Fixed

- Coordinate limits that depend on `unit` no longer apply when `unit` is missing. Previously, a record without `unit` was silently limited to coordinates of at most 1. `unit` is now required whenever geometry is present.

### Changed

- Every open object limits the length of its keys.
- Inline `vocabulary` lists must be unique and hold at most 100 labels. Use `vocabulary_url` for larger vocabularies.
- `document-extraction`, `entity-extraction` and `object-detection` share identical geometry definitions.
- `entity-extraction`: an entity's location can be a text span.
- `geolocation` follows RFC 7946.
- `regression`: `quantile_level` is required when `statistic` is `"quantile"`, and only allowed then.
- `llm-output`: adds `generation_params.top_k` and `generation_metadata.usage.cached_prompt_tokens`.

## v0.5.0 (2026-02-20)

### Changed

- `document-extraction`: `text` is only required when `block_type` is `"text"` or `"line"`, so purely visual elements such as logos no longer need placeholder text.
- `document-extraction`: `block_type` accepts `"multi_polygon"`, for blocks that are visually split or occluded. This maps one-to-one onto COCO segmentation arrays.
- `document-extraction`: `page_width` and `page_height` accept either a single number or a list of widths or heights for specific pages, for documents with mixed page sizes.

## v0.4.0 (2026-01-25)

### Added

- `audio-transcription`: `duration`.

## v0.3.0 (2026-01-20)

### Added

- `embedding`: sparse vectors, as an object with parallel `indices` and `values` arrays and a `dimensions` count. Plain arrays of numbers still work.

### Changed

- `embedding`: `target` may be up to 256 characters, to fit file paths and longer hashes.

## v0.2.0 (2025-12-30)

### Changed

- The `_license` field is renamed `x-license`, to follow JSON Schema's rules for unknown keywords.

## v0.1.2 (2025-12-27)

### Fixed

- `entity-extraction`: polygons no longer accept arbitrary extra fields.

## v0.1.1 (2025-12-16)

### Fixed

- Every `date-time` string is limited to 128 characters.
