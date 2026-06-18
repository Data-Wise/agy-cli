# R package Validation Bridge (`rforge`) Tutorial

**BLUF:** The `agy rforge` plugin bridges python validation workflows with R package development by executing `devtools` commands directly in an R process.

---

## 🛠 Prerequisites

*   **R installation** with the `devtools` package installed.
*   **A valid R package directory** containing a `DESCRIPTION` file.

---

## 🚀 Commands and Usage

Execute these commands from your R package directory, or pass the package location via the `--pkg-dir` option.

### 1. Compile Documentation (`rforge document`)
Generates/updates Rd help files and `NAMESPACE` from `roxygen2` comments.
*   **Command:** `agy rforge document [--pkg-dir /path/to/pkg]`
*   **R equivalent:** `devtools::document()`

### 2. Run Unit Tests (`rforge test`)
Executes the testing suite in `tests/testthat/`.
*   **Command:** `agy rforge test [--pkg-dir /path/to/pkg]`
*   **R equivalent:** `devtools::test()`

### 3. Check Package Integrity (`rforge check`)
Performs a comprehensive package check without documenting to speed up execution.
*   **Command:** `agy rforge check [--pkg-dir /path/to/pkg]`
*   **R equivalent:** `devtools::check(document = FALSE)`

---

Integrate package validation directly into validation workflows:

```bash
# Verify docs, run tests, and run package checks sequentially
agy rforge document && agy rforge test && agy rforge check
```

---

## 📁 Recommended Directory Structure

To work correctly with `agy rforge`, ensure your R package directory is structured as follows:

```text
my_r_package/
├── DESCRIPTION         # Required: defines metadata and package dependencies
├── NAMESPACE           # Exports and imports functions
├── R/
│   └── functions.R     # R source code containing Roxygen2 comments
└── tests/
    ├── testthat.R      # Main testing runner
    └── testthat/       # Test script directory
        └── test-func.R # Individual test files
```

---

## 🏁 Step-by-Step E2E Package Validation Walkthrough

To validate your package:

1.  **Generate Documentation:** Compile the Roxygen2 markup:
    ```bash
    agy rforge --pkg-dir ./my_r_package document
    ```
2.  **Execute Tests:** Validate that all unit test files in `tests/testthat/` pass:
    ```bash
    agy rforge --pkg-dir ./my_r_package test
    ```
3.  **Run Comprehensive Check:** Verify metadata consistency and CRAN readiness:
    ```bash
    agy rforge --pkg-dir ./my_r_package check
    ```

