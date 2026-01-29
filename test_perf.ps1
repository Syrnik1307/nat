$teacher_creds = @{email="smoke_teacher@test.local"; password="TestPass123!"} | ConvertTo-Json
$student_creds = @{email="smoke_student@test.local"; password="TestPass123!"} | ConvertTo-Json

Write-Host "=== Testing login speed ==="
$sw = [Diagnostics.Stopwatch]::StartNew()
$token_resp = Invoke-RestMethod -Uri "https://lectio.tw1.ru/api/jwt/token/" -Method POST -Body $student_creds -ContentType "application/json"
$sw.Stop()
Write-Host "Login time: $($sw.ElapsedMilliseconds)ms"

$token = $token_resp.access

Write-Host "`n=== Testing homework list speed ==="
$headers = @{Authorization="Bearer $token"}
$sw = [Diagnostics.Stopwatch]::StartNew()
try {
    $hw = Invoke-RestMethod -Uri "https://lectio.tw1.ru/api/homework/" -Headers $headers
    $sw.Stop()
    Write-Host "Homework list time: $($sw.ElapsedMilliseconds)ms"
    Write-Host "Items count: $($hw.results.Count)"
} catch {
    $sw.Stop()
    Write-Host "Error: $($_.Exception.Message)"
    Write-Host "Time: $($sw.ElapsedMilliseconds)ms"
}

Write-Host "`n=== Testing submissions list speed ==="
$sw = [Diagnostics.Stopwatch]::StartNew()
try {
    $subs = Invoke-RestMethod -Uri "https://lectio.tw1.ru/api/submissions/" -Headers $headers
    $sw.Stop()
    Write-Host "Submissions list time: $($sw.ElapsedMilliseconds)ms"
} catch {
    $sw.Stop()
    Write-Host "Error: $($_.Exception.Message)"
    Write-Host "Time: $($sw.ElapsedMilliseconds)ms"
}
