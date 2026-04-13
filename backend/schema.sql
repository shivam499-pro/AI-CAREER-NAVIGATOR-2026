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
-- CHALLENGE ATTEMPTS TABLE
-- Tracks when users start weekly challenges
-- =============================================================================

CREATE TABLE IF NOT EXISTS challenge_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    week_number INTEGER NOT NULL,
    year INTEGER NOT NULL,
    status TEXT DEFAULT 'started',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Unique constraint
    CONSTRAINT challenge_attempts_unique UNIQUE (user_id, week_number, year)
);

-- Index for challenge_attempts
CREATE INDEX IF NOT EXISTS challenge_attempts_user_week_year_idx ON challenge_attempts(user_id, week_number, year);


-- =============================================================================
-- USER_CAREER_MEMORY TABLE
-- Tracks user evolution over time for career paths
-- =============================================================================

CREATE TABLE IF NOT EXISTS user_career_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    career_path TEXT NOT NULL,
    skill_area TEXT,
    performance_score INTEGER,
    confidence_score FLOAT DEFAULT 0.0,
    trend TEXT DEFAULT 'stable',
    session_count INTEGER DEFAULT 1,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for user_career_memory
CREATE INDEX IF NOT EXISTS user_career_memory_user_id_idx ON user_career_memory(user_id);
CREATE INDEX IF NOT EXISTS user_career_memory_career_path_idx ON user_career_memory(career_path);

COMMENT ON TABLE user_career_memory IS 'Tracks user career evolution over time for different career paths';


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
COMMENT ON TABLE challenge_attempts IS 'Tracks when users start weekly challenges';


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


-- =============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- Enable RLS on all user data tables and add policies
-- =============================================================================

-- =============================================================================
-- PROFILES TABLE RLS
-- =============================================================================

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- Users can view their own profile
CREATE POLICY "profiles_select_own" ON profiles
FOR SELECT USING (auth.uid() = user_id);

-- Users can insert their own profile
CREATE POLICY "profiles_insert_own" ON profiles
FOR INSERT WITH CHECK (auth.uid() = user_id OR auth.role() = 'service_role');

-- Users can update their own profile
CREATE POLICY "profiles_update_own" ON profiles
FOR UPDATE USING (auth.uid() = user_id OR auth.role() = 'service_role');

-- Users can delete their own profile
CREATE POLICY "profiles_delete_own" ON profiles
FOR DELETE USING (auth.uid() = user_id OR auth.role() = 'service_role');


-- =============================================================================
-- ANALYSES TABLE RLS
-- =============================================================================

ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;

-- Users can view their own analysis
CREATE POLICY "analyses_select_own" ON analyses
FOR SELECT USING (auth.uid() = user_id OR auth.role() = 'service_role');

-- Users can insert their own analysis
CREATE POLICY "analyses_insert_own" ON analyses
FOR INSERT WITH CHECK (auth.uid() = user_id OR auth.role() = 'service_role');


-- Users can update their own analysis
CREATE POLICY "analyses_update_own" ON analyses
FOR UPDATE USING (auth.uid() = user_id OR auth.role() = 'service_role');

-- Users can delete their own analysis
CREATE POLICY "analyses_delete_own" ON analyses
FOR DELETE USING (auth.uid() = user_id OR auth.role() = 'service_role');


-- =============================================================================
-- INTERVIEW_SESSIONS TABLE RLS
-- =============================================================================

ALTER TABLE interview_sessions ENABLE ROW LEVEL SECURITY;

-- Users can view their own sessions
CREATE POLICY "interview_sessions_select_own" ON interview_sessions
FOR SELECT USING (auth.uid() = user_id OR auth.role() = 'service_role');

-- Users can insert their own sessions
CREATE POLICY "interview_sessions_insert_own" ON interview_sessions
FOR INSERT WITH CHECK (auth.uid() = user_id OR auth.role() = 'service_role');

-- Users can update their own sessions
CREATE POLICY "interview_sessions_update_own" ON interview_sessions
FOR UPDATE USING (auth.uid() = user_id OR auth.role() = 'service_role');


