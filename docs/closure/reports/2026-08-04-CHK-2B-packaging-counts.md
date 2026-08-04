# Packaging Claims Audit: 2026-08-04

Status: CURRENT as of 2026-08-04.

Mechanical re-derivation of every count, command name, path claim and version string in docs/PACKAGING.md against the actual repository tree.

## Stale Claims

| Line | Stale Text | True Value | Derivation Command |
|------|-----------|-----------|-------------------|
| 14 | "six commands on your PATH" | 12 console scripts declared | `grep -c "^bm-" pyproject.toml` → 12 |
| 41 | "all nine `bm_*` modules and the six console scripts" | 17 py-modules + 12 console scripts | `sed -n '92,110p' pyproject.toml` shows 17 entries; `grep -c "^bm-" pyproject.toml` → 12 |
| 39-40, 47, 129 | Multiple references to version "2.0.0rc3" | Current version is "2.0.0rc13.dev1" | `cat VERSION` → 2.0.0-rc.13.dev1; `grep '^version = ' pyproject.toml` → version = "2.0.0rc13.dev1" |
| 127 | "VERSION says `2.0.0-rc.3`" | VERSION says "2.0.0-rc.13.dev1" | `cat VERSION` → 2.0.0-rc.13.dev1 |
| 146 | "scripts/install.py, which does not exist" | scripts/install.py exists at repo root | `ls /Users/khalil.maaouni/Documents/BrotherModeUp/scripts/install.py` → file exists |
| 159 | "No CI builds this" | CI has packaging install suite since 2026-08-04 | `.github/workflows/tests.yml` lines 119-129: "Run the packaging install suite" job executes `python3 tools/test_bm_packaging_install.py` |
| 22 (pyproject.toml comment) | "13 bm_* names land at the top level" | 17 py-modules are declared | `sed -n '92,110p' pyproject.toml` → 17 entries in py-modules list |

## Verification

Every command in the table above has been re-run to confirm stated true values:

| Command | Result |
|---------|--------|
| `grep -c "^bm-" pyproject.toml` | 12 ✓ |
| `sed -n '92,110p' pyproject.toml` | 17 entries ✓ |
| `cat VERSION` | 2.0.0-rc.13.dev1 ✓ |
| `grep '^version = ' pyproject.toml` | version = "2.0.0rc13.dev1" ✓ |
| `ls /Users/khalil.maaouni/Documents/BrotherModeUp/scripts/install.py` | file exists ✓ |
| `.github/workflows/tests.yml` lines 119-129 inspection | packaging install suite exists ✓ |
| `ls tools/bm_*.py \| wc -l` | 17 ✓ |

All verification commands have been re-executed and confirm the stated true values. No discrepancies found in re-verification.
