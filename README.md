# AI Career Navigator 2026

> **Your Personal AI-Powered Career Mentor** — Built for Indian CS Students & Fresh Graduates

AI Career Navigator is a full-stack, AI-driven career intelligence platform that reads your **real** GitHub, LeetCode, LinkedIn, and Resume profiles to deliver honest, data-driven career guidance. No self-reported forms. No mock results. Just hard metrics from your actual profiles.

---

## Table of Contents

1. [Why This Exists](#why-this-exists)
2. [Features](#features)
3. [Tech Stack](#tech-stack)
4. [Architecture Overview](#architecture-overview)
5. [Database Schema](#database-schema)
6. [Project Structure](#project-structure)
7. [Getting Started](#getting-started)
8. [Environment Variables](#environment-variables)
9. [API Reference](#api-reference)
10. [Design System](#design-system)
11. [Testing](#testing)
12. [Documentation](#documentation)
13. [License](#license)

---

## Why This Exists

Most career platforms ask you to manually fill in skills, projects, and experience — data that is often incomplete, outdated, or simply inaccurate. **AI Career Navigator** solves this by:

- **Reading your real GitHub** — repos, languages, stars, forks, and commit activity
- **Reading your real LeetCode** — problems solved, difficulty breakdown, contest rating
- **Reading your real Resume** — PDF upload with AI-powered skill extraction
- **Reading your real Certificates** — AI analysis of course and certification documents
- **Fusing all of the above** into a single, unified career intelligence profile

The result is a career mentor that knows you better than you know yourself.

---

## Features

### Core Intelligence

| Feature | Description |
|---|---|
| **Profile Reading Engine** | Fetches real data from GitHub REST API, LeetCode GraphQL API, and uploaded PDF resumes/certificates |
| **AI Analysis Engine** | Powered by **Google Gemini 2.5 Flash** (Free Tier). Combines all profile data into a single AI call with smart caching (1-hour TTL, LRU eviction) |
| **Career Path Recommender** | Suggests personalized career paths with match percentages, salary insights, top target companies, and recommended certifications |
| **Skill Gap Analyzer** | Visual breakdown of skills you **have** vs. skills you **need** for each recommended career path, with learning resources |
| **Roadmap Generator** | AI-generated, time-bound 24-week action plan with weekly milestones, skills to learn, and deliverables |
| **Resume Score** | AI-evaluated resume quality score (0–100) with breakdown across skills match, GitHub activity, LeetCode strength, certifications, and resume quality |
| **Career Brain** | Central intelligence layer that aggregates profile, analysis, interview sessions, job applications, streaks, and rank into a single `CareerBrain` object with job readiness score, trend analysis, and actionable recommendations |
| **Career Evolution Engine** | Predictive intelligence that detects long-term skill evolution patterns — volatility, growth state, and per-career-path trajectory |
| **Career Memory Engine** | Tracks user evolution over time across career paths with trend detection (improving / stable / declining) |

### Interview Preparation

| Feature | Description |
|---|---|
| **AI Interview Coach** | Generates role-specific interview questions (HR, Technical, System Design) with AI-generated model answers and scoring |
| **4 Interview Packs** | Warm Up (friendly HR), Technical Round (strict engineering), FAANG Prep (Google/Meta/Amazon pressure simulation), System Design (architecture & scalability) |
| **Voice Interview** | Full voice input support via Web Speech API — speak your answers naturally. Includes text-to-speech for question reading |
| **Communication Score** | AI analyzes filler words (`um`, `uh`, `like`, etc.) and gives a real-time communication effectiveness score |
| **AI Coaching Hints** | Per-question AI hints showing what the interviewer is looking for, how to structure your answer, and a sample response |
| **AI Coach Panel** | Live sidebar during interviews showing your weakest career path, a personalized AI tip, and your job readiness score |
| **Simulation Mode** | Timed interview — 2 minutes per question. Timer turns red in the last 30 seconds. Auto-submits on timeout |
| **Anti-Cheat System** | Paste detection, typing behavior analysis (keystroke rate, start time), and authenticity status tracking |
| **AI Personas** | Friendly, Strict, FAANG, and Google-style interviewer personalities with distinct messaging styles |
| **Detailed Feedback** | Per-question score (0–10), good points, missing points, model answer, and improvement tip |

### Gamification

| Feature | Description |
|---|---|
| **Daily Streaks** | Duolingo-style streak tracking. Maintain your practice streak to build consistency |
| **XP & Ranks** | 7-level progression system: 🌱 Fresher → 📚 Beginner → 💼 Junior → ⚡ Mid-level → 🚀 Senior → 👑 Principal → 🏆 Legend |
| **Achievement Badges** | 12+ auto-awarded badges including First Step, Perfect Score, Week Warrior, Monthly Legend, Interview Master, Hard Mode Hero, Voice Pro, and Weekly Champion |
| **Weekly Challenge** | ISO-week-based coding challenge with a live countdown timer, leaderboard, and shareable results |
| **Challenge a Friend** | Create custom interview challenges with 8-character shareable codes. Friends can accept and compete on the leaderboard |
| **Progress Tracker** | Visual progress bar showing profile completeness across all onboarding steps |

### Job & Career Tools

| Feature | Description |
|---|---|
| **Job Matching** | AI-powered job matching engine that calculates match scores based on your verified skill set against real job descriptions |
| **Job Search** | Real-time job search via SerpAPI (Google Jobs) with location and role filtering |
| **Save & Apply** | Bookmark jobs, track application statuses (Applied → Interview → Offer / Rejected), and manage your job pipeline |
| **Market Analyzer** | Analyzes job market demand for specific roles — high-demand, growing, and stable skills per role category |
| **Recommendation Engine** | Personalized job and career recommendations scored by skill match and experience level fit |
| **Career Copilot** | AI decision layer that generates your next action, skill gap roadmap, and job readiness status (Not Ready / Almost Ready / Ready) |
| **Weekly Email Reports** | AI-generated HTML weekly performance reports sent via Gmail — best session, average score, weakest career path, streak, rank, and personalized AI tip |

### Profile & Document Management

| Feature | Description |
|---|---|
| **Unified Profile** | Comprehensive profile supporting students, professionals, freshers, and career switchers with academic, professional, and goal fields |
| **Onboarding Flow** | Multi-step onboarding wizard that adapts questions based on user type (student / professional / fresher / career_switch) |
| **Resume Upload** | PDF-only upload with magic-byte validation (max 10MB). Text extracted via PyMuPDF. Skills auto-extracted and merged into profile |
| **Certificate Upload** | Upload PDF, JPG, or PNG certificates (max 5MB each, up to 10 files). Gemini AI extracts course name, provider, score, date, skills unlocked, and credibility rating |
| **Document Management** | Unified `user_documents` table with confidence-weighted skill merging across all uploaded documents |
| **Profile Completeness Score** | Real-time 0–100 completeness score based on GitHub, LeetCode, Resume, academic info, skills, experience, and career goal |

### Infrastructure & Reliability

| Feature | Description |
|---|---|
| **Supabase Auth** | Full authentication with JWT verification middleware and role-based access control (RBAC) |
| **Circuit Breaker** | Fault tolerance pattern for all external service calls (GitHub, LeetCode, Gemini) — prevents cascading failures |
| **Rate Limiting** | API rate limiting via `slowapi` with per-IP tracking |
| **Redis Caching** | Redis-backed caching layer with in-memory fallback, per-user keys, and TTL-based expiry |
| **Structured Logging** | JSON-structured request/response logging middleware |
| **Metrics** | Real-time request counters, error rates, and slow-request tracking exposed at `/metrics` |
| **WebSocket** | Real-time push notifications for job status, market updates, and recommendations |
| **Async Job Processing** | Background job queue for long-running AI analysis with idempotency keys to prevent duplicate jobs |
| **Input Sanitization** | Prompt injection detection and neutralization (30+ patterns) before all Gemini API calls |
| **Global Error Handler** | Catches all unhandled exceptions and returns safe JSON — never leaks stack traces to the frontend |
| **Health Check** | `/health` endpoint reports real-time status of database, Gemini AI, and memory engine |

---

## Tech Stack

### Frontend

| Layer | Technology |
|---|---|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS |
| Animations | Framer Motion |
| Charts | Recharts |
| Auth | Supabase Auth (client-side) |
| Package Manager | pnpm |

### Backend

| Layer | Technology |
|---|---|
| Framework | FastAPI (Python) |
| AI Model | Google Gemini 2.5 Flash (Free Tier) |
| Database | Supabase (PostgreSQL) |
| Auth | Supabase Auth (JWT verification) |
| Caching | Redis (with in-memory fallback) |
| Rate Limiting | slowapi |
| Task Queue | Supabase-backed async job system |
| PDF Parsing | PyMuPDF (fitz) |
| Testing | pytest |

### External APIs

| Service | Purpose |
|---|---|
| GitHub REST API | User profile, repos, coding activity |
| LeetCode GraphQL API | Problems solved, difficulty breakdown, skill tags |
| SerpAPI (Google Jobs) | Real-time job and internship search |
| Gmail SMTP | Weekly AI performance email reports |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ Dashboard│ │ Analysis │ │Interview │ │   Jobs & More    │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
│         │              │             │              │           │
│         │    ┌─────────┴──────┐     │     ┌────────┴──────┐    │
│         │    │Career Orchestrator│   │     │Career Safe    │    │
│         │    │(Single Brain)    │   │     │(Safe Accessors)│   │
│         │    └─────────────────┘   │     └───────────────┘    │
│         │                          │                           │
│  ┌──────▼──────────────────────────▼────────────────────────┐  │
│  │              Supabase Client (Auth + DB)                  │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST API (JWT Bearer)
┌────────────────────────────▼────────────────────────────────────┐
│                      BACKEND (FastAPI)                           │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Routers   │  │  Services   │  │      Core Layer         │ │
│  │             │  │             │  │                         │ │
│  │ auth        │  │ gemini      │  │ middleware (JWT, RBAC)  │ │
│  │ analysis    │  │ github      │  │ cache (Redis/Memory)    │ │
│  │ interview   │  │ leetcode    │  │ circuit_breaker         │ │
│  │ jobs        │  │ analysis_svc│  │ metrics                 │ │
│  │ resume      │  │ job_match   │  │ websocket               │ │
│  │ profile     │  │ career_brain│  │ supabase_client         │ │
│  │ streaks     │  │ evolution   │  │ config                  │ │
│  │ ranks       │  │ memory      │  │                         │ │
│  │ badges      │  │ badge_svc   │  │                         │ │
│  │ challenges  │  │ resume_svc  │  │                         │ │
│  │ weekly_chal │  │ document    │  │                         │ │
│  │ email       │  │ skill_extr  │  │                         │ │
│  │ career      │  │ profile_svc │  │                         │ │
│  │ roadmap     │  │ recommender │  │                         │ │
│  │ documents   │  │ market      │  │                         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│         │                  │                                     │
│         └──────────────────┼─────────────────────────────────────┘
│                             │
│                    ┌────────▼────────┐
│                    │   Supabase      │
│                    │  (PostgreSQL)   │
│                    └─────────────────┘
└──────────────────────────────────────────────────────────────────┘
```

### Request Flow — AI Analysis

```
User clicks "Run Analysis"
        │
        ▼
Frontend: POST /api/v1/analysis/run
        │
        ▼
Backend: Creates async job (idempotent)
        │
        ▼
Background Task:
  1. Fetch enriched profile from Supabase
  2. Fetch GitHub data (REST API)
  3. Fetch LeetCode data (GraphQL API)
  4. Get resume text from profile
  5. Call Gemini 2.5 Flash (single combined call, 6-in-1)
     → Strengths, Weaknesses, Career Paths, Skill Gaps,
       Roadmap, Resume Score, Salary Insights, Certifications
  6. Save results to Supabase (upsert)
  7. Update job status → completed
        │
        ▼
Frontend: Polls GET /api/v1/analysis/job/{job_id}
        │
        ▼
Frontend: Renders Analysis Dashboard
```

### Request Flow — Interview Session

```
User selects interview pack (Warm Up / Technical / FAANG / System Design)
        │
        ▼
Frontend: POST /api/v1/interview/generate-questions
        │
        ▼
Backend: Returns AI-generated questions (cached 15 min, throttled 20 sec/user)
        │
        ▼
User answers questions (text or voice)
        │
        ▼
Per-question: POST /api/v1/interview/evaluate
  → AI scores answer (0–10), gives good points, missing points,
    model answer, and improvement tip
        │
        ▼
Session complete → POST /api/v1/interview/complete
  → Updates streak, XP, rank, badges
  → If weekly mode → submits to weekly leaderboard
        │
        ▼
Frontend: Results screen with score breakdown, XP earned,
          new badges, streak update, rank progress
```

---

## Database Schema

The project uses **Supabase (PostgreSQL)** with 15+ tables and full Row Level Security (RLS).

### Core Tables

| Table | Purpose |
|---|---|
| `profiles` | User profile data — academic, professional, career goals, GitHub/LeetCode usernames, resume text |
| `analyses` | AI-generated career analysis — strengths, weaknesses, career paths, skill gaps, roadmap, resume score |
| `interview_sessions` | Interview practice session data — questions, answers, scores, career path |
| `user_streaks` | Daily practice streak tracking (Duolingo-style) — current streak, longest streak, last practice date |
| `user_ranks` | User XP and ranking — XP points, level (1–7), rank title |
| `user_badges` | Earned achievement badges — badge ID, earned timestamp |
| `user_documents` | Unified document storage — resume, certificates, cover letters with AI-extracted data |
| `user_career_memory` | Career evolution tracking — per-career-path performance scores and trends |
| `analysis_jobs` | Async job tracking — background AI analysis job status (pending/processing/completed/failed) |

### Social & Challenge Tables

| Table | Purpose |
|---|---|
| `challenges` | Shared interview challenges — 8-character code, creator, career path, questions |
| `challenge_results` | Challenge submission results and leaderboard entries |
| `weekly_challenges` | Weekly challenge definitions — ISO week number, year, theme, career path, questions |
| `weekly_results` | Weekly challenge submissions and leaderboard |
| `challenge_attempts` | Tracks when users start weekly challenges (resume support) |

### Job Tracking Tables

| Table | Purpose |
|---|---|
| `saved_jobs` | Bookmarked/saved job listings |
| `job_applications` | Job application pipeline — status tracking (applied/interview/rejected/offer) |

### Key Indexes

All user-facing tables have indexes on `user_id`, and leaderboard tables have indexes on `score DESC` for efficient ranking queries.

---

## Project Structure

```
career-navigator/
├── README.md                          # This file
├── package.json                       # Root workspace config
├── pnpm-lock.yaml                     # Lock file
├── .gitignore
│
├── frontend/                          # Next.js 14 Frontend
│   ├── app/                           # App Router pages
│   │   ├── page.tsx                   # Landing page (hero, features, testimonials)
│   │   ├── layout.tsx                 # Root layout
│   │   ├── globals.css                # Global styles + Tailwind
│   │   ├── auth/                      # Authentication
│   │   │   ├── login/page.tsx
│   │   │   ├── signup/page.tsx
│   │   │   └── callback/route.ts      # OAuth callback
│   │   ├── dashboard/page.tsx         # Main dashboard (Career Brain, Progress, Match Fit)
│   │   ├── analysis/page.tsx          # AI Career Analysis (paths, gaps, roadmap, salary)
│   │   ├── interview/page.tsx         # AI Interview Coach (4 packs, voice, sim mode)
│   │   │   ├── components/
│   │   │   │   ├── SetupScreen.tsx    # Interview pack selection
│   │   │   │   ├── InterviewScreen.tsx# Live interview with AI coach panel
│   │   │   │   ├── ResultsScreen.tsx  # Score breakdown, feedback, badges
│   │   │   │   └── AICoachPanel.tsx   # Weak area, AI tip, readiness score
│   │   │   └── hooks/
│   │   │       ├── useInterviewSession.ts  # Core session state machine
│   │   │       ├── useVoiceInput.ts        # Web Speech API (STT + TTS)
│   │   │       ├── useSimTimer.ts          # 2-min countdown per question
│   │   │       └── useWeeklyChallenge.ts   # Weekly challenge + localStorage resume
│   │   ├── challenges/page.tsx        # Weekly challenge hub (countdown, leaderboard)
│   │   ├── challenge/[code]/page.tsx  # Shared challenge view + submission
│   │   ├── jobs/page.tsx              # Job search, save, apply, pipeline
│   │   ├── applications/page.tsx      # Job application tracker (kanban-style)
│   │   ├── resume/page.tsx            # Resume upload + certificate management
│   │   ├── profile/page.tsx           # Profile editor (academic, professional, goals)
│   │   ├── onboarding/page.tsx        # Multi-step onboarding wizard
│   │   ├── badges/page.tsx            # Achievement gallery (earned + locked)
│   │   ├── progress/page.tsx          # Progress charts + Career Copilot insights
│   │   └── ...
│   ├── components/                    # Shared React components
│   │   ├── Navbar.tsx                 # Main navigation (10 routes)
│   │   ├── CareerCoach.tsx            # AI Career Coach widget (dashboard)
│   │   ├── CareerRoadmap.tsx          # Visual 24-week roadmap timeline
│   │   ├── ProgressTracker.tsx        # Profile completeness progress bar
│   │   ├── MatchFitScore.tsx          # Radial match-fit score gauge
│   │   └── ui/                        # shadcn/ui components
│   ├── lib/                           # Shared utilities
│   │   ├── supabase.ts                # Supabase client singleton
│   │   ├── api.ts                     # API client with retry logic
│   │   ├── career-orchestrator.ts     # Single brain decision system
│   │   ├── career-safe.ts             # Safe data accessors (null-safe)
│   │   └── utils.ts
│   ├── public/                        # Static assets
│   ├── next.config.js
│   ├── tailwind.config.js
│   └── tsconfig.json
│
├── backend/                           # FastAPI Backend
│   ├── main.py                        # App entry point, router registration, middleware
│   ├── requirements.txt               # Python dependencies
│   ├── schema.sql                     # Complete Supabase database schema + RLS policies
│   ├── celery_config.py               # Celery configuration (for async tasks)
│   ├── check_results.py               # Result checking utility
│   ├── utils.py
│   │
│   ├── routers/                       # API Route Handlers (v1 prefix)
│   │   ├── auth.py                    # Signup, login, me (Supabase Auth)
│   │   ├── analysis.py                # Run analysis, job status, job history
│   │   ├── interview.py               # Generate questions, evaluate, complete session
│   │   ├── jobs.py                    # Job recommendations, save, apply, applications
│   │   ├── resume.py                  # Resume PDF upload + text extraction
│   │   ├── profile.py                 # Get/save profile, progress
│   │   ├── profile_enhanced.py        # Enhanced profile (academic, skills, goals)
│   │   ├── documents.py               # Certificate upload + AI analysis
│   │   ├── streaks.py                 # Get/update daily practice streak
│   │   ├── ranks.py                   # Get/update XP and level
│   │   ├── badges.py                  # Get user badges, check/award badges
│   │   ├── challenges.py              # Create challenge, submit, leaderboard
│   │   ├── weekly_challenge.py        # Current week challenge, start, submit, leaderboard
│   │   ├── email_report.py            # Send weekly AI performance email
│   │   ├── career.py                  # Career evolution data
│   │   ├── career_brain.py            # Central career intelligence endpoint
│   │   └── roadmap.py                 # Milestone progress tracking
│   │
│   ├── services/                      # Business Logic & AI
│   │   ├── gemini_service.py          # Google Gemini 2.5 Flash client (6-in-1, caching, sanitization)
│   │   ├── analysis_service.py        # Run AI analysis, save/load results
│   │   ├── async_job_service.py       # Background job queue with idempotency
│   │   ├── career_brain_service.py    # Aggregates all user data → CareerBrain
│   │   ├── career_evolution_engine.py # Predictive skill evolution analysis
│   │   ├── career_memory_engine.py    # Long-term career memory tracking
│   │   ├── badge_service.py           # Auto badge checking and awarding
│   │   ├── resume_service.py          # PDF text extraction + skill extraction
│   │   ├── document_service.py        # Document CRUD + basic skill extraction
│   │   ├── profile_service.py         # Profile CRUD + completeness scoring
│   │   ├── profile_builder.py         # Merges all documents into unified skill profile
│   │   ├── skill_extractor.py         # AI-powered skill extraction by category
│   │   ├── github_service.py          # GitHub REST API client
│   │   ├── leetcode_service.py        # LeetCode GraphQL API client
│   │   ├── job_matching_service.py    # Skill-based job matching engine
│   │   ├── jobs_service.py            # SerpAPI job search + LinkedIn/Internshala URLs
│   │   ├── recommendation_engine.py   # Personalized job/career recommendations
│   │   └── market_analyzer.py         # Job market demand analysis by role
│   │
│   ├── core/                          # Infrastructure & Cross-Cutting Concerns
│   │   ├── middleware.py              # JWT verification, RBAC, structured logging, API response format
│   │   ├── cache.py                   # Redis caching client with in-memory fallback
│   │   ├── circuit_breaker.py         # Circuit breaker pattern for external calls
│   │   ├── metrics.py                 # Request metrics collector (counts, errors, slow requests)
│   │   ├── websocket.py               # WebSocket manager for real-time updates
│   │   ├── supabase_client.py         # Centralized Supabase singleton client
│   │   └── config.py                  # Environment variable management (Settings class)
│   │
│   ├── lib/                           # Shared libraries
│   │   └── auth.py                    # JWT verification utilities
│   │
│   ├── models/                        # Pydantic Data Models
│   │   ├── analysis.py
│   │   └── user.py
│   │
│   ├── tests/                         # pytest Test Suite
│   │   ├── conftest.py
│   │   ├── test_api_endpoints.py
│   │   ├── test_auth.py
│   │   ├── test_cache.py
│   │   ├── test_file_validation.py
│   │   ├── test_gemini_rate_limit.py
│   │   └── test_input_sanitization.py
│   │
│   └── docs/
│       └── response_contract.md       # API response format specification
│
└── docs/
    └── uml_diagrams.md                # Architecture UML diagrams
```

---

## Getting Started

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Node.js | 18+ | Frontend runtime |
| pnpm | Latest | Package manager (faster than npm) |
| Python | 3.10+ | Backend runtime |
| Supabase Account | — | Database + Auth |
| Google AI Studio API Key | — | Free tier Gemini 2.5 Flash |
| GitHub Personal Access Token | — | Optional — higher API rate limits |
| SerpAPI Key | — | Optional — real-time job search |
| Gmail + App Password | — | Optional — weekly email reports |
| Redis | — | Optional — falls back to in-memory cache |

### 1. Clone the Repository

```bash
cd career-navigator
```

### 2. Frontend Setup

```bash
cd frontend
pnpm install
```

Create a `.env.local` file:

```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Run the development server:

```bash
pnpm dev
```

Visit **http://localhost:3000**

### 3. Backend Setup

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file:

```env
# ── Supabase (Required) ──────────────────────────────────────────────
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_KEY=your_supabase_service_role_key
SUPABASE_ANON_KEY=your_supabase_anon_key

# ── AI (Required) ────────────────────────────────────────────────────
GEMINI_API_KEY=your_google_gemini_api_key

# ── External APIs (Optional) ─────────────────────────────────────────
GITHUB_TOKEN=your_github_personal_access_token
SERPAPI_KEY=your_serpapi_key

# ── Email (Optional) ─────────────────────────────────────────────────
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_gmail_app_password

# ── Server ───────────────────────────────────────────────────────────
CORS_ORIGINS=http://localhost:3000
```

Run the backend server:

```bash
python main.py
# or with uvicorn directly:
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

API will be available at **http://localhost:8000**

### 4. Database Setup

1. Open your Supabase project → **SQL Editor**
2. Copy and paste the entire contents of [`backend/schema.sql`](backend/schema.sql)
3. Execute the SQL to create all 15+ tables, indexes, and RLS policies

---

## Environment Variables

### Required

| Variable | Description |
|---|---|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service role key (backend-only, never expose to frontend) |
| `SUPABASE_ANON_KEY` | Supabase anon/public key (frontend-safe) |
| `GEMINI_API_KEY` | Google AI Studio API key for Gemini 2.5 Flash |

### Optional

| Variable | Description |
|---|---|
| `GITHUB_TOKEN` | GitHub Personal Access Token — raises API rate limits from 60 → 5000 req/hr |
| `SERPAPI_KEY` | SerpAPI key — enables real-time job search via Google Jobs |
| `GMAIL_USER` | Gmail address for sending weekly AI performance reports |
| `GMAIL_APP_PASSWORD` | Gmail app password (not your regular password) |
| `CORS_ORIGINS` | Comma-separated allowed origins (default: `http://localhost:3000`) |
| `REDIS_URL` | Redis connection URL (default: `redis://localhost:6379/0`) |
| `ENV` | Set to `production` for production mode |

---

## API Reference

### Base URL

```
http://localhost:8000
```

All API routes are prefixed with `/api/v1/` (except `/health`, `/metrics`, and `/`).

### Interactive Docs

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Health & Monitoring

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | API root — version and docs link |
| `/health` | GET | Health check with per-service status (database, Gemini, memory engine) |
| `/metrics` | GET | Application metrics — request counts, error rates, slow requests |

### Authentication

All protected endpoints require a `Bearer` token from Supabase Auth in the `Authorization` header.

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/auth/signup` | POST | User signup (Supabase Auth handles this client-side) |
| `/api/v1/auth/login` | POST | User login (Supabase Auth handles this client-side) |
| `/api/v1/auth/me` | GET | Get current authenticated user |

### Analysis

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/analysis/` | GET | Get current user's AI analysis |
| `/api/v1/analysis/run` | POST | Trigger AI analysis (async with background processing) |
| `/api/v1/analysis/job/{job_id}` | GET | Get async job status |
| `/api/v1/analysis/jobs` | GET | Get user's job history |

### Interview

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/interview/generate-questions` | POST | Generate AI interview questions (cached 15 min, throttled 20 sec/user) |
| `/api/v1/interview/evaluate` | POST | Evaluate a single answer (score 0–10 + feedback) |
| `/api/v1/interview/complete` | POST | Complete session — updates streak, XP, rank, badges |
| `/api/v1/interview/question-hint` | POST | Get AI coaching hint for a specific question |
| `/api/v1/interview/sessions` | GET | Get user's interview session history |

### Profile

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/profile/me` | GET | Get current user's enriched profile |
| `/api/v1/profile/save` | POST | Save/update user profile |
| `/api/v1/profile/progress` | GET | Get profile completeness progress |
| `/api/v1/profile/enhanced` | GET | Get enhanced profile (academic, skills, experience, goals) |
| `/api/v1/profile/match-fit` | GET | Get match-fit score for target role |

### Jobs

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/jobs/recommendations` | GET | Get AI-matched job recommendations |
| `/api/v1/jobs/search` | GET | Search jobs via SerpAPI |
| `/api/v1/jobs/save` | POST | Save/bookmark a job |
| `/api/v1/jobs/apply` | POST | Apply to a job (track in pipeline) |
| `/api/v1/jobs/applications` | GET | Get user's job application pipeline |
| `/api/v1/jobs/saved` | GET | Get user's saved jobs |

### Resume & Documents

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/resume/upload` | POST | Upload PDF resume (max 10MB, magic-byte validated) |
| `/api/v1/resume/status/{user_id}` | GET | Get resume upload status |
| `/api/v1/documents/upload-files` | POST | Upload + AI-analyze certificates (PDF/JPG/PNG, max 5MB each, 10 files) |
| `/api/v1/documents/list` | GET | List all user documents |
| `/api/v1/documents/{id}` | GET | Get single document |
| `/api/v1/documents/{id}` | DELETE | Delete document |

### Gamification

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/streaks/{user_id}` | GET | Get user's current streak |
| `/api/v1/streaks/update` | POST | Update streak after session completion |
| `/api/v1/ranks/{user_id}` | GET | Get user's rank and XP |
| `/api/v1/ranks/update` | POST | Update XP and level |
| `/api/v1/badges/{user_id}` | GET | Get user's earned badges (paginated) |
| `/api/v1/badges/check` | POST | Check and award badges for an event |

### Challenges

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/challenges/create` | POST | Create a shareable interview challenge |
| `/api/v1/challenges/{code}` | GET | Get challenge by code |
| `/api/v1/challenges/{code}/submit` | POST | Submit challenge answers |
| `/api/v1/challenges/{code}/leaderboard` | GET | Get challenge leaderboard |
| `/api/v1/weekly-challenge/current` | GET | Get current week's challenge (auto-creates if missing) |
| `/api/v1/weekly-challenge/start` | POST | Start weekly challenge attempt |
| `/api/v1/weekly-challenge/submit` | POST | Submit weekly challenge |
| `/api/v1/weekly-challenge/leaderboard` | GET | Weekly challenge leaderboard |
| `/api/v1/weekly-challenge/attempt` | GET | Check user's attempt status |

### Career Intelligence

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/career-brain` | GET | Get full Career Brain (job readiness, skill insights, recommendations, alerts) |
| `/api/v1/career/evolution/{user_id}` | GET | Get career evolution profile |
| `/api/v1/roadmap/milestone` | PATCH | Update roadmap milestone status (with 3-day time-gate) |

### Email

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/email/send-report` | POST | Send weekly AI performance email report |

### WebSocket

| Endpoint | Description |
|---|---|
| `/ws` | WebSocket for real-time job status, notifications, and market updates |

---

## Design System

### Color Palette

| Color | Hex | Usage |
|---|---|---|
| Primary Blue | `#1E3A5F` | Headers, primary buttons, navbar |
| Accent Blue | `#2E6CB8` | Links, highlights |
| Electric Violet | `#6C3FC8` | Accents, badges, branding, primary CTA |
| Success Green | `#22C55E` | Skills you have, positive feedback |
| Warning Orange | `#F59E0B` | Skills to improve, streak fire |
| Error Red | `#EF4444` | Missing skills, negative feedback |
| Background Dark | `#0F172A` / `#001F5B` | Page backgrounds |

### Typography

- **Display**: `Dancing Script` (brand wordmark "Jaisuuu...")
- **Body**: System sans-serif with Tailwind defaults
- **Weights**: Bold/ExtraBold for headings, Medium for body

### Component Patterns

- **Cards**: `rounded-2xl`, `border border-white/5`, `bg-slate-900/30` with hover lift
- **Buttons**: `rounded-xl`, `bg-primary-violet`, `shadow-lg` with hover transitions
- **Progress bars**: Gradient fills (`from-purple-600 to-violet-400`)
- **Animations**: Framer Motion — `fadeIn`, `staggerChildren`, `layout` animations

---

## Testing

The backend includes a comprehensive pytest test suite:

```bash
cd backend
pytest
```

### Test Files

| File | Coverage |
|---|---|
| `tests/test_api_endpoints.py` | All API route integration tests |
| `tests/test_auth.py` | JWT verification and authentication |
| `tests/test_cache.py` | Redis + in-memory cache behavior |
| `tests/test_file_validation.py` | PDF magic-byte and size validation |
| `tests/test_gemini_rate_limit.py` | Gemini API rate limit handling |
| `tests/test_input_sanitization.py` | Prompt injection detection and neutralization |

---

## Documentation

| Document | Description |
|---|---|
| [`docs/uml_diagrams.md`](docs/uml_diagrams.md) | Architecture UML diagrams — component, sequence, and deployment views |
| [`backend/docs/response_contract.md`](backend/docs/response_contract.md) | Standardized API response format specification |
| [`backend/schema.sql`](backend/schema.sql) | Complete Supabase database schema with RLS policies |

---

## Key Architectural Decisions

### Why FastAPI + Next.js?

FastAPI provides automatic OpenAPI docs, async/await native support, and Pydantic validation — ideal for the many AI service integrations. Next.js App Router gives file-based routing, server components, and a rich ecosystem for the interactive frontend.

### Why Supabase?

Supabase provides PostgreSQL with real-time subscriptions, built-in Auth (JWT), and a generous free tier — eliminating the need to manage a separate auth server or database connection pool.

### Why Gemini 2.5 Flash?

The free tier provides 15 RPM with no credit card required. The 6-in-1 combined analysis call (strengths + weaknesses + career paths + skill gaps + roadmap + resume score in one prompt) minimizes API calls and maximizes cost efficiency.

### Why the Career Orchestrator Pattern?

The frontend [`career-orchestrator.ts`](frontend/lib/career-orchestrator.ts) is a **single source of truth** for all AI decisions. It fuses progress data, evolution data, and career memory into one `CareerBrain` object. All pages (interview, progress, dashboard) consume this single object — eliminating scattered decision logic and ensuring consistent AI behavior across the entire app.

### Why Async Job Processing?

AI analysis can take 10–30 seconds. Rather than blocking the HTTP request, the backend creates an async job and returns a `job_id` immediately. The frontend polls for status. This also enables idempotent job creation — duplicate requests within a 5-minute window return the existing job instead of creating a new one.

---

## License

MIT License
