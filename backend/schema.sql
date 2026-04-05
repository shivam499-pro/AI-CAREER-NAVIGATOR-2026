-- =============================================================================
-- AI Career Navigator 2026 - Database Schema
-- Generated from Pydantic models and router/supabase table interactions
-- =============================================================================

-- =============================================================================
-- PROFILES TABLE
-- Stores user profile data including education, work experience, and goals
-- =============================================================================

CREATE TABLE IF NOT EXISTS profiles (
    -- Primary key (references Supabase auth.users)
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Basic contact info
    email TEXT,
    github_username TEXT,
    leetcode_username TEXT,
    linkedin_url TEXT,
    
    -- Resume data
    resume_text TEXT,
    resume_filename TEXT,
    resume_url TEXT,
    
    -- Academic info (students/freshers)
    college_name TEXT,
    degree TEXT,
    branch TEXT,
    year_of_study TEXT,
    graduation_year INTEGER,
    cgpa TEXT,
    
    -- User type classification
    user_type TEXT,  -- 'student' | 'professional' | 'fresher' | 'career_switch'
    
    -- Professional info
    current_job_title TEXT,
    current_company TEXT,
    years_of_experience INTEGER,
    current_tech_stack JSONB,
    reason_for_switching TEXT,
    
    -- Career goals
    career_goal TEXT,
    target_companies JSONB,
    preferred_work_type TEXT,
    job_search_timeline TEXT,
    
    -- Skills and certifications
    extra_skills TEXT[],
    certificates TEXT[],
    
    -- Additional fields (referenced in profile_enhanced.py)
    experience JSONB,
    preferred_location TEXT,
    open_to TEXT,
    codechef_rating INTEGER,
    codeforces_rating INTEGER,
    hackathon_wins INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RLS Placeholder for profiles:
-- ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Users can view own profile" ON profiles FOR SELECT USING (auth.uid() = user_id);
-- CREATE POLICY "Users can update own profile" ON profiles FOR UPDATE USING (auth.uid() = user_id);
-- CREATE POLICY "Service role can all" ON profiles FOR ALL USING (auth.role() = 'service_role');


-- =============================================================================
-- ANALYSES TABLE
-- Stores AI-generated career analysis results
-- =============================================================================

CREATE TABLE IF NOT EXISTS analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    
    -- External data (JSONB)
    github_data JSONB,
    leetcode_data JSONB,
    
    -- AI analysis results (JSONB)
    analysis JSONB,  -- strengths, weaknesses, experience_level
    career_paths JSONB,
    skill_gaps JSONB,
    roadmap JSONB,
    
    -- Simple fields
    experience_level TEXT,
    strengths TEXT[],
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add unique constraint for user_id
ALTER TABLE analyses ADD CONSTRAINT analyses_user_id_unique UNIQUE (user_id);

-- RLS Placeholder for analyses:
-- ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Users can view own analysis" ON analyses FOR SELECT USING (auth.uid() = user_id);
-- CREATE POLICY "Users can insert own analysis" ON analyses FOR INSERT WITH CHECK (auth.uid() = user_id);
-- CREATE POLICY "Users can update own analysis" ON analyses FOR UPDATE USING (auth.uid() = user_id);


-- =============================================================================
-- INTERVIEW_SESSIONS TABLE
-- Stores interview practice session data
-- =============================================================================

CREATE TABLE IF NOT EXISTS interview_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    career_path TEXT NOT NULL,
    
    -- Session data (JSONB)
    questions JSONB,
    answers JSONB,
    scores JSONB,
    
    -- Scores
    total_score FLOAT NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RLS Placeholder for interview_sessions:
-- ALTER TABLE interview_sessions ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Users can view own sessions" ON interview_sessions FOR SELECT USING (auth.uid() = user_id);
-- CREATE POLICY "Users can insert own sessions" ON interview_sessions FOR INSERT WITH CHECK (auth.uid() = user_id);


-- =============================================================================
-- USER_STREAKS TABLE
-- Stores daily practice streak data (Duolingo-style)
-- =============================================================================

CREATE TABLE IF NOT EXISTS user_streaks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE,
    
    -- Streak data
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_practice_date DATE,
    total_sessions INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RLS Placeholder for user_streaks:
-- ALTER TABLE user_streaks ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Users can view own streak" ON user_streaks FOR SELECT USING (auth.uid() = user_id);
-- CREATE POLICY "Users can update own streak" ON user_streaks FOR UPDATE USING (auth.uid() = user_id);


-- =============================================================================
-- USER_RANKS TABLE
-- Stores user XP and ranking data
-- =============================================================================

CREATE TABLE IF NOT EXISTS user_ranks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE,
    
    -- Rank data
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    rank_title TEXT DEFAULT '🌱 Fresher',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RLS Placeholder for user_ranks:
-- ALTER TABLE user_ranks ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Users can view own rank" ON user_ranks FOR SELECT USING (auth.uid() = user_id);
-- CREATE POLICY "Users can update own rank" ON user_ranks FOR UPDATE USING (auth.uid() = user_id);


-- =============================================================================
-- USER_BADGES TABLE
-- Stores earned achievement badges
-- =============================================================================

CREATE TABLE IF NOT EXISTS user_badges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    badge_id TEXT NOT NULL,
    earned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Unique constraint on user_id + badge_id
    CONSTRAINT user_badges_user_badge_unique UNIQUE (user_id, badge_id)
);

-- RLS Placeholder for user_badges:
-- ALTER TABLE user_badges ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Users can view own badges" ON user_badges FOR SELECT USING (auth.uid() = user_id);
-- CREATE POLICY "Users can insert own badges" ON user_badges FOR INSERT WITH CHECK (auth.uid() = user_id);


