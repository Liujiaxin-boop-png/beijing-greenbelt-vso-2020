param([ValidateSet('All','D','A','B','C','Map')][string]$Task='All',[switch]$Maps,[string]$Observations='',[string]$Panel='',[string]$Dest='D:\ER_StagePractice',[string]$Archive='D:\ER219_results\年度评价_2015_2025_原始GIS边界',[string]$Python='C:/ER219_user\AppData\Local\Programs\Python\Python312\python.exe')
$ErrorActionPreference='Stop'
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)){throw "找不到 Python 3.12：$Python"}
$cmdArgs=@((Join-Path $PSScriptRoot '隔离复算.py'),'--task',$Task,'--dest',$Dest,'--archive',$Archive)
if($Observations){$cmdArgs+=@('--observations',$Observations)}
if($Panel){$cmdArgs+=@('--panel',$Panel)}
if($Maps){$cmdArgs+='--maps'}
& $Python @cmdArgs
exit $LASTEXITCODE
