# MVC Architecture Documentation

## Overview

The AI Career Navigator project follows a **Model-View-Controller (MVC)** architecture pattern, split between the **Frontend** (Next.js/React) and **Backend** (FastAPI/Python).

---

## Frontend MVC (Next.js/React)

### View Layer

The View layer consists of React components that render the UI:

| Component | File Path | Purpose |
|-----------|-----------|---------|
| Interview Page | `frontend/app/interview/page.tsx` | Main interview interface container |
| Setup Screen | `frontend/app/interview/components/SetupScreen.tsx` | Interview configuration UI |
| Interview Screen | `frontend/app/interview/components/InterviewScreen.tsx` | Active interview session UI |
| Results Screen | `frontend/app/interview/components/ResultsScreen.tsx` | Interview results display |
| Analysis Page | `frontend/app/analysis/page.tsx` | Career analysis display |
| Resume Page | `frontend/app/resume/page.tsx` | Resume management UI |
| Dashboard Page | `frontend/app/dashboard/page.tsx` | User dashboard |
| UI Components | `frontend/components/ui/*` | Reusable UI primitives |

### Controller Layer

The Controller layer manages state and business logic through custom hooks:

| Hook | File Path | Responsibility |
|------|-----------|----------------|
| `useInterviewSession` | `frontend/app/interview/hooks/useInterviewSession.ts` | Interview state management, answer submission, session flow |
| `useVoiceInput` | `frontend/app/interview/hooks/useVoiceInput.ts` | Voice recording and speech-to-text |
| `useSimTimer` | `frontend/app/interview/hooks/useSimTimer.ts` | Simulation timer logic |
| `useWeeklyChallenge` | `frontend/app/interview/hooks/useWeeklyChallenge.ts` | Weekly challenge state |
| `api.ts` | `frontend/lib/api.ts` | API client for backend communication |

### Model Layer

The Model layer defines data structures and data access:

| Module | File Path | Purpose |
|--------|-----------|---------|
| Supabase Client | `frontend/lib/supabase.ts` | Database client and types |
| API Types | `frontend/lib/api.ts` | TypeScript interfaces for API data |
| Career Orchestrator | `frontend/lib/career-orchestrator.ts` | Career brain data fetching |

---

## Backend MVC (FastAPI/Python)

### View Layer

The View layer handles HTTP responses:

| Component | File Path | Purpose |
|-----------|-----------|---------|
| JSON Responses | `backend/routers/*.py` | Structured API responses |
| Error Handlers | `backend/main.py` | Global error handling |

### Controller Layer

The Controller layer consists of FastAPI routers:

| Router | File Path | Endpoints |
|--------|-----------|-----------|
| Interview | `backend/routers/interview.py` | `/generate-questions`, `/evaluate-answer`, `/save-session` |
| Analysis | `backend/routers/analysis.py` | `/run`, `/job/{id}`, `/career-paths` |
| Auth | `backend/routers/auth.py` | `/login`, `/signup`, `/callback` |
| Resume | `backend/routers/resume.py` | `/upload`, `/list`, `/{id}` |
| Jobs | `backend/routers/jobs.py` | `/recommendations` |
| Profile | `backend/routers/profile.py` | `/me`, `/save`, `/progress` |
| Badges | `backend/routers/badges.py` | `/check`, `/award` |
| Streaks | `backend/routers/streaks.py` | `/update`, `/status` |
| Ranks | `backend/routers/ranks.py` | `/update`, `/status` |
| Weekly Challenge | `backend/routers/weekly_challenge.py` | `/leaderboard`, `/submit` |

### Model Layer

The Model layer contains data models and services:

| Module | File Path | Purpose |
|--------|-----------|---------|
| Analysis Models | `backend/models/analysis.py` | Pydantic models for analysis data |
| User Models | `backend/models/user.py` | Pydantic models for user data |
| Supabase Client | `backend/core/supabase_client.py` | Database client |
| Gemini Service | `backend/services/gemini_service.py` | AI analysis and question generation |
| Badge Service | `backend/services/badge_service.py` | Badge calculation and awarding |
| Job Matching Service | `backend/services/job_matching_service.py` | Job recommendation logic |

