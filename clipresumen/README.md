# ClipResumen

Resumidor de videos de YouTube con IA. SaaS construido con **FastAPI**,
**Next.js**, **PostgreSQL** y la **API de Claude (Anthropic)**.

> Estado actual: **Fase 0 — esqueleto funcional**. El proyecto levanta con
> `docker-compose up` pero todavía no incluye lógica de negocio (extracción de
> transcripciones, resúmenes, auth, etc.). Esas funcionalidades se añaden en las
> fases siguientes.

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

## Roadmap de fases

- [x] **Fase 0** — Setup del proyecto
- [x] **Fase 1** — Extracción de transcripciones de YouTube
- [x] **Fase 2** — Integración con la API de Claude para resumir
- [x] **Fase 3** — Base de datos y persistencia
- [x] **Fase 4** — Autenticación y sistema de usuarios
- [x] **Fase 5** — Frontend funcional
- [x] **Fase 6** — Monetización (Stripe)
- [ ] **Fase 7** — Self-hosting en VPS
