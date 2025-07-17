# PowerShell 脚本：激活虚拟环境并运行测试
# 用法: .\activate_and_test.ps1

Write-Host "🚀 DifyChatBackend 登录接口重构测试" -ForegroundColor Green
Write-Host "=" * 60

# 检查虚拟环境
if (Test-Path ".venv") {
    Write-Host "✅ 找到虚拟环境" -ForegroundColor Green
} else {
    Write-Host "⚠️  虚拟环境不存在，正在创建..." -ForegroundColor Yellow
    python -m venv .venv
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ 虚拟环境创建成功" -ForegroundColor Green
    } else {
        Write-Host "❌ 虚拟环境创建失败" -ForegroundColor Red
        exit 1
    }
}

# 激活虚拟环境
Write-Host "🔧 激活虚拟环境..." -ForegroundColor Cyan
& ".\.venv\Scripts\Activate.ps1"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 虚拟环境激活成功" -ForegroundColor Green
} else {
    Write-Host "❌ 虚拟环境激活失败，使用系统Python" -ForegroundColor Yellow
}

# 升级pip
Write-Host "📦 升级pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

# 安装依赖
if (Test-Path "requirements.txt") {
    Write-Host "📦 安装项目依赖..." -ForegroundColor Cyan
    python -m pip install -r requirements.txt
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ 依赖安装完成" -ForegroundColor Green
    } else {
        Write-Host "⚠️  依赖安装失败，但继续测试" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  requirements.txt不存在，跳过依赖安装" -ForegroundColor Yellow
}

# 运行快速检查
Write-Host "`n🔍 运行快速检查..." -ForegroundColor Cyan
python quick_check.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 快速检查通过" -ForegroundColor Green
    
    # 询问是否运行完整测试
    $runFullTest = Read-Host "`n🧪 是否运行完整测试? (y/N)"
    
    if ($runFullTest -eq "y" -or $runFullTest -eq "Y") {
        Write-Host "`n🚀 运行完整测试..." -ForegroundColor Cyan
        python run_login_test.py
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n🎉 完整测试通过!" -ForegroundColor Green
        } else {
            Write-Host "`n❌ 完整测试失败" -ForegroundColor Red
        }
    } else {
        Write-Host "`n💡 提示:" -ForegroundColor Cyan
        Write-Host "   - 运行完整测试: python run_login_test.py"
        Write-Host "   - 启动服务器: python app.py"
        Write-Host "   - 手动测试API: python test_login_api.py"
        Write-Host "   - 功能演示: python demo_login_api.py"
    }
} else {
    Write-Host "❌ 快速检查失败，请先修复问题" -ForegroundColor Red
}

Write-Host "`n=" * 60
Write-Host "✨ 任务2.2 登录接口重构验证完成" -ForegroundColor Green
