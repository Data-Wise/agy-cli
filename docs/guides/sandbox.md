# Tutorial 8 · Sandbox Vaults

⏱️ **5 minutes** • 🟢 Beginner • ✓ 3 steps

> **TL;DR** (30 seconds)
> - **What:** Generate mock Obsidian database graphs, covariate balance CSV datasets, and Atlas YAML logs using `cagy sandbox`.
> - **Why:** Safely stress-test assumptions and run validation diagnostics in an isolated test workspace.
> - **How:** Run `cagy sandbox generate ./my-sandbox --violations positivity`.
> - **Next:** [Command Reference](commands.md)

---

## What Gets Generated

A single `cagy sandbox generate` call creates a complete self-contained test environment:

```text
./my-sandbox/
├── vault_db.sqlite          ← Mock Obsidian SQLite graph
├── causal_data.csv          ← Observational dataset (treatment, outcome, covariates)
├── study_design.yaml        ← Ready-to-use eval config
├── atlas/
│   ├── sessions.yaml        ← Empty Atlas sessions file
│   └── registry.yaml        ← Empty Atlas registry file
```

---

## Step 1 — Generate a Clean Vault

```bash
cagy sandbox generate ./test-vault
```

Output:

```
╭─ Sandbox Generator ────────────────────────────────────────────╮
│ ✔ Sandbox Vault successfully generated!                        │
│                                                                │
│ Location:       ./test-vault                                   │
│ Obsidian DB:    ./test-vault/vault_db.sqlite                   │
│ Causal Data:    ./test-vault/causal_data.csv                   │
│ Study Design:   ./test-vault/study_design.yaml                 │
│ Atlas Sessions: ./test-vault/atlas/sessions.yaml               │
│ Atlas Registry: ./test-vault/atlas/registry.yaml               │
│                                                                │
│ Violations injected: False                                     │
╰────────────────────────────────────────────────────────────────╯
```

---

## Step 2 — Generate with Injected Violations

Inject Positivity, Exchangeability, and SUTVA violations for negative testing:

```bash
cagy sandbox generate ./test-vault-violations --violations
```

Then run eval on it to confirm the engine catches them:

```bash
cagy eval ./test-vault-violations/study_design.yaml --non-interactive
```

Expected: all three assumption checks **fail** with violation details.

---

## Step 3 — Use in Pytest Fixtures

Integrate sandboxes into your test suite via a `pytest` fixture:

```python
import pytest
from agy.core.sandbox import SandboxVault

@pytest.fixture
def clean_vault(tmp_path):
    sandbox = SandboxVault(tmp_path / "sandbox")
    return sandbox.build(violations=False)

@pytest.fixture
def violation_vault(tmp_path):
    sandbox = SandboxVault(tmp_path / "sandbox")
    return sandbox.build(violations=True)

def test_positivity_violation_detected(violation_vault):
    # eval the generated study_design.yaml
    design_path = violation_vault["design_path"]
    # ... assert violations are reported
```

---

## Step 4 — Combine with `cagy obs`

The generated `vault_db.sqlite` is a valid Obsidian SQLite database — immediately auditable:

```bash
cagy obs --db-path ./test-vault/vault_db.sqlite health
cagy obs --db-path ./test-vault/vault_db.sqlite orphans
cagy obs --db-path ./test-vault/vault_db.sqlite hubs --sort pagerank
```

---

## ✅ What's Next

| Ready to... | Go to |
|---|---|
| Understand what violations mean | [Tutorial 2 → Causal Assumptions](../tutorials/02-causal-assumptions.md) |
| Audit the generated vault graph | [Tutorial 5 → Obsidian Vault Audit](plugins.md) |
| Write tests against real CLI output | [Development & CI](development_workflows.md) |
