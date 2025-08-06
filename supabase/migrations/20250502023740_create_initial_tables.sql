-- Migration to create initial tables: profiles and report_jobs

-- 1. Create profiles table
CREATE TABLE public.profiles (
    id uuid NOT NULL PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    updated_at timestamptz,
    credits integer DEFAULT 10 -- Example: Give users 10 credits initially
);
-- Enable RLS for profiles table (good practice, though we might keep policies simple initially)
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
-- Allow users to view their own profile
CREATE POLICY "Allow individual user select access" ON public.profiles
    FOR SELECT USING (auth.uid() = id);
-- Allow users to update their own profile (if needed later, e.g., username)
-- CREATE POLICY "Allow individual user update access" ON public.profiles
--     FOR UPDATE USING (auth.uid() = id);


-- 2. Create report_jobs table
CREATE TABLE public.report_jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), -- Use uuid for ID
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    status text CHECK (status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending',
    report_type text,
    report_parameters jsonb,
    analysis_content text, -- Stores the generated report content
    error_message text,    -- Stores any error message if status is 'failed'
    updated_at timestamptz DEFAULT now() -- Add updated_at for tracking changes
);
-- Enable RLS for report_jobs table
ALTER TABLE public.report_jobs ENABLE ROW LEVEL SECURITY;
-- Allow users to view their own jobs
CREATE POLICY "Allow individual user select access" ON public.report_jobs
    FOR SELECT USING (auth.uid() = user_id);
-- Allow Edge Function (service_role) to insert jobs - This needs user_id from function context
-- The Edge function runs with the user's permissions if invoked correctly, so specific INSERT policy might not be needed if RLS is based on user_id
-- However, a specific policy allowing the function/user to INSERT is safer if function context fails.
CREATE POLICY "Allow individual user insert access" ON public.report_jobs
    FOR INSERT WITH CHECK (auth.uid() = user_id);
-- Allow workers (using service_role typically) to update jobs
-- Workers might need broader update access, restrict columns if possible
CREATE POLICY "Allow service role update access" ON public.report_jobs
    FOR UPDATE USING (true); -- More permissive, service role bypasses RLS by default but explicit policy is clearer
-- Allow users to delete their own jobs (optional)
-- CREATE POLICY "Allow individual user delete access" ON public.report_jobs
--     FOR DELETE USING (auth.uid() = user_id);

-- Add an index on user_id for faster lookups in report_jobs
CREATE INDEX report_jobs_user_id_idx ON public.report_jobs(user_id);

-- Optional: Function and Trigger to update 'updated_at' timestamp automatically
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER on_report_job_update
  BEFORE UPDATE ON public.report_jobs
  FOR EACH ROW
  EXECUTE PROCEDURE public.handle_updated_at();
