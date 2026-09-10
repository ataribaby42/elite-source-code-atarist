$ErrorActionPreference = 'Stop'
$eliteVendor = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\vendor'))
$eliteWork = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\build\toolchain'))
$eliteTools = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\tools'))
$eliteManifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'toolchain.json') -Raw | ConvertFrom-Json
New-Item -ItemType Directory -Path $eliteVendor -Force | Out-Null
New-Item -ItemType Directory -Path $eliteWork -Force | Out-Null
foreach ($eliteName in @('vasm', 'vlink')) {
    $eliteArchive = Join-Path $eliteVendor "$eliteName.tar.gz"
    $eliteSpec = $eliteManifest.$eliteName
    if (-not (Test-Path -LiteralPath $eliteArchive)) {
        Invoke-WebRequest -Uri $eliteSpec.url -OutFile $eliteArchive -UseBasicParsing
    }
    $eliteHash = (Get-FileHash -LiteralPath $eliteArchive -Algorithm SHA256).Hash
    if ($eliteHash -ne $eliteSpec.sha256) {
        throw "Archive hash mismatch: $eliteArchive. Upstream may have changed; review the version before updating toolchain.json."
    }
    if (-not (Test-Path -LiteralPath (Join-Path $eliteWork "$eliteName\make.rules"))) {
        & tar.exe -xzf $eliteArchive -C $eliteWork
        if ($LASTEXITCODE -ne 0) { throw "Cannot extract $eliteArchive" }
    }
    & (Join-Path $PSScriptRoot "build-$eliteName.cmd")
    if ($LASTEXITCODE -ne 0) { throw "Cannot build $eliteName" }
}
New-Item -ItemType Directory -Path $eliteTools -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $eliteWork 'vasm\vasmm68k_mot.exe') -Destination (Join-Path $eliteTools 'vasmm68k_mot.exe') -Force
Copy-Item -LiteralPath (Join-Path $eliteWork 'vlink\vlink.exe') -Destination (Join-Path $eliteTools 'vlink.exe') -Force
Write-Output "Native Windows vasm and vlink are ready in $eliteTools."
