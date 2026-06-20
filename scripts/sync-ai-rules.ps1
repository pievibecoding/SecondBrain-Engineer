# sync-ai-rules.ps1
# Sync .kiro/steering/ sang format của các AI agent khác
# Chạy: .\scripts\sync-ai-rules.ps1

$ROOT = Split-Path -Parent $PSScriptRoot
$STEERING = "$ROOT\.kiro\steering"

Write-Host "Syncing AI rules from $STEERING..." -ForegroundColor Cyan

# Đọc tất cả steering files (bỏ front-matter)
function Get-SteeringContent($file) {
    $content = Get-Content $file -Raw
    # Bỏ front-matter (--- ... ---)
    if ($content -match "(?s)^---.*?---\s*(.*)$") {
        return $Matches[1].Trim()
    }
    return $content.Trim()
}

$files = @(
    "$STEERING\project-context.md",
    "$STEERING\backend-rules.md",
    "$STEERING\frontend-rules.md",
    "$STEERING\nas-rules.md",
    "$STEERING\lightrag-api.md",
    "$STEERING\graphiti-api.md",
    "$STEERING\test-conventions.md"
)

# Build merged content
$merged = @"
# SecondBrain — AI Agent Rules
# Auto-generated from .kiro/steering/ — DO NOT EDIT DIRECTLY
# Run scripts/sync-ai-rules.ps1 to regenerate
# Last synced: $(Get-Date -Format 'yyyy-MM-dd HH:mm')

"@

foreach ($file in $files) {
    if (Test-Path $file) {
        $name = [System.IO.Path]::GetFileNameWithoutExtension($file)
        $merged += "`n`n<!-- === $name === -->`n`n"
        $merged += Get-SteeringContent $file
    }
}

# Claude Code / Codex CLI → CLAUDE.md
$merged | Out-File "$ROOT\CLAUDE.md" -Encoding UTF8
Write-Host "  ✓ CLAUDE.md" -ForegroundColor Green

# Windsurf → .windsurfrules
$merged | Out-File "$ROOT\.windsurfrules" -Encoding UTF8
Write-Host "  ✓ .windsurfrules" -ForegroundColor Green

# Cursor → .cursorrules
$merged | Out-File "$ROOT\.cursorrules" -Encoding UTF8
Write-Host "  ✓ .cursorrules" -ForegroundColor Green

# Kiro steering đã có sẵn tại .kiro/steering/ — không cần copy
Write-Host "  ✓ .kiro/steering/ (source, no copy needed)" -ForegroundColor Green

Write-Host "`nSync complete! Rules distributed to all agents." -ForegroundColor Cyan
Write-Host "Remember: Edit .kiro/steering/*.md then re-run this script." -ForegroundColor Yellow
