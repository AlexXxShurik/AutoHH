#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

SERVER_LOG="$ROOT/input_server.log"
SERVER_PID_FILE="$ROOT/.input_server.pid"
COOKIE="$ROOT/data/cookies.pkl"

stop_all() {
  docker compose down 2>/dev/null || true
  if [ -f "$SERVER_PID_FILE" ]; then
    kill "$(cat "$SERVER_PID_FILE")" 2>/dev/null || true
    rm -f "$SERVER_PID_FILE"
  fi
}

case "${1:-}" in
  stop)
    echo "Остановка..."
    stop_all
    echo "Остановлено."
    exit 0
    ;;
esac

# сервер ввода держим запущенным в фоне (нужен и для повторного входа при истёкших куки)
if ! kill -0 "$(cat "$SERVER_PID_FILE" 2>/dev/null)" 2>/dev/null; then
  echo "Сервер ввода: http://localhost:8765"
  nohup poetry run python -m app.input_server >> "$SERVER_LOG" 2>&1 &
  echo $! > "$SERVER_PID_FILE"
  sleep 2
fi

if [ -s "$COOKIE" ]; then
  docker compose up -d --build
  echo "Контейнер запущен в фоне. Логи: docker compose logs -f autohh"
  exit 0
fi

echo "Куки не найдены — интерактивный вход (страница откроется в браузере)."
echo "Жду появления $COOKIE..."
docker compose up --build > "$ROOT/compose_login.log" 2>&1 &
COMPOSE_PID=$!

for _ in $(seq 1 180); do
  if [ -s "$COOKIE" ]; then
    echo "Куки созданы."
    break
  fi
  if ! kill -0 "$COMPOSE_PID" 2>/dev/null; then
    echo "Контейнер завершился. Логи:"
    cat "$ROOT/compose_login.log"
    exit 1
  fi
  sleep 2
done

if [ ! -s "$COOKIE" ]; then
  echo "Куки не созданы за отведённое время. Логи:"
  cat "$ROOT/compose_login.log"
  exit 1
fi

sleep 3
echo "Останавливаю интерактивный режим и запускаю контейнер в фоне..."
docker compose stop
wait "$COMPOSE_PID" 2>/dev/null || true
docker compose up -d
echo "Готово. Контейнер работает в фоне. Логи: docker compose logs -f autohh"
