param([int]$Figure)
$ErrorActionPreference='Stop'
$file=Join-Path $PSScriptRoot ("case{0}.json" -f $Figure)
$spec=Get-Content -LiteralPath $file -Encoding utf8 -Raw|ConvertFrom-Json
$tmpl=(Get-Content -LiteralPath 'D:/ER219_code/arcmap_hi_20261106/context_fig1.json' -Encoding utf8 -Raw|ConvertFrom-Json).input_template
$native='D:/ER219_code/arcmap_hi_20261106/run_native.ps1'
$ps86='C:/Windows/SysWOW64/WindowsPowerShell/v1.0/powershell.exe'
& $ps86 -NoProfile -File $native -InputMxd $tmpl -OutputMxd $spec.output_mxd -Config $file
if($LASTEXITCODE -ne 0){throw 'ArcObjects map construction failed'}
& $ps86 -NoProfile -File $native -InputMxd $spec.output_mxd -Config $file -ExportOnly
if($LASTEXITCODE -ne 0){throw 'ArcObjects native export failed'}
foreach ($ext in 'png','pdf'){
 Copy-Item -LiteralPath ($spec.export_stem+'.'+$ext) -Destination ([IO.Path]::ChangeExtension($spec.output_mxd,$ext)) -Force
}
