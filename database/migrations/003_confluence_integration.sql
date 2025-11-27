-- Migration: 003_confluence_integration.sql
-- Description: Add Confluence integration support with publications tracking
-- Date: 2025-09-02

-- Create confluence_publications table
CREATE TABLE IF NOT EXISTS confluence_publications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    confluence_page_id TEXT NOT NULL,
    confluence_page_url TEXT NOT NULL,
    confluence_space_key TEXT NOT NULL,
    parent_page_id TEXT,
    page_title TEXT NOT NULL,
    publication_status TEXT NOT NULL DEFAULT 'published',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    last_retry_at TIMESTAMP,
    
    -- Foreign key constraint
    FOREIGN KEY (job_id) REFERENCES jobs (job_id) ON DELETE CASCADE,
    
    -- Unique constraint to prevent duplicate publications
    UNIQUE(job_id, confluence_page_id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_confluence_publications_job_id 
    ON confluence_publications(job_id);

CREATE INDEX IF NOT EXISTS idx_confluence_publications_page_id 
    ON confluence_publications(confluence_page_id);

CREATE INDEX IF NOT EXISTS idx_confluence_publications_space_key 
    ON confluence_publications(confluence_space_key);

CREATE INDEX IF NOT EXISTS idx_confluence_publications_status 
    ON confluence_publications(publication_status);

CREATE INDEX IF NOT EXISTS idx_confluence_publications_created_at 
    ON confluence_publications(created_at);

-- Create trigger to update updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_confluence_publications_updated_at
    AFTER UPDATE ON confluence_publications
    FOR EACH ROW
BEGIN
    UPDATE confluence_publications 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;

-- Add comments for documentation
PRAGMA table_info(confluence_publications);