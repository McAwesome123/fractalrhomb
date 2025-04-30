Push-Location $PSScriptRoot
& ".venv\Scripts\Activate.ps1"

Write-Host "Starting bot"

try {
	python "fractalrhomb.py" @args
}
finally {
	deactivate
	Pop-Location
}
