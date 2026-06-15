#!/usr/bin/env bash
# =============================================================================
# setup.sh — Agent doi soat ZION x SACOMBANK (Claw-a-thon 2026)
# Lo HET phan chay local: cai deps -> chay agent -> tu test endpoint.
# Phan PUSH GitHub & DEPLOY AgentBase can tai khoan cua ban -> xem cuoi script.
#
# Cach dung:
#   ./setup.sh            # tu chon: co Docker thi dung Docker, khong thi dung Python
#   ./setup.sh --local    # ep chay bang Python (venv)
#   ./setup.sh --docker   # ep build & chay bang Docker
#   ./setup.sh --sample   # dung du lieu GIA LAP thay vi data that
#   ./setup.sh --batch     # chi chay 1 lan xuat Excel (khong mo server)
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-8000}"
MODE="auto"; SAMPLE=""; BATCH=""
for a in "$@"; do
  case "$a" in
    --local)  MODE="local" ;;
    --docker) MODE="docker" ;;
    --sample) SAMPLE="--sample" ;;
    --batch)  BATCH="1" ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Tham so la: $a (bo qua)";;
  esac
done

say(){ printf "\n\033[1;36m==> %s\033[0m\n" "$*"; }
ok(){  printf "\033[1;32m✔ %s\033[0m\n" "$*"; }
err(){ printf "\033[1;31mx %s\033[0m\n" "$*" >&2; }

# --- chon mode ---
if [ "$MODE" = "auto" ]; then
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then MODE="docker"; else MODE="local"; fi
fi
say "Mode: $MODE   |   Port: $PORT   |   Sample: ${SAMPLE:-(data that)}"

# --- smoke test endpoint (curl hoac python) ---
http_get(){ # $1=url
  if command -v curl >/dev/null 2>&1; then curl -fs "$1"; else
    python3 - "$1" <<'PY'
import sys,urllib.request; print(urllib.request.urlopen(sys.argv[1],timeout=30).read().decode())
PY
  fi
}
http_post(){ # $1=url
  if command -v curl >/dev/null 2>&1; then curl -fs -X POST "$1"; else
    python3 - "$1" <<'PY'
import sys,urllib.request
r=urllib.request.Request(sys.argv[1],method="POST"); print(urllib.request.urlopen(r,timeout=120).read().decode())
PY
  fi
}

run_smoke(){ # $1=base_url
  local base="$1"
  say "Smoke test: $base/health"; http_get "$base/health"; echo; ok "health OK"
  say "Smoke test: POST $base/reconcile"; http_post "$base/reconcile"; echo; ok "reconcile OK"
}

# =============================== LOCAL (Python) ===============================
if [ "$MODE" = "local" ]; then
  command -v python3 >/dev/null 2>&1 || { err "Chua co python3. Cai Python 3.11+ roi chay lai."; exit 1; }
  say "Tao virtualenv .venv & cai dependency"
  python3 -m venv .venv
  # shellcheck disable=SC1091
  . .venv/bin/activate 2>/dev/null || . .venv/Scripts/activate
  python -m pip install -q --upgrade pip
  python -m pip install -q -r requirements.txt
  ok "Da cai xong"

  if [ -n "$SAMPLE" ]; then python -m src.generate_sample_data; fi

  if [ -n "$BATCH" ]; then
    say "Chay batch (xuat Excel 1 lan)"; python run.py ${SAMPLE:-}; 
    ok "Xong. Bao cao: data/output/DOI_SOAT_ZION_SACOMBANK.xlsx"; exit 0
  fi

  say "Khoi dong agent o cong $PORT"
  PORT="$PORT" python agent.py & APID=$!
  trap 'kill $APID 2>/dev/null || true' EXIT
  sleep 2
  run_smoke "http://127.0.0.1:$PORT"
  ok "Bao cao: data/output/DOI_SOAT_ZION_SACOMBANK.xlsx"
  echo; ok "Agent dang chay tai http://localhost:$PORT  (Ctrl+C de dung)"
  wait $APID
fi

# =============================== DOCKER =======================================
if [ "$MODE" = "docker" ]; then
  command -v docker >/dev/null 2>&1 || { err "Chua co Docker. Cai Docker Desktop roi chay lai."; exit 1; }
  docker info >/dev/null 2>&1 || { err "Docker chua chay (mo Docker Desktop, cho 'Engine running')."; exit 1; }
  IMG="zion-recon-agent:latest"
  say "Build image $IMG"; docker build -t "$IMG" .; ok "Build xong"

  if [ -n "$BATCH" ]; then
    say "Chay batch trong container"
    docker run --rm -v "$PWD/data/output:/app/data/output" "$IMG" python run.py ${SAMPLE:-}
    ok "Xong. Bao cao: data/output/DOI_SOAT_ZION_SACOMBANK.xlsx"; exit 0
  fi

  say "Chay container (cong $PORT)"
  CID=$(docker run -d -p "$PORT:8000" -v "$PWD/data/output:/app/data/output" "$IMG" ${SAMPLE:+python agent.py})
  trap 'docker rm -f "$CID" >/dev/null 2>&1 || true' EXIT
  sleep 4
  run_smoke "http://127.0.0.1:$PORT"
  ok "Bao cao da ghi ra ./data/output/"
  echo; ok "Container dang chay (id ${CID:0:12}) tai http://localhost:$PORT"
  echo "   Dung:   docker rm -f ${CID:0:12}"
fi

# =============================== NEXT STEPS ===================================
cat <<'NEXT'

────────────────────────────────────────────────────────────────────────────
✅ Phan LOCAL da chay & test xong. Hai buoc sau CAN TAI KHOAN CUA BAN (xem DEPLOY.md):

1) PUSH GITHUB (nen de repo PRIVATE - co du lieu that):
     git init && git add . && git commit -m "first deploy"
     git branch -M main
     git remote add origin https://github.com/<username>/<repo>.git
     git push -u origin main
   (hoac dung GitHub Desktop: Add Local Repo -> Publish)

2) DEPLOY AGENTBASE (GreenNode):
     git clone https://github.com/vngcloud/greennode-agentbase-skills .agentbase
     claude        # Claude Code CLI -> chon Recommended, nhap IAM key cua ban
   -> nhan link endpoint public. Nop: link repo + link endpoint (deadline 17/06 12:00).
────────────────────────────────────────────────────────────────────────────
NEXT
