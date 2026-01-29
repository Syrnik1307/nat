$sw = [Diagnostics.Stopwatch]::StartNew()
try {
    $r = Invoke-WebRequest -Uri "https://lectio.tw1.ru/api/jwt/verify/" -Method POST -Body '{"token":"fake"}' -ContentType "application/json" -UseBasicParsing
    Write-Host "Status: $($r.StatusCode)"
} catch {
    Write-Host "Error: $($_.Exception.Message)"
}
$sw.Stop()
Write-Host "Time: $($sw.ElapsedMilliseconds)ms"
