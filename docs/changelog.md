# Changelog

All notable changes to `agy-cli`. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

---

## [0.3.0] — 2026-06-27

### Added
- Obsidian graph visualization command (`cagy obs graph`) to output subgraphs in Mermaid or ASCII tree structures.
- Literature gap finder command (`cagy obs gaps`) to discover isolated methodological concepts and unconnected project/setting notes.

---

## [0.2.1] — 2026-06-27

### Changed
- Renamed CLI entrypoint command from `agy` to `cagy` to avoid conflicts with Google's Antigravity CLI.
- Read version dynamically from package metadata to prevent stale CLI version reports.

---

## [0.2.0] — 2026-06-27

### Added
- Atlas Session Sync tutorial (Tutorial 6)
- Obsidian Vault Audit tutorial (Tutorial 5) with graph theory background
- Sandbox tutorial with pytest fixture integration (Tutorial 8)
- Worktree reference page with lifecycle diagram
- Custom 404 page
- γ favicon and logo
- Full MkDocs site redesign with Material theme, custom CSS, and 8 tutorials
- CI/CD workflow for automated docs deployment to GitHub Pages
- Homebrew tap integration with automated release pipeline

### Changed
- Home page feature grid now showcases `obs` and `rforge` (replacing `balance`/`sandbox`)
- All tutorial pages upgraded with **What's Next** navigation tables
- `development_workflows.md` updated with worktree integration and release pipeline docs

---

## [0.1.0] — 2024-06-01

### Added
- `cagy eval` — concurrent causal assumption validator (Positivity, Exchangeability, SUTVA, Covariate Balance)
  - `--method matching` — 1:1 propensity score matching with pre/post SMD table
  - `--method weighting` — IPW reweighting
  - Auto-saves Markdown audit report after every run
- `cagy dag` — compile edge-notation DAG strings to `ggdag`/`dagitty` R code
- `cagy obs` — Obsidian SQLite graph bridge
  - `orphans` — notes with $k_{in} = 0$, $k_{out} = 0$
  - `hubs` — high-centrality notes by PageRank / degree
  - `health` — broken internal wikilinks
- `cagy atlas` — Atlas session synchronizer
  - `start-session` — named work context (project + task + description)
  - `status` — elapsed duration of active session
  - `trail` — ordered breadcrumb history
  - `log-crumb` — append timestamped activity entry
- `cagy rforge` — R package devtools bridge
  - `check` — `devtools::check(document = FALSE)`
  - `test` — `devtools::test()`
  - `document` — `devtools::document()`
- `cagy sandbox generate` — isolated test vault with mock SQLite, CSV, and YAML
  - `--violations` — inject Positivity, Exchangeability, and SUTVA violations
- `cagy worktree` — git worktree lifecycle manager
  - `add` / `list` / `remove`
- Rotating error log at `~/.config/obs/obs.log` (5 MB, 3 backups)
- `AGY_LOG_FILE` environment variable override
- Homebrew distribution via `data-wise/tap`

---

## Links

- [GitHub Releases](https://github.com/Data-Wise/agy-cli/releases)
- [Issues](https://github.com/Data-Wise/agy-cli/issues)
- [Homebrew Tap](https://github.com/Data-Wise/homebrew-tap)
