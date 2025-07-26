#!/usr/bin/env powershell
# 项目清理脚本 - 删除空文件和临时文件

Write-Host "🧹 开始清理项目目录..." -ForegroundColor Green

# 1. 删除空文件
$emptyFiles = Get-ChildItem -File -Recurse | Where-Object { $_.Length -eq 0 -and $_.Name -notmatch "^\." }
if ($emptyFiles) {
    Write-Host "📋 发现 $($emptyFiles.Count) 个空文件:" -ForegroundColor Yellow
    foreach ($file in $emptyFiles) {
        Write-Host "  - 删除: $($file.FullName.Replace((Get-Location).Path + '\', ''))" -ForegroundColor Red
        Remove-Item $file.FullName -Force
    }
} else {
    Write-Host "✅ 没有发现空文件" -ForegroundColor Green
}

# 2. 删除临时文件模式
$tempPatterns = @(
    "test_*.py",
    "*_test.py", 
    "debug_*.py",
    "demo_*.py",
    "verify_*.py",
    "analyze_*.py",
    "fix_*.py",
    "diagnose_*.py",
    "quick_*.py",
    "simple_*.py",
    "run_*.py",
    "temp_*.*",
    "tmp_*.*",
    "*.tmp",
    "*.temp"
)

$removedCount = 0
foreach ($pattern in $tempPatterns) {
    $matchingFiles = Get-ChildItem -Path "." -Filter $pattern -File | Where-Object { 
        $_.Directory.Name -ne "tests" -and 
        $_.Directory.Name -ne "archived_files" -and
        $_.Name -notmatch "\.example$"
    }
    
    foreach ($file in $matchingFiles) {
        Write-Host "  - 删除临时文件: $($file.Name)" -ForegroundColor Red
        Remove-Item $file.FullName -Force
        $removedCount++
    }
}

if ($removedCount -eq 0) {
    Write-Host "✅ 没有发现临时文件" -ForegroundColor Green
} else {
    Write-Host "📋 删除了 $removedCount 个临时文件" -ForegroundColor Yellow
}

# 3. 清理 __pycache__ 目录
$pycacheDirectories = Get-ChildItem -Path "." -Name "__pycache__" -Directory -Recurse
if ($pycacheDirectories) {
    Write-Host "📋 清理 Python 缓存目录..." -ForegroundColor Yellow
    foreach ($dir in $pycacheDirectories) {
        Remove-Item -Path $dir -Recurse -Force
        Write-Host "  - 删除: $dir" -ForegroundColor Red
    }
} else {
    Write-Host "✅ 没有发现 Python 缓存目录" -ForegroundColor Green
}

# 4. 检查 Git 状态
Write-Host "`n📊 当前 Git 状态:" -ForegroundColor Cyan
git status --porcelain | ForEach-Object {
    if ($_ -match "^\?\?") {
        Write-Host "  未跟踪: $($_.Substring(3))" -ForegroundColor Yellow
    } elseif ($_ -match "^M ") {
        Write-Host "  已修改: $($_.Substring(3))" -ForegroundColor Blue
    } elseif ($_ -match "^A ") {
        Write-Host "  新增加: $($_.Substring(3))" -ForegroundColor Green
    } elseif ($_ -match "^D ") {
        Write-Host "  已删除: $($_.Substring(3))" -ForegroundColor Red
    }
}

Write-Host "`n✨ 清理完成！" -ForegroundColor Green
Write-Host "💡 建议定期运行此脚本保持项目整洁" -ForegroundColor Cyan
