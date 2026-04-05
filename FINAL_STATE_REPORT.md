# AI Career Navigator 2026 — Final State Report

> **Generated:** April 5, 2026  
> **Purpose:** Onboarding guide for new developers joining the project

---

## 1. Project Overview

**AI Career Navigator** is a full-stack web application that acts as your personal AI-powered career mentor. It analyzes users' real GitHub, LeetCode, LinkedIn, and Resume profiles to provide personalized career guidance, including:

- AI-generated career path recommendations with match percentages
- Skill gap analysis with prioritized learning resources
- Personalized roadmap with weekly milestones
- Interview preparation with AI-generated questions and answer evaluation
- Job search integration
- Gamification (streaks, XP, ranks, badges)
- Weekly coding challenges

---

## 2. Tech Stack

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| Next.js | 14.2.0 | App Router framework |
| React | 18.2.0 | UI library |
| TypeScript | 5.3.3 | Type safety |
| Tailwind CSS | 3.4.1 | Styling |
| Framer Motion | 10.18.0 | Animations |
| Recharts | 2.10.4 | Data visualization |
| Lucide React | 0.312.0 | Icons |
| Radix UI | Various | Accessible UI primitives |
| Supabase SSR | 0.1.0 | Auth helpers |

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| FastAPI | ≥0.109.0 | Web framework |
| Uvicorn | ≥0.27.0 | ASGI server |
| Google Gemini | ≥1.68.0 | AI (Gemini 2.5 Flash) |
| PyMuPDF | 1.27.2 | PDF text extraction |
| Pydantic | ≥2.11.7 | Data validation |
| Supabase | 2.28.2 | Database client |
| SlowAPI | 0.1.9 | Rate limiting |
| PyJWT | ≥2.8.0 | Token handling |

### Database & Auth
- **Provider:** Supabase (PostgreSQL)
- **Authentication:** Supabase Auth + custom JWT tokens
- **Package Manager:** pnpm (frontend), pip (backend)

---

## 3. Project Structure

```
career-navigator/
├── backend/                      # FastAPI Backend
│   ├── main.py                   # Entry point, router registration, env validation
│   ├── requirements.txt          # Python dependencies
│   ├── schema.sql                # Complete database schema with RLS policies
│   ├── lib/
│   │   └── auth.py               # JWT token creation/validation, get_current_user
│   ├── models/
│   │   ├── __init__.py
│   │   ├── analysis.py
│   │   └── user.py
│   ├── routers/                  # API endpoints (14 routers)
│   │   ├── analysis.py           # AI career analysis
│   │   ├── auth.py               # Authentication
│   │   ├── badges.py             # Achievement badges
│   │   ├── challenges.py          # Shared interview challenges
│   │   ├── documents.py          # Document handling
│   │   ├── email_report.py       # Weekly progress emails
│   │   ├── interview.py          # Interview practice
│   │   ├── jobs.py               # Job search
│   │   ├── profile_enhanced.py   # User profiles
│   │   ├── ranks.py              # XP/level system
│   │   ├── resume.py             # Resume upload/parsing
│   │   ├── streaks.py            # Daily practice streaks
│   │   ├── weekly_challenge.py   # Weekly coding challenges
│   │   └── __init__.py
│   └── services/                  # Business logic
│       ├── gemini_service.py     # AI analysis (sanitized, cached, rate-limited)
│       ├── github_service.py     # GitHub API integration
│       ├── jobs_service.py      # SerpAPI job search
│       ├── leetcode_service.py   # LeetCode GraphQL integration
│       ├── resume_service.py     # PDF text extraction
│       └── __init__.py
│
├── frontend/                     # Next.js Frontend
│   ├── package.json
│   ├── next.config.js
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── middleware.ts             # Route protection (auth required except public routes)
│   ├── app/                      # App Router pages (18 pages)
│   │   ├── layout.tsx            # Root layout with auth state
│   │   ├── page.tsx              # Landing page
│   │   ├── globals.css
│   │   ├── auth/                 # Authentication pages
│   │   │   ├── login/
│   │   │   ├── signup/
│   │   │   └── callback/         # OAuth callback handler
│   │   ├── dashboard/            # Main user dashboard
│   │   ├── analysis/              # AI analysis results
│   │   ├── resume/                # Resume upload
│   │   ├── interview/             # Interview practice
│   │   ├── jobs/                  # Job search
│   │   ├── challenges/            # Challenge listing
│   │   ├── challenge/[code]/     # Individual challenge
│   │   ├── badges/                # Achievements
│   │   ├── progress/              # Progress tracking
│   │   ├── profile/               # User profile
│   │   ├── onboarding/            # New user onboarding wizard
│   │   └── error.tsx / loading.tsx # Error boundaries
│   ├── components/                # Reusable UI components
│   │   ├── ui/                    # Radix/shadcn primitives
│   │   ├── Navbar.tsx
│   │   ├── CareerRoadmap.tsx
│   │   ├── MatchFitScore.tsx
│   │   └── ProgressTracker.tsx
│   └── lib/
│       ├── api.ts                 # Frontend API client
│       ├── supabase.ts            # Supabase client
│       └── utils.ts               # Utilities (cn, etc.)
│
├── package.json                  # Root (framer-motion)
├── pnpm-lock.yaml
├── README.md                     # User-facing documentation
├── project_summary.md            # Technical deep-dive
└── .gitignore
```

