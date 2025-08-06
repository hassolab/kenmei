-- Update the status check constraint for report_jobs to include multi-phase statuses

-- 1. Drop the existing constraint (The name might be generated, find it first if this fails)
-- Supabase often auto-names constraints like report_jobs_status_check_... Find exact name via Studio or psql if needed.
-- Assuming the name is 'report_jobs_status_check' based on the error message.
ALTER TABLE public.report_jobs
DROP CONSTRAINT IF EXISTS report_jobs_status_check;

-- 2. Add the new constraint with all expected status values
ALTER TABLE public.report_jobs
ADD CONSTRAINT report_jobs_status_check CHECK (status IN (
    'pending',
    'processing_phase_1',
    'phase_1_complete',
    'pending_phase_2',
    'processing_phase_2',
    'phase_2_complete',
    'pending_phase_3',
    'processing_phase_3',
    'completed',
    'failed',
    'queue_failed' -- Added status for when Redis publish fails
)); 