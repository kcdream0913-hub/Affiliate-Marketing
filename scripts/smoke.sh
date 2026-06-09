#!/usr/bin/env bash
# Sprint 0 smoke: compliance gate on sample corpus + SQL syntax sanity.
set -euo pipefail
cd "$(dirname "$0")/.."

python - <<'EOF'
import sys, os
sys.path.insert(0, os.getcwd())
from src.compliance import gate
r = gate(
    script="Make $10k/month while you sleep",
    caption="link in bio",
)
assert r.blocked, "smoke FAIL: HIGH creative not blocked"
r2 = gate(
    script="This stand folds flat and fits in your pocket.",
    caption="#ad Paid link in bio",
    platform_toggle_set=True,
    onscreen_text="#ad · AI-generated",
    c2pa_present=True,
)
assert not r2.blocked, "smoke FAIL: clean creative blocked"
print("smoke: compliance gate OK")
EOF

# SQL sanity: file exists and is non-trivial
test -s supabase/migrations/001_initial_schema.sql && echo "smoke: migration present"
echo "SMOKE PASS"
