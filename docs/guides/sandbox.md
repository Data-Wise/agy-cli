# Sandbox Vault Generator

The Sandbox Vault Generator automates creating temporary Obsidian vaults, mock databases, and causal datasets for integration and end-to-end (E2E) testing.

---

## 🛠️ CLI Usage

To generate a test sandbox vault at a specified path:
```bash
agy sandbox generate ./my-sandbox-vault
```

To generate a vault with pre-injected positivity, exchangeability, and SUTVA violations:
```bash
agy sandbox generate ./my-sandbox-vault --violations
```

---

## 🐍 Python API Usage

You can use the `SandboxVault` helper programmatically inside tests and scripts.

```python
from pathlib import Path
from agy.core.sandbox import SandboxVault

# Instantiate the sandbox helper
sandbox = SandboxVault(Path("./my-sandbox-vault"))

# Generate the directory structure, DB, and datasets
results = sandbox.build(violations=False)

print(results["db_path"])      # Path to mock sqlite database
print(results["data_path"])    # Path to mock causal CSV dataset
print(results["design_path"])  # Path to study_design.yaml
```

### Pytest Fixture Integration
Define a fixture inside your tests to manage sandboxes cleanly:
```python
import pytest
from agy.core.sandbox import SandboxVault

@pytest.fixture
def temp_vault(tmp_path):
    sandbox = SandboxVault(tmp_path / "sandbox")
    results = sandbox.build(violations=False)
    yield results
    # Teardown logic if needed (tmp_path is cleaned by pytest automatically)
```
