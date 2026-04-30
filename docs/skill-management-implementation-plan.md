# Skill Management System - Implementation Plan

## ✅ Phase 1: Database (COMPLETED)

### Migration Results:
```
✅ pending_skills table created (13 columns)
✅ skill_id added to youtube_video_skills
✅ 3 existing skills linked successfully
✅ Indexes and constraints added
✅ Triggers for updated_at created
```

### Database Schema:
```sql
-- Master skills table (1,296 skills)
skills (id, name, category, parent_skill_id, vector)

-- Pending skills for review
pending_skills (
  id, skill_name, source, suggested_by, suggested_at,
  status, reviewed_by, reviewed_at, merged_into,
  notes, metadata, created_at, updated_at
)

-- YouTube video skills (now with FK)
youtube_video_skills (
  id, video_id, skill_name, skill_id, created_at
)
```

---

## 🚧 Phase 2: Backend API (IN PROGRESS)

### Endpoints to Implement:

#### **A. Skills CRUD**
```python
GET    /admin/skills                    # List all skills (paginated)
POST   /admin/skills                    # Create new skill
GET    /admin/skills/{skill_id}         # Get skill details
PUT    /admin/skills/{skill_id}         # Update skill
DELETE /admin/skills/{skill_id}         # Delete skill
GET    /admin/skills/search?q=react     # Search skills
```

#### **B. Pending Skills Review**
```python
GET    /admin/skills/pending                      # List pending skills
POST   /admin/skills/pending/{id}/approve         # Approve → Add to skills table
POST   /admin/skills/pending/{id}/reject          # Reject with reason
POST   /admin/skills/pending/{id}/merge           # Merge into existing skill
GET    /admin/skills/pending/stats                # Stats (pending count, etc.)
```

#### **C. Skill Categories**
```python
GET    /admin/skills/categories                   # List all categories
POST   /admin/skills/categories                   # Create category
```

---

## 📋 Phase 3: Frontend (PENDING)

### Pages to Create:

#### **A. Admin Taxonomy Page** (`/admin/taxonomy`)
```
┌─────────────────────────────────────────────────┐
│ Skills Management                               │
├─────────────────────────────────────────────────┤
│ [Search] [Filter by Category ▼] [+ Add Skill]  │
├─────────────────────────────────────────────────┤
│ Name          │ Category      │ Actions         │
├───────────────┼───────────────┼─────────────────┤
│ React         │ Technology    │ [Edit] [Delete] │
│ JavaScript    │ Technology    │ [Edit] [Delete] │
│ Python        │ Technology    │ [Edit] [Delete] │
└─────────────────────────────────────────────────┘
```

**Features:**
- ✅ List all 1,296 skills with pagination
- ✅ Search by name
- ✅ Filter by category
- ✅ Add new skill (with category)
- ✅ Edit skill (name, category, parent)
- ✅ Delete skill (with confirmation)
- ✅ Bulk operations (merge, delete)

#### **B. Pending Skills Page** (`/admin/taxonomy/pending`)
```
┌─────────────────────────────────────────────────────────┐
│ Pending Skills Review                    [3 Pending]    │
├─────────────────────────────────────────────────────────┤
│ Skill Name    │ Source   │ Suggested │ Actions          │
├───────────────┼──────────┼───────────┼──────────────────┤
│ TypeScript    │ YouTube  │ 2h ago    │ [Approve] [Merge]│
│ Vue.js        │ Manual   │ 1d ago    │ [Approve] [Merge]│
│ Docker        │ Job Post │ 3d ago    │ [Approve] [Merge]│
└─────────────────────────────────────────────────────────┘
```

**Features:**
- ✅ List pending skills
- ✅ Show source (YouTube, Job Posting, Manual)
- ✅ Approve → Add to skills table
- ✅ Reject → Mark as rejected with reason
- ✅ Merge → Select existing skill to merge into
- ✅ Bulk approve/reject

#### **C. Tag Input Component** (for YouTube modal)
```
┌─────────────────────────────────────────────┐
│ Select Skills *                             │
├─────────────────────────────────────────────┤
│ [React ×] [JavaScript ×] [TypeScript ×]     │
│ ┌─────────────────────────────────────────┐ │
│ │ Type to search or add new...            │ │
│ └─────────────────────────────────────────┘ │
│ Suggestions:                                │
│ • Python                                    │
│ • Node.js                                   │
│ • Docker                                    │
└─────────────────────────────────────────────┘
```

**Features:**
- ✅ Autocomplete from 1,296 existing skills
- ✅ Add new skill (goes to pending_skills)
- ✅ Remove selected skills
- ✅ Visual tags with × button
- ✅ Keyboard navigation (Arrow keys, Enter, Backspace)

---

## 🔄 Workflow Example

### **Scenario: Admin adds YouTube video with new skill**

1. **Admin opens Add Video modal**
   - Pastes YouTube URL
   - Clicks "Fetch Info"

2. **Admin selects skills**
   - Types "React" → Autocomplete shows "React" (exists)
   - Selects "React" ✅
   - Types "TypeScript" → Autocomplete shows "TypeScript" (exists)
   - Selects "TypeScript" ✅
   - Types "Svelte" → Not found
   - Presses Enter → "Svelte" added as new skill
   - ⚠️ Warning: "Svelte will be added for review"

