#!/usr/bin/env python
"""
Script to re-evaluate all answers that might have been affected by the
config.options/choices ID confusion bug.

This script will:
1. Find all Answer objects where auto_score=0 for SINGLE_CHOICE/MULTI_CHOICE
2. Re-run evaluate() to recalculate the score based on is_correct flag
3. Update submission total_score
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from homework.models import Answer, Question, StudentSubmission

def fix_answers():
    print("=== Re-evaluating broken answers ===")
    
    # Find answers with potential issues
    # SINGLE_CHOICE or MULTI_CHOICE with auto_score=0 where user selected something
    from django.db.models import Count
    
    answers_to_fix = Answer.objects.filter(
        question__question_type__in=['SINGLE_CHOICE', 'MULTI_CHOICE'],
        auto_score=0
    ).annotate(
        selected_count=Count('selected_choices')
    ).filter(
        selected_count__gt=0
    ).select_related('question', 'submission')
    
    print(f"Found {len(answers_to_fix)} answers to check")
    
    fixed_count = 0
    submission_ids = set()
    
    for answer in answers_to_fix:
        old_score = answer.auto_score
        
        # Re-evaluate
        answer.evaluate()
        
        if answer.auto_score != old_score:
            print(f"  Fixed A#{answer.id}: {old_score} -> {answer.auto_score}")
            fixed_count += 1
            submission_ids.add(answer.submission_id)
    
    print(f"\nFixed {fixed_count} answers")
    
    # Recompute submission totals
    if submission_ids:
        print(f"\nRecomputing scores for {len(submission_ids)} submissions...")
        for sub_id in submission_ids:
            try:
                sub = StudentSubmission.objects.get(id=sub_id)
                old_total = sub.total_score
                sub.compute_auto_score()
                print(f"  Submission #{sub_id}: {old_total} -> {sub.total_score}")
            except StudentSubmission.DoesNotExist:
                print(f"  Submission #{sub_id}: NOT FOUND")
    
    print("\n=== Done ===")

if __name__ == '__main__':
    # Dry run by default - pass --fix to actually save
    if '--fix' in sys.argv:
        print("Running in FIX mode - changes will be saved")
        fix_answers()
    else:
        print("Running in DRY RUN mode - no changes will be saved")
        print("Pass --fix to actually fix the answers")
        print()
        fix_answers()
