$ErrorActionPreference = 'Continue'

$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
$outFile = "prod_extended_smoke_output_$ts.txt"

$null = powershell -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\prod_extended_smoke.ps1" 2>&1 |
    Tee-Object -FilePath "$PSScriptRoot\$outFile"

Write-Output "SAVED_TO=$outFile"

exit $LASTEXITCODE
