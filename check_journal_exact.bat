@echo off
ssh tp "sudo journalctl --since '2026-02-02 12:41:10' --until '2026-02-02 12:42:00' 2>/dev/null"
