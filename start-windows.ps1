param([int]$Port = 8000, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$arguments = @('--port', "$Port")
if ($NoBrowser) { $arguments += '--no-browser' }
& "$PSScriptRoot\start-windows.bat" @arguments
exit $LASTEXITCODE
