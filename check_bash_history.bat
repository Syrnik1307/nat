@echo off
ssh tp "cat ~/.bash_history 2>/dev/null | grep -iE 'notify|payment|mark_old' | tail -20"
