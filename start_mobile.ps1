param(
    [Parameter(Mandatory=$true)][string]$BindAddress,
    [Parameter(Mandatory=$true)][string]$Certificate,
    [Parameter(Mandatory=$true)][string]$PrivateKey,
    [int]$Port = 8766
)

$ErrorActionPreference = "Stop"
$env:SAD_MOBILE_HOST = $BindAddress
$env:SAD_MOBILE_CERT = $Certificate
$env:SAD_MOBILE_KEY = $PrivateKey
$env:SAD_MOBILE_PORT = "$Port"

python mobile_doctor.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Mobile preflight blocked startup. Fix the failed checks above."
    exit $LASTEXITCODE
}

python mobile.py
