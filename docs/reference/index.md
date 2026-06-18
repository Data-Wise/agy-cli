# Reference

Technical reference documentation for `agy-cli`.

<div class="grid cards" markdown>

-   :material-console:{ .lg } **Command Reference**

    ---

    Every `agy` subcommand, flag, option, and exit code.

    [:octicons-arrow-right-24: View Reference](../guides/commands.md)

-   :material-function-variant:{ .lg } **Asymptotic Theory & EIF**

    ---

    Influence functions, semiparametric efficiency bounds, doubly robust estimators.

    [:octicons-arrow-right-24: Read Reference](../guides/asymptotic_theory.md)

-   :material-source-branch:{ .lg } **Worktree Workflow**

    ---

    Git worktree conventions for context-isolated feature development.

    [:octicons-arrow-right-24: Read Reference](worktree.md)

-   :material-cog:{ .lg } **Development & CI Workflows**

    ---

    Branch strategy, GitHub Actions, local `uv` commands, and release process.

    [:octicons-arrow-right-24: Read Reference](../guides/development_workflows.md)

</div>

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `AGY_LOG_FILE` | `~/.config/obs/obs.log` | Override error log file path. Uses `RotatingFileHandler` (5 MB, 3 backups). |

**Example — redirect logs to project directory:**

```bash
export AGY_LOG_FILE=./logs/agy.log
agy eval study_design.yaml
```
