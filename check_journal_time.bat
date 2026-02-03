@echo off
ssh tp "sudo journalctl --since '2026-02-02 12:35' --until '2026-02-02 12:50' 2>/dev/null | grep -iE 'payment|webhook|notify|tbank|yookassa' | head -50"
