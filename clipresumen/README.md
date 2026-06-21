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

Alembic ya está configurado y lee la URL de la base de datos desde la
configuración de la app. Aún no hay modelos ni migración inicial (eso llega en
la Fase 3). Cuando existan modelos:

```bash
# Dentro del contenedor backend
docker-compose exec backend alembic revision --autogenerate -m "initial"
docker-compose exec backend alembic upgrade head
```

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

## Roadmap de fases

- [x] **Fase 0** — Setup del proyecto
- [x] **Fase 1** — Extracción de transcripciones de YouTube
- [ ] **Fase 2** — Integración con la API de Claude para resumir
- [ ] **Fase 3** — Base de datos y persistencia
- [ ] **Fase 4** — Autenticación y sistema de usuarios
- [ ] **Fase 5** — Frontend funcional
- [ ] **Fase 6** — Monetización (Stripe)
- [ ] **Fase 7** — Self-hosting en VPS
