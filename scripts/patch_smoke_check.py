#!/usr/bin/env python3
"""Patch smoke_check_v2.sh to add asset integrity check (check #13)."""

path = "/opt/lectio-monitor/smoke_check_v2.sh"
with open(path, "r") as f:
    c = f.read()

# Check if already patched
if "check_asset_integrity" in c:
    print("ALREADY_PATCHED")
    exit(0)

func = """
# 13. Check ALL assets from manifest exist on disk (prevents partial deploy)
check_asset_integrity() {
    local manifest="${PROJECT_ROOT}/frontend/build/asset-manifest.json"
    if [[ ! -f "$manifest" ]]; then
        echo "FAIL:asset-manifest.json not found"
        return 1
    fi
    local result
    result=$(python3 -c "
import json, os
root='/var/www/teaching_panel/frontend/build'
m=json.load(open(root+'/asset-manifest.json'))
miss=[]
total=0
for v in m.get('files',{}).values():
    if v.startswith('/'):
        total+=1
        if not os.path.exists(root+v): miss.append(v)
if miss: print('FAIL:%d/%d missing:%s' % (len(miss),total,' '.join(miss[:5])))
else: print('OK:%d assets' % total)
" 2>/dev/null)
    if [[ "$result" == FAIL:* ]]; then
        echo "$result"
        return 1
    fi
    echo "$result"
    return 0
}

"""

# Insert before run_all_checks
c = c.replace("run_all_checks() {", func + "run_all_checks() {", 1)

# Add the call after check_chunk_loading block  
old_block = '        res=$(check_chunk_loading)\n        [[ "$res" == FAIL:* ]] && { issues+=("${res#FAIL:}"); ((critical_count++)); }'

new_block = old_block + """

        # 13. Asset integrity (ALL files from manifest on disk)
        res=$(check_asset_integrity)
        [[ "$res" == FAIL:* ]] && { issues+=("${res#FAIL:}"); ((critical_count++)); }"""

c = c.replace(old_block, new_block, 1)

# Update check count
c = c.replace('(12/12)', '(13/13)')

with open(path, "w") as f:
    f.write(c)

print("PATCHED_OK")
