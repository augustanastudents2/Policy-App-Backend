-- ASA Policy App Database Schema
-- Run this SQL in your Supabase SQL Editor
-- This is the complete schema with all current database structure
--
-- Created with the help of Cursor AI

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Policies Table
-- Note: Database columns use 'name' and 'content', but API uses 'policy_name' and 'policy_content'
-- The API automatically maps between these names
CREATE TABLE IF NOT EXISTS policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    policy_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,  -- Maps to API field 'policy_name'
    section TEXT NOT NULL,
    content TEXT DEFAULT '',  -- Maps to API field 'policy_content'
    status TEXT DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT,
    updated_by TEXT
);

-- Bylaws Table
-- Note: Database columns use 'number', 'title', 'content', but API uses 'bylaw_number', 'bylaw_title', 'bylaw_content'
-- The API automatically maps between these names
-- IMPORTANT: 'number' is INTEGER (not TEXT) to match API requirement
CREATE TABLE IF NOT EXISTS bylaws (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    number INTEGER UNIQUE NOT NULL,  -- INTEGER - maps to API field 'bylaw_number'
    title TEXT NOT NULL,  -- Maps to API field 'bylaw_title'
    content TEXT DEFAULT '',  -- Maps to API field 'bylaw_content'
    status TEXT DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT,
    updated_by TEXT
);

-- Suggestions Table
CREATE TABLE IF NOT EXISTS suggestions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    policy_id UUID REFERENCES policies(id) ON DELETE SET NULL,
    bylaw_id UUID REFERENCES bylaws(id) ON DELETE SET NULL,
    suggestion TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users Table
-- Note: The 'id' field should match the user ID from Supabase Auth (auth.users)
-- When a user registers/logs in via Supabase Auth, their ID is stored here
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,  -- References auth.users(id) from Supabase Auth
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    role TEXT DEFAULT 'public' CHECK (role IN ('public', 'admin', 'policy_working_group')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Policy Versions Table (for version history)
CREATE TABLE IF NOT EXISTS policy_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    policy_id UUID REFERENCES policies(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    name TEXT NOT NULL,
    section TEXT NOT NULL,
    content TEXT DEFAULT '',
    status TEXT DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT
);

-- Policy Reviews Table (for tracking user reviews)
CREATE TABLE IF NOT EXISTS policy_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    policy_id TEXT NOT NULL,  -- References policies.policy_id (TEXT), not UUID
    user_email TEXT NOT NULL,  -- Email of the user who submitted the review
    review_status TEXT NOT NULL CHECK (review_status IN ('confirm', 'needs_work')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(policy_id, user_email)  -- One review per user per policy
);

-- Indexes for Policies
CREATE INDEX IF NOT EXISTS idx_policies_status ON policies(status);
CREATE INDEX IF NOT EXISTS idx_policies_section ON policies(section);
CREATE INDEX IF NOT EXISTS idx_policies_policy_id ON policies(policy_id);
CREATE INDEX IF NOT EXISTS idx_policies_created_at ON policies(created_at);

-- Indexes for Bylaws
CREATE INDEX IF NOT EXISTS idx_bylaws_status ON bylaws(status);
CREATE INDEX IF NOT EXISTS idx_bylaws_number ON bylaws(number);
CREATE INDEX IF NOT EXISTS idx_bylaws_created_at ON bylaws(created_at);

-- Indexes for Suggestions
CREATE INDEX IF NOT EXISTS idx_suggestions_status ON suggestions(status);
CREATE INDEX IF NOT EXISTS idx_suggestions_policy_id ON suggestions(policy_id);
CREATE INDEX IF NOT EXISTS idx_suggestions_bylaw_id ON suggestions(bylaw_id);
CREATE INDEX IF NOT EXISTS idx_suggestions_created_at ON suggestions(created_at);

-- Indexes for Users
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- Indexes for Policy Versions
CREATE INDEX IF NOT EXISTS idx_policy_versions_policy_id ON policy_versions(policy_id);
CREATE INDEX IF NOT EXISTS idx_policy_versions_version_number ON policy_versions(policy_id, version_number);

-- Indexes for Policy Reviews
CREATE INDEX IF NOT EXISTS idx_policy_reviews_policy_id ON policy_reviews(policy_id);
CREATE INDEX IF NOT EXISTS idx_policy_reviews_user_email ON policy_reviews(user_email);
CREATE INDEX IF NOT EXISTS idx_policy_reviews_status ON policy_reviews(review_status);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers to automatically update updated_at
CREATE TRIGGER update_policies_updated_at BEFORE UPDATE ON policies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bylaws_updated_at BEFORE UPDATE ON bylaws
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_suggestions_updated_at BEFORE UPDATE ON suggestions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_policy_reviews_updated_at BEFORE UPDATE ON policy_reviews
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) Policies
-- Enable RLS on tables
ALTER TABLE policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE bylaws ENABLE ROW LEVEL SECURITY;
ALTER TABLE suggestions ENABLE ROW LEVEL SECURITY;
ALTER TABLE policy_reviews ENABLE ROW LEVEL SECURITY;

