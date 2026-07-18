<#
  sign_windows_local.ps1
  Sign AutoMacro.exe with a self-signed certificate and trust it on THIS PC,
  so Windows SmartScreen stops warning that the publisher is unknown.

  SCOPE / HONESTY:
    * This removes the SmartScreen "unknown publisher" prompt on the machine
      where you run it.
    * It does NOT satisfy Smart App Control (SAC). SAC only trusts
      certificates Microsoft already knows, so a self-signed certificate will
      not clear it. If SAC is ON and blocking the app, either turn Smart App
      Control off (Windows Security -> App & browser control -> Smart App
      Control), or sign the build with a purchased code-signing certificate.

  USAGE (run in an ELEVATED PowerShell -- "Run as administrator"):
    powershell -ExecutionPolicy Bypass -File sign_windows_local.ps1 `
        -ExePath "C:\path\to\AutoMacro\AutoMacro.exe"
#>
param(
    [string]$ExePath = "dist\AutoMacro\AutoMacro.exe"
)

if (-not (Test-Path $ExePath)) {
    Write-Error "Executable not found: $ExePath"
    exit 1
}

Write-Host "Creating a self-signed code-signing certificate..."
$cert = New-SelfSignedCertificate `
    -Type CodeSigningCert `
    -Subject "CN=AutoMacro (self-signed)" `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -KeyUsage DigitalSignature `
    -FriendlyName "AutoMacro self-signed"

# Trust the certificate on this machine (requires administrator).
$tmp = Join-Path $env:TEMP "automacro-cert.cer"
Export-Certificate -Cert $cert -FilePath $tmp | Out-Null
Write-Host "Trusting the certificate (Trusted Root + Trusted Publishers)..."
try {
    Import-Certificate -FilePath $tmp -CertStoreLocation "Cert:\LocalMachine\Root" | Out-Null
    Import-Certificate -FilePath $tmp -CertStoreLocation "Cert:\LocalMachine\TrustedPublisher" | Out-Null
} catch {
    Write-Warning "Could not add to LocalMachine stores. Re-run this script as administrator."
    Remove-Item $tmp -ErrorAction SilentlyContinue
    exit 1
}
Remove-Item $tmp -ErrorAction SilentlyContinue

Write-Host "Signing $ExePath ..."
Set-AuthenticodeSignature -FilePath $ExePath -Certificate $cert `
    -TimestampServer "http://timestamp.digicert.com" | Format-List

Write-Host ""
Write-Host "Done. Launch AutoMacro.exe -- SmartScreen should no longer warn on this PC."
Write-Host "If Smart App Control is enforcing, see the note at the top of this script."