-- =============================================================================
-- CHALLENGES TABLE
-- Stores shared interview challenges
-- =============================================================================

CREATE TABLE IF NOT EXISTS challenges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    challenge_code TEXT NOT NULL UNIQUE,
    creator_id UUID NOT NULL,
    career_path TEXT NOT NULL,
    questions JSONB NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RLS Placeholder for challenges:
-- ALTER TABLE challenges ENABLE ROW LEVEL SECURITY;


-- =============================================================================
-- CHALLENGE_RESULTS TABLE
-- Stores challenge submission results/leaderboard
-- =============================================================================

CREATE TABLE IF NOT EXISTS challenge_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    challenge_code TEXT NOT NULL,
    user_id UUID NOT NULL,
    user_email TEXT,
    user_name TEXT,
    score FLOAT NOT NULL,
    answers JSONB,
    completed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RLS Placeholder for challenge_results:
-- ALTER TABLE challenge_results ENABLE ROW LEVEL SECURITY;


-- =============================================================================
-- WEEKLY_CHALLENGES TABLE
-- Stores weekly challenge definitions
-- =============================================================================

CREATE TABLE IF NOT EXISTS weekly_challenges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    week_number INTEGER NOT NULL,
    year INTEGER NOT NULL,
    career_path TEXT NOT NULL,
    questions JSONB NOT NULL,
    creator_id UUID,
    
    -- Unique constraint
    CONSTRAINT weekly_challenges_week_year_unique UNIQUE (week_number, year),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RLS Placeholder for weekly_challenges:
-- ALTER TABLE weekly_challenges ENABLE ROW LEVEL SECURITY;


-- =============================================================================
-- WEEKLY_RESULTS TABLE
-- Stores weekly challenge submissions
-- =============================================================================

CREATE TABLE IF NOT EXISTS weekly_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    user_email TEXT,
    week_number INTEGER NOT NULL,
    year INTEGER NOT NULL,
    score FLOAT NOT NULL,
    answers JSONB,
    completed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RLS Placeholder for weekly_results:
-- ALTER TABLE weekly_results ENABLE ROW LEVEL SECURITY;


-- =============================================================================
-- INDEXES
-- Performance optimization indexes
-- =============================================================================

-- Indexes for profiles
CREATE INDEX IF NOT EXISTS profiles_user_id_idx ON profiles(user_id);
CREATE INDEX IF NOT EXISTS profiles_github_idx ON profiles(github_username);
CREATE INDEX IF NOT EXISTS profiles_leetcode_idx ON profiles(leetcode_username);

-- Indexes for analyses
CREATE INDEX IF NOT EXISTS analyses_user_id_idx ON analyses(user_id);
CREATE INDEX IF NOT EXISTS analyses_created_at_idx ON analyses(created_at DESC);

-- Indexes for interview_sessions
CREATE INDEX IF NOT EXISTS interview_sessions_user_id_idx ON interview_sessions(user_id);
CREATE INDEX IF NOT EXISTS interview_sessions_created_at_idx ON interview_sessions(created_at DESC);

-- Indexes for user_streaks
CREATE INDEX IF NOT EXISTS user_streaks_user_id_idx ON user_streaks(user_id);

-- Indexes for user_ranks
CREATE INDEX IF NOT EXISTS user_ranks_user_id_idx ON user_ranks(user_id);
CREATE INDEX IF NOT EXISTS user_ranks_xp_idx ON user_ranks(xp DESC);

-- Indexes for user_badges
CREATE INDEX IF NOT EXISTS user_badges_user_id_idx ON user_badges(user_id);

-- Indexes for challenges
CREATE INDEX IF NOT EXISTS challenges_code_idx ON challenges(challenge_code);

-- Indexes for challenge_results
CREATE INDEX IF NOT EXISTS challenge_results_code_idx ON challenge_results(challenge_code);
CREATE INDEX IF NOT EXISTS challenge_results_score_idx ON challenge_results(score DESC);

-- Indexes for weekly_results
CREATE INDEX IF NOT EXISTS weekly_results_week_year_idx ON weekly_results(week_number, year);
CREATE INDEX IF NOT EXISTS weekly_results_score_idx ON weekly_results(score DESC);


-- =============================================================================
-- SEQUENCES (if needed for auto-increment)
-- =============================================================================

-- No sequences needed - using gen_random_uuid() for UUIDs


-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE profiles IS 'User profile data including education, work experience, and career goals';
COMMENT ON TABLE analyses IS 'AI-generated career analysis results';
COMMENT ON TABLE interview_sessions IS 'Interview practice session data';
COMMENT ON TABLE user_streaks IS 'Daily practice streak tracking (Duolingo-style)';
COMMENT ON TABLE user_ranks IS 'User XP and ranking data';
COMMENT ON TABLE user_badges IS 'Earned achievement badges';
COMMENT ON TABLE challenges IS 'Shared interview challenges';
COMMENT ON TABLE challenge_results IS 'Challenge submission results for leaderboard';
COMMENT ON TABLE weekly_challenges IS 'Weekly challenge definitions';
COMMENT ON TABLE weekly_results IS 'Weekly challenge submissions';


-- =============================================================================
-- MIGRATION NOTES
-- =============================================================================
-- 
-- To apply this schema:
-- 1. Open Supabase SQL Editor
-- 2. Copy and paste this entire file
-- 3. Execute
--
-- After applying, configure Row Level Security (RLS) policies
-- based on your authentication requirements.
--
-- Note: This schema assumes Supabase auth.users table exists
-- for the user_id foreign key references.
-- 
-- =============================================================================
