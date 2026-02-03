@echo off
ssh tp "sudo journalctl --since '2026-02-02 12:30' --until '2026-02-02 13:00' 2>/dev/null | grep -v 'kernel\|systemd\|sshd\|cron' | head -100"
