-- ============================================================================
-- Add Soft Delete Support for User CVs
-- ============================================================================
-- Adds deleted_at column to user_cvs table for soft delete functionality
-- CVs with deleted_at IS NOT NULL are hidden from users but retained in DB
-- ============================================================================

BEGIN;

-- Add deleted_at column to user_cvs table
ALTER TABLE user_cvs 
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;

-- Add index on deleted_at for efficient filtering
CREATE INDEX IF NOT EXISTS idx_user_cvs_deleted_at 
ON user_cvs (deleted_at);

-- Add partial index for active (non-deleted) CVs
CREATE INDEX IF NOT EXISTS idx_user_cvs_active 
ON user_cvs (user_id, created_at DESC) 
WHERE deleted_at IS NULL;

COMMIT;

-- ============================================================================
-- Verify migration
-- ============================================================================
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'user_cvs' 
  AND column_name = 'deleted_at';
