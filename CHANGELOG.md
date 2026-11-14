# Changelog

## 2.5.4 - 2026-11-14

- Retain cast labels and URLs, and qualify upload dates instead of treating page-comment timestamps as publication dates.

## 2.5.3 — 2026-10-27

- Fix default search pagination and avoid double-encoding spaces in search terms.
- Return real thumbnails and clean titles from listings, and skip profile cards that are not videos.
- Decode HTML entities in profile JSON results.
- Support both property-style and method-style author and performer helpers.
- Bound collaborator loading so a missing profile does not abort the whole result.
- Handle empty channels and model URL aliases, and export Channel and Account.
- Use the published `eaf-base-api>=4.2.5` dependency.

