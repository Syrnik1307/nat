#!/bin/bash
echo "=== Python processes memory usage ==="
ps aux | grep python | grep -v grep | awk '{sum+=$6} END {print "Total RSS: " sum/1024 " MB"}'

echo ""
echo "=== Memory by process ==="
ps aux | grep python | grep -v grep | awk '{print $6/1024 " MB - " $11}' | sort -rn | head -10