-- Policies: Public can view approved policies
CREATE POLICY "Public can view approved policies"
    ON policies FOR SELECT
    USING (status = 'approved');

-- Bylaws: Public can view approved bylaws
CREATE POLICY "Public can view approved bylaws"
    ON bylaws FOR SELECT
    USING (status = 'approved');

-- Suggestions: Public can insert suggestions
CREATE POLICY "Public can insert suggestions"
    ON suggestions FOR INSERT
    WITH CHECK (true);

-- Admin RLS Policies
-- Allow admin users to perform all operations on policies
CREATE POLICY "Admin can manage policies"
    ON policies FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id::text = current_setting('request.jwt.claims', true)::json->>'sub'
            AND users.role = 'admin'
        )
    );

-- Policy Working Group RLS Policies
-- Allow policy_working_group members to view all policies (draft and approved)
CREATE POLICY "Policy working group can view all policies"
    ON policies FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id::text = current_setting('request.jwt.claims', true)::json->>'sub'
            AND users.role = 'policy_working_group'
        )
    );

-- Allow policy_working_group members to insert policies
CREATE POLICY "Policy working group can insert policies"
    ON policies FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id::text = current_setting('request.jwt.claims', true)::json->>'sub'
            AND users.role = 'policy_working_group'
        )
    );

-- Allow policy_working_group members to update policies
CREATE POLICY "Policy working group can update policies"
    ON policies FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id::text = current_setting('request.jwt.claims', true)::json->>'sub'
            AND users.role = 'policy_working_group'
        )
    );

-- Allow admin users to perform all operations on bylaws
CREATE POLICY "Admin can manage bylaws"
    ON bylaws FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id::text = current_setting('request.jwt.claims', true)::json->>'sub'
            AND users.role = 'admin'
        )
    );

-- Policy Working Group RLS Policies for Bylaws
-- Allow policy_working_group members to view all bylaws (draft and approved)
CREATE POLICY "Policy working group can view all bylaws"
    ON bylaws FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id::text = current_setting('request.jwt.claims', true)::json->>'sub'
            AND users.role = 'policy_working_group'
        )
    );

-- Allow policy_working_group members to insert bylaws
CREATE POLICY "Policy working group can insert bylaws"
    ON bylaws FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id::text = current_setting('request.jwt.claims', true)::json->>'sub'
            AND users.role = 'policy_working_group'
        )
    );

-- Allow policy_working_group members to update bylaws
CREATE POLICY "Policy working group can update bylaws"
    ON bylaws FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id::text = current_setting('request.jwt.claims', true)::json->>'sub'
            AND users.role = 'policy_working_group'
        )
    );

-- Allow admin and policy_working_group to manage suggestions
CREATE POLICY "Admin and policy_working_group can manage suggestions"
    ON suggestions FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id::text = current_setting('request.jwt.claims', true)::json->>'sub'
            AND users.role IN ('admin', 'policy_working_group')
        )
    );

-- Policy Reviews RLS Policies
-- Allow authenticated users to insert/update their own reviews
CREATE POLICY "Users can submit their own reviews"
    ON policy_reviews FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id::text = current_setting('request.jwt.claims', true)::json->>'sub'
            AND users.email = policy_reviews.user_email
        )
    );

CREATE POLICY "Users can update their own reviews"
    ON policy_reviews FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id::text = current_setting('request.jwt.claims', true)::json->>'sub'
            AND users.email = policy_reviews.user_email
        )
    );

-- Allow authenticated users to view all reviews (for statistics)
CREATE POLICY "Authenticated users can view all reviews"
    ON policy_reviews FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id::text = current_setting('request.jwt.claims', true)::json->>'sub'
        )
    );

-- Allow admin to delete all reviews (for reset functionality)
-- Note: Users cannot delete their own reviews - they can only update by submitting a new review
CREATE POLICY "Admin can delete all reviews"
    ON policy_reviews FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id::text = current_setting('request.jwt.claims', true)::json->>'sub'
            AND users.role = 'admin'
        )
    );

-- Note: Admin operations can also use the service role key which bypasses RLS
-- The backend uses service role key for admin operations to ensure proper access
