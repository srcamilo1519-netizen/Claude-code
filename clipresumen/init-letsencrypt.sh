#!/usr/bin/env bash
# One-time TLS bootstrap: issues the first Let's Encrypt certificate.
#
# Reads DOMAIN and CERTBOT_EMAIL from .env. Run once on a fresh server after
# DNS for your domain points at this VPS. Afterwards the `certbot` service
# renews automatically.
#
#   ./init-letsencrypt.sh
#
set -euo pipefail
cd "$(dirname "$0")"

# Load .env
set -a
# shellcheck disable=SC1091
[ -f .env ] && . ./.env
set +a

: "${DOMAIN:?Set DOMAIN in .env}"
: "${CERTBOT_EMAIL:?Set CERTBOT_EMAIL in .env}"

COMPOSE="docker compose -f docker-compose.prod.yml"
CERT_DIR="./certbot/conf/live/${DOMAIN}"

mkdir -p ./certbot/www "./certbot/conf/live/${DOMAIN}"

# Staging avoids hitting Let's Encrypt rate limits while testing.
# Set CERTBOT_STAGING=1 in .env to use the staging environment.
STAGING_ARG=""
if [ "${CERTBOT_STAGING:-0}" = "1" ]; then
  STAGING_ARG="--staging"
fi

echo "1/4 Creating a temporary self-signed certificate so nginx can start…"
docker run --rm \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  --entrypoint openssl certbot/certbot \
  req -x509 -nodes -newkey rsa:2048 -days 1 \
  -keyout "/etc/letsencrypt/live/${DOMAIN}/privkey.pem" \
  -out "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" \
  -subj "/CN=${DOMAIN}"

echo "2/4 Starting nginx…"
$COMPOSE up -d nginx

echo "3/4 Requesting the real certificate from Let's Encrypt…"
rm -rf "${CERT_DIR}"
$COMPOSE run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    ${STAGING_ARG} \
    --email ${CERTBOT_EMAIL} -d ${DOMAIN} \
    --rsa-key-size 4096 --agree-tos --no-eff-email --force-renewal" certbot

echo "4/4 Reloading nginx with the new certificate…"
$COMPOSE exec nginx nginx -s reload

echo "Done. https://${DOMAIN} should now serve a valid certificate."
