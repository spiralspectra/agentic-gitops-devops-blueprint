# CodeMender — On-Demand Security Scanning

CodeMender is an autonomous code-security scanning agent on Google Cloud. It finds vulnerabilities (LLM-guided scan), verifies them (writes and runs a proof-of-concept exploit in a local sandbox), and fixes them (generates a patch, re-runs the build/tests and the exploit).

> **Important Decision:** CodeMender is **not** a stage in the automated CI/CD pipeline for this repository. It is run on demand from an engineer's terminal; patches and fixes proceed through the standard PR review and verification gates.

---

## 1. Local Setup

1. **CLI Installation**: Install the `cm` binary on your system PATH.
2. **Credentials**: Authenticate Application Default Credentials with `roles/aiplatform.user` on the Google Cloud project:
   ```bash
   gcloud auth application-default login
   ```
3. **Dependencies Pre-fetched**: Ensure local python virtual environment is initialized:
   ```bash
   uv sync --extra dev
   ```

---

## 2. Running Scans

Use the provided wrapper script `./codemender/cm.sh` which enforces containment flags:

```bash
# Check environment and credentials health
./codemender/cm.sh health --strict

# Initialize configuration verification
./codemender/cm.sh init --verify

# Run offline build test
./codemender/cm.sh build

# Scan agent codebase in quick mode
./codemender/cm.sh find agents/ --quick

# Scan only changes introduced in current Git branch
./codemender/cm.sh find . --diff=origin/main

# Guided natural language inquiry
./codemender/cm.sh ask "check for potential SQL injection or RLS bypass" agents/
```

---

## 3. Sandboxed Execution & Safety
The agent executes within a `permissive-closed` sandbox environment where network access is blocked. Code changes must pass `./codemender/build.sh` (Python byte-compilation, offline unit tests, and shell script syntax validation) before patches can be proposed.
