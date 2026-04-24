param(
  [int]$Port = 8000,
  [switch]$NoReload
)

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$python = Join-Path $scriptDir '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
  throw "Python virtual environment not found at $python. Create it before starting the API."
}

$lanIp = Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object {
    $_.IPAddress -ne '127.0.0.1' -and
    $_.IPAddress -notlike '169.254*' -and
    $_.InterfaceAlias -notmatch 'VMware|VirtualBox|Loopback|vEthernet|Hyper-V'
  } |
  Sort-Object InterfaceMetric |
  Select-Object -First 1 -ExpandProperty IPAddress

Write-Host "Starting Planify API on http://0.0.0.0:$Port" -ForegroundColor Cyan
if ($lanIp) {
  Write-Host "Use this URL on a real phone: http://${lanIp}:$Port" -ForegroundColor Green
}

$args = @(
  '-m',
  'uvicorn',
  'app.main:app',
  '--host',
  '0.0.0.0',
  '--port',
  "$Port"
)

if (-not $NoReload) {
  $args += '--reload'
}

& $python @args
