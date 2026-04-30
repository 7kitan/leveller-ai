# YouTube Video Curation System - Database Schema

## Overview
This document describes the database schema changes required to support the YouTube video curation system with skill-based filtering, level classification, and language support.

## Schema Changes

### 1. Update `youtube_videos` Table

Add new columns to support curation metadata:

```sql
-- Add new columns to youtube_videos table
ALTER TABLE youtube_videos
ADD COLUMN language VARCHAR(10) DEFAULT NULL,
ADD COLUMN skill_level VARCHAR(50) DEFAULT NULL,
ADD COLUMN is_curated BOOLEAN DEFAULT FALSE,
ADD COLUMN quality_score FLOAT DEFAULT NULL,
ADD COLUMN created_by UUID REFERENCES users(id) ON DELETE SET NULL;

-- Add indexes for filtering
CREATE INDEX idx_youtube_videos_language ON youtube_videos(language);
CREATE INDEX idx_youtube_videos_skill_level ON youtube_videos(skill_level);
CREATE INDEX idx_youtube_videos_is_curated ON youtube_videos(is_curated);
CREATE INDEX idx_youtube_videos_quality_score ON youtube_videos(quality_score DESC);

-- Add composite index for common filter combinations
CREATE INDEX idx_youtube_videos_filters ON youtube_videos(language, skill_level, is_curated);
```

**Column Descriptions:**
- `language`: Video language code ("en", "vi", etc.)
- `skill_level`: Target skill level ("Junior", "Mid-level", "Senior", "Expert")
- `is_curated`: Whether video was manually added/verified by admin
- `quality_score`: Optional quality metric (0-100) for ranking
- `created_by`: Admin user who added the curated video

---

### 2. Create `youtube_video_skills` Junction Table

Many-to-many relationship between videos and skills:

```sql
-- Junction table for video-skill relationships
CREATE TABLE youtube_video_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id VARCHAR(20) NOT NULL REFERENCES youtube_videos(video_id) ON DELETE CASCADE,
    skill_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(video_id, skill_name)
);

-- Indexes for fast lookups
CREATE INDEX idx_youtube_video_skills_video_id ON youtube_video_skills(video_id);
CREATE INDEX idx_youtube_video_skills_skill_name ON youtube_video_skills(skill_name);
```

**Usage:**
- Each video can have multiple skills
- Each skill can be associated with multiple videos
- Enables filtering videos by specific skills

---

### 3. Create `skill_taxonomy` Table (Optional - Phase 2)

Skill normalization and alias management:

```sql
-- Skill taxonomy for normalization
CREATE TABLE skill_taxonomy (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_name VARCHAR(100) UNIQUE NOT NULL,
    aliases TEXT[] DEFAULT '{}',
    category VARCHAR(50),
    related_skills TEXT[] DEFAULT '{}',
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_skill_taxonomy_canonical ON skill_taxonomy(canonical_name);
CREATE INDEX idx_skill_taxonomy_aliases ON skill_taxonomy USING GIN(aliases);
CREATE INDEX idx_skill_taxonomy_category ON skill_taxonomy(category);

-- Sample data
INSERT INTO skill_taxonomy (canonical_name, aliases, category, related_skills) VALUES
('JavaScript', ARRAY['JS', 'Javascript', 'ECMAScript', 'ES6', 'ES2015'], 'Programming Language', ARRAY['TypeScript', 'Node.js', 'React']),
('React', ARRAY['ReactJS', 'React.js'], 'Frontend Framework', ARRAY['React Hooks', 'React Router', 'Redux', 'Next.js']),
('Python', ARRAY['python', 'py'], 'Programming Language', ARRAY['Django', 'Flask', 'FastAPI', 'NumPy']),
('Machine Learning', ARRAY['ML', 'Machine-Learning'], 'AI/ML', ARRAY['Deep Learning', 'Neural Networks', 'TensorFlow', 'PyTorch']),
('TypeScript', ARRAY['TS', 'Typescript'], 'Programming Language', ARRAY['JavaScript', 'Node.js', 'Angular']),
('SQL', ARRAY['sql', 'Structured Query Language'], 'Database', ARRAY['PostgreSQL', 'MySQL', 'Database Design']),
('Docker', ARRAY['docker', 'Containerization'], 'DevOps', ARRAY['Kubernetes', 'Container', 'CI/CD']),
('AWS', ARRAY['Amazon Web Services', 'aws'], 'Cloud', ARRAY['EC2', 'S3', 'Lambda', 'Cloud Computing']);
```

**Benefits:**
- Handles skill name variations (JS → JavaScript)
- Suggests related skills for better recommendations
- Enables semantic search improvements

---

### 4. Create `skill_embeddings` Table (Optional - Phase 2)

For semantic search using vector embeddings:

```sql
-- Requires pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Skill embeddings for semantic search
CREATE TABLE skill_embeddings (
    skill_name VARCHAR(100) PRIMARY KEY,
    embedding VECTOR(384),  -- Using all-MiniLM-L6-v2 model (384 dimensions)
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Vector similarity index
CREATE INDEX idx_skill_embeddings_vector ON skill_embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**Usage:**
- Enables semantic similarity search
- Finds related skills even with different terminology
- Example: "frontend development" → matches "React", "Vue", "Angular"

---

## API Endpoints Required

### Backend Routes

```python
# Admin endpoints
POST   /api/admin/youtube/fetch-metadata    # Fetch video metadata from YouTube API
POST   /api/admin/youtube/curated           # Add curated video with skills
GET    /api/admin/youtube/skills            # Get list of available skills
GET    /api/admin/youtube                   # List videos with filters
DELETE /api/admin/youtube/{video_id}        # Delete video

