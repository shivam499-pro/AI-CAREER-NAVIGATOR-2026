# AI Career Navigator 2026 — Project Summary

> **Prepared for:** Planning Lead (Gemini)  
> **Status:** Development Phase (Mock Mode Enabled)  
> **Repository:** `shivam499-pro/AI-CAREER-NAVIGATOR-2026`

---

## 1. Tech Stack

### Frontend
- **Framework:** Next.js 14 (App Router) with TypeScript
- **Styling:** Tailwind CSS + Radix UI (shadcn/ui)
- **Animations:** Framer Motion
- **Data Visualization:** Recharts
- **Icons:** Lucide React

### Backend
- **Framework:** FastAPI (Python 3.10+)
- **Server:** Uvicorn
- **AI Integration:** Google Gemini 2.5 Flash (via `google-genai`)
- **PDF Parsing:** PyMuPDF (`fitz`)
- **Data Validation:** Pydantic

### Database & Auth
- **Provider:** Supabase (PostgreSQL)
- **Integration:** `@supabase/supabase-js` (Frontend) & `supabase-py` (Backend)

---

## 2. File Tree (High-Level)

```text
career-navigator/
├── backend/                  # FastAPI Backend
│   ├── main.py               # Entry point & Router registration
│   ├── routers/              # API endpoints (auth, analysis, jobs, resume, etc.)
│   ├── services/             # Core logic (AI, GitHub, LeetCode, Resume)
│   ├── models/               # Pydantic schemas
│   └── .env                  # Backend secrets
├── frontend/                 # Next.js Frontend
│   ├── app/                  # App Router pages (onboarding, dashboard, analysis)
│   ├── components/           # UI components (shadcn/ui)
│   ├── lib/                  # Utilities (supabase client, api helpers)
│   └── .env.local            # Frontend public keys
└── README.md                 # Project documentation
```

---

## 3. Core Logic Flow

### Journey: Resume Upload → Career Roadmap

1.  **Resume Upload:** 
    - User uploads PDF via `frontend/app/resume/page.tsx`.
    - `POST /api/resume/upload` called in `backend/routers/resume.py`.
    - PyMuPDF extracts raw text via `resume_service.py`.
    - Text is saved to `profiles` table in Supabase.

2.  **AI Analysis Trigger:**
    - `POST /api/analysis/start` called from `frontend/app/analysis/page.tsx`.
    - Backend fetches GitHub (REST) and LeetCode (GraphQL) data.
    - `gemini_service.run_combined_analysis` combines Resume + GitHub + LeetCode data into 1 prompt.

3.  **Result Persistence:**
    - Gemini returns structured JSON: `analysis`, `career_paths`, `skill_gaps`, `roadmap`.
    - Results are cached in-memory and saved to `analyses` table.
    - Frontend renders the Roadmap and Skill Gaps using `Recharts` and `framer-motion`.

---

## 4. The 'Last Mile' Status

### 3 Most Recent Features
1.  **Gemini 2.5 Flash Upgrade:** Upgraded from 2.0 to 2.5 for faster and more precise career mapping.
2.  **Claude → Gemini Migration:** Successfully transitioned all AI services from Anthropic to Google Gemini.
3.  **Enhanced Profile & Onboarding:** Added a multi-step onboarding wizard and academic profile CRUD.

### Current TODOs/Known Bugs
- [ ] **Security:** `middleware.ts` in frontend is currently a pass-through; needs strict route protection.
- [ ] **Interview Bug:** `interview.py` endpoint crashes due to accessing `request.user_id` instead of `body.user_id`.
- [ ] **Data Completeness:** Jobs page falls back to mock data if SerpAPI keys are missing or query fails.
- [ ] **Cache Bounding:** The in-memory analysis cache in `gemini_service.py` lacks a TTL/LRU limit.

---

## 5. Environment Variables (.env)

| Key | Description | Required |
|-----|-------------|----------|
| `GEMINI_API_KEY` | Google AI Studio Key | **Yes** |
| `SUPABASE_URL` | Supabase Project URL | **Yes** |
| `SUPABASE_SERVICE_KEY` | Supabase Service Role Key | **Yes** (Backend) |
| `NEXT_PUBLIC_SUPABASE_URL` | Frontend Supabase URL | **Yes** |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY`| Frontend Anon Key | **Yes** |
| `GITHUB_TOKEN` | GitHub Personal Access Token | Optional |
| `SERPAPI_KEY` | SerpAPI for Job Search | Optional |

---

## 6. Known Limitations
- **Gemini Free Tier:** Subject to Rate Limits (RPM/RPD). If exceeded, analysis will fail.
- **Mock Mode:** `MOCK_MODE = True` is currently enabled in `gemini_service.py` for testing without API consumption.
- **PDF Extraction:** Complex layouts (multi-column) may result in disorganized text extraction.

---

## 7. Database Schema (Supabase)

### Table: `profiles`
- `user_id` (UUID, Primary Key)
- `github_username`, `leetcode_username`, `linkedin_url`
- `resume_text` (Text), `resume_filename`
- `college_name`, `degree`, `branch`, `cgpa`
- `extra_skills` (Text[]), `career_goal`

### Table: `analyses`
- `user_id` (UUID, Foreign Key)
- `analysis` (JSONB) - strengths/weakness
- `career_paths` (JSONB), `skill_gaps` (JSONB), `roadmap` (JSONB)
- `experience_level` (Text), `created_at`

---

## 8. What's NOT yet implemented
- **Real-time Job Alerts:** Currently search-based only.
- **Mock Interviews UI:** Backend exists, but frontend needs full interactive chat state management.
- **Skill Certification Verification:** Currently relies on self-reported/resume data.
- **Community/Social:** No peer-to-peer roadmap sharing.
