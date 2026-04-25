"""
Migration: Backfill NULL duration_hours for courses

This script updates courses with NULL duration_hours by:
1. Estimating from modules count (2 hours per module)
2. Setting default based on level (Beginner: 10h, Intermediate: 20h, Advanced: 30h)
3. Using a default of 15h if no level information

Run: python backend/scripts/migrate_backfill_course_durations.py
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from shared.database import SessionLocal
from shared.models import Course
from sqlalchemy import func
import json


def estimate_duration_from_modules(modules_json):
    """Estimate duration from modules count (2 hours per module)"""
    if not modules_json:
        return None
    
    try:
        if isinstance(modules_json, str):
            modules = json.loads(modules_json)
        else:
            modules = modules_json
        
        if isinstance(modules, list) and len(modules) > 0:
            return len(modules) * 2.0
    except:
        pass
    
    return None


def estimate_duration_from_level(level):
    """Estimate duration based on course level"""
    if not level:
        return 15.0  # Default
    
    level_lower = level.lower()
    
    if 'beginner' in level_lower:
        return 10.0
    elif 'intermediate' in level_lower or 'mid' in level_lower:
        return 20.0
    elif 'advanced' in level_lower or 'expert' in level_lower or 'senior' in level_lower:
        return 30.0
    else:
        return 15.0  # Default


def backfill_course_durations():
    """Main migration function"""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("MIGRATION: Backfill Course Durations")
        print("=" * 80)
        
        # Get statistics before migration
        total_courses = db.query(Course).count()
        null_duration_courses = db.query(Course).filter(Course.duration_hours == None).all()
        null_count = len(null_duration_courses)
        
        print(f"\n[BEFORE MIGRATION]")
        print(f"   Total courses: {total_courses}")
        print(f"   Courses with NULL duration: {null_count} ({null_count/total_courses*100:.1f}%)")
        print(f"   Courses with valid duration: {total_courses - null_count}")
        
        if null_count == 0:
            print("\n[OK] No courses need updating. Migration complete!")
            return
        
        print(f"\n[UPDATING] {null_count} COURSES...")
        print("-" * 80)
        
        updated_count = 0
        strategy_stats = {
            'modules': 0,
            'level': 0,
            'default': 0
        }
        
        for course in null_duration_courses:
            estimated_duration = None
            strategy = None
            
            # Strategy 1: Estimate from modules
            estimated_duration = estimate_duration_from_modules(course.modules)
            if estimated_duration:
                strategy = 'modules'
                strategy_stats['modules'] += 1
            
            # Strategy 2: Estimate from level
            if not estimated_duration:
                estimated_duration = estimate_duration_from_level(course.level)
                if course.level:
                    strategy = 'level'
                    strategy_stats['level'] += 1
                else:
                    strategy = 'default'
                    strategy_stats['default'] += 1
            
            # Update course
            course.duration_hours = estimated_duration
            updated_count += 1
            
            # Log every 50 updates
            if updated_count % 50 == 0:
                print(f"   Progress: {updated_count}/{null_count} courses updated...")
        
        # Commit all changes
        db.commit()
        
        print(f"\n[MIGRATION COMPLETE]")
        print("-" * 80)
        print(f"   Updated: {updated_count} courses")
        print(f"\n[STRATEGY BREAKDOWN]")
        print(f"   From modules count: {strategy_stats['modules']} courses")
        print(f"   From level: {strategy_stats['level']} courses")
        print(f"   Default (15h): {strategy_stats['default']} courses")
        
        # Get statistics after migration
        null_after = db.query(Course).filter(Course.duration_hours == None).count()
        valid_after = db.query(Course).filter(Course.duration_hours > 0).count()
        
        print(f"\n[AFTER MIGRATION]")
        print(f"   Total courses: {total_courses}")
        print(f"   Courses with NULL duration: {null_after}")
        print(f"   Courses with valid duration: {valid_after} ({valid_after/total_courses*100:.1f}%)")
        
        # Calculate average duration by level
        print(f"\n[AVERAGE DURATION BY LEVEL]")
        levels = ['Beginner', 'Intermediate', 'Advanced', 'Mixed']
        for level in levels:
            avg = db.query(func.avg(Course.duration_hours)).filter(
                Course.level.ilike(f'%{level}%'),
                Course.duration_hours != None
            ).scalar()
            if avg:
                count = db.query(Course).filter(
                    Course.level.ilike(f'%{level}%'),
                    Course.duration_hours != None
                ).count()
                print(f"   {level}: {avg:.1f}h (n={count})")
        
        print("\n" + "=" * 80)
        print("[SUCCESS] Migration completed successfully!")
        print("=" * 80)
        
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] during migration: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("\n[WARNING] This will update courses with NULL duration_hours")
    print("   Press Ctrl+C to cancel, or Enter to continue...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Migration cancelled by user.")
        sys.exit(0)
    
    backfill_course_durations()
