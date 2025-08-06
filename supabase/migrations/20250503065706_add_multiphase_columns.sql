-- Add multi-phase columns to report_jobs table and adjust existing columns

-- 1. Drop the old 'analysis_content' column if it exists (replace with phase-specific columns)
ALTER TABLE public.report_jobs
DROP COLUMN IF EXISTS analysis_content;

-- 2. Drop the old 'error_message' column if it exists (will add a more structured error column later if needed)
ALTER TABLE public.report_jobs
DROP COLUMN IF EXISTS error_message;

-- 3. Add the new report_type column (can store 'trend_analysis', 'social_listening', etc.)
ALTER TABLE public.report_jobs
ADD COLUMN IF NOT EXISTS report_type TEXT;

-- 4. Add the column for Phase 1 base analysis content
ALTER TABLE public.report_jobs
ADD COLUMN IF NOT EXISTS base_analysis_content TEXT;

-- 5. Add the column for Phase 2 specific analysis content
ALTER TABLE public.report_jobs
ADD COLUMN IF NOT EXISTS specific_analysis_content TEXT;

-- 6. Add the column for Phase 3 output file paths (array of text)
ALTER TABLE public.report_jobs
ADD COLUMN IF NOT EXISTS output_file_paths TEXT[];

-- 7. (Optional but recommended) Add a column for structured error details
ALTER TABLE public.report_jobs
ADD COLUMN IF NOT EXISTS error_details JSONB; -- Store errors as JSON 