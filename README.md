# AI Career Navigator-2026

Your personal AI-powered career mentor that reads your real GitHub, LeetCode, LinkedIn, and Resume profiles to provide personalized career guidance.

## Features

- **Profile Reading Engine**: Reads real user profiles (GitHub, LeetCode, LinkedIn, Resume)
- **AI Analysis Engine**: Analyzes skills, experience level, and career interests
- **Career Path Recommender**: Suggests personalized career paths
- **Skill Gap Analyzer**: Visual breakdown of skills you have vs. need
- **Roadmap Generator**: Personalized, time-bound action plan
- **Job Suggestions**: Matched job and internship opportunities

## Tech Stack

- **Frontend**: Next.js 14 (React) + Tailwind CSS + TypeScript
- **Backend**: Python FastAPI
- **Database**: Supabase (PostgreSQL)
- **AI**: Claude API (claude-sonnet-4-20250514)
- **Authentication**: Supabase Auth

## Project Structure

```
career-navigator/
├── frontend/                    # Next.js frontend
│   ├── app/                     # Next.js App Router pages
│   ├── components/              # React components
│   │   └── ui/                  # shadcn/ui components
│   ├── lib/                     # Utilities and API clients
│   └── public/                  # Static assets
├── backend/                     # FastAPI backend
│   ├── routers/                 # API route handlers
│   ├── services/                # Business logic
│   └── models/                 # Data models
└── README.md
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- Supabase account

### 1. Clone the Repository

```bash
cd career-navigator
```

### 2. Frontend Setup

```bash
cd frontend
npm install
```

Create a `.env.local` file:

```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Run the development server:

```bash
npm run dev
```

Visit http://localhost:3000

### 3. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SUPABASE_ANON_KEY=your_supabase_anon_key
ANTHROPIC_API_KEY=your_claude_api_key
GITHUB_TOKEN=your_github_token  # Optional
SERPAPI_KEY=your_serpapi_key     # Optional
CORS_ORIGINS=http://localhost:3000
```

Run the backend server:

```bash
python main.py
```

API will be available at http://localhost:8000

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Color Palette

| Color | Hex Code | Usage |
|-------|----------|-------|
| Primary Blue | #1E3A5F | Headers, primary buttons |
| Accent Blue | #2E6CB8 | Links, highlights |
| Electric Violet | #6C3FC8 | Accents, badges |
| Success Green | #22C55E | Skills you have |
| Warning Orange | #F59E0B | Skills to improve |
| Error Red | #EF4444 | Missing skills |

## License

MIT License