3. **Backend processes request**
   ```python
   for skill_name in data.skills:
       skill = db.query(Skill).filter(Skill.name == skill_name).first()
       if skill:
           # Existing skill → Use skill.id
           db.execute(text("""
               INSERT INTO youtube_video_skills (video_id, skill_id, skill_name)
               VALUES (:vid, :sid, :name)
           """), {"vid": video_id, "sid": skill.id, "name": skill_name})
       else:
           # New skill → Add to pending_skills
           db.execute(text("""
               INSERT INTO pending_skills (skill_name, source, suggested_by, metadata)
               VALUES (:name, 'youtube', :user_id, :meta)
           """), {
               "name": skill_name,
               "user_id": admin_user.id,
               "meta": json.dumps({"video_id": video_id})
           })
           # Also add to youtube_video_skills (without skill_id)
           db.execute(text("""
               INSERT INTO youtube_video_skills (video_id, skill_name)
               VALUES (:vid, :name)
           """), {"vid": video_id, "name": skill_name})
   ```

4. **Admin reviews pending skills**
   - Goes to `/admin/taxonomy/pending`
   - Sees "Svelte" in pending list
   - Options:
     - **Approve** → Add to skills table, update youtube_video_skills.skill_id
     - **Reject** → Mark as rejected, remove from youtube_video_skills
     - **Merge** → Select "Svelte.js" (existing), update youtube_video_skills.skill_id

---

## 📊 Current Status

| Component | Status | Progress |
|-----------|--------|----------|
| Database Schema | ✅ Done | 100% |
| Backend Models | ✅ Done | 100% |
| Backend Schemas | ✅ Done | 100% |
| Backend Endpoints | 🚧 In Progress | 0% |
| Frontend Taxonomy Page | ⏳ Pending | 0% |
| Frontend Pending Page | ⏳ Pending | 0% |
| Frontend Tag Input | ⏳ Pending | 0% |
| YouTube Modal Update | ⏳ Pending | 0% |
| Testing | ⏳ Pending | 0% |
| Documentation | 🚧 In Progress | 50% |

---

## ⏱️ Time Estimates

| Task | Estimated Time | Priority |
|------|----------------|----------|
| Backend API Endpoints | 1-2 hours | 🔴 High |
| Frontend Taxonomy Page | 2-3 hours | 🔴 High |
| Frontend Pending Page | 1-2 hours | 🔴 High |
| Tag Input Component | 1-2 hours | 🟡 Medium |
| YouTube Modal Update | 30 min | 🟡 Medium |
| Testing & Bug Fixes | 1-2 hours | 🟡 Medium |
| Documentation | 30 min | 🟢 Low |
| **TOTAL** | **7-12 hours** | |

---

## 🎯 Next Immediate Steps

### **Right Now (30 minutes):**
1. ✅ Add backend API endpoints for skills CRUD
2. ✅ Add backend API endpoints for pending skills review
3. ✅ Copy updated main.py to container
4. ✅ Restart admin service
5. ✅ Test endpoints with curl

### **Today (if time permits - 2-3 hours):**
6. Create frontend Taxonomy page skeleton
7. Create frontend Pending Skills page skeleton
8. Add basic CRUD operations

### **Tomorrow (4-6 hours):**
9. Complete frontend pages with full functionality
10. Create Tag Input component
11. Update YouTube modal
12. End-to-end testing
13. Documentation

---

## 🐛 Known Issues & Considerations

### **Issue 1: Skill Name Conflicts**
**Problem:** User adds "React" but it already exists as "React.js"
**Solution:** 
- Fuzzy matching in autocomplete
- Show "Did you mean: React.js?" suggestion
- Admin can merge in pending review

### **Issue 2: Bulk Operations**
**Problem:** Admin wants to merge 10 similar skills
**Solution:**
- Add bulk merge feature in taxonomy page
- Select multiple skills → Merge into one

### **Issue 3: Skill Hierarchy**
**Problem:** Skills have parent_skill_id but no UI to manage
**Solution:**
- Phase 2 feature: Tree view for skill hierarchy
- Drag & drop to reorganize

### **Issue 4: Skill Deletion**
**Problem:** Deleting skill breaks FK constraints
**Solution:**
- Check if skill is used in youtube_video_skills, job_skill_requirement, etc.
- Show warning: "This skill is used in 5 videos. Merge instead?"
- Soft delete option

---

## 📝 API Documentation Preview

### **GET /admin/skills**
```bash
curl -X GET "http://localhost:8001/admin/skills?limit=20&offset=0&category=Technology&search=react"
```

**Response:**
```json
{
  "total": 1296,
  "skills": [
    {
      "id": "uuid-here",
      "name": "React",
      "category": "Technology",
      "parent_skill_id": null,
      "usage_count": 15
    }
  ]
}
```

### **POST /admin/skills/pending/{id}/approve**
```bash
curl -X POST "http://localhost:8001/admin/skills/pending/uuid-here/approve" \
  -H "Authorization: Bearer token" \
  -d '{"notes": "Approved - valid frontend framework"}'
```

**Response:**
```json
{
  "message": "Skill approved and added to master table",
  "skill_id": "new-uuid",
  "skill_name": "Svelte",
  "updated_videos": 3
}
```

---

**Status:** 🚧 Implementation in progress  
**Last Updated:** 2026-05-01  
**Estimated Completion:** 2026-05-02
