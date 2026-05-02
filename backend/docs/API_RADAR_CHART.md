# Radar Chart API Documentation

## Overview

The radar chart feature provides a 5-dimension visualization of CV vs JD skill comparison. This groups detailed skill categories into 5 core dimensions for clear, actionable insights.

## Integration Point

The radar chart data is automatically calculated and included in the gap analysis response at:
- **Endpoint**: `POST /analysis/gap` → `GET /analysis/status/{task_id}`
- **Location**: `result.radar_chart` field in the response

## Response Structure

### radar_chart Object

```json
{
  "radar_chart": {
    "dimensions": [
      "Core Programming",
      "Infrastructure & DevOps",
      "Data & Databases",
      "Development Tools & Practices",
      "Specialized Technical Skills"
    ],
    "cv_scores": [85.0, 70.0, 95.0, 80.0, 50.0],
    "jd_scores": [100, 100, 100, 100, 100],
    "match_percentages": [85.0, 70.0, 95.0, 80.0, 50.0],
    "overall_match": 76.0,
    "dimension_details": {
      "Core Programming": {
        "cv_skills": ["javascript", "python", "react"],
        "jd_skills": ["javascript", "python", "react", "typescript"],
        "matched": ["javascript", "python", "react"],
        "missing": ["typescript"],
        "extra": [],
        "match_rate": 0.75,
        "match_percentage": 75.0,
        "priority": 1,
        "icon": "💻",
        "description": "Programming languages, frameworks, and core libraries",
        "skill_count": {
          "cv": 3,
          "jd": 4,
          "matched": 3,
          "missing": 1
        }
      },
      "Infrastructure & DevOps": {
        "cv_skills": ["docker", "kubernetes"],
        "jd_skills": ["docker", "kubernetes", "aws"],
        "matched": ["docker", "kubernetes"],
        "missing": ["aws"],
        "extra": [],
        "match_rate": 0.67,
        "match_percentage": 67.0,
        "priority": 2,
        "icon": "☁️",
        "description": "Cloud platforms, containers, CI/CD, and infrastructure tools",
        "skill_count": {
          "cv": 2,
          "jd": 3,
          "matched": 2,
          "missing": 1
        }
      }
      // ... other dimensions
    },
    "priority_gaps": [
      {
        "dimension": "Specialized Technical Skills",
        "match_percentage": 50.0,
        "gap": 50.0,
        "missing_skills": ["microservices", "api gateway"],
        "missing_count": 2,
        "priority": 5,
        "severity": "high",
        "icon": "🎯"
      }
    ],
    "summary": {
      "total_jd_skills": 20,
      "total_matched": 15,
      "total_missing": 5,
      "dimensions_count": 5
    }
  }
}
```

## Field Descriptions

### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `dimensions` | `string[]` | Array of 5 dimension names in priority order |
| `cv_scores` | `number[]` | Match percentages for each dimension (0-100) |
| `jd_scores` | `number[]` | Always [100, 100, 100, 100, 100] (baseline) |
| `match_percentages` | `number[]` | Same as cv_scores (for clarity) |
| `overall_match` | `number` | Overall match percentage across all dimensions |
| `dimension_details` | `object` | Detailed breakdown for each dimension |
| `priority_gaps` | `array` | Dimensions with match < 70% (sorted by severity) |
| `summary` | `object` | Aggregate statistics |

### dimension_details Object

Each dimension contains:

| Field | Type | Description |
|-------|------|-------------|
| `cv_skills` | `string[]` | Skills from CV in this dimension (lowercase) |
| `jd_skills` | `string[]` | Skills from JD in this dimension (lowercase) |
| `matched` | `string[]` | Skills present in both CV and JD |
| `missing` | `string[]` | Skills in JD but not in CV (gaps) |
| `extra` | `string[]` | Skills in CV but not in JD (bonus skills) |
| `match_rate` | `number` | Match ratio (0.0-1.0) |
| `match_percentage` | `number` | Match percentage (0-100) |
| `priority` | `number` | Dimension priority (1-5, lower = higher priority) |
| `icon` | `string` | Emoji icon for UI display |
| `description` | `string` | Human-readable dimension description |
| `skill_count` | `object` | Skill counts (cv, jd, matched, missing) |

### priority_gaps Array

Each gap object contains:

| Field | Type | Description |
|-------|------|-------------|
| `dimension` | `string` | Dimension name |
| `match_percentage` | `number` | Current match percentage |
| `gap` | `number` | Gap size (100 - match_percentage) |
| `missing_skills` | `string[]` | List of missing skills |
| `missing_count` | `number` | Number of missing skills |
| `priority` | `number` | Dimension priority (1-5) |
| `severity` | `string` | "high" (<50%), "medium" (50-70%), "low" (70-100%) |
| `icon` | `string` | Emoji icon |

## Dimension Mapping

The 5 radar dimensions map detailed skill categories as follows:

