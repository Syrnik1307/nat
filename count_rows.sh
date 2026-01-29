#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
sqlite3 db.sqlite3 <<EOF
SELECT 'homework: ' || COUNT(*) FROM homework_homework;
SELECT 'submissions: ' || COUNT(*) FROM homework_studentsubmission;
SELECT 'groups: ' || COUNT(*) FROM schedule_group;
SELECT 'students: ' || COUNT(*) FROM accounts_customuser WHERE role='student';
SELECT 'assigned_groups: ' || COUNT(*) FROM homework_homework_assigned_groups;
SELECT 'assigned_students: ' || COUNT(*) FROM homework_homework_assigned_students;
SELECT 'group_assignments: ' || COUNT(*) FROM homework_homeworkgroupassignment;
EOF
