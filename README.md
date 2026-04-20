# CAPTCHA Robustness Benchmark Dashboard

A research-grade platform for measuring CAPTCHA resistance against automated attacks using real computer-vision models, real social-network account data, and rigorous statistical testing.

> **Research basis:**  
> Attack methodology — Gao et al., *"CAPTCHA Is Dead, Long Live CAPTCHA!"*, USENIX Security 2021  
> Account scoring — Kozlov et al., *"PAS: Post-Authentication State for Bot Detection"*, RAID 2020  
> Real account data — [fcakyon/instafake-dataset](https://github.com/fcakyon/instafake-dataset) (2,594 Instagram records)

---

## Table of Contents

- [What It Does](#what-it-does)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Sign In](#sign-in)
- [Feature Walkthrough](#feature-walkthrough)
  - [CAPTCHA Library](#captcha-library)
  - [Attack Benchmark](#attack-benchmark)
  - [PAS Model & Account Classification](#pas-model--account-classification)
  - [A/B Experiments](#ab-experiments)
  - [Backtesting](#backtesting)
  - [Reports](#reports)
- [Real Data Sources](#real-data-sources)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Development](#development)
- [Running Tests](#running-tests)

---

## What It Does

The dashboard answers three questions CAPTCHA designers care about:

| Question | How It's Answered |
|---|---|
| Can a state-of-the-art model solve my CAPTCHA automatically? | YOLOv8n runs real inference on uploaded challenge images, computing a measured Attack Success Rate (ASR) |
| How do my design choices affect attack resistance? | Category diversity, occlusion level, and variation density are scored and mapped to ASR penalties using Gao et al. Tables 11–12 |
| Are accounts passing my CAPTCHA genuine users or bots? | A Random Forest trained on 2,594 real Instagram accounts assigns GPAS / BPAS / EPAS proxy labels |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Browser  →  React 18 + Vite (localhost:4000)               │
│              TanStack Query · Zustand · Recharts             │
└──────────────────────┬──────────────────────────────────────┘
                       │  /v1  /auth  (proxied)
┌──────────────────────▼──────────────────────────────────────┐
│  FastAPI + SQLAlchemy 2 async (localhost:8888)               │
│  JWT auth · CAPTCHA CRUD · Attack dispatch · Reports        │
└──────┬───────────────────────────────────┬──────────────────┘
       │                                   │
┌──────▼──────┐                   ┌────────▼────────┐
│ PostgreSQL 15│                   │   Redis 7        │
│  (port 5433) │                   │   (port 6380)    │
└─────────────┘                   └────────┬─────────┘
                                           │  RQ job queue
                                  ┌────────▼─────────┐
                                  │  Python Worker    │
                                  │  YOLOv8n inference│
                                  │  PAS model train  │
                                  └──────────────────┘
```

| Service | Image | Port |
|---|---|---|
| `web` | node:20-alpine | 4000 |
| `api` | python:3.11-slim (custom) | 8888 |
| `db` | postgres:15-alpine | 5433 |
| `redis` | redis:7-alpine | 6380 |
| `worker` | Same as api | — |

---

## Quick Start

### Prerequisites

- Docker Desktop (running)
- Ports 4000, 8888, 5433, 6380 free

### Start

```bash
git clone https://github.com/vatsal2025/Cache-Benchmark.git
cd Cache-Benchmark
docker compose up -d
```

First launch builds the API/worker image and pulls base images (~3–5 min). Subsequent starts take ~15 seconds.

### Verify

```bash
docker compose ps
```

All five services should show `Up` or `Up (healthy)`.

### Stop

```bash
docker compose down
```

---

## Sign In

Open **http://localhost:4000** and sign in with the pre-seeded admin credentials:

| Field | Value |
|---|---|
| Client ID | `am2Eojw8-UcPIfNa8UuWCA` |
| Client Secret | `Benchmark2024!` |

> To register a new organisation instead, switch to the **Register** tab. The system returns your `client_id` and `client_secret` — save the secret, it is shown only once.

---

## Feature Walkthrough

### CAPTCHA Library

Central registry for all CAPTCHA submissions owned by your organisation.

- **Register** a new CAPTCHA with name, version, type, category set size, occlusion level, and variation count.
- **Design scores** are computed automatically — category diversity (0–1), occlusion (0–1), variation density (0–1).
- **Sample images** for real YOLOv8n attacks are stored at:
  ```
  api/storage/development/<org_id>/captchas/<captcha_id>/
  ```
  Supported: `.jpg`, `.jpeg`, `.png`, `.webp`

Two CAPTCHAs are pre-seeded:

| Name | Purpose |
|---|---|
| VTT Control v1 | Standard grid challenge, 15 real sample images pre-loaded |
| VTT Enhanced v2 | Higher-design-score variant for comparison experiments |

---

### Attack Benchmark

For any CAPTCHA, run one or all four attack types with one click.

#### Attack Types

| Type | Description | Typical ASR (VTT) |
|---|---|---|
| **Holistic** | End-to-end neural pipeline on the full challenge grid | 0.43–0.67 |
| **Modular** | Tile-by-tile detection, then aggregate | 0.64–0.88 |
| **Bot Baseline** | Naive script bot, no image understanding | ~4–6 % of holistic |
| **Random Baseline** | Pure random tile selection | 1/196 ≈ 0.5 % |

#### How It Works

1. Click **Run All Attacks** on the Attack Benchmark page.
2. Four jobs are dispatched to the RQ worker queue immediately.
3. The worker scans storage for uploaded images belonging to that CAPTCHA:
   - **Images found** → YOLOv8n runs inference tile-by-tile → real ASR measured.
   - **No images** → Gao et al. reference ASRs + design penalties → estimated ASR.
4. UI auto-polls every 3 s until all jobs complete.

#### Results Display

- Bar chart with ASR per attack type and Gao et al. reference lines overlaid.
- Error distribution pie (classification error, grid prediction, semantic parsing, abstract attribute).
- Per-category ASR (regular geometries, digits, English letters, Chinese characters).
- Results table with:
  - `real · Nimg` badge (YOLOv8n measured) or `est.` badge (literature estimate).
  - Human Parity Score = ASR ÷ human pass rate.
  - Model version and image count used.
- **Green banner** — real YOLOv8n measurement confirmed.
- **Yellow banner** — estimated results, upload images to enable real measurement.

#### Design Penalty Formula

```
penalty = category_diversity_score × 0.16
        + occlusion_score           × 0.16
        + variation_density_score   × 0.10

adjusted_ASR = max(0.05, base_ASR − penalty)
```

---

### PAS Model & Account Classification

Predicts account quality after CAPTCHA clearance using a Random Forest trained on real Instagram data.

#### Labels

| Label | Meaning |
|---|---|
| **GPAS** | Genuine user — normal social activity and friend graph |
| **BPAS** | Fake / automated account — high follow ratio, spam reports |
| **EPAS** | Empty / dormant account — insufficient signals to classify |

#### Training Data

- **Source:** [fcakyon/instafake-dataset](https://github.com/fcakyon/instafake-dataset)
- **Records:** 2,594 real Instagram accounts (genuine + fake + automated + non-automated)
- **Features:** follower count, following count, media count, profile completeness, bio length, privacy setting, username length, username digit ratio, friend requests sent, abuse reports received
- **Cached** in `api/storage/data/instafake_pas.parquet` after first download

#### Metrics (held-out test set)

| Class | F1 |
|---|---|
| GPAS | 0.997 |
| BPAS | 0.970 |
| EPAS | 1.000 |

---

### A/B Experiments

Controlled experiments comparing two CAPTCHA variants.

1. Go to **Experiments → New Experiment**.
2. Select control CAPTCHA and treatment CAPTCHA.
3. Set target sample size and significance threshold (default α = 0.05).
4. Launch — the platform tracks pass rates and computes statistical significance using a **two-proportion Z-test** with **Wald confidence intervals**.
5. A winner is declared once significance is reached.

---

### Backtesting

Replay historical challenge data against the trained PAS model to measure what fraction of passing accounts would have been flagged under different policy thresholds.

---

### Reports

Generate a PDF benchmark report for any CAPTCHA from its detail page. The report includes all attack results, design scores, and PAS metrics.

---

## Real Data Sources

| Data | Source | Used For |
|---|---|---|
| YOLOv8n weights | [Ultralytics](https://github.com/ultralytics/ultralytics) (auto-downloaded, 6 MB) | Real ASR measurement on CAPTCHA tiles |
| Instagram account records | [fcakyon/instafake-dataset](https://github.com/fcakyon/instafake-dataset) | PAS model training |
| CAPTCHA sample images | Pre-loaded (15 photos: cars, buses, trucks, motorcycles, crosswalks, traffic lights, stop signs, fire hydrants) | Real YOLOv8n inference |
| Reference ASRs | Gao et al. USENIX Security 2021 Table 3 | Fallback estimates and benchmark reference lines |
| Design penalties | Gao et al. Tables 11–12 | ASR reduction formula |

---

## API Reference

Base URL: `http://localhost:8888`  
All `/v1` endpoints require `Authorization: Bearer <token>`.

```
POST   /auth/token                        →  Obtain JWT (client_id + client_secret)
POST   /auth/register                     →  Register new organisation

GET    /v1/captchas                        →  List CAPTCHAs
POST   /v1/captchas                        →  Register new CAPTCHA
GET    /v1/captchas/{id}                   →  CAPTCHA detail
POST   /v1/captchas/{id}/attacks           →  Enqueue attack jobs
GET    /v1/captchas/{id}/attacks           →  List attack results
GET    /v1/attacks/{run_id}                →  Single attack run

GET    /v1/experiments                     →  List experiments
POST   /v1/experiments                     →  Create experiment
GET    /v1/experiments/{id}                →  Experiment detail

GET    /healthz                            →  Service health check
```

Interactive docs: **http://localhost:8888/docs**

---

## Project Structure

```
captcha-benchmark/
├── docker-compose.yml
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/                   # DB migrations
│   ├── app/
│   │   ├── main.py
│   │   ├── core/                  # Config, DB, security, deps
│   │   ├── models/                # SQLAlchemy ORM models
│   │   ├── schemas/               # Pydantic request/response schemas
│   │   ├── routes/                # FastAPI route handlers
│   │   ├── services/              # Seed, report generation
│   │   ├── workers/               # RQ job handlers
│   │   └── ml/
│   │       ├── attack_engine.py   # Run attack — YOLO or estimated
│   │       ├── image_attack.py    # YOLOv8n inference engine
│   │       ├── pas_model.py       # PAS Random Forest model
│   │       ├── real_data.py       # instafake-dataset downloader
│   │       ├── synthetic_data.py  # Fallback synthetic data generator
│   │       ├── statistics.py      # Z-test, Wald CI
│   │       └── design_guidelines.py
│   └── tests/
├── web/
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── pages/                 # Route-level React components
│       ├── lib/                   # API client, utilities
│       └── store/                 # Zustand auth store
└── infra/                         # Infrastructure configs
```

---

## Development

### Running the API locally (outside Docker)

```bash
cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL="postgresql+asyncpg://cb_user:cb_password@localhost:5433/captcha_benchmark"
export SYNC_DATABASE_URL="postgresql://cb_user:cb_password@localhost:5433/captcha_benchmark"
export REDIS_URL="redis://localhost:6380/0"
export SECRET_KEY="dev-secret-key-change-in-production-32chars"

uvicorn app.main:app --reload
```

### Running the web app locally

```bash
cd web
npm install --legacy-peer-deps
npm run dev
```

### Applying database migrations

```bash
docker compose exec api alembic upgrade head
```

---

## Running Tests

```bash
docker compose exec api pytest tests/ -v
```

All 22 tests cover:

- Synthetic data generation and PAS label distribution
- PAS model training and prediction
- Attack engine (random baseline, holistic, design penalty)
- Statistical functions (Wald CI, two-proportion Z-test)
- Design guideline score computation

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| UI shows 0 CAPTCHAs after login | You registered a new org — sign out and use the seeded credentials above |
| Run All Attacks does nothing | Check browser console; verify `curl http://localhost:8888/healthz` returns `{"status":"ok"}` |
| Attack results show `est.` badge | No images in storage for that CAPTCHA — place images in `api/storage/development/<org_id>/captchas/<captcha_id>/` |
| `api` container keeps restarting | `docker compose logs api --tail=30` — usually a pending migration |
| Worker not processing jobs | `docker compose restart worker` |

---

## License

MIT
