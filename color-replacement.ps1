# Color replacement script for consistent design system
$frontendPath = "c:\Users\User\Desktop\nat\frontend\src"

# Array of color replacement pairs (old, new)
$replacements = @(
    @('#667eea', '#1e3a8a'),
    @('#764ba2', '#0c1e3a'),
    @('#3B82F6', '#1e3a8a'),
    @('#3b82f6', '#1e3a8a'),
    @('#2563eb', '#1e3a8a'),
    @('#2563EB', '#1e3a8a'),
    @('#0284c7', '#1e3a8a'),
    @('#f59e0b', '#ef4444'),
    @('#F59E0B', '#ef4444'),
    @('#f9e7b4', '#fee2e2'),
    @('#10b981', '#1e3a8a'),
    @('#10B981', '#1e3a8a'),
    @('#059669', '#0c1e3a'),
    @('#1d4ed8', '#0c1e3a'),
    @('#60a5fa', '#1e3a8a'),
    @('#fbbf24', '#ef4444')
)

# Get all CSS files
$cssFiles = Get-ChildItem -Path $frontendPath -Filter "*.css" -Recurse | Where-Object { $_.FullName -notmatch 'node_modules' }

$totalReplaced = 0
foreach ($file in $cssFiles) {
    $content = Get-Content $file.FullName -Raw
    $originalContent = $content
    
    foreach ($pair in $replacements) {
        $oldColor = $pair[0]
        $newColor = $pair[1]
        $content = $content -replace [regex]::Escape($oldColor), $newColor
    }
    
    if ($content -ne $originalContent) {
        Set-Content -Path $file.FullName -Value $content -NoNewline
        Write-Host "✓ Updated: $($file.Name)"
        $totalReplaced++
    }
}

Write-Host "`n✓ Total files updated: $totalReplaced"
