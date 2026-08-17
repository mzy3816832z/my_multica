# run_env.ps1 —— UI 自动化测试环境一键起停脚本
# 作用：后台起后端(SQLite) + 前端(Vite) -> 就绪探测 -> 前台阻塞跑测试 -> 收尾杀进程
# 用法（在仓库根目录，同一轮内一次性执行）：
#   powershell -ExecutionPolicy Bypass -File test\ui\run_env.ps1
#
# 前置（一次性，请单独执行，不要在前台阻塞本脚本）：
#   1. 后端依赖已装：server\.venv 或 server\venv
#   2. 前端依赖已装：web\node_modules
#   3. USE_SQLITE=True 下已完成 migrate + 执行 seed_data\seed_script.py

$ErrorActionPreference = 'Stop'
$Root = Resolve-Path (Join-Path $PSScriptRoot '..\..')

# 端口默认值刻意避开常见的本地开发环境(8000/5173)，避免和手动起的服务撞端口
$BackendPort  = if ($env:TEST_BACKEND_PORT)  { [int]$env:TEST_BACKEND_PORT }  else { 8001 }
$FrontendPort = if ($env:TEST_FRONTEND_PORT) { [int]$env:TEST_FRONTEND_PORT } else { 5174 }
$BackendUrl   = "http://127.0.0.1:$BackendPort"
$FrontendUrl  = "http://localhost:$FrontendPort"

# 自动探测后端 venv（.venv 优先，其次 venv）
$python = Join-Path $Root 'server\.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = Join-Path $Root 'server\venv\Scripts\python.exe' }
if (-not (Test-Path $python)) { throw "未找到后端 venv：server\.venv 或 server\venv" }

$node   = (Get-Command node.exe -ErrorAction Stop).Source
$viteJs = Join-Path $Root 'web\node_modules\vite\bin\vite.js'
if (-not (Test-Path $viteJs)) { throw "未找到前端依赖：请先 cd web && npm install" }

$repDir = Join-Path $Root 'test\report'
New-Item -ItemType Directory -Force -Path $repDir | Out-Null

# 1) 端口预检：被占就报错退出，绝不让残留进程干扰
foreach ($p in @($BackendPort, $FrontendPort)) {
  if (Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue) {
    throw "端口 $p 已被占用，请先清理残留的 runserver/vite 进程"
  }
}

# 2) 后台起后端（--noreload 单进程；USE_SQLITE 走 server\db.sqlite3）
$env:USE_SQLITE = 'True'
$be = Start-Process -FilePath $python `
  -ArgumentList 'manage.py','runserver',"127.0.0.1:$BackendPort",'--noreload' `
  -WorkingDirectory (Join-Path $Root 'server') `
  -RedirectStandardOutput (Join-Path $repDir 'backend.log') `
  -RedirectStandardError  (Join-Path $repDir 'backend.err.log') `
  -PassThru -WindowStyle Hidden

# 3) 后台起前端（/api 与 /uploads 代理指向后端端口）
$env:VITE_PORT       = "$FrontendPort"
$env:VITE_API_TARGET = $BackendUrl
$fe = Start-Process -FilePath $node -ArgumentList $viteJs `
  -WorkingDirectory (Join-Path $Root 'web') `
  -RedirectStandardOutput (Join-Path $repDir 'frontend.log') `
  -RedirectStandardError  (Join-Path $repDir 'frontend.err.log') `
  -PassThru -WindowStyle Hidden

# 4) 前台就绪探测（带超时，不空等）
function Wait-Http($url, $seconds) {
  $deadline = (Get-Date).AddSeconds($seconds)
  while ((Get-Date) -lt $deadline) {
    try { Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3 | Out-Null; return $true }
    catch { Start-Sleep -Seconds 2 }
  }
  return $false
}
if (-not (Wait-Http $BackendUrl 90)) { throw "后端未就绪，见 test\report\backend.err.log" }
if (-not (Wait-Http $FrontendUrl 90)) { throw "前端未就绪，见 test\report\frontend.err.log" }

# 5) 前台阻塞跑测试（一次性拿全量结果，约 4~6 分钟）
$env:UI_BASE_URL = $FrontendUrl
& $python (Join-Path $Root 'test\ui\run_ui_tests.py')
$code = $LASTEXITCODE

# 6) 收尾：杀掉两个服务
Stop-Process -Id $be.Id -Force -ErrorAction SilentlyContinue
Stop-Process -Id $fe.Id -Force -ErrorAction SilentlyContinue
exit $code
