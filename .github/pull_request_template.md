Fixes #

### Summary
- 

### Verification Evidence (5 Required Gates)
- [ ] `lint`: `uv run ruff check --config pyproject.toml . && uv run ruff format --check --config pyproject.toml . && uv run codespell --toml pyproject.toml .`
- [ ] `terraform-plan`: read-only plan clean (no unauthorized destroys or replacements)
- [ ] `tests`: `uv run pytest tests/unit tests/integration -v`
- [ ] `evals`: `python tests/eval/check_thresholds.py` (no quality floors breached or thresholds lowered)
- [ ] `frontend-build`: container build & embeddability smoke check green (embeddable headers, no X-Frame-Options)
- [ ] Documentation updated if commands, gates, or environment variables changed