# Query parameters for GET /api/admin/youtube:
# - search: string (title/channel search)
# - language: string ("en", "vi", "all")
# - level: string ("Junior", "Mid-level", "Senior", "Expert", "all")
# - skill: string (skill name or "all")
# - limit: int (default 10)
# - offset: int (default 0)
```

### Example Request/Response

**POST /api/admin/youtube/curated**
```json
{
  "video_id": "dQw4w9WgXcQ",
  "skills": ["JavaScript", "React", "Web Development"],
  "skill_level": "Mid-level",
  "language": "en"
}
```

**Response:**
```json
{
  "success": true,
  "video_id": "dQw4w9WgXcQ",
  "message": "Video added successfully"
}
```

---

## Migration Strategy

### Phase 1: Basic Curation (MVP)
1. ✅ Add columns to `youtube_videos`
2. ✅ Create `youtube_video_skills` table
3. ✅ Add indexes
4. ✅ Update admin UI with filters
5. ✅ Implement add video modal

### Phase 2: Advanced Features (Optional)
1. ⚠️ Create `skill_taxonomy` table
2. ⚠️ Implement skill normalization logic
3. ⚠️ Add `skill_embeddings` table
4. ⚠️ Implement semantic search
5. ⚠️ Add auto-tagging from video metadata

---

## Rollback Plan

If issues occur, rollback with:

```sql
-- Remove indexes
DROP INDEX IF EXISTS idx_youtube_videos_language;
DROP INDEX IF EXISTS idx_youtube_videos_skill_level;
DROP INDEX IF EXISTS idx_youtube_videos_is_curated;
DROP INDEX IF EXISTS idx_youtube_videos_quality_score;
DROP INDEX IF EXISTS idx_youtube_videos_filters;

-- Remove tables (in order)
DROP TABLE IF EXISTS skill_embeddings;
DROP TABLE IF EXISTS youtube_video_skills;
DROP TABLE IF EXISTS skill_taxonomy;

-- Remove columns
ALTER TABLE youtube_videos
DROP COLUMN IF EXISTS language,
DROP COLUMN IF EXISTS skill_level,
DROP COLUMN IF EXISTS is_curated,
DROP COLUMN IF EXISTS quality_score,
DROP COLUMN IF EXISTS created_by;
```

---

## Performance Considerations

1. **Indexes**: All filter columns are indexed for fast queries
2. **Composite Index**: Common filter combinations use a single composite index
3. **Junction Table**: Normalized design prevents data duplication
4. **Vector Search**: IVFFlat index for fast similarity search (Phase 2)

---

## Data Validation

### Constraints

```sql
-- Add check constraints
ALTER TABLE youtube_videos
ADD CONSTRAINT check_language CHECK (language IN ('en', 'vi') OR language IS NULL),
ADD CONSTRAINT check_skill_level CHECK (skill_level IN ('Junior', 'Mid-level', 'Senior', 'Expert') OR skill_level IS NULL),
ADD CONSTRAINT check_quality_score CHECK (quality_score >= 0 AND quality_score <= 100 OR quality_score IS NULL);
```

---

## Testing Queries

### Get all curated videos for a skill
```sql
SELECT v.*, array_agg(s.skill_name) as skills
FROM youtube_videos v
JOIN youtube_video_skills s ON v.video_id = s.video_id
WHERE s.skill_name = 'React'
  AND v.is_curated = true
  AND v.language = 'en'
GROUP BY v.id
ORDER BY v.quality_score DESC NULLS LAST;
```

### Get videos with multiple skill filters
```sql
SELECT v.*, array_agg(DISTINCT s.skill_name) as skills
FROM youtube_videos v
JOIN youtube_video_skills s ON v.video_id = s.video_id
WHERE s.skill_name IN ('React', 'JavaScript', 'TypeScript')
  AND v.skill_level = 'Mid-level'
  AND v.language = 'en'
GROUP BY v.id
HAVING COUNT(DISTINCT s.skill_name) >= 2  -- Has at least 2 of the requested skills
ORDER BY v.quality_score DESC NULLS LAST;
```

### Get available skills with video counts
```sql
SELECT skill_name, COUNT(*) as video_count
FROM youtube_video_skills
GROUP BY skill_name
ORDER BY video_count DESC;
```

---

## Next Steps

1. **Backend Implementation**:
   - Create migration file with Phase 1 schema changes
   - Implement API endpoints for video curation
   - Add skill extraction logic from video metadata

2. **Frontend Integration**:
   - ✅ Admin UI with filters (completed)
   - ✅ Add Video modal (completed)
   - Test with real data

3. **Data Population**:
   - Seed `skill_taxonomy` with common skills
   - Backfill existing videos with skills (manual or AI-assisted)
   - Generate embeddings for semantic search (Phase 2)

4. **Monitoring**:
   - Track curation coverage (% of videos with skills)
   - Monitor search relevance metrics
   - Collect user feedback on video recommendations