-- Users can delete their own sessions
CREATE POLICY "interview_sessions_delete_own" ON interview_sessions
FOR DELETE USING (auth.uid() = user_id OR auth.role() = 'service_role');


-- =============================================================================
-- USER_STREAKS TABLE RLS
-- =============================================================================

ALTER TABLE user_streaks ENABLE ROW LEVEL SECURITY;

-- Users can view their own streak
CREATE POLICY "user_streaks_select_own" ON user_streaks
FOR SELECT USING (auth.uid() = user_id OR auth.role() = 'service_role');

-- Users can insert their own streak
CREATE POLICY "user_streaks_insert_own" ON user_streaks
FOR INSERT WITH CHECK (auth.uid() = user_id OR auth.role() = 'service_role');

-- Users can update their own streak
CREATE POLICY "user_streaks_update_own" ON user_streaks
FOR UPDATE USING (auth.uid() = user_id OR auth.role() = 'service_role');

-- Users can delete their own streak
CREATE POLICY "user_streaks_delete_own" ON user_streaks
FOR DELETE USING (auth.uid() = user_id OR auth.role() = 'service_role');


-- =============================================================================
-- USER_RANKS TABLE RLS
-- =============================================================================

ALTER TABLE user_ranks ENABLE ROW LEVEL SECURITY;

-- Users can view their own rank
CREATE POLICY "user_ranks_select_own" ON user_ranks
FOR SELECT USING (auth.uid() = user_id OR auth.role() = 'service_role');

-- Users can insert their own rank
CREATE POLICY "user_ranks_insert_own" ON user_ranks
FOR INSERT WITH CHECK (auth.uid() = user_id OR auth.role() = 'service_role');

-- Users can update their own rank
CREATE POLICY "user_ranks_update_own" ON user_ranks
FOR UPDATE USING (auth.uid() = user_id OR auth.role() = 'service_role');

-- Users can delete their own rank
CREATE POLICY "user_ranks_delete_own" ON user_ranks
FOR DELETE USING (auth.uid() = user_id OR auth.role() = 'service_role');


-- =============================================================================
-- USER_BADGES TABLE RLS
-- =============================================================================

ALTER TABLE user_badges ENABLE ROW LEVEL SECURITY;

-- Users can view their own badges
CREATE POLICY "user_badges_select_own" ON user_badges
FOR SELECT USING (auth.uid() = user_id OR auth.role() = 'service_role');

-- Users can insert their own badges
CREATE POLICY "user_badges_insert_own" ON user_badges
FOR INSERT WITH CHECK (auth.uid() = user_id OR auth.role() = 'service_role');

-- Users can update their own badges
CREATE POLICY "user_badges_update_own" ON user_badges
FOR UPDATE USING (auth.uid() = user_id OR auth.role() = 'service_role');

-- Users can delete their own badges
CREATE POLICY "user_badges_delete_own" ON user_badges
FOR DELETE USING (auth.uid() = user_id OR auth.role() = 'service_role');


-- =============================================================================
-- CHALLENGES TABLE RLS
-- =============================================================================

ALTER TABLE challenges ENABLE ROW LEVEL SECURITY;

-- All authenticated users can view challenges (public content)
CREATE POLICY "challenges_select_all" ON challenges
FOR SELECT TO authenticated USING (true);

-- Only challenge creator can insert
CREATE POLICY "challenges_insert_own" ON challenges
FOR INSERT WITH CHECK (auth.uid() = creator_id OR auth.role() = 'service_role');

-- Only challenge creator can update
CREATE POLICY "challenges_update_own" ON challenges
FOR UPDATE USING (auth.uid() = creator_id OR auth.role() = 'service_role');

-- Only challenge creator can delete
CREATE POLICY "challenges_delete_own" ON challenges
FOR DELETE USING (auth.uid() = creator_id OR auth.role() = 'service_role');


-- =============================================================================
-- CHALLENGE_RESULTS TABLE RLS
-- =============================================================================

