# API Endpoints Documentation

Base URL: `http://localhost:8000` (development) or `https://api.yourdomain.com` (production)

## Authentication

All authenticated endpoints require the `Authorization` header:
```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

Token TTL: 7 days

---

## Auth Endpoints

### Register

Create a new user account.

**POST** `/auth/register`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "John Doe",
  "captcha_token": "03AGdBq..."
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid-here",
    "email": "user@example.com",
    "role": "user",
    "full_name": "John Doe"
  },
  "expires_in": 604800
}
```

**Errors:**
- `400` - Email already registered, invalid captcha, validation error
- `429` - Too many registration attempts

---

### Login

Authenticate and receive access token.

**POST** `/auth/login`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "captcha_token": "03AGdBq..."
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid-here",
    "email": "user@example.com",
    "role": "user",
    "full_name": "John Doe"
  },
  "expires_in": 604800
}
```

**Errors:**
- `401` - Invalid credentials
- `403` - Account locked or disabled
- `503` - Maintenance mode (non-admin users)

---

### Get Current User

Get authenticated user information.

**GET** `/auth/me`

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Response:** `200 OK`
```json
{
  "id": "uuid-here",
  "email": "user@example.com",
  "role": "user",
  "full_name": "John Doe"
}
```

**Errors:**
- `401` - Invalid or expired token

---

### Logout

Revoke current access token.

**POST** `/auth/logout`

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Response:** `200 OK`
```json
{
  "message": "Logged out successfully"
}
```

---

### Update Profile

Update user profile information.

**PATCH** `/auth/profile`

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Request Body:**
```json
{
  "full_name": "Jane Doe",
  "old_password": "oldpassword123",
  "password": "newpassword123"
}
```

**Response:** `200 OK`
```json
{
  "id": "uuid-here",
  "email": "user@example.com",
  "full_name": "Jane Doe",
  "role": "user",
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

## CV Endpoints

### Upload CV

Upload and parse a CV file.

**POST** `/cv/upload`

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
Content-Type: multipart/form-data
```

**Request Body:**
```
file: [CV file - PDF, DOCX, DOC, TXT]
```

**Response:** `200 OK`
```json
{
  "cv_id": "uuid-here",
  "filename": "john_doe_cv.pdf",
  "status": "pending",
  "message": "CV uploaded successfully. Parsing in progress..."
}
```

**Errors:**
- `400` - Invalid file format, file too large
- `401` - Unauthorized

---

### Get User CVs

List all CVs for authenticated user.

**GET** `/cv/list`

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Query Parameters:**
- `limit` (optional, default: 20) - Number of results
- `offset` (optional, default: 0) - Pagination offset

**Response:** `200 OK`
```json
{
  "items": [
    {
      "id": "uuid-here",
      "filename": "john_doe_cv.pdf",
      "status": "completed",
      "uploaded_at": "2024-01-01T00:00:00Z",
      "parsed_data": {
        "full_name": "John Doe",
        "email": "john@example.com",
        "phone": "+1234567890",
        "skills": ["Python", "JavaScript", "Docker"],
        "experience": [...]
      }
    }
  ],
  "total": 5,
  "limit": 20,
  "offset": 0
}
```

---

### Get CV Details

Get detailed information about a specific CV.

**GET** `/cv/{cv_id}`

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Response:** `200 OK`
```json
{
  "id": "uuid-here",
  "filename": "john_doe_cv.pdf",
  "status": "completed",
  "uploaded_at": "2024-01-01T00:00:00Z",
  "parsed_data": {
    "full_name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890",
    "summary": "Experienced software engineer...",
    "skills": ["Python", "JavaScript", "Docker"],
    "experience": [
      {
        "title": "Senior Developer",
        "company": "Tech Corp",
        "duration": "2020-2023",
        "description": "Led development team..."
      }
    ],
    "education": [...]
  }
}
```

**Errors:**
- `404` - CV not found
- `403` - Not authorized to access this CV

---

### Delete CV

Delete a CV.

**DELETE** `/cv/{cv_id}`

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Response:** `200 OK`
```json
{
  "message": "CV deleted successfully"
}
```

---

## Job Description Endpoints

### List Job Descriptions

Get all available job descriptions.

**GET** `/jd/list`

**Query Parameters:**
- `limit` (optional, default: 20)
- `offset` (optional, default: 0)
- `q` (optional) - Search query

**Response:** `200 OK`
```json
{
  "items": [
    {
      "id": "uuid-here",
      "title": "Senior Python Developer",
      "company": "Tech Corp",
      "location": "Remote",
      "description": "We are looking for...",
      "required_skills": ["Python", "Django", "PostgreSQL"],
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 50,
  "limit": 20,
  "offset": 0
}
```

---

### Get Job Description Details

**GET** `/jd/{jd_id}`

**Response:** `200 OK`
```json
{
  "id": "uuid-here",
  "title": "Senior Python Developer",
  "company": "Tech Corp",
  "location": "Remote",
  "description": "Full job description...",
  "required_skills": ["Python", "Django", "PostgreSQL"],
  "preferred_skills": ["Docker", "AWS"],
  "experience_required": "5+ years",
  "salary_range": "$100k - $150k",
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

## Analysis Endpoints

### Analyze CV vs Job

Perform gap analysis between CV and job description.

**POST** `/analysis/gap`

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Request Body:**
```json
{
  "cv_id": "uuid-here",
  "jd_id": "uuid-here"
}
```

**Response:** `200 OK`
```json
{
  "analysis_id": "uuid-here",
  "status": "completed",
  "match_score": 75,
  "gaps": {
    "missing_skills": ["Kubernetes", "GraphQL"],
    "weak_areas": ["Cloud Architecture"],
    "strengths": ["Python", "Django", "PostgreSQL"]
  },
  "recommendations": [
    {
      "skill": "Kubernetes",
      "priority": "high",
      "reason": "Required for the position"
    }
  ]
}
```

---

### Get Analysis History

Get all gap analyses for authenticated user.

**GET** `/analysis/history`

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Query Parameters:**
- `limit` (optional, default: 20)
- `offset` (optional, default: 0)

**Response:** `200 OK`
```json
{
  "items": [
    {
      "id": "uuid-here",
      "cv_id": "uuid-here",
      "jd_id": "uuid-here",
      "match_score": 75,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 10,
  "limit": 20,
  "offset": 0
}
```

---

## Recommendation Endpoints

### Get Course Recommendations

Get personalized course recommendations based on gap analysis.

**POST** `/recommend/courses`

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Request Body:**
```json
{
  "analysis_id": "uuid-here",
  "limit": 10
}
```

**Response:** `200 OK`
```json
{
  "recommendations": [
    {
      "course_id": "uuid-here",
      "title": "Kubernetes for Developers",
      "provider": "Udemy",
      "platform": "udemy",
      "url": "https://udemy.com/course/...",
      "rating": 4.7,
      "level": "intermediate",
      "duration": "10 hours",
      "relevance_score": 95,
      "skills_covered": ["Kubernetes", "Docker", "DevOps"]
    }
  ]
}
```

---

## Admin Endpoints

All admin endpoints require `role: admin`.

### List All Users

**GET** `/auth/admin/users`

**Headers:**
```
Authorization: Bearer ADMIN_TOKEN
```

**Query Parameters:**
- `limit` (optional, default: 20)
- `offset` (optional, default: 0)
- `q` (optional) - Search by email or name

**Response:** `200 OK`
```json
{
  "items": [
    {
      "id": "uuid-here",
      "email": "user@example.com",
      "full_name": "John Doe",
      "role": "user",
      "is_active": true,
      "is_flagged": false,
      "daily_token_limit": 0,
      "today_usage": 150,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 100,
  "limit": 20,
  "offset": 0
}
```

---

### Update User

**PATCH** `/auth/admin/users/{user_id}`

**Headers:**
```
Authorization: Bearer ADMIN_TOKEN
```

**Request Body:**
```json
{
  "is_active": false,
  "role": "admin",
  "daily_token_limit": 10000
}
```

**Response:** `200 OK`
```json
{
  "id": "uuid-here",
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "admin",
  "is_active": false,
  "is_flagged": false,
  "daily_token_limit": 10000,
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### Get Blocked IPs

**GET** `/admin/blocked-ips`

**Headers:**
```
Authorization: Bearer ADMIN_TOKEN
```

**Response:** `200 OK`
```json
{
  "total": 3,
  "blocked_ips": [
    {
      "ip_address": "192.168.1.100",
      "ttl_seconds": 82800,
      "ttl_hours": 23.0,
      "attempts": 5,
      "expires_in": "23h 0m"
    }
  ]
}
```

See [IP_BLOCK_MANAGEMENT.md](./IP_BLOCK_MANAGEMENT.md) for complete IP blocking documentation.

---

### System Settings

**GET** `/admin/settings`

Get all system settings.

**Headers:**
```
Authorization: Bearer ADMIN_TOKEN
```

**Response:** `200 OK`
```json
{
  "AI_MODEL": "gpt-4o-mini",
  "GAP_LLM_MODEL": "gpt-4o-mini",
  "MAINTENANCE_MODE": "false",
  "MAINTENANCE_DURATION": ""
}
```

---

**PUT** `/admin/settings/{key}`

Update a system setting.

**Headers:**
```
Authorization: Bearer ADMIN_TOKEN
```

**Request Body:**
```json
{
  "value": "gpt-4o"
}
```

**Response:** `200 OK`
```json
{
  "key": "AI_MODEL",
  "value": "gpt-4o",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

---

### Job Export/Import

#### Get Export Info

Get information for planning job export (total count, recommended parts, estimated size).

**GET** `/jd/admin/export-info`

**Headers:**
```
Authorization: Bearer ADMIN_TOKEN
```

**Response:** `200 OK`
```json
{
  "total_jobs": 5000,
  "recommended_parts": 3,
  "recommended_per_part": 1666,
  "estimated_total_size_mb": 48.83,
  "estimated_size_per_part_mb": 16.28
}
```

---

#### Export Jobs

Export jobs with pagination. Use export-info endpoint first to plan your export.

**GET** `/jd/admin/export`

**Headers:**
```
Authorization: Bearer ADMIN_TOKEN
```

**Query Parameters:**
- `limit` (optional, default: 2000, max: 5000) - Number of jobs per part
- `offset` (optional, default: 0) - Starting position
- `part` (optional) - Part number for reference

**Example:**
```
GET /jd/admin/export?limit=2000&offset=0&part=1
GET /jd/admin/export?limit=2000&offset=2000&part=2
GET /jd/admin/export?limit=2000&offset=4000&part=3
```

**Response:** `200 OK`
```json
{
  "count": 2000,
  "jobs": [
    {
      "id": "uuid-here",
      "source_id": "job123",
      "title": "Senior Backend Developer",
      "company": "Tech Corp",
      "description": "...",
      "requirements": "...",
      "embedding": [0.1, 0.2, ...],
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "metadata": {
    "exported_at": "2024-01-01T12:00:00Z",
    "total_available": 5000,
    "offset": 0,
    "limit": 2000,
    "part": 1,
    "has_more": true,
    "next_offset": 2000,
    "total_exported": 2000
  }
}
```

---

#### Upload URLs for Batch Crawling

Upload a .txt file with TopCV job URLs (one per line) and queue them for background crawling. Each URL will be crawled by a worker and automatically saved to the database.

**POST** `/jd/admin/crawl/upload-urls`

**Headers:**
```
Authorization: Bearer ADMIN_TOKEN
Content-Type: multipart/form-data
```

**Request Body:**
- `file`: .txt file with URLs (one per line)

**Example .txt file:**
```
https://www.topcv.vn/viec-lam/senior-backend-developer/123456.html
https://www.topcv.vn/viec-lam/frontend-developer/789012.html
https://www.topcv.vn/viec-lam/devops-engineer/345678.html
```

**Response:** `200 OK`
```json
{
  "message": "URLs queued for background crawling",
  "queued": 150,
  "skipped": 5,
  "total_urls": 155,
  "task_ids": ["task-id-1", "task-id-2", "..."]
}
```

**Notes:**
- Only TopCV URLs are supported
- Invalid URLs are automatically skipped
- Each URL is processed by a Celery worker
- Duplicate jobs (by source_id) are automatically skipped
- Skills are extracted asynchronously after job is saved

---

#### Import Jobs

Import jobs with pre-computed vectors. Duplicates (by source_id) are automatically skipped.

**POST** `/jd/admin/import-full`

**Headers:**
```
Authorization: Bearer ADMIN_TOKEN
Content-Type: application/json
```

**Request Body:**
```json
{
  "jobs": [
    {
      "source_id": "job123",
      "title": "Senior Backend Developer",
      "company": "Tech Corp",
      "description": "...",
      "requirements": "...",
      "embedding": [0.1, 0.2, ...]
    }
  ]
}
```

**Response:** `200 OK`
```json
{
  "imported": 1500,
  "skipped": 500,
  "errors": 0,
  "details": {
    "skipped_items": [
      {
        "source_id": "job123",
        "reason": "Already exists"
      }
    ]
  }
}
```

---

### Course Export/Import

#### Get Course Export Info

Get information for planning course export (total count, recommended parts, estimated size).

**GET** `/recommend/admin/export-info`

**Headers:**
```
Authorization: Bearer ADMIN_TOKEN
```

**Response:** `200 OK`
```json
{
  "total_courses": 3000,
  "recommended_parts": 2,
  "recommended_per_part": 1500,
  "estimated_total_size_mb": 23.44,
  "estimated_size_per_part_mb": 11.72
}
```

---

#### Export Courses

Export courses with pagination. Use export-info endpoint first to plan your export.

**GET** `/recommend/admin/export`

**Headers:**
```
Authorization: Bearer ADMIN_TOKEN
```

**Query Parameters:**
- `limit` (optional, default: 2000, max: 5000) - Number of courses per part
- `offset` (optional, default: 0) - Starting position
- `part` (optional) - Part number for reference

**Example:**
```
GET /recommend/admin/export?limit=1500&offset=0&part=1
GET /recommend/admin/export?limit=1500&offset=1500&part=2
```

**Response:** `200 OK`
```json
{
  "count": 1500,
  "courses": [
    {
      "id": "uuid-here",
      "source_id": "course456",
      "source_platform": "coursera",
      "title": "Machine Learning Specialization",
      "description": "...",
      "embedding": [0.1, 0.2, ...],
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "metadata": {
    "exported_at": "2024-01-01T12:00:00Z",
    "total_available": 3000,
    "offset": 0,
    "limit": 1500,
    "part": 1,
    "has_more": true,
    "next_offset": 1500,
    "total_exported": 1500
  }
}
```

---

#### Upload URLs for Batch Crawling

Upload a .txt file with Coursera course URLs (one per line) and queue them for background crawling. Each URL will be crawled by a worker and automatically saved to the database.

**POST** `/recommend/admin/courses/crawl/upload-urls`

**Headers:**
```
Authorization: Bearer ADMIN_TOKEN
Content-Type: multipart/form-data
```

**Request Body:**
- `file`: .txt file with URLs (one per line)

**Example .txt file:**
```
https://www.coursera.org/learn/machine-learning
https://www.coursera.org/learn/deep-learning
https://www.coursera.org/specializations/data-science
```

**Response:** `200 OK`
```json
{
  "message": "URLs queued for background crawling",
  "queued": 45,
  "skipped": 2,
  "total_urls": 47,
  "task_ids": ["task-id-1", "task-id-2", "..."]
}
```

**Notes:**
- Only Coursera URLs are supported
- Invalid URLs are automatically skipped
- Each URL is processed by a Celery worker
- Duplicate courses (by source_id or URL) are automatically skipped
- Embeddings are generated automatically

---

#### Import Courses

Import courses with pre-computed vectors. Duplicates (by source_platform + source_id) are automatically skipped.

**POST** `/recommend/admin/import-full`

**Headers:**
```
Authorization: Bearer ADMIN_TOKEN
Content-Type: application/json
```

**Request Body:**
```json
{
  "courses": [
    {
      "source_id": "course456",
      "source_platform": "coursera",
      "title": "Machine Learning Specialization",
      "description": "...",
      "embedding": [0.1, 0.2, ...]
    }
  ]
}
```

**Response:** `200 OK`
```json
{
  "imported": 1200,
  "skipped": 300,
  "errors": 0,
  "details": {
    "skipped_items": [
      {
        "source_id": "course456",
        "source_platform": "coursera",
        "reason": "Already exists"
      }
    ]
  }
}
```

---

## Error Responses

All endpoints may return these error responses:

### 400 Bad Request
```json
{
  "detail": "Validation error message"
}
```

### 401 Unauthorized
```json
{
  "detail": "Invalid or expired token"
}
```

### 403 Forbidden
```json
{
  "detail": "Admin privileges required"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 429 Too Many Requests
```json
{
  "detail": "Rate limit exceeded. Please try again later."
}
```

### 503 Service Unavailable
```json
{
  "detail": "Hệ thống đang bảo trì. Vui lòng quay lại sau.",
  "maintenance": true,
  "duration": "2 hours"
}
```

---

## Rate Limits

- `/auth/login`: 20 requests/minute
- `/auth/register`: 5 requests/day per IP
- `/auth/refresh`: 30 requests/minute (deprecated)
- `/auth/forgot-password`: 5 requests/minute
- Most other endpoints: No strict limit (monitored)

---

## Notes

- All timestamps are in ISO 8601 format (UTC)
- All IDs are UUIDs
- File uploads limited to 10MB
- Supported CV formats: PDF, DOCX, DOC, TXT
- Token expires after 7 days of inactivity