### 1. Core Programming (💻)
- Programming Language, Scripting Language
- Framework, Library
- Frontend Framework, Backend Framework
- JavaScript Library, Style Sheet Language, Markup Language

### 2. Infrastructure & DevOps (☁️)
- Cloud Platform, Cloud Service, Cloud Technology
- Containerization, DevOps, DevOps Tool
- Operating System, Web Server, Load Balancer Tool
- Networking, Networking Tool, Networking Concept

### 3. Data & Databases (🗄️)
- Database, Database Technology, Database Language
- Query Language, Big Data Technology, Cache
- Model (ML/AI), NLP Task, LLM Task, AI Tool

### 4. Development Tools & Practices (🛠️)
- Tool, Version Control, Methodology
- Testing Framework, Build Tool, Documentation
- Collaboration Tool, Design Tool, Project Management Tool
- Reporting Tool, Standard, Development

### 5. Specialized Technical Skills (🎯)
- Technical Skill, Technical Knowledge, Architecture
- System, API Technology, Security
- Security Tool, Security Technology, Firewall Tool
- Endpoint Protection Tool, SIEM Tool, Concept
- Programming Concept, Design, Performance Optimization
- Accessibility, State Management, Analytical Technique

## Usage Example

### Frontend Integration (Chart.js)

```javascript
// Extract radar chart data from gap analysis response
const radarData = analysisResult.radar_chart;

// Configure Chart.js radar chart
const chartConfig = {
  type: 'radar',
  data: {
    labels: radarData.dimensions,
    datasets: [
      {
        label: 'Your Skills',
        data: radarData.cv_scores,
        backgroundColor: 'rgba(54, 162, 235, 0.2)',
        borderColor: 'rgb(54, 162, 235)',
        pointBackgroundColor: 'rgb(54, 162, 235)',
      },
      {
        label: 'Job Requirements',
        data: radarData.jd_scores,
        backgroundColor: 'rgba(255, 99, 132, 0.2)',
        borderColor: 'rgb(255, 99, 132)',
        pointBackgroundColor: 'rgb(255, 99, 132)',
      }
    ]
  },
  options: {
    scales: {
      r: {
        min: 0,
        max: 100,
        ticks: { stepSize: 20 }
      }
    }
  }
};

// Display priority gaps
radarData.priority_gaps.forEach(gap => {
  console.log(`${gap.icon} ${gap.dimension}: ${gap.match_percentage}% (${gap.severity})`);
  console.log(`  Missing: ${gap.missing_skills.join(', ')}`);
});
```

### Display Priority Gaps

```javascript
// Show gaps that need attention (match < 70%)
const priorityGaps = radarData.priority_gaps;

if (priorityGaps.length > 0) {
  console.log('Areas to improve:');
  priorityGaps.forEach(gap => {
    const severity = gap.severity === 'high' ? '🔴' : 
                     gap.severity === 'medium' ? '🟡' : '🟢';
    console.log(`${severity} ${gap.dimension}: ${gap.match_percentage}%`);
    console.log(`   Missing skills: ${gap.missing_skills.slice(0, 3).join(', ')}`);
    if (gap.missing_count > 3) {
      console.log(`   ... and ${gap.missing_count - 3} more`);
    }
  });
}
```

## Calculation Logic

1. **Skill Extraction**: Extract skills with categories from CV and JD
2. **Dimension Mapping**: Map each skill's category to one of 5 dimensions
3. **Match Calculation**: For each dimension:
   - `match_rate = matched_skills / jd_skills`
   - `match_percentage = match_rate * 100`
4. **Overall Match**: `(total_matched / total_jd_skills) * 100`
5. **Priority Gaps**: Dimensions with `match_percentage < 70%`

## Edge Cases

### No JD Skills in Dimension
If JD has no requirements in a dimension:
- `match_rate = 1.0` (100%)
- `match_percentage = 100`
- No gap reported

### Missing Skill Categories
If skills don't have category information:
- Default category: "Technology"
- May map to "Other" dimension (excluded from radar)

### Empty CV or JD
If CV or JD has no skills:
- `radar_chart = null`
- Log warning in backend

## Performance

- **Calculation Time**: < 10ms (pure Python, no LLM)
- **Memory**: Minimal (skill lists are small)
- **Caching**: Included in gap analysis cache (Redis)

## Related Endpoints

- `POST /analysis/gap` - Trigger gap analysis (includes radar chart)
- `GET /analysis/status/{task_id}` - Get analysis result with radar chart
- `GET /analysis/user/latest` - Get latest analysis (includes radar chart)

## Notes

- Radar chart is calculated automatically for all gap analyses
- Soft skills are excluded from radar chart (shown separately)
- Skills are normalized to lowercase for matching
- Categories must match taxonomy for accurate dimension mapping
- Frontend should handle `radar_chart: null` gracefully

## Version History

- **v1.0** (2026-05-01): Initial implementation with 5-dimension grouping