---

## Data Flow Example: Interview Session

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND FLOW                             │
└─────────────────────────────────────────────────────────────────┘

User Input
    ↓
[View] SetupScreen.tsx
    - User selects career path, difficulty, interview mode
    ↓
[Controller] useInterviewSession.ts
    - startInterview() called
    - Calls api.generateQuestions()
    ↓
[Model] api.ts → fetch('/api/v1/interview/generate-questions')
    ↓
                    HTTP Request
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│                        BACKEND FLOW                               │
└─────────────────────────────────────────────────────────────────┘
    ↓
[Controller] interview.py:generate_questions()
    - Validates user via AuthMiddleware
    - Checks cache, throttling
    ↓
[Model] gemini_service.py:generate_interview_questions()
    - Calls Google Gemini API
    - Returns personalized questions
    ↓
[View] JSON Response { success, questions, source, meta }
    ↑
                    HTTP Response
                        ↑
[Model] api.ts ← Response parsed
    ↓
[Controller] useInterviewSession.ts
    - setQuestions() updates state
    - setScreen('interview')
    ↓
[View] InterviewScreen.tsx
    - Renders questions
    - User answers questions
    - submitAnswer() called
```

---

## Key Design Patterns

### 1. Separation of Concerns

```
Frontend:
  View = React Components (presentation only)
  Controller = Custom Hooks (state + logic)
  Model = Types + API Client (data)

Backend:
  View = JSON Responses (data serialization)
  Controller = Routers (request handling)
  Model = Services + Models (business logic + data)
```

### 2. Data Flow Pattern

```typescript
// Frontend Controller Pattern
function useInterviewSession() {
  const [state, setState] = useState(initialState);
  
  const startInterview = useCallback(async () => {
    const questions = await api.generateQuestions(data);
    setState(prev => ({ ...prev, questions, screen: 'interview' }));
  }, []);
  
  return { state, startInterview, ...actions };
}
```

```python
# Backend Controller Pattern
@router.post("/generate-questions")
async def generate_questions(
  request: Request,
  body: GenerateQuestionsRequest,
  current_user: AuthenticatedUser = Depends(get_current_user)
):
  # Controller logic
  questions = gemini_service.generate_interview_questions(...)
  return {"success": True, "questions": questions}
```

### 3. Type Safety

```typescript
// Frontend Model (TypeScript)
interface Question {
  id: number;
  question: string;
  type: string;
  difficulty: string;
  hint: string;
}
```

```python
# Backend Model (Pydantic)
class CareerPath(BaseModel):
    name: str
    match_percentage: int
    reason: str
```

---

## File Structure Mapping

```
frontend/
├── app/
│   ├── interview/
│   │   ├── page.tsx              # View: Container
│   │   ├── components/           # View: UI Components
│   │   └── hooks/                # Controller: State Management
│   ├── analysis/
│   │   └── page.tsx              # View: Analysis Display
│   └── ...
├── components/
│   └── ui/                       # View: Reusable Components
└── lib/
    ├── api.ts                    # Model: API Client + Types
    ├── supabase.ts               # Model: Database Client
    └── career-orchestrator.ts    # Model: Data Fetching

backend/
├── routers/                      # Controller: API Endpoints
│   ├── interview.py
│   ├── analysis.py
│   └── ...
├── models/                       # Model: Pydantic Models
│   ├── analysis.py
│   └── user.py
├── services/                     # Model: Business Logic
│   ├── gemini_service.py
│   ├── badge_service.py
│   └── ...
└── core/
    └── supabase_client.py       # Model: Database Client
```

---

## Best Practices Applied

1. **Single Responsibility**: Each file has one clear purpose
2. **Type Safety**: TypeScript interfaces and Pydantic models
3. **Separation of Concerns**: UI, logic, and data are isolated
4. **Reusability**: Custom hooks and UI components are reusable
5. **Testability**: Services and hooks can be unit tested independently
6. **Scalability**: Modular structure allows easy feature addition