ALTER TABLE challenge_results ENABLE ROW LEVEL SECURITY;

-- All authenticated users can view all challenge results (leaderboard)
CREATE POLICY "challenge_results_select_all" ON challenge_results
FOR SELECT TO authenticated USING (true);

-- Users can insert their own results
CREATE POLICY "challenge_results_insert_own" ON challenge_results
FOR INSERT WITH CHECK (auth.uid() = user_id OR auth.role() = 'service_role');

-- Users can update their own results
CREATE POLICY "challenge_results_update_own" ON challenge_results
FOR UPDATE USING (auth.uid() = user_id OR auth.role() = 'service_role');

-- Users can delete their own results
CREATE POLICY "challenge_results_delete_own" ON challenge_results
FOR DELETE USING (auth.uid() = user_id OR auth.role() = 'service_role');


-- =============================================================================
-- WEEKLY_CHALLENGES TABLE RLS
-- =============================================================================

ALTER TABLE weekly_challenges ENABLE ROW LEVEL SECURITY;

-- All authenticated users can view weekly challenges (public content)
CREATE POLICY "weekly_challenges_select_all" ON weekly_challenges
FOR SELECT TO authenticated USING (true);

-- Only service role can insert/update/delete weekly challenges
CREATE POLICY "weekly_challenges_service_role" ON weekly_challenges
FOR ALL USING (auth.role() = 'service_role');


-- =============================================================================
-- WEEKLY_RESULTS TABLE RLS
-- =============================================================================

ALTER TABLE weekly_results ENABLE ROW LEVEL SECURITY;

-- All authenticated users can view all weekly results (leaderboard)
CREATE POLICY "weekly_results_select_all" ON weekly_results
FOR SELECT TO authenticated USING (true);

-- Users can insert their own weekly results
CREATE POLICY "weekly_results_insert_own" ON weekly_results
FOR INSERT WITH CHECK (auth.uid() = user_id OR auth.role() = 'service_role');

-- Users can update their own weekly results
CREATE POLICY "weekly_results_update_own" ON weekly_results
FOR UPDATE USING (auth.uid() = user_id OR auth.role() = 'service_role');

-- Users can delete their own weekly results
CREATE POLICY "weekly_results_delete_own" ON weekly_results
FOR DELETE USING (auth.uid() = user_id OR auth.role() = 'service_role');


-- =============================================================================
-- CHALLENGE ATTEMPTS TABLE RLS
-- =============================================================================

ALTER TABLE challenge_attempts ENABLE ROW LEVEL SECURITY;

-- Users can view their own attempts
CREATE POLICY "challenge_attempts_select_own" ON challenge_attempts
FOR SELECT USING (auth.uid() = user_id OR auth.role() = 'service_role');

-- Users can insert their own attempts
CREATE POLICY "challenge_attempts_insert_own" ON challenge_attempts
FOR INSERT WITH CHECK (auth.uid() = user_id OR auth.role() = 'service_role');

-- Users can update their own attempts
CREATE POLICY "challenge_attempts_update_own" ON challenge_attempts
FOR UPDATE USING (auth.uid() = user_id OR auth.role() = 'service_role');


-- =============================================================================
-- USER_CAREER_MEMORY TABLE RLS
-- =============================================================================

ALTER TABLE user_career_memory ENABLE ROW LEVEL SECURITY;

-- Users can view their own career memory
CREATE POLICY "user_career_memory_select_own" ON user_career_memory
FOR SELECT USING (auth.uid() = user_id OR auth.role() = 'service_role');

-- Users can insert their own career memory
CREATE POLICY "user_career_memory_insert_own" ON user_career_memory
FOR INSERT WITH CHECK (auth.uid() = user_id OR auth.role() = 'service_role');

-- Users can update their own career memory
CREATE POLICY "user_career_memory_update_own" ON user_career_memory
FOR UPDATE USING (auth.uid() = user_id OR auth.role() = 'service_role');

-- Users can delete their own career memory
CREATE POLICY "user_career_memory_delete_own" ON user_career_memory
FOR DELETE USING (auth.uid() = user_id OR auth.role() = 'service_role');


