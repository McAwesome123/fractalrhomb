Push-Location $PSScriptRoot

Write-Host "Creating venv"
python -m venv .venv

Write-Host "Activating venv"
& ".venv\Scripts\Activate.ps1"

Write-Host "Installing requirements"
python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host "Creating .env"
if (Test-Path ".env") {
	if (Test-Path ".env.bak") {
		Move-Item -Confirm -Force ".env" ".env.bak"
	}
	else {
		Move-Item ".env" ".env.bak"
	}
}

Write-Output 'FRACTALTHORNS_USER_AGENT="fractalrhomb/{VERSION_SHORT}"' > ".env"
Write-Output 'DISCORD_BOT_TOKEN="Replace me!"' >> ".env"
Write-Output 'BOT_ADMIN_USERS=[]' >> ".env"

deactivate
Pop-Location

Write-Host "Setup complete"
Write-Host "Add a bot token to .env and use start_bot.ps1 to run"
