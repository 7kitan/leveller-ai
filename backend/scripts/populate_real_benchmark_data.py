"""
Script to populate benchmark test cases with REAL CV and Job IDs from database.
This replaces PLACEHOLDER values with actual data.

Usage:
    python -m scripts.populate_real_benchmark_data

Requirements:
    - Database must have at least 5 CVs with status='completed'
    - Database must have at least 5 active Jobs
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.database import SessionLocal
from shared.models import LLMTestCase, UserCV, Job, Course, YouTubeCourse
import json

def get_real_cvs(db, limit=10):
    """Get real CVs from database"""
    cvs = db.query(UserCV)\
            .filter(UserCV.status == "completed")\
            .filter(UserCV.cv_parsed_json.isnot(None))\
            .order_by(UserCV.created_at.desc())\
            .limit(limit)\
            .all()
    
    print(f"✓ Found {len(cvs)} completed CVs")
    for cv in cvs[:5]:
        print(f"  - {cv.id}: {cv.full_name or 'Unknown'} ({cv.experience_years_total or 0} years exp)")
    
    return cvs

def get_real_jobs(db, limit=10):
    """Get real Jobs from database"""
    jobs = db.query(Job)\
             .filter(Job.status == "active")\
             .filter(Job.requirements.isnot(None))\
             .order_by(Job.created_at.desc())\
             .limit(limit)\
             .all()
    
    print(f"✓ Found {len(jobs)} active jobs")
    for job in jobs[:5]:
        print(f"  - {job.id}: {job.title_raw} at {job.company_name}")
    
    return jobs

def get_real_courses(db, limit=10):
    """Get real Courses from database"""
    courses = db.query(Course)\
                .filter(Course.is_active == True)\
                .order_by(Course.created_at.desc())\
                .limit(limit)\
                .all()
    
    print(f"✓ Found {len(courses)} active courses")
    return courses

def get_real_youtube_videos(db, limit=10):
    """Get real YouTube videos from database"""
    videos = db.query(YouTubeCourse)\
               .order_by(YouTubeCourse.created_at.desc())\
               .limit(limit)\
               .all()
    
    print(f"✓ Found {len(videos)} YouTube videos")
    return videos

def update_test_case_with_real_data(db, test_case, cvs, jobs, courses, youtube_videos):
    """Update a single test case with real IDs"""
    input_data = test_case.input_data
    updated = False
    
    # Replace CV placeholders
    if "cv_id" in input_data and isinstance(input_data["cv_id"], str):
        if input_data["cv_id"].startswith("PLACEHOLDER"):
            if cvs:
                cv = cvs.pop(0)
                input_data["cv_id"] = str(cv.id)
                print(f"  ✓ Updated cv_id to {cv.id} ({cv.full_name})")
                updated = True
    
    # Replace Job placeholders
    if "job_id" in input_data and isinstance(input_data["job_id"], str):
        if input_data["job_id"].startswith("PLACEHOLDER"):
            if jobs:
                job = jobs.pop(0)
                input_data["job_id"] = str(job.id)
                
                # Also update jd_text if present
                if "jd_text" in input_data and job.requirements:
                    input_data["jd_text"] = job.requirements[:1000]  # First 1000 chars
                
                print(f"  ✓ Updated job_id to {job.id} ({job.title_raw})")
                updated = True
    
    # Replace Course placeholders in course_candidates
    if "course_candidates" in input_data:
        for candidate in input_data["course_candidates"]:
            if "course_id" in candidate and isinstance(candidate["course_id"], str):
                if candidate["course_id"].startswith("PLACEHOLDER") and courses:
                    course = courses.pop(0)
                    candidate["course_id"] = str(course.id)
                    candidate["title"] = course.title
                    candidate["platform"] = course.platform or "Udemy"
                    
                    # Extract skills from course
                    if course.skills_raw:
                        candidate["skills"] = course.skills_raw[:5]  # First 5 skills
                    
                    print(f"  ✓ Updated course_id to {course.id} ({course.title})")
                    updated = True
    
    # Replace YouTube video placeholders
    if "youtube_candidates" in input_data:
        for candidate in input_data["youtube_candidates"]:
            if "video_id" in candidate and isinstance(candidate["video_id"], str):
                if candidate["video_id"].startswith("PLACEHOLDER") and youtube_videos:
                    video = youtube_videos.pop(0)
                    candidate["video_id"] = video.video_id
                    candidate["title"] = video.title
                    candidate["channel_name"] = video.channel_name
                    print(f"  ✓ Updated video_id to {video.video_id} ({video.title})")
                    updated = True
    
    if updated:
        test_case.input_data = input_data
        db.commit()
        return True
    
    return False

def main():
    print("=" * 80)
    print("POPULATE REAL BENCHMARK DATA")
    print("=" * 80)
    print()
    
    db = SessionLocal()
    
    try:
        # Step 1: Get real data from database
        print("Step 1: Fetching real data from database...")
        print("-" * 80)
        cvs = get_real_cvs(db, limit=20)
        jobs = get_real_jobs(db, limit=20)
        courses = get_real_courses(db, limit=10)
        youtube_videos = get_real_youtube_videos(db, limit=10)
        print()
        
        if len(cvs) < 5:
            print("❌ ERROR: Need at least 5 completed CVs in database")
            print("   Please upload and parse some CVs first")
            return
        
        if len(jobs) < 5:
            print("❌ ERROR: Need at least 5 active jobs in database")
            print("   Please run the job crawler first")
            return
        
        # Step 2: Get all test cases with placeholders
        print("Step 2: Finding test cases with PLACEHOLDER values...")
        print("-" * 80)
        
        test_cases = db.query(LLMTestCase).all()
        print(f"✓ Found {len(test_cases)} total test cases")
        
        # Filter test cases that have placeholders
        placeholder_cases = []
        for case in test_cases:
            input_str = json.dumps(case.input_data)
            if "PLACEHOLDER" in input_str:
                placeholder_cases.append(case)
        
        print(f"✓ Found {len(placeholder_cases)} test cases with PLACEHOLDER values")
        print()
        
        if len(placeholder_cases) == 0:
            print("✓ No test cases need updating. All test cases already have real data!")
            return
        
        # Step 3: Update test cases
        print("Step 3: Updating test cases with real data...")
        print("-" * 80)
        
        updated_count = 0
        for i, case in enumerate(placeholder_cases, 1):
            print(f"\nTest Case {i}/{len(placeholder_cases)}: {case.id}")
            
            # Make copies of lists for this test case
            cvs_copy = list(cvs)
            jobs_copy = list(jobs)
            courses_copy = list(courses)
            videos_copy = list(youtube_videos)
            
            if update_test_case_with_real_data(db, case, cvs_copy, jobs_copy, courses_copy, videos_copy):
                updated_count += 1
        
        print()
        print("=" * 80)
        print(f"✓ SUCCESS: Updated {updated_count} test cases with real data")
        print("=" * 80)
        print()
        print("Next steps:")
        print("1. Run benchmark via API: POST /admin/benchmarks/run")
        print("2. Or use the benchmark runner script: python -m scripts.run_benchmark_api")
        print()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