---

## 4. What's Working (After Improvements)

### ✅ Security Features
1. **Route Protection** - [`frontend/middleware.ts`](frontend/middleware.ts:1) properly enforces authentication. Unauthenticated users are redirected to `/auth/login`.

2. **JWT Authentication** - [`backend/lib/auth.py`](backend/lib/auth.py:1) implements:
   - Access tokens (1-hour expiry)
   - Refresh tokens (7-day expiry)
   - Token validation with expiry checks
   - Supabase token fallback validation

3. **Rate Limiting** - [`backend/main.py`](backend/main.py:80) uses SlowAPI to protect endpoints:
   - Analysis: 5 requests/minute
   - Interview: 10 requests/minute
   - Global per-IP limit

4. **Input Sanitization** - [`backend/services/gemini_service.py`](backend/services/gemini_service.py:88) sanitizes all user inputs before AI prompts:
   - Prompt injection detection with pattern matching
   - Max input length limits
   - Logging of blocked attempts

5. **Environment Validation** - [`backend/main.py`](backend/main.py:9) validates required env vars at startup:
   - Exits with clear error if missing
   - Warns about missing optional vars

6. **CORS Configuration** - Properly restricted to configured origins.

### ✅ Bugs Fixed
1. **Interview Bug** - Fixed in [`backend/routers/interview.py`](backend/routers/interview.py:98):
   - Changed `request.user_id` → `body.user_id` (was accessing wrong object)

2. **Cache Bounding** - Added in [`backend/services/gemini_service.py`](backend/services/gemini_service.py:238):
   - LRU eviction when > 100 entries
   - TTL expiry (1 hour)
   - Automatic cleanup on each request

3. **Mock Mode** - Now properly disabled (`MOCK_MODE = False` in [`gemini_service.py line 19`](backend/services/gemini_service.py:19))

### ✅ Features Complete
1. **Profile System** - Full onboarding wizard with 4 user types:
   - Student (college, degree, branch, year, CGPA)
   - Professional (job title, company, years exp, tech stack)
   - Fresher
   - Career Switcher

2. **AI Analysis** - Single combined Gemini call replaces 4+ separate calls:
   - Analyzes GitHub + LeetCode + Resume + Profile
   - Returns: strengths, weaknesses, experience level
   - Career paths with match percentages
   - Skill gaps with priorities and resources
   - Personalized roadmap with weekly milestones

3. **Interview Prep** - Complete flow:
   - Question generation based on career path + profile
   - Answer evaluation with scoring
   - AI coaching hints
   - Session history storage

4. **Gamification**:
   - Daily streaks (Duolingo-style)
   - XP and levels
   - Rank titles (🌱 Fresher → 🏆 Industry Expert)
   - Achievement badges

