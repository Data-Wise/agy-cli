# agy-cli

**agy-cli** is the core workflow engine for Antigravity (Gemini CLI), optimized for stats researchers working on causal inference and managing Obsidian/Atlas subprojects.

---

## 🎯 Bottom Line Up Front (BLUF)
*   **Speed:** Startup time $T < 10\text{ms}$ running entirely in-process.
*   **Assumptions Verification:** Automatically evaluates Positivity, Backdoor Exchangeability, and SUTVA.
*   **Plugins:** Connects directly to local SQLite Obsidian graphs and Atlas session files.
*   **Developer Sandbox:** Generates dummy markdown vaults and dataset CSVs to test validation engines.

---

## 🚀 Installation & Quick Start

### Installation

#### Option 1: Homebrew (Recommended)
```bash
brew tap data-wise/tap
brew install agy
```

#### Option 2: Source Installation
```bash
git clone git@github.com:Data-Wise/agy-cli.git
cd agy-cli
uv sync --all-extras
```

### Basic Commands

#### 1. Show CLI Status
```bash
uv run agy status
```

#### 2. Run Causal Inference Assumptions Validation
```bash
uv run agy eval study_design.yaml
```

#### 3. Compile Causal Diagram to R ggdag/dagitty Code
```bash
uv run agy dag "W -> Y, X -> W, X -> Y" -t W -y Y
```

#### 4. Sandbox Vault Generation (For Testing)
```bash
uv run agy sandbox generate ./my-test-vault --violations
```
