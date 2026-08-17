# run_all_env.ps1 —— 全量 UI 测试（V1.0 + V1.1）一键起停脚本
# 用法（在仓库根目录，同一轮内一次性执行）：
#   powershell -ExecutionPolicy Bypass -File test\ui\run_all_env.ps1

$ErrorActionPreference = 'Stop'
$Root = Resolve-Path (Join-Path $PSScriptRoot '..\..')

$BackendPort  = if ($env:TEST_BACKEND_PORT)  { [int]$env:TEST_BACKEND_PORT }  else { 8001 }
$FrontendPort = if ($env:TEST_FRONTEND_PORT) { [int]$env:TEST_FRONTEND_PORT } else { 5174 }
$BackendUrl   = "http://127.0.0.1:$BackendPort"
$FrontendUrl  = "http://localhost:$FrontendPort"

$python = Join-Path $Root 'server\.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = Join-Path $Root 'server\venv\Scripts\python.exe' }
if (-not (Test-Path $python)) { throw "未找到后端 venv：server\.venv 或 server\venv" }

$node   = (Get-Command node.exe -ErrorAction Stop).Source
$viteJs = Join-Path $Root 'web\node_modules\vite\bin\vite.js'
if (-not (Test-Path $viteJs)) { throw "未找到前端依赖：请先 cd web && npm install" }

$repDir = Join-Path $Root 'test\report'
New-Item -ItemType Directory -Force -Path $repDir | Out-Null

foreach ($p in @($BackendPort, $FrontendPort)) {
  $c = Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue
  if ($c) {
    $pids = ($c | Select-Object -ExpandProperty OwningProcess -Unique) -join ','
    throw "端口 $p 已被占用（PID: $pids），请先清理残留进程：Stop-Process -Id $pids -Force"
  }
}

function Wait-Http($url, $seconds) {
  $deadline = (Get-Date).AddSeconds($seconds)
  while ((Get-Date) -lt $deadline) {
    try {
      Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3 | Out-Null
      return $true
    } catch {
      if ($_.Exception.Response) { return $true }
      Start-Sleep -Seconds 2
    }
  }
  return $false
}

$be = $null
$fe = $null
$code = 1
try {
  $env:USE_SQLITE = 'True'
  $be = Start-Process -FilePath $python `
    -ArgumentList 'manage.py','runserver',"127.0.0.1:$BackendPort",'--noreload' `
    -WorkingDirectory (Join-Path $Root 'server') `
    -RedirectStandardOutput (Join-Path $repDir 'backend.log') `
    -RedirectStandardError  (Join-Path $repDir 'backend.err.log') `
    -PassThru -WindowStyle Hidden

  $env:VITE_PORT       = "$FrontendPort"
  $env:VITE_API_TARGET = $BackendUrl
  $fe = Start-Process -FilePath $node -ArgumentList $viteJs `
    -WorkingDirectory (Join-Path $Root 'web') `
    -RedirectStandardOutput (Join-Path $repDir 'frontend.log') `
    -RedirectStandardError  (Join-Path $repDir 'frontend.err.log') `
    -PassThru -WindowStyle Hidden

  if (-not (Wait-Http $BackendUrl 90)) { throw "后端未就绪，见 test\report\backend.err.log" }
  if (-not (Wait-Http $FrontendUrl 90)) { throw "前端未就绪，见 test\report\frontend.err.log" }

  $env:UI_BASE_URL = $FrontendUrl
  & $python (Join-Path $Root 'test\ui\run_all_tests.py')
  $code = $LASTEXITCODE
}
finally {
  if ($be) { Stop-Process -Id $be.Id -Force -ErrorAction SilentlyContinue }
  if ($fe) { Stop-Process -Id $fe.Id -Force -ErrorAction SilentlyContinue }
}
exit $code
