param(
    [Parameter(Mandatory=$true)][string]$Map,
    [Parameter(Mandatory=$true)][string]$Template,
    [string]$FillFrom,
    [string]$Out,
    [string]$PythonPath,
    [switch]$FFERPGVisuals
)
$ErrorActionPreference = 'Stop'
if (-not $PythonPath) {
    if (Get-Command python -ErrorAction SilentlyContinue) { $PythonPath = 'python' }
    elseif (Get-Command py -ErrorAction SilentlyContinue) { $PythonPath = 'py' }
    else { throw 'Python 3 is required. Install it on PATH or supply -PythonPath.' }
}
$Map = (Resolve-Path -LiteralPath $Map).Path
$Template = (Resolve-Path -LiteralPath $Template).Path
if (-not $Out) { $Out = Join-Path (Split-Path -Parent $Map) ('1.29.2\' + [IO.Path]::GetFileName($Map)) }
if ((Test-Path -LiteralPath $Out) -or (Test-Path -LiteralPath ($Out + '.tmp'))) { throw "Output already exists: $Out" }
New-Item -ItemType Directory -Force -Path (Split-Path -Parent ([IO.Path]::GetFullPath($Out))) | Out-Null
$conversionArgs = @((Join-Path $PSScriptRoot 'tools\downgrade.py'), $Map, $Out,
    '--w3i-template', $Template, '--name', [IO.Path]::GetFileNameWithoutExtension($Map))
if ($FillFrom) { $conversionArgs += @('--fill-from', (Resolve-Path -LiteralPath $FillFrom).Path) }
if ($FFERPGVisuals) { $conversionArgs += '--fferpg-visuals' }
& $PythonPath @conversionArgs
exit $LASTEXITCODE