5. **Challenges**:
   - Shared interview challenges with shareable codes
   - Weekly coding challenges
   - Leaderboard tracking

6. **Email Reports** - Weekly progress emails via Gmail SMTP.

---

## 5. Database Schema

### Tables (10 total)
| Table | Purpose |
|-------|---------|
| `profiles` | User profiles, education, experience, goals |
| `analyses` | AI analysis results |
| `interview_sessions` | Interview practice history |
| `user_streaks` | Daily practice streaks |
| `user_ranks` | XP and rank titles |
| `user_badges` | Earned badges |
| `challenges` | Shared challenges |
| `challenge_results` | Challenge submissions |
| `weekly_challenges` | Weekly challenge definitions |
| `weekly_results` | Weekly challenge submissions |

### Security
- **Row Level Security (RLS)** enabled on all tables
- Users can only access their own data
- Service role bypass available for admin operations

---

## 6. Environment Variables

### Required
```env
# Backend (.env)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key
GEMINI_API_KEY=your_google_ai_studio_key
JWT_SECRET_KEY=your-32-char-minimum-secret

# Frontend (.env.local)
NEXT_PUBLIC_SUPABASE_URL=your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Optional
```env
GITHUB_TOKEN=your_github_pat          # Higher rate limits
SERPAPI_KEY=your_serpapi_key          # Real job search data
GMAIL_USER=your-email@gmail.com        # Weekly emails
GMAIL_APP_PASSWORD=your_16char_app_password
```

---

## 7. What's NOT Working / Known Limitations

| Issue | Status | Workaround |
|-------|--------|------------|
| **Job Search Fallback** | Jobs page uses mock data without `SERPAPI_KEY` | Get SerpAPI key from serpapi.com |
| **Rate Limiting** | Gemini free tier has 15 RPM / 1,500 RPD limit | Wait 60s, exponential backoff implemented |
| **PDF Extraction** | Multi-column layouts may extract poorly | User uploads clean PDFs |
| **RLS on Challenges** | Public read access needed | Adjust policies in schema.sql |

---

## 8. Running the Project

### Backend
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate | Unix: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Fill in values
python main.py
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Frontend
```bash
cd frontend
pnpm install
cp .env.example .env.local  # Fill in values
pnpm dev
# App: http://localhost:3000
```

---

## 9. API Endpoints Summary

| Prefix | Endpoints |
|--------|-----------|
| `/api/auth` | login, signup, refresh, logout |
| `/api/analysis` | start, results/{user_id}, status/{user_id} |
| `/api/profile` | GET, POST (enhanced CRUD) |
| `/api/resume` | upload, get |
| `/api/interview` | generate-questions, evaluate-answer, save-session, history, progress |
| `/api/jobs` | search |
| `/api/streaks` | get, update |
| `/api/ranks` | get, update |
| `/api/badges` | get, award |
| `/api/challenges` | list, create, submit |
| `/api/weekly` | current, submit |
| `/api/email` | send-weekly |
| `/api/documents` | upload, download |

---

## 10. Future Development

### Not Yet Implemented
- **Real-time Job Alerts** - WebSocket-based notifications
- **Interactive Interview UI** - Full chat interface with message history
- **Skill Certification Verification** - Third-party API integration
- **Community Features** - Share roadmaps, peer reviews

---

## 11. Key Files for Reference

| File | Description |
|------|-------------|
| [`project_summary.md`](project_summary.md:1) | Detailed technical overview |
| [`README.md`](README.md:1) | User-facing setup guide |
| [`backend/schema.sql`](backend/schema.sql:1) | Complete DB schema with RLS |
| [`backend/main.py`](backend/main.py:1) | App entry, router setup, validation |
| [`backend/services/gemini_service.py`](backend/services/gemini_service.py:1) | AI logic, sanitization, caching |
| [`backend/lib/auth.py`](backend/lib/auth.py:1) | JWT and auth logic |
| [`frontend/middleware.ts`](frontend/middleware.ts:1) | Route protection |

---

*This report reflects the complete state of the project after all improvements, security enhancements, and bug fixes.*
