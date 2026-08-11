@echo off
chcp 65001 >nul
echo ================================================
echo   ETC客服QA — 一键开发环境搭建
echo ================================================
echo.

:: 检查Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未检测到Python，请先安装Python 3.10+
    echo   下载: https://www.anaconda.com/download
    pause
    exit /b 1
)

:: 检查Docker
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未检测到Docker，请先安装Docker Desktop
    echo   下载: https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)
echo ✓ Docker 已安装

:: 创建.env（如果不存在）
if not exist .env (
    if exist .env.template (
        echo 📋 从模板创建 .env 文件...
        copy .env.template .env >nul
        echo.
        echo ⚠️  请编辑 .env 填入你的 DEEPSEEK_API_KEY
        echo    路径: %CD%\.env
        echo.
        start notepad .env
        echo 填好Key后保存，然后重新运行本脚本
        pause
        exit /b 1
    ) else (
        echo ❌ 未找到 .env.template
        pause
        exit /b 1
    )
) else (
    echo ✓ .env 文件已存在
)

:: 安装Python依赖
echo.
echo === 安装Python依赖 ===
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo ❌ 依赖安装失败
    pause
    exit /b 1
)
echo ✓ 依赖安装完成

:: 安装modelscope（模型下载需要）
pip install modelscope -q 2>nul

:: 下载模型
echo.
echo === 下载模型 ===
echo 首次下载约5.6GB，已存在的模型会跳过
python scripts/setup/download_models.py
if %errorlevel% neq 0 (
    echo ⚠️  模型下载可能不完整，可稍后重试:
    echo   python scripts/setup/download_models.py
)

:: 启动MySQL容器
echo.
echo === 启动MySQL容器 ===
docker compose -f docker-compose.dev.yml up -d mysql
if %errorlevel% neq 0 (
    echo ❌ MySQL容器启动失败
    pause
    exit /b 1
)
echo 等待MySQL就绪...
timeout /t 15 /nobreak >nul

:: 初始化数据库
echo.
echo === 初始化数据库 ===
set ETC_QA_ENV=dev
python scripts/data/init_db.py dev
if %errorlevel% neq 0 (
    echo ❌ 数据库初始化失败
    pause
    exit /b 1
)

echo.
echo ================================================
echo   ✓ 开发环境搭建完成！
echo ================================================
echo.
echo 启动方式:
echo   Docker: docker compose -f docker-compose.dev.yml up etc-qa
echo   本地:   python main.py
echo.
echo API文档: http://localhost:8000/docs
echo.
pause