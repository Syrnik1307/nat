pwsh -NoProfile -Command {
    ssh root@72.56.81.163 "sqlite3 /var/www/teaching_panel/teaching_panel/db.sqlite3 'SELECT \"homework:\" || COUNT(*) FROM homework_homework UNION ALL SELECT \"submissions:\" || COUNT(*) FROM homework_studentsubmission UNION ALL SELECT \"groups:\" || COUNT(*) FROM schedule_group UNION ALL SELECT \"students:\" || COUNT(*) FROM accounts_customuser WHERE role=\"student\";'"
}
