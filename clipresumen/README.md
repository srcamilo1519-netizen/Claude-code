# ClipResumen

Resumidor de videos de YouTube con IA. SaaS construido con **FastAPI**,
**Next.js**, **PostgreSQL** y la **API de Claude (Anthropic)**.

> Estado actual: **Fases 0–7 completas**. Extracción de transcripciones,
> resúmenes con IA, persistencia, autenticación JWT, frontend funcional,
> monetización con Stripe y despliegue en VPS (Nginx + SSL + backups +
> monitoreo). Desarrollo: `docker-compose up`. Producción: ver
> [Despliegue en un VPS](#despliegue-en-un-vps-fase-7).

## Stack

| Capa       | Tecnología                                           |
| ---------- | ---------------------------------------------------- |
| Backend    | FastAPI · SQLAlchemy 2 · Alembic · Pydantic v2       |
| Frontend   | Next.js 14 (App Router) · TypeScript · TailwindCSS   |
| Base datos | PostgreSQL 16                                        |
| IA         | API de Claude (Anthropic)                            |
| Infra      | Docker · docker-compose                              |

## Estructura

```
clipresumen/
├── backend/                FastAPI + Python
│   ├── app/
│   │   ├── core/           config y conexión a la base de datos
│   │   ├── models/         modelos SQLAlchemy (Fase 3)
│   │   ├── routers/        endpoints HTTP
│   │   └── services/       lógica de negocio (Fase 1+)
│   ├── alembic/            migraciones de base de datos
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/               Next.js + TypeScript + Tailwind
│   ├── app/                App Router (layout, páginas)
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml      backend + frontend + postgres
├── .env.example
└── README.md
```

## Puesta en marcha

Requisitos: Docker y Docker Compose.

```bash
# 1. Copia las variables de entorno y ajústalas
cp .env.example .env

# 2. Levanta los tres servicios
docker-compose up --build
```

Servicios disponibles:

| Servicio | URL                              |
| -------- | -------------------------------- |
| Frontend | http://localhost:3000            |
| Backend  | http://localhost:8000            |
| API docs | http://localhost:8000/docs       |
| Health   | http://localhost:8000/health     |
| Health DB| http://localhost:8000/health/db  |
| Postgres | localhost:5432                   |

## Variables de entorno

Todas se documentan en [`.env.example`](./.env.example). Las imprescindibles
para esta fase son `DATABASE_URL`, `POSTGRES_*` y `CORS_ORIGINS`.
`ANTHROPIC_API_KEY`, `JWT_SECRET` y las claves de Stripe se usan en fases
posteriores.

## Migraciones (Alembic)

Alembic está configurado y lee la URL de la base de datos desde la
configuración de la app. La migración inicial (tablas `users`, `summaries`,
`usage_logs`) ya está en `alembic/versions/`. Para aplicarla:

```bash
# Dentro del contenedor backend
docker-compose exec backend alembic upgrade head
```

Para generar nuevas migraciones tras cambiar los modelos:

```bash
docker-compose exec backend alembic revision --autogenerate -m "mensaje"
docker-compose exec backend alembic upgrade head
```

### Modelo de datos (Fase 3)

- **`users`** — `id`, `email`, `password_hash`, `plan` (free/pro/business),
  `credits_remaining`, `created_at`.
- **`summaries`** — `id`, `user_id` (FK), `youtube_url`, `video_title`,
  `video_duration`, `transcript_length`, `summary_json`,
  `processing_time_seconds`, `created_at`.
- **`usage_logs`** — `id`, `user_id` (FK), `action`, `tokens_used`,
  `created_at` (para trackear el costo de la API de Claude por usuario).

Endpoints añadidos:

- `POST /api/summarize` ahora guarda el resumen en `summaries`, registra el uso
  en `usage_logs` y devuelve el detalle (incluido el `id` del resumen).
- `GET /api/summaries` — lista los resúmenes del usuario.
- `GET /api/summaries/{id}` — detalle de un resumen.

> La autenticación llega en la Fase 4. De momento el `user_id` se resuelve con
> un usuario *dev* temporal (`app/core/deps.py`).

## Tests

Los tests del backend usan `pytest`. Los unitarios corren sin red; los tests
que llaman a YouTube están marcados como `integration` y se omiten por defecto.

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt

pytest                 # solo tests offline (rápidos, deterministas)
pytest -m integration  # incluye extracción real desde YouTube (requiere red)
```

## Servicio de transcripciones (Fase 1)

`app/services/youtube_service.py` expone `extract_transcript(url)`, que:

- Reconoce URLs `watch?v=`, `youtu.be/`, `shorts/`, `embed/`.
- Obtiene la transcripción con `youtube-transcript-api`, prefiriendo el idioma
  original y con fallback a inglés/español.
- Lee título y duración con `yt-dlp` (solo metadata, sin descargar el video).
- Aplica un rate limiter básico entre solicitudes a YouTube.
- Lanza errores específicos: `InvalidYouTubeURLError`, `VideoNotFoundError`,
  `VideoPrivateError`, `TranscriptNotAvailableError`, `RateLimitedError`.

Devuelve un `TranscriptResult` con `video_id`, `title`, `duration_seconds`,
`language`, `transcript` y `transcript_length`.

## Resumen con IA (Fase 2)

`app/services/summarizer_service.py` expone `summarize_transcript(text)`, que:

- Usa el modelo **`claude-sonnet-4-6`** (configurable con `SUMMARIZER_MODEL`).
- Genera un `VideoSummary` estructurado (título, puntos clave, resumen
  extendido, timestamps relevantes, conclusión/CTA) mediante *structured
  outputs* (`messages.parse`), de modo que el JSON se renderiza directo en el
  frontend.
- El system prompt prohíbe explícitamente inventar información ausente en la
  transcripción.
- Para transcripciones muy largas (>100.000 caracteres) aplica *map-reduce*:
  resume cada fragmento y luego resume los resúmenes parciales.
- Maneja errores de la API: timeout, rate limit, respuestas malformadas, falta
  de `ANTHROPIC_API_KEY`.

El endpoint **`POST /api/summarize`** conecta `youtube_service` +
`summarizer_service` y devuelve el resultado final:

```bash
curl -X POST http://localhost:8000/api/summarize \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

> Requiere `ANTHROPIC_API_KEY` en el `.env`. Aún sin autenticación (Fase 4).

## Autenticación (Fase 4)

JWT con bcrypt. Endpoints del backend:

- `POST /api/auth/register` — registro (email + password ≥ 8). Hashea con
  bcrypt y devuelve `access_token` + `refresh_token`.
- `POST /api/auth/login` — devuelve ambos tokens.
- `POST /api/auth/refresh` — renueva el `access_token`.
- `GET /api/auth/me` — perfil del usuario autenticado.

Las rutas `/api/summarize` y `/api/summaries*` quedan protegidas por la
dependencia `get_current_user` (valida el Bearer token). Cada usuario nuevo
recibe **5 créditos**; cada resumen descuenta 1, y si no quedan créditos el
endpoint responde **402 Payment Required**.

### Frontend

- Páginas `/login` y `/register`.
- `AuthContext` (`context/AuthContext.tsx`) con estado de sesión global.
- Los tokens se guardan en **cookies httpOnly** (no `localStorage`), gestionadas
  por *Route Handlers* de Next (`app/api/auth/*`) que hacen de proxy al backend.
  El navegador nunca ve el token; `/api/auth/me` refresca el access token
  automáticamente con el refresh token cuando expira.

> Variable nueva: `BACKEND_URL` (URL interna que usan los Route Handlers para
> alcanzar el backend; en docker-compose es `http://backend:8000`).

## Frontend funcional (Fase 5)

Páginas (Next.js App Router, TailwindCSS, tema oscuro, mobile-first):

- **`/`** — input grande para la URL de YouTube, botón *Resumir* con spinner de
  carga. Sin sesión muestra el preview pero redirige a login antes de procesar;
  con sesión llama a `/api/summarize` y navega al resultado. Maneja el 402
  (sin créditos).
- **`/summary/[id]`** — video de YouTube embebido arriba, resumen estructurado
  (título, puntos clave, resumen extendido, timestamps, conclusión), y botones
  para **copiar**, **descargar Markdown** y **descargar PDF** (jsPDF, cargado de
  forma lazy).
- **`/dashboard`** — historial de resúmenes, créditos restantes y plan visibles,
  y botón *Mejorar plan* (→ `/pricing`, Fase 6).

Las llamadas a datos pasan por *Route Handlers* proxy (`app/api/summarize`,
`app/api/summaries`, `app/api/summaries/[id]`) que adjuntan el Bearer token
desde la cookie httpOnly y refrescan el access token automáticamente — el
navegador nunca manipula el JWT.

## Monetización con Stripe (Fase 6)

Planes:

| Plan     | Precio   | Créditos          |
| -------- | -------- | ----------------- |
| FREE     | $0       | 5 resúmenes/mes   |
| PRO      | $9/mes   | 100 resúmenes/mes |
| BUSINESS | $29/mes  | Ilimitado + API   |

Endpoints del backend:

- `POST /api/billing/create-checkout-session` — crea la sesión de checkout de
  Stripe (modo suscripción) y devuelve la URL.
- `POST /api/billing/webhook` — verifica la firma y actualiza plan/créditos ante
  `checkout.session.completed`, `customer.subscription.*` (alta/cambio/baja),
  `invoice.payment_succeeded` (recarga créditos) y `invoice.payment_failed`.
- `GET /api/billing/portal` — link al portal de Stripe para gestionar la
  suscripción.

El plan BUSINESS es ilimitado: omite el gate de créditos y no descuenta. En el
frontend, **`/pricing`** muestra las tres tarjetas con botones *Suscribirse* que
redirigen al checkout de Stripe; el dashboard ofrece *Gestionar suscripción*
(portal) a los planes de pago.

### Configurar Stripe

Usa **modo de prueba** primero. En tu `.env` (ver `.env.example`):

- `STRIPE_SECRET_KEY` — `sk_test_…` (en producción: `sk_live_…`).
- `STRIPE_WEBHOOK_SECRET` — `whsec_…` (al crear el endpoint del webhook, o con
  `stripe listen --forward-to localhost:8000/api/billing/webhook`).
- `STRIPE_PRICE_PRO` / `STRIPE_PRICE_BUSINESS` — los `price_…` recurrentes de
  cada plan.
- `FRONTEND_BASE_URL` — para los redirects de checkout/portal.

> Para producción **solo** reemplazas estos valores en el `.env` por las claves
> LIVE — no hay nada que cambiar en el código.

## Despliegue en un VPS (Fase 7)

Stack de producción: imágenes multi-stage (más pequeñas, sin hot-reload), Nginx
como reverse proxy con SSL automático (Certbot/Let's Encrypt), redirección
HTTP→HTTPS y rate limiting. Todo con `docker-compose.prod.yml`.

### Arquitectura en producción

```
Internet ──443/80──▶ Nginx ─┬─ /                → frontend (Next.js :3000)
                            └─ /webhook/stripe   → backend  (FastAPI :8000)
                                                   backend ──▶ postgres
```

El navegador solo habla con Nginx→frontend; el frontend hace de proxy al
backend (con el token de la cookie httpOnly). El backend solo se expone
públicamente para el webhook de Stripe.

### 1. Comprar y preparar el VPS

- **Proveedor/tamaño recomendado:** Hetzner **CX22** (2 vCPU / 4 GB, ~€4/mes) o
  DigitalOcean **2 vCPU / 4 GB**. Suficiente para los primeros cientos de
  usuarios. Imagen: **Ubuntu 22.04**.
- Entra por SSH y prepara el firewall y Docker:

  ```bash
  # Firewall: solo SSH + HTTP + HTTPS
  ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable

  # Docker + plugin compose
  curl -fsSL https://get.docker.com | sh
  ```

### 2. Apuntar tu dominio al servidor

En tu registrador (Namecheap, Cloudflare, …) crea un registro **A**:

| Tipo | Nombre | Valor            |
| ---- | ------ | ---------------- |
| A    | `@`    | IP de tu VPS     |
| A    | `www`  | IP de tu VPS *(opcional)* |

Espera a que propague (`dig +short tu-dominio.com` debe devolver la IP).

### 3. Clonar y configurar

```bash
git clone <url-del-repo> /opt/clipresumen
cd /opt/clipresumen/clipresumen
cp .env.example .env
nano .env   # completa TODAS las variables
```

En `.env` para producción, asegúrate de definir como mínimo:

- `POSTGRES_PASSWORD` (clave fuerte) y `DATABASE_URL` acorde.
- `ANTHROPIC_API_KEY`, `JWT_SECRET` (`openssl rand -hex 32`).
- `DOMAIN` y `CERTBOT_EMAIL`.
- Stripe: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_*`,
  `FRONTEND_BASE_URL=https://tu-dominio.com`.

### 4. Primer despliegue desde cero

```bash
cd /opt/clipresumen/clipresumen

# Construir imágenes y aplicar migraciones
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d postgres
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# Emitir el certificado TLS (levanta también backend, frontend y nginx)
./init-letsencrypt.sh
```

> Consejo: pon `CERTBOT_STAGING=1` en `.env` la primera vez para no gastar el
> límite de Let's Encrypt; cuando funcione, ponlo a `0` y vuelve a ejecutar
> `./init-letsencrypt.sh`.

Verifica: `docker compose -f docker-compose.prod.yml ps` y abre
`https://tu-dominio.com`.

### 5. Webhook de Stripe

En el dashboard de Stripe → Developers → Webhooks, crea un endpoint apuntando a
`https://tu-dominio.com/webhook/stripe` y copia el `whsec_…` a
`STRIPE_WEBHOOK_SECRET` en `.env`. Luego `./deploy.sh` (o reinicia el backend).

### 6. Actualizaciones (sin downtime apreciable)

```bash
./deploy.sh   # pull → build → migrate → recrea solo backend/frontend
```

### 7. Backups automáticos de PostgreSQL

`backup.sh` hace `pg_dump | gzip` a `./backups` y, si configuras
`BACKUP_RCLONE_REMOTE`, lo sube a almacenamiento externo (S3, B2, …) con
[rclone](https://rclone.org). Prográmalo a diario con cron:

```bash
crontab -e
# 0 3 * * *  cd /opt/clipresumen/clipresumen && ./backup.sh >> /var/log/clipresumen-backup.log 2>&1
```

Restaurar: `gunzip -c backups/archivo.sql.gz | docker compose -f docker-compose.prod.yml exec -T postgres psql -U clipresumen -d clipresumen`.

### 8. Monitoreo (opcional) — logs centralizados

Stack ligero Loki + Promtail + Grafana:

```bash
docker compose -f docker-compose.monitoring.yml up -d
# Grafana queda en localhost; accede por túnel SSH:
ssh -L 3001:localhost:3001 usuario@tu-servidor   # → http://localhost:3001
```

Promtail recoge los logs de todos los contenedores y los envía a Loki; Grafana
viene con el datasource de Loki ya provisionado.

### Comandos útiles

```bash
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml restart backend
```

## Roadmap de fases

- [x] **Fase 0** — Setup del proyecto
- [x] **Fase 1** — Extracción de transcripciones de YouTube
- [x] **Fase 2** — Integración con la API de Claude para resumir
- [x] **Fase 3** — Base de datos y persistencia
- [x] **Fase 4** — Autenticación y sistema de usuarios
- [x] **Fase 5** — Frontend funcional
- [x] **Fase 6** — Monetización (Stripe)
- [x] **Fase 7** — Self-hosting en VPS
