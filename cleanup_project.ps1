# 项目清理脚本
# 用于清理Python缓存文件、日志文件和临时文件

Write-Host "🧹 开始清理项目..." -ForegroundColor Green

$projectRoot = $PSScriptRoot
if (-not $projectRoot) {
    $projectRoot = "d:\ChatDify_Codes\DifyChatBackend"
}

Write-Host "📂 项目根目录: $projectRoot" -ForegroundColor Cyan

# 1. 清理Python缓存文件
Write-Host "🔄 清理Python缓存文件..." -ForegroundColor Yellow
$pycacheDirectories = Get-ChildItem -Path $projectRoot -Name "__pycache__" -Recurse -Directory | Where-Object { 
    $fullPath = Join-Path $projectRoot $_
    $fullPath -notlike "*\.venv\*" -and $fullPath -notlike "*\site-packages\*"
}

foreach ($dir in $pycacheDirectories) {
    $fullPath = Join-Path $projectRoot $dir
    Write-Host "  📁 删除: $fullPath" -ForegroundColor Gray
    Remove-Item -Path $fullPath -Recurse -Force -ErrorAction SilentlyContinue
}

# 2. 清理.pyc文件
Write-Host "🔄 清理.pyc文件..." -ForegroundColor Yellow
$pycFiles = Get-ChildItem -Path $projectRoot -Filter "*.pyc" -Recurse | Where-Object {
    $_.Directory.FullName -notlike "*\.venv\*" -and $_.Directory.FullName -notlike "*\site-packages\*"
}

foreach ($file in $pycFiles) {
    Write-Host "  📄 删除: $($file.FullName)" -ForegroundColor Gray
    Remove-Item -Path $file.FullName -Force -ErrorAction SilentlyContinue
}

# 3. 清理日志文件（保留空文件）
Write-Host "🔄 清理日志文件..." -ForegroundColor Yellow
$logFiles = Get-ChildItem -Path "$projectRoot\logs" -Filter "*.log" -ErrorAction SilentlyContinue

foreach ($logFile in $logFiles) {
    $size = [math]::Round($logFile.Length / 1KB, 2)
    if ($size -gt 100) {  # 如果日志文件大于100KB则清空
        Write-Host "  📝 清空日志文件: $($logFile.Name) (${size}KB)" -ForegroundColor Gray
        Clear-Content -Path $logFile.FullName -ErrorAction SilentlyContinue
    }
}

# 4. 清理临时文件
Write-Host "🔄 清理临时文件..." -ForegroundColor Yellow
$tempPatterns = @("*.tmp", "*.temp", "*.bak", "*.backup", "*.old", "*.orig", "*~")

foreach ($pattern in $tempPatterns) {
    $tempFiles = Get-ChildItem -Path $projectRoot -Filter $pattern -Recurse | Where-Object {
        $_.Directory.FullName -notlike "*\.venv\*" -and $_.Directory.FullName -notlike "*\site-packages\*"
    }
    
    foreach ($file in $tempFiles) {
        Write-Host "  🗑️ 删除临时文件: $($file.FullName)" -ForegroundColor Gray
        Remove-Item -Path $file.FullName -Force -ErrorAction SilentlyContinue
    }
}

# 5. 清理系统文件
Write-Host "🔄 清理系统文件..." -ForegroundColor Yellow
$systemFiles = @(".DS_Store", "Thumbs.db", "Desktop.ini")

foreach ($sysFile in $systemFiles) {
    $files = Get-ChildItem -Path $projectRoot -Name $sysFile -Recurse -Force | Where-Object {
        $fullPath = Join-Path $projectRoot $_
        $fullPath -notlike "*\.venv\*"
    }
    
    foreach ($file in $files) {
        $fullPath = Join-Path $projectRoot $file
        Write-Host "  🖥️ 删除系统文件: $fullPath" -ForegroundColor Gray
        Remove-Item -Path $fullPath -Force -ErrorAction SilentlyContinue
    }
}

# 6. 统计清理结果
Write-Host "`n📊 清理统计:" -ForegroundColor Green

$remainingPycache = Get-ChildItem -Path $projectRoot -Name "__pycache__" -Recurse -Directory | Where-Object { 
    $fullPath = Join-Path $projectRoot $_
    $fullPath -notlike "*\.venv\*"
} | Measure-Object

$remainingPyc = Get-ChildItem -Path $projectRoot -Filter "*.pyc" -Recurse | Where-Object {
    $_.Directory.FullName -notlike "*\.venv\*"
} | Measure-Object

Write-Host "  📁 剩余__pycache__目录: $($remainingPycache.Count)" -ForegroundColor Cyan
Write-Host "  📄 剩余*.pyc文件: $($remainingPyc.Count)" -ForegroundColor Cyan

# 7. 检查日志文件大小
if (Test-Path "$projectRoot\logs") {
    $logFiles = Get-ChildItem -Path "$projectRoot\logs" -Filter "*.log" -ErrorAction SilentlyContinue
    foreach ($logFile in $logFiles) {
        $size = [math]::Round($logFile.Length / 1KB, 2)
        Write-Host "  📝 日志文件 $($logFile.Name): ${size}KB" -ForegroundColor Cyan
    }
}

Write-Host "`n✅ 项目清理完成!" -ForegroundColor Green
Write-Host "💡 提示: 可以将此脚本添加到开发工作流中定期运行" -ForegroundColor Cyan
