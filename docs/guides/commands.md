# Command Reference Guide

This document lists all available commands in the `agy` CLI utility, detailing their purposes, subcommands, options, and example invocations.

---

## 📌 Global Structure
```text
agy [OPTIONS] COMMAND [ARGS]...
```

*   **`--version`**: Show the CLI engine version and exit.
*   **`--help`**: Show global help documentation.

---

## 1. `status`
Show the baseline status of the `agy-cli` engine.
```bash
cagy status
```

---

## 2. `eval`
Concurrently evaluate observational study causal assumptions (Positivity, Exchangeability, SUTVA, and Covariate Balance).
```bash
cagy eval [STUDY_DESIGN_FILE] [OPTIONS]
```

### Options
*   **`-t, --treatment <NAME>`**: Specify the exposure variable.
*   **`-o, --outcome <NAME>`**: Specify the outcome variable.
*   **`-c, --covariates <LIST>`**: Comma-separated list of confounders.
*   **`-d, --data <PATH>`**: Path to dataset CSV.
*   **`-g, --dag-str <DAG>`**: Causal DAG paths description.
*   **`--interactive / --non-interactive`**: Enable or disable interactive survey prompts.
*   **`--method <none|matching|weighting>`**: Propensity score adjustment method for balance checking (default: `none`).

### Examples
Validate assumptions using inline settings:
```bash
cagy eval -t W -o Y -c X -d ./data.csv -g "X -> W, X -> Y, W -> Y" --non-interactive
```

Evaluate covariate balance after 1:1 propensity score matching:
```bash
cagy eval -t W -o Y -c X -d ./data.csv -g "X -> W, X -> Y, W -> Y" --non-interactive --method matching
```

---

## 3. `dag`
Compile textual DAG descriptions to R code.
```bash
cagy dag <DAG_STRING> [OPTIONS]
```

### Options
*   **`-o, --output <PATH>`**: Output compiled R script to file path.
*   **`-t, --treatment <NAME>`**: Inject exposure metadata.
*   **`-y, --outcome <NAME>`**: Inject outcome metadata.

### Examples
Generate and compile to an R file:
```bash
cagy dag "W -> Y, X -> W, X -> Y" -t W -y Y -o my_dag.R
```

---

## 4. `obs` (Obsidian Bridge)
Directly query SQLite databases indexing local Obsidian vaults.
```bash
cagy obs --db-path <DB_PATH> COMMAND [ARGS]...
```

### Subcommands
*   **`orphans`**: List notes with no connections ($k_{in} = 0$, $k_{out} = 0$).
*   **`hubs`**: List central notes.
    *   *Options:* `-l, --limit <INT>` (default 10), `-s, --sort <pagerank|out_degree|in_degree|total_degree>`.
*   **`health`**: List broken internal note links.

---

## 5. `atlas` (Atlas Bridge)
Bridge CLI workspace sessions with the Atlas state synchronizer.
```bash
cagy atlas --sessions-path <SESSIONS_YAML> --registry-path <REGISTRY_YAML> COMMAND [ARGS]...
```

### Subcommands
*   **`status`**: Show the current active project session and its elapsed duration.
*   **`trail`**: List recent developer breadcrumbs.
    *   *Options:* `-l, --limit <INT>` (default 10).
*   **`start-session`**: Starts a new active Atlas session.
    *   *Options:* `-p, --project <NAME>` (required), `-t, --task <NAME>` (required), `-d, --desc <TEXT>`.
*   **`log-crumb`**: Append a breadcrumb trail item.
    *   *Arguments:* `<TEXT>` (required).
    *   *Options:* `-t, --type <NAME>` (default "command"), `-p, --project <NAME>`.

---

## 6. `sandbox` (Sandbox Vaults)
Generate isolated sandbox vault environments containing mock data, notes, and configs.
```bash
cagy sandbox generate <VAULT_PATH> [OPTIONS]
```

### Options
*   **`--violations`**: Inject positivity, exchangeability, and SUTVA violations.

### Examples
```bash
cagy sandbox generate ./my-sandbox-dir --violations
```

---

## 7. `worktree` (Git Worktree Isolation)
Automate persistent git worktrees for clean context-isolated development.
```bash
cagy worktree COMMAND [ARGS]...
```

### Subcommands
*   **`add <NAME>`**: Create a persistent worktree off `dev` branch.
*   **`list`**: List registered git worktrees.
*   **`remove <NAME>`**: Decommission worktree and delete its local branch.

---

## 8. `rforge` (R Package Bridge)
Directly check, test, and document R packages using an in-process R bridge.
```bash
cagy rforge [OPTIONS] COMMAND [ARGS]...
```

### Options
*   **`--pkg-dir <PATH>`**: Path to the target R package directory.

### Subcommands
*   **`check`**: Run package integrity check via `devtools::check(document = FALSE)`.
*   **`test`**: Run unit test suites via `devtools::test()`.
*   **`document`**: Compile Roxygen2 documentation via `devtools::document()`.

