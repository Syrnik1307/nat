#!/bin/bash
sqlite3 /var/www/teaching_panel/teaching_panel/db.sqlite3 "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'homework%' ORDER BY name;"
