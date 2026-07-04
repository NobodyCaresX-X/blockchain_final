@echo off
chcp 65001 >nul
title 区块链众筹系统 - 一键测试启动器
cls

echo.
echo ╔══════════════════════════════════════════════════════════════════════════╗
echo ║                          区块链众筹系统                                  ║
echo ║                        【一键测试启动器】                                 ║
echo ╚══════════════════════════════════════════════════════════════════════════╝
echo.
echo 正在启动测试环境，请稍候...
echo.

cd /d "%~dp0"

echo [1/5] 检查环境...

where conda >nul 2>&1
if %errorlevel% neq 0 (
    echo   ✗ Conda 未安装或未添加到 PATH
    echo   请安装 Miniconda 并配置环境变量
    pause
    exit /b 1
)

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo   ✗ Node.js 未安装或未添加到 PATH
    echo   请安装 Node.js (推荐 LTS 版本)
    pause
    exit /b 1
)

where npx >nul 2>&1
if %errorlevel% neq 0 (
    echo   ✗ npx 未找到，请确保 Node.js 正确安装
    pause
    exit /b 1
)

echo   ✓ 环境检查通过

echo.
echo [2/5] 启动 Hardhat 本地区块链...

tasklist /FI "IMAGENAME eq node.exe" /NH | findstr /I "hardhat" >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✗ 检测到 Hardhat 已在运行，正在关闭...
    taskkill /F /IM "node.exe" >nul 2>&1
    timeout /t 2 /nobreak >nul
)

start "Hardhat 节点" /D "%~dp0hardhat" cmd /c "node node_modules/hardhat/bin/hardhat.js node"

echo   ✓ Hardhat 节点已启动
echo   等待节点就绪...
timeout /t 5 /nobreak >nul

echo.
echo [3/5] 编译并部署智能合约...

cd hardhat

if not exist "node_modules" (
    echo   正在安装依赖...
    npm install
)

npx hardhat compile >nul 2>&1
if %errorlevel% neq 0 (
    echo   ✗ 合约编译失败
    pause
    exit /b 1
)

npx hardhat run scripts/deploy.js --network localhost >nul 2>&1
if %errorlevel% neq 0 (
    echo   ✗ 合约部署失败
    pause
    exit /b 1
)

echo   ✓ 合约编译部署成功

cd ..

echo.
echo [4/5] 启动后端服务...

start "后端服务" cmd /c "conda activate ai_env && python start_external_chain_mode.py"

echo   ✓ 后端服务已启动
echo   等待服务就绪...
timeout /t 8 /nobreak >nul

echo.
echo [5/5] 打开浏览器...

start http://127.0.0.1:8000

echo.
echo ╔══════════════════════════════════════════════════════════════════════════╗
echo ║                          启动完成！                                      ║
echo ║                                                                          ║
echo ║   访问地址: http://127.0.0.1:8000                                        ║
echo ║                                                                          ║
echo ║   使用 Metamask 连接:                                                    ║
echo ║     - 网络名称: Hardhat Local                                            ║
echo ║     - RPC URL: http://127.0.0.1:8545                                     ║
echo ║     - 链 ID: 31337                                                      ║
echo ║     - 货币符号: ETH                                                      ║
echo ║                                                                          ║
echo ║   测试账户私钥 (第一个):                                                  ║
echo ║     0xac0974bec39a17e36ba4a6b4d238ff948bacb478cbed5efcae784d7bf4f2ff80  ║
echo ║                                                                          ║
echo ║   按任意键关闭此窗口...                                                   ║
echo ╚══════════════════════════════════════════════════════════════════════════╝
echo.

pause >nul