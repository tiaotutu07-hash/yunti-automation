$env:HTTP_PROXY="http://127.0.0.1:7890"
$env:HTTPS_PROXY="http://127.0.0.1:7890"

Write-Host "Proxy enabled: http://127.0.0.1:7890"

.\.venv\Scripts\Activate.ps1

Write-Host "Virtual environment activated."