-- =============================================================================
-- USER_DOCUMENTS TABLE
-- Stores structured extracted data per document upload
-- =============================================================================

CREATE TABLE IF NOT EXISTS user_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    document_name TEXT NOT NULL,
    document_type TEXT NOT NULL DEFAULT 'other',  -- 'certificate' | 'resume' | 'cover_letter' | 'other'
    extracted_data JSONB NOT NULL DEFAULT '{}',
    storage_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for user_documents
CREATE INDEX IF NOT EXISTS user_documents_user_id_idx ON user_documents(user_id);
CREATE INDEX IF NOT EXISTS user_documents_user_id_type_idx ON user_documents(user_id, document_type);


-- =============================================================================
-- VERIFICATION QUERY
-- Run this to verify RLS is enabled on all tables
-- =============================================================================
-- 
-- SELECT 
--     schemaname,
--     tablename,
--     rowsecurity
-- FROM pg_tables 
-- WHERE schemaname = 'public' 
-- ORDER BY tablename;
-- 
-- =============================================================================


-- =============================================================================
-- SAVED_JOBS TABLE
-- Stores jobs bookmarked by users
-- =============================================================================

CREATE TABLE IF NOT EXISTS saved_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    job_id TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    apply_url TEXT,
    match_score FLOAT,
    matched_skills JSONB,
    missing_skills JSONB,
    saved_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT saved_jobs_unique UNIQUE (user_id, job_id)
);

-- Index for saved_jobs
CREATE INDEX IF NOT EXISTS saved_jobs_user_id_idx ON saved_jobs(user_id);
CREATE INDEX IF NOT EXISTS saved_jobs_saved_at_idx ON saved_jobs(saved_at DESC);


-- =============================================================================
-- JOB_APPLICATIONS TABLE
-- Tracks job application statuses
-- =============================================================================

CREATE TABLE IF NOT EXISTS job_applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    job_id TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    apply_url TEXT,
    match_score FLOAT,
    matched_skills JSONB,
    missing_skills JSONB,
    status TEXT NOT NULL DEFAULT 'applied' CHECK (status IN ('applied', 'interview', 'rejected', 'offer')),
    notes TEXT,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT job_applications_unique UNIQUE (user_id, job_id)
);

-- Index for job_applications
CREATE INDEX IF NOT EXISTS job_applications_user_id_idx ON job_applications(user_id);
CREATE INDEX IF NOT EXISTS job_applications_status_idx ON job_applications(status);
CREATE INDEX IF NOT EXISTS job_applications_applied_at_idx ON job_applications(applied_at DESC);


-- =============================================================================
-- SAVED_JOBS TABLE RLS
-- =============================================================================

ALTER TABLE saved_jobs ENABLE ROW LEVEL SECURITY;

-- Users can view their own saved jobs
CREATE POLICY "saved_jobs_select_own" ON saved_jobs
FOR SELECT USING (auth.uid() = user_id);

-- Users can insert their own saved jobs
CREATE POLICY "saved_jobs_insert_own" ON saved_jobs
FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Users can delete their own saved jobs
CREATE POLICY "saved_jobs_delete_own" ON saved_jobs
FOR DELETE USING (auth.uid() = user_id);


-- =============================================================================
-- JOB_APPLICATIONS TABLE RLS
-- =============================================================================

ALTER TABLE job_applications ENABLE ROW LEVEL SECURITY;

-- Users can view their own applications
CREATE POLICY "job_applications_select_own" ON job_applications
FOR SELECT USING (auth.uid() = user_id);

-- Users can insert their own applications
CREATE POLICY "job_applications_insert_own" ON job_applications
FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Users can update their own applications
CREATE POLICY "job_applications_update_own" ON job_applications
FOR UPDATE USING (auth.uid() = user_id);

-- Users can delete their own applications
CREATE POLICY "job_applications_delete_own" ON job_applications
FOR DELETE USING (auth.uid() = user_id);
