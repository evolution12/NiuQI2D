# Backend Integration Checklist

> Owner: backend integration and test.
> Goal: define non-blocking acceptance checkpoints for frontend integration and the M5-06 end-to-end flow.

This checklist is intentionally contract-focused. During early development, failing or missing endpoints should be reported with reproducible steps, not treated as a blocker for unrelated feature work.

---

## 1. Current Baseline

Checked on 2026-05-23 against the current workspace:

| Area | Current status | Notes |
|------|----------------|-------|
| `/health` | Implemented | Returns `{"status":"ok"}` without `/api/v1` prefix. |
| `/api/v1/upload` | Implemented | Supports `reference` and `raw_image`; validates extension, content type, size, and image bytes. |
| `/api/v1/assets` | Route shell only | No callable CRUD endpoints yet. |
| `/api/v1/generation` | Route shell only | No callable generate/history endpoints yet. |
| `/api/v1/export` | Route shell only | No callable export endpoints yet. |
| `/api/v1/projects` | Route shell only | No callable CRUD endpoints yet. |
| `/api/v1/styles` | Route shell only | No callable CRUD/analyze endpoints yet. |
| `/api/v1/settings` | Route shell only | No callable config/test endpoints yet. |
| Error envelope | Implemented globally | `NiuQIError`, validation errors, and unexpected errors use `{ "error": { "code", "message", "details" } }`. |
| Schema source | Implemented for existing models | `python/fastapi_app/schemas.py` exists; frontend `types/index.ts` is not present yet. |
| Test tooling | Needs setup before M5-06 | `fastapi.testclient` requires `httpx`; add test dependencies when automated E2E work starts. |

---

## 2. Integration Nodes A-F

### Node A: Generation API

Backend completion signal: M2-04 generation API is runnable from curl or an HTTP client.

Required checks:

- [ ] `POST /api/v1/generation` accepts prompt, style, asset type, subtype when applicable, generation mode, and optional reference image.
- [ ] Fast preview mode returns 4-6 candidates or a documented test stub response when API mocking is enabled.
- [ ] Quality mode returns 2-3 candidates or a documented test stub response when API mocking is enabled.
- [ ] Candidate images are stored through `StorageManager` under the data directory.
- [ ] Post-processing log is persisted with each generation record.
- [ ] Selected candidate can be promoted into the asset library.
- [ ] Missing API key returns the standard error envelope with a stable code, preferably `API_KEY_INVALID`.
- [ ] Invalid parameters return `INVALID_PARAM` with useful `details`.

Frontend can start: M2-05 generation page UI.

Minimum reproducible handoff:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/generation \
  -H "Content-Type: application/json" \
  -d "{\"project_id\":\"<project_id>\",\"style_id\":\"<style_id>\",\"prompt\":\"idle hero\",\"asset_type\":\"character\",\"asset_subtype\":\"static_image\",\"mode\":\"preview\"}"
