$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $Python)) {
    $Python = Join-Path (Split-Path -Parent $ProjectRoot) '.venvs\planlayercreator-hermes\Scripts\python.exe'
}
if (!(Test-Path -LiteralPath $Python)) { throw "缺少构建环境：$Python。请参阅 README.md。" }
$env:PYTHONIOENCODING = 'utf-8'
Push-Location (Join-Path $ProjectRoot 'src')
try {
    $env:QT_QPA_PLATFORM = 'offscreen'
    & $Python -B -O main.py --self-test (Join-Path $ProjectRoot ('process_test\self_test_' + (Get-Date -Format 'yyyyMMdd_HHmmss')))
    if ($LASTEXITCODE -ne 0) { throw "执行失败，退出码：$LASTEXITCODE" }
} finally { Pop-Location }
