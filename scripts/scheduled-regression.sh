#!/usr/bin/env bash
# Плановая регрессия (VPS). Не дергать вручную в часы пик — cron в 01:00–03:00 MSK.
set -euo pipefail

REPO="${REPO:-/root/apps/site-audit}"
LOG_DIR="${REGRESSION_LOG_DIR:-/var/log/site-audit}"
LOCK="${REGRESSION_LOCK:-/var/run/site-audit-regression.lock}"
export TZ="${REGRESSION_TZ:-Europe/Moscow}"

MODE="${1:-auto}"
mkdir -p "$LOG_DIR"

_ts() {
  date '+%Y-%m-%d %H:%M:%S %Z'
}

_log() {
  echo "[$(_ts)] $*" | tee -a "${LOG_DIR}/regression.log"
}

if [[ -f "$LOCK" ]]; then
  _log "SKIP: уже идёт прогон (lock $LOCK)"
  exit 0
fi

_hour="$(date +%H)"
if [[ "$MODE" == "auto" ]]; then
  MODE="weekly"
fi

# Доп. защита: cron должен вызывать с weekly|monthly; вне окна — только с FORCE=1
if [[ "${FORCE:-0}" != "1" ]] && [[ "$MODE" != "weekly" && "$MODE" != "monthly" ]]; then
  _log "ERROR: укажите weekly или monthly"
  exit 2
fi
if [[ "${FORCE:-0}" != "1" ]] && { [[ "$_hour" -lt 1 ]] || [[ "$_hour" -ge 3 ]]; }; then
  _log "SKIP: вне окна 01:00–02:59 MSK (сейчас час=$_hour). FORCE=1 — принудительно."
  exit 0
fi

cleanup() {
  rm -f "$LOCK"
}
trap cleanup EXIT
echo "$$" >"$LOCK"

cd "$REPO"
git -C "$REPO" pull -q 2>/dev/null || true

_run() {
  local reg_file="$1"
  local label="$2"
  local stamp
  stamp="$(date '+%Y%m%d-%H%M')"
  local out="${LOG_DIR}/${label}-${stamp}.log"
  _log "START $label ($reg_file) -> $out"
  (
    set -o pipefail
    cd "$REPO"
    REGRESSION_FILE="$reg_file" nice -n 10 ionice -c2 -n7 bash scripts/vps-regression.sh
  ) 2>&1 | tee -a "$out" | tee -a "${LOG_DIR}/regression.log"
  local ec=${PIPESTATUS[0]}
  if [[ "$ec" -eq 0 ]]; then
    _log "OK $label exit=$ec"
  else
    _log "FAIL $label exit=$ec (см. $out)"
  fi
  return "$ec"
}

fail=0
case "$MODE" in
  weekly)
    _run "regression_urls.json" "strict9" || fail=1
    ;;
  monthly)
    _run "regression_urls_panel50.json" "panel50" || fail=1
    ;;
  *)
    _log "ERROR: unknown mode $MODE"
    exit 2
    ;;
esac

exit "$fail"