```

### Node B: Asset Management API

Backend completion signal: M3-04 asset CRUD/list/status endpoints are runnable.

Required checks:

- [ ] `GET /api/v1/assets?project_id=<id>` lists only assets for the requested project.
- [ ] `POST /api/v1/assets` creates an asset from an existing stored image path.
- [ ] `GET /api/v1/assets/{asset_id}` returns a single asset.
- [ ] `PATCH /api/v1/assets/{asset_id}` updates name, status, tags, and paths where supported.
- [ ] `DELETE /api/v1/assets/{asset_id}` deletes or marks the asset according to the final product decision.
- [ ] Unknown asset returns `RESOURCE_NOT_FOUND`.
- [ ] `AssetResponse` matches frontend `Asset` type exactly once `types/index.ts` exists.

Frontend can start: M3-05 asset library page UI.

### Node C: Project Management API

Backend completion signal: M4-02 project CRUD/list endpoints are runnable.

Required checks:

- [ ] `GET /api/v1/projects` lists projects ordered predictably.
- [ ] `POST /api/v1/projects` creates a project with optional `style_id`.
- [ ] `GET /api/v1/projects/{project_id}` returns project details.
- [ ] `PATCH /api/v1/projects/{project_id}` updates name and default style.
- [ ] `DELETE /api/v1/projects/{project_id}` cleans project-owned assets and generation records according to DB cascade rules.
- [ ] Project isolation is observable through asset and generation history queries.
- [ ] Unknown project returns `RESOURCE_NOT_FOUND`.

Frontend can start: M4-05 sidebar and project switching.

### Node D: Settings API

Backend completion signal: M5-01 settings read/write/test endpoints are runnable.

Required checks:

- [ ] `GET /api/v1/settings` returns provider/model fields and key-set booleans, never raw API keys.
- [ ] `PUT /api/v1/settings` persists raw API keys only to local `{data_dir}/config.json`.
- [ ] `POST /api/v1/settings/test-image-api` returns `success`, `message`, and `latency_ms`.
- [ ] `POST /api/v1/settings/test-text-api` returns `success`, `message`, and `latency_ms`.
- [ ] Preview and quality image model settings can be changed independently.
- [ ] Invalid key or failed provider call returns a standard error envelope or a failed test response, consistently documented.

Frontend can start: M5-03 settings page UI.

### Node E: Style API

Backend completion signal: M4-01 style CRUD and reference-image analysis endpoints are runnable.

Required checks:

- [ ] `GET /api/v1/styles` lists style profiles.
- [ ] `POST /api/v1/styles` creates a style profile.
- [ ] `GET /api/v1/styles/{style_id}` returns a single profile.
- [ ] `PATCH /api/v1/styles/{style_id}` updates palette, size, perspective, reference path, and `extra_params`.
- [ ] `DELETE /api/v1/styles/{style_id}` handles styles referenced by projects or generation records predictably.
- [ ] Reference image upload can be linked to a style.
- [ ] Reference image analysis returns a stable schema that frontend can render.
- [ ] `ArtStyle`, `Perspective`, and `StyleProfileResponse` match frontend types.

Frontend can start: M4-04 style library UI.

### Node F: Export API

Backend completion signal: M3-03 export endpoints are runnable.

Required checks:

- [ ] `POST /api/v1/export` supports `png_single`, `spritesheet_png_json`, and `tileset_png_json` where applicable.
- [ ] Export output is written under the configured exports directory unless user-selected path support is explicitly added.
- [ ] Sprite sheet export emits PNG plus JSON metadata with frame coordinates.
- [ ] Tileset export emits PNG plus JSON metadata with tile coordinates.
- [ ] Export records are persisted and queryable.
- [ ] Exported assets move to `exported` status.
- [ ] Invalid asset combinations return `INVALID_PARAM`.
- [ ] Missing assets return `RESOURCE_NOT_FOUND`.

Frontend can start: M3-06 export page UI.

---

## 3. Endpoint Smoke Matrix

Run this matrix whenever a node claims "ready". For endpoints that are not implemented yet, record `not implemented` plus the route file and current branch.

| Feature | Endpoint group | Happy path | Error path |
|---------|----------------|------------|------------|
| Health | `/health` | `GET` returns `status=ok` | Not applicable. |
| Upload | `/api/v1/upload` | Valid PNG upload returns path/url | Invalid MIME or missing required form field returns error envelope. |
| Settings | `/api/v1/settings` | Read, update, test image, test text | Invalid provider/key failure is stable and documented. |
| Projects | `/api/v1/projects` | Create, list, get, update, delete | Unknown id returns `RESOURCE_NOT_FOUND`. |
| Styles | `/api/v1/styles` | Create, upload reference, analyze, update, list | Bad enum returns `INVALID_PARAM` or validation envelope. |
| Generation | `/api/v1/generation` | Configure key, generate candidates, select candidate | Missing key, timeout, provider failure use stable codes. |
| Assets | `/api/v1/assets` | Asset appears after selection; list/filter/update works | Cross-project or missing asset does not leak data. |
| Export | `/api/v1/export` | Export selected assets; metadata is valid | Unsupported format or missing asset returns standard error. |

---

## 4. Error Envelope Contract

Every backend error consumed by the frontend must follow this shape:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "资源不存在",
    "details": null
  }
}
```

