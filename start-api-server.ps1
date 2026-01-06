# PowerShell script to start the Farnsworth Fusor API Server locally
# Run from project root: .\start-api-server.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Farnsworth Fusor API Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.7 or higher" -ForegroundColor Yellow
    exit 1
}

# Check if virtual environment exists
$venvPath = "venv"
$venvScripts = "venv\Scripts\Activate.ps1"

if (Test-Path $venvScripts) {
    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    & $venvScripts
    Write-Host "Virtual environment activated" -ForegroundColor Green
}
else {
    Write-Host "No virtual environment found - using system Python" -ForegroundColor Yellow
    Write-Host "Tip: Create a venv with: python -m venv venv" -ForegroundColor Yellow
}

Write-Host ""

# Check if required packages are installed
Write-Host "Checking dependencies..." -ForegroundColor Cyan
try {
    python -c "import flask" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARNING: Flask not found. Installing dependencies..." -ForegroundColor Yellow
        Write-Host "This may take a moment..." -ForegroundColor Yellow
        pip install -r requirements.txt
    }
    else {
        Write-Host "Dependencies OK" -ForegroundColor Green
    }
}
catch {
    Write-Host "WARNING: Could not verify dependencies" -ForegroundColor Yellow
}

Write-Host ""

# Check if port 5000 is available
Write-Host "Checking if port 5000 is available..." -ForegroundColor Cyan
$portInUse = Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "WARNING: Port 5000 is already in use!" -ForegroundColor Red
    Write-Host "Another instance may be running, or another application is using this port." -ForegroundColor Yellow
    Write-Host "Press Ctrl+C to exit, or close the other application." -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -ne "y" -and $continue -ne "Y") {
        exit 1
    }
}
else {
    Write-Host "Port 5000 is available" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting API Server..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "API Server will be available at: http://localhost:5000" -ForegroundColor Green
Write-Host "API Endpoints: http://localhost:5000/api/*" -ForegroundColor Green
Write-Host ""
Write-Host "Target Raspberry Pi: 192.168.0.2" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Change to the Host_Codebase directory
Set-Location src\Host_Codebase

# Start the API server
try {
    python web_api_server.py --host 0.0.0.0 --port 5000 --debug
}
catch {
    Write-Host ""
    Write-Host "ERROR: Failed to start API server" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "1. Ensure all dependencies are installed: pip install -r requirements.txt" -ForegroundColor Yellow
    Write-Host "2. Check if port 5000 is available" -ForegroundColor Yellow
    Write-Host "3. Verify Python version: python --version (needs 3.7+)" -ForegroundColor Yellow
    exit 1
}
finally {
    # Return to original directory
    Set-Location ..\..
}

