#!/bin/bash
# deploy.sh — Atualiza o weather-analytics no servidor de produção
# Uso: bash deploy.sh
set -euo pipefail

echo "→ Delegando para deploy centralizado do infra..."
/home/ubuntu/infra/deploy/deploy-streamlit-weather.sh
