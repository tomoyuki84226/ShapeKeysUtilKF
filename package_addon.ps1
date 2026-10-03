$ErrorActionPreference = 'Stop'

$projectRoot = $PSScriptRoot
$packageName = 'ShapeKeysUtilKF'
$stageRoot = Join-Path $projectRoot 'build_package'
$addonRoot = Join-Path $stageRoot $packageName
$outputPath = Join-Path $projectRoot "$packageName-3.0.1.zip"

if (Test-Path -LiteralPath $stageRoot) {
    Remove-Item -LiteralPath $stageRoot -Recurse -Force
}

New-Item -ItemType Directory -Path $addonRoot | Out-Null
Copy-Item -LiteralPath (Join-Path $projectRoot '__init__.py') -Destination $addonRoot
Copy-Item -LiteralPath (Join-Path $projectRoot 'scripts') -Destination $addonRoot -Recurse
Copy-Item -LiteralPath (Join-Path $projectRoot 'LICENSE.md') -Destination $addonRoot
Copy-Item -LiteralPath (Join-Path $projectRoot 'README.md') -Destination $addonRoot
Copy-Item -LiteralPath (Join-Path $projectRoot 'README.ja.md') -Destination $addonRoot

Get-ChildItem -LiteralPath $addonRoot -Directory -Recurse -Filter '__pycache__' |
    Sort-Object FullName -Descending |
    Remove-Item -Recurse -Force

if (Test-Path -LiteralPath $outputPath) {
    Remove-Item -LiteralPath $outputPath -Force
}

Compress-Archive -LiteralPath $addonRoot -DestinationPath $outputPath -CompressionLevel Optimal
Remove-Item -LiteralPath $stageRoot -Recurse -Force

Write-Output $outputPath
