$ErrorActionPreference = "Stop"

Write-Host "SAD Windows preflight..."
python windows_doctor.py
if ($LASTEXITCODE -ne 0) {
    throw "SAD Windows preflight blocked startup."
}

Write-Host "Starting SAD Alpha on loopback..."
python alpha.py
