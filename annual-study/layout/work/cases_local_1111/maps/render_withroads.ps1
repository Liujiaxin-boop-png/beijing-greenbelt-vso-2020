param([int]$Figure)
$ErrorActionPreference='Stop'
$cfg=Join-Path $PSScriptRoot ("withroads{0}.json" -f $Figure)
$spec=Get-Content -LiteralPath $cfg -Encoding utf8 -Raw|ConvertFrom-Json
$tmpl=(Get-Content -LiteralPath 'D:/ER219_code/arcmap_hi_20261106/context_fig1.json' -Encoding utf8 -Raw|ConvertFrom-Json).input_template
$native=Join-Path $PSScriptRoot 'withroads/run_native.ps1'
$ps86='C:/Windows/SysWOW64/WindowsPowerShell/v1.0/powershell.exe'
& $ps86 -NoProfile -File $native -InputMxd $tmpl -OutputMxd $spec.output_mxd -Config $cfg
if($LASTEXITCODE -ne 0){throw 'build failed'}
& $ps86 -NoProfile -File $native -InputMxd $spec.output_mxd -Config $cfg -ExportOnly
if($LASTEXITCODE -ne 0){throw 'export failed'}
