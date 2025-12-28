# PowerShell script to serve the Farnsworth Fusor Web Interface locally
# Run from project root: .\start-web-interface.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Farnsworth Fusor Web Interface" -ForegroundColor Cyan
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

Write-Host ""

# Check if port 8080 is available
Write-Host "Checking if port 8080 is available..." -ForegroundColor Cyan
$portInUse = Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "WARNING: Port 8080 is already in use!" -ForegroundColor Red
    Write-Host "Another instance may be running, or another application is using this port." -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -ne "y" -and $continue -ne "Y") {
        exit 1
    }
}
else {
    Write-Host "Port 8080 is available" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Web Interface Server..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Web Interface will be available at: http://localhost:8080" -ForegroundColor Green
Write-Host ""
Write-Host "IMPORTANT: Make sure the API server is running!" -ForegroundColor Yellow
Write-Host "Start it in another terminal with: .\start-api-server.ps1" -ForegroundColor Yellow
Write-Host ""
Write-Host "The web interface will automatically connect to:" -ForegroundColor Cyan
Write-Host "  API Server: http://localhost:5000/api" -ForegroundColor Cyan
Write-Host ""
Write-Host "Opening browser in 3 seconds..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Wait a moment, then open browser
Start-Sleep -Seconds 3
Start-Process "http://localhost:8080"

# Change to website directory
Set-Location website

# Start Python HTTP server
try {
    python -m http.server 8080
}
catch {
    Write-Host ""
    Write-Host "ERROR: Failed to start web server" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "1. Check if port 8080 is available" -ForegroundColor Yellow
    Write-Host "2. Verify Python version: python --version (needs 3.7+)" -ForegroundColor Yellow
    Write-Host "3. Ensure you're in the project root directory" -ForegroundColor Yellow
    exit 1
}
finally {
    # Return to original directory
    Set-Location ..
}

