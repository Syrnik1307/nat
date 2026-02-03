@echo off
ssh tp "sudo journalctl --since '2026-02-02 12:40' --until '2026-02-02 12:45' 2>/dev/null | head -150"
