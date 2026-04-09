@echo off
chcp 65001 >nul 2>&1
echo ============================================================
echo   🎮 抖音数据采集+同步+部署 一键脚本
echo ============================================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo [1/3] 📡 开始采集数据...
python scrape_douyin.py
if %errorlevel% neq 0 (
    echo ❌ 采集失败，终止
    pause
    exit /b 1
)
echo.
echo [2/3] 🔗 同步数据到HTML...
python sync_to_html.py
if %errorlevel% neq 0 (
    echo ❌ 同步失败
    pause
    exit /b 1
)
echo.
echo [3/3] 📤 推送到GitHub...
if exist ".git" (
    git add douyin-analytics.html scrape_results.json
    git commit -m "🤖 自动更新数据 (%date:~0,4%-%date:~5,2%-%date:~8,2%)"
    git push
    if %errorlevel% eq 0 (
        echo ✅ GitHub推送成功!
    ) else (
        echo ⚠️ GitHub推送失败，请检查git配置
    )
) else (
    echo ⚠️ 未找到Git仓库，跳过部署
    echo    运行: python setup_github.py 初始化Git仓库
)

echo.
echo ============================================================
echo   ✅ 全部完成！
echo   数据已更新: douyin-analytics.html
echo ============================================================
pause
