$ErrorActionPreference = "Continue"

Write-Host "Copying script..."
& scp run_migrate.sh root@72.56.81.163:/tmp/

Write-Host "Running migration..."
& ssh root@72.56.81.163 "bash /tmp/run_migrate.sh"

Write-Host "Done!"
