#!/usr/bin/env bash
# Apply the consulting asset migration to consulting-playbook and slugger.
# Run this script from a machine with push access to both repos.
#
# Usage: bash apply-migration.sh [--dry-run]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRY_RUN="${1:-}"

log() { echo "[migration] $*"; }

if [[ "$DRY_RUN" == "--dry-run" ]]; then
  log "DRY RUN mode — no git push will occur"
fi

# ──────────────────────────────────────────────────────────────────────────────
# consulting-playbook
# ──────────────────────────────────────────────────────────────────────────────

log "Cloning consulting-playbook..."
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
git clone https://github.com/Young-Consultations/consulting-playbook "$TMP/consulting-playbook"
cd "$TMP/consulting-playbook"
git checkout -b copilot/migrate-consulting-assets
git am "$SCRIPT_DIR/0001-consulting-playbook-migrate-assets.patch"

if [[ "$DRY_RUN" != "--dry-run" ]]; then
  git push origin copilot/migrate-consulting-assets
  log "consulting-playbook branch pushed. Create PR: Migrate consulting operating assets from Slugger"
fi

# ──────────────────────────────────────────────────────────────────────────────
# slugger
# ──────────────────────────────────────────────────────────────────────────────

log "Cloning slugger..."
git clone https://github.com/Young-Consultations/slugger "$TMP/slugger"
cd "$TMP/slugger"
git checkout -b copilot/remove-consulting-assets
git am "$SCRIPT_DIR/0002-slugger-remove-assets.patch"

if [[ "$DRY_RUN" != "--dry-run" ]]; then
  git push origin copilot/remove-consulting-assets
  log "slugger branch pushed. Create PR: Remove consulting assets after consulting-playbook extraction"
fi

log "Migration complete."
log "  consulting-playbook PR: https://github.com/Young-Consultations/consulting-playbook/compare/copilot/migrate-consulting-assets"
log "  slugger PR:             https://github.com/Young-Consultations/slugger/compare/copilot/remove-consulting-assets"
