[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$Python,
    [string]$Vasm,
    [string]$Vlink,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$BuildOptions
)
$ErrorActionPreference = 'Stop'
$elitePythonOptions = @()
if (-not $Python) {
    $eliteCommand = Get-Command python, python3 -CommandType Application -ErrorAction SilentlyContinue |
        Where-Object { $_.Source -notlike '*WindowsApps*' } | Select-Object -First 1
    if ($eliteCommand) {
        $Python = $eliteCommand.Source
    } else {
        $eliteLauncher = Get-Command py -CommandType Application -ErrorAction SilentlyContinue
        if ($eliteLauncher) {
            $Python = $eliteLauncher.Source
            $elitePythonOptions = @('-3')
        } else {
            $eliteInstallRoot = Join-Path $env:LOCALAPPDATA 'Programs\Python'
            $Python = Get-ChildItem -LiteralPath $eliteInstallRoot -Directory -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -match '^Python3\d+$' } |
                Sort-Object { [int]($_.Name -replace '^Python', '') } -Descending |
                ForEach-Object { Join-Path $_.FullName 'python.exe' } |
                Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
        }
    }
}
if (-not $Python) { throw 'Python 3.10+ is required. Run build_orig.bat -Python C:\path\python.exe.' }
$eliteArguments = $elitePythonOptions + @("$PSScriptRoot\build.py")
if ($Vasm) { $eliteArguments += @('--vasm', $Vasm) }
if ($Vlink) { $eliteArguments += @('--vlink', $Vlink) }
$eliteArguments += $BuildOptions
& $Python @eliteArguments
exit $LASTEXITCODE
