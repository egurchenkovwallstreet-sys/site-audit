#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Запустите с sudo или от root."
  exit 1
fi

apt-get update
apt-get upgrade -y
apt-get install -y git curl ca-certificates

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi

if ! docker compose version >/dev/null 2>&1; then
  apt-get install -y docker-compose-plugin || true
fi

echo "Docker готов. Добавьте пользователя в группу docker:"
echo "  usermod -aG docker \$SUDO_USER"
echo "Затем перелогиньтесь и клонируйте репозиторий (см. docs/server-setup.md)."