Acceptance checks:

- [ ] No route returns raw `HTTPException` detail objects to frontend callers.
- [ ] Validation errors use `error.code = "INVALID_PARAM"`.
- [ ] Provider failures use stable codes such as `API_KEY_INVALID`, `API_CALL_FAILED`, or `TIMEOUT`.
- [ ] Unexpected exceptions return `INTERNAL_ERROR` without leaking tracebacks.
- [ ] `details` is either `null` or a JSON object; never a string.

Suggested quick checks:

```bash
curl -i http://127.0.0.1:8000/api/v1/projects/not-found
curl -i -X POST http://127.0.0.1:8000/api/v1/upload
```

---

## 5. Schema Sync Checklist

Source of truth: `python/fastapi_app/schemas.py`.

When frontend `types/index.ts` exists, check:

- [ ] Every TypeScript interface or type includes a comment naming the matching Pydantic class.
- [ ] Enum literal values match Python enum values exactly:
  - [ ] `ArtStyle`
  - [ ] `Perspective`
  - [ ] `AssetType`
  - [ ] `AssetSubtype`
  - [ ] `AssetStatus`
  - [ ] `ExportFormat`
- [ ] Required vs optional fields match Pydantic defaults and `| None`.
- [ ] Timestamp fields are represented as strings in TypeScript.
- [ ] `ExportRecordResponse.metadata` maps from backend serialization alias, not the SQLAlchemy field name `export_metadata`.
- [ ] API client request/response names map to Pydantic request/response classes.

Report mismatches as a small table:

| Schema | Field | Backend | Frontend | Impact |
|--------|-------|---------|----------|--------|

---

## 6. M5-06 End-to-End Test Nodes

Primary flow priority:

1. Configure API key.
2. Generate candidates.
3. Run post-processing.
4. Save selected candidate to asset library.
5. Export selected asset.
6. Query generation/export/asset history.

### E2E-01: Settings and API Readiness

- [ ] Start backend with isolated `NIUQI2D_DATA_DIR`.
- [ ] `GET /health` succeeds.
- [ ] `GET /api/v1/settings` returns masked key state.
- [ ] `PUT /api/v1/settings` stores image/text providers, API keys, preview model, and quality model.
- [ ] API test endpoints return documented success or failure without exposing key values.

### E2E-02: Style and Project Setup

- [ ] Create a style profile.
- [ ] Upload a reference image with `purpose=reference`.
- [ ] Attach the reference image path to the style or run style analysis.
- [ ] Create a project using the style.
- [ ] Query projects and styles to confirm IDs are stable.

### E2E-03: Generation to Asset

- [ ] Generate preview candidates with the project/style.
- [ ] Confirm each candidate has image path, dimensions or metadata, generation record id, and postprocess log.
- [ ] Select one candidate.
- [ ] Confirm an asset is created and linked to the generation record.
- [ ] Query assets by project and generation history.

### E2E-04: Export and History

- [ ] Export the selected asset as PNG single.
- [ ] Export a compatible asset set as sprite sheet or tileset when available.
- [ ] Confirm files exist and metadata JSON parses.
- [ ] Confirm asset status becomes `exported`.
- [ ] Query export records.

### E2E-05: Isolation and Cleanup

- [ ] Create a second project.
- [ ] Confirm assets from project A do not appear in project B queries.
- [ ] Delete one project.
- [ ] Confirm project-owned data is removed or hidden according to the final deletion contract.
- [ ] Confirm unrelated project data remains available.

### E2E-06: Error and Recovery

- [ ] Clear or invalidate API key.
- [ ] Generation fails with a frontend-actionable error code.
- [ ] Restore API key or mock provider.
- [ ] Retry succeeds without orphaning partial records.
- [ ] Trigger invalid upload and invalid enum requests; both return standard error envelopes.

---

## 7. Bug Report Format

Use this compact format for integration findings:

```text
Title:
Node:
Endpoint:
Environment:
Steps:
Expected:
Actual:
Response body:
Relevant ids/files:
```

Keep fixes scoped to the failing contract unless the owning task explicitly requests broader implementation work.
