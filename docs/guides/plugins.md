# Plugins: Obsidian & Atlas Integrations

The `agy` CLI implements an in-process plugin architecture designed to integrate knowledge vaults and active developer sessions.

---

## 🪨 Obsidian Knowledge Bridge (`agy obs`)

The Obsidian plugin runs sqlite queries targeting local vault indexes to maintain knowledge graph health.

### Commands

#### 1. List Orphan Notes
Finds notes with no incoming or outgoing connections ($k_{in} = 0$ and $k_{out} = 0$).
```bash
agy obs --db-path ~/vault_db.sqlite orphans
```

#### 2. Find central Hub Notes
Identifies hub notes ranked by PageRank or connection degrees.
```bash
agy obs --db-path ~/vault_db.sqlite hubs --sort pagerank --limit 5
```

#### 3. Graph Health Audit
Detects broken internal note links.
```bash
agy obs --db-path ~/vault_db.sqlite health
```

---

## 🗺️ Atlas Session Synchronizer (`agy atlas`)

The Atlas plugin reads session logs to bridge CLI activities with background workspace context.

### Commands

#### 1. Show Session Status
Displays the active workspace project, task, start time, and current duration.
```bash
agy atlas --sessions-path ~/sessions.yaml status
```

#### 2. View Breadcrumb Trail
Prints the most recent developer breadcrumbs (commands executed or files touched).
```bash
agy atlas --registry-path ~/registry.yaml trail --limit 10
```

#### 3. Start a new Active Session
Creates and registers a new active workspace project session.
```bash
agy atlas --sessions-path ~/sessions.yaml start-session --project causal-analysis --task "Data modeling" --desc "Fitting propensity scores"
```

#### 4. Log Breadcrumbs
Appends a custom breadcrumb item to the registry trail.
```bash
agy atlas --registry-path ~/registry.yaml log-crumb "Ran check_covariate_balance" --type "command"
```

---

## 🛠️ R Package Validation Bridge (`agy rforge`)

The RForge plugin implements an in-process bridge that executes package checks, document compiling, and unit testing within an R subprocess.

### Commands

#### 1. Compile Documentation
Runs `devtools::document()` to update help documents and namespaces from Roxygen2 syntax.
```bash
agy rforge --pkg-dir /path/to/package document
```

#### 2. Run Tests
Runs unit testing suites using `devtools::test()`.
```bash
agy rforge --pkg-dir /path/to/package test
```

#### 3. Run Package Checks
Executes check validations utilizing `devtools::check(document = FALSE)`.
```bash
agy rforge --pkg-dir /path/to/package check
```

