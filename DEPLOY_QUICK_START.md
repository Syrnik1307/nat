# 🚀 Quick Start - Production Deployment

## Files Created/Modified

### Backend Code Changes
1. ✅ `teaching_panel/schedule/models.py` - Added `default=''` to gdrive fields
2. ✅ `teaching_panel/schedule/migrations/0032_fix_gdrive_file_id_default.py` - Migration file (auto-generated)
3. ✅ `teaching_panel/schedule/tasks.py` - Added `sync_missing_zoom_recordings` task (+67 lines)
4. ✅ `teaching_panel/schedule/serializers.py` - Added `use_direct_stream` logic (+28 lines)
5. ✅ `teaching_panel/teaching_panel/settings.py` - Added sync task to CELERY_BEAT_SCHEDULE

### Deployment Scripts
1. ✅ `deploy_production_fixes.sh` - Main deployment script with backup/migration/restart
2. ✅ `fix_duplicate_celery_workers.sh` - Celery worker deduplication tool
3. ✅ `verify_production_fixes.py` - Automated test suite

### Documentation
1. ✅ `PRODUCTION_FIXES_REPORT.md` - Full technical documentation (this file's companion)

---

## 🎯 One-Command Deployment

```bash
# Upload scripts to production
scp deploy_production_fixes.sh fix_duplicate_celery_workers.sh verify_production_fixes.py tp:/tmp/

# SSH to production and run
ssh tp "cd /tmp && sudo bash deploy_production_fixes.sh"

# Verify deployment
ssh tp "cd /var/www/teaching_panel && source ../venv/bin/activate && python /tmp/verify_production_fixes.py"
```

---

## ⏱️ Estimated Deployment Time

- **Upload files:** 10 seconds
- **Backup database:** 5 seconds
- **Run migrations:** 30 seconds (confirmation required)
- **Restart services:** 20 seconds
- **Verification tests:** 15 seconds

**Total:** ~2 minutes

---

## ⚠️ Critical: Manual Confirmation Required

The deployment script will **pause** before running migrations:

```
⚠️  WARNING: Migrations are IRREVERSIBLE!
The following migration will be applied:
  - 0032_fix_gdrive_file_id_default (adds default='' to gdrive fields)

Backup location: /tmp/deploy_20260207_123456.sqlite3

Type MIGRATE to continue, or anything else to skip: _
```

**Type:** `MIGRATE` (case-sensitive)

---

## 📋 Pre-Deployment Checklist

- [ ] Read `PRODUCTION_FIXES_REPORT.md`
- [ ] Notify team of upcoming deployment
- [ ] Verify current production is healthy
- [ ] Check disk space: `df -h` (need ~500MB for backup)
- [ ] Ensure no users are actively uploading recordings

---

## 🧪 Post-Deployment Verification

Run these commands **immediately after deployment**:

```bash
# 1. Check services are running
systemctl status teaching-panel celery-worker

# 2. Check for errors in logs
journalctl -u teaching-panel -n 50 | grep -i error

# 3. Verify Celery worker count (should be 1)
systemctl list-units --type=service --state=active | grep celery | grep worker

# 4. Run automated tests
cd /var/www/teaching_panel
source ../venv/bin/activate
python /tmp/verify_production_fixes.py

# Expected output: "✅ All tests passed! Ready for production."
```

---

## 🔄 Rollback Plan

If something breaks:

```bash
# Find backup file
ls -lth /tmp/deploy_*.sqlite3 | head -1

# Restore database (replace TIMESTAMP with actual value)
sudo cp /tmp/deploy_YYYYMMDD_HHMMSS.sqlite3 /var/www/teaching_panel/db.sqlite3
sudo chown www-data:www-data /var/www/teaching_panel/db.sqlite3

# Restart service
sudo systemctl restart teaching-panel celery-worker

# Verify rollback
curl http://localhost:8000/api/health/
```

---

## 📞 Emergency Contacts

If deployment fails:

1. **Check logs:** `journalctl -u teaching-panel -n 100`
2. **Django shell:** `cd /var/www/teaching_panel && source ../venv/bin/activate && python manage.py shell`
3. **Database check:** `sqlite3 db.sqlite3 "PRAGMA integrity_check;"`
4. **Restore backup** (see Rollback Plan above)

---

## ✅ Success Criteria

Deployment is successful when:

1. ✅ All services show as `active (running)` in systemd
2. ✅ No errors in last 50 log lines
3. ✅ Only 1 Celery worker service active
4. ✅ All 7 verification tests pass
5. ✅ Can login/upload recording without errors

---

## 🎉 What Changed (User-Facing)

### For Teachers
- **Improved:** Large recordings (>100MB) now stream faster
- **Fixed:** Recording uploads no longer fail with "NULL constraint" error
- **New:** Automatic fallback if Zoom webhook misses a recording (checks every 30 min)

### For Admins
- **Improved:** No more duplicate Celery workers consuming resources
- **New:** Automated deployment script with backup/rollback
- **New:** Verification test suite

---

## 📚 Next Steps After Deployment

1. **Monitor for 24 hours:** Check logs daily for errors
2. **Test critical workflows:** 
   - Create lesson → Record → Verify appears in dashboard
   - Upload standalone recording → Verify storage quota updated
   - Access large recording → Verify streaming is smooth
3. **Frontend update (optional):** Update video player to use `use_direct_stream` flag
4. **Documentation:** Update internal wiki with new streaming behavior

---

**Deployment Script Version:** 1.0.0  
**Last Updated:** February 7, 2026  
**Status:** ✅ Ready for Production
