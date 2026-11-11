param([string]$Folder,[string]$Report)
$ErrorActionPreference='Stop'
if([IntPtr]::Size -ne 4){throw 'Requires 32-bit Windows PowerShell'}
$base='C:\Windows\Microsoft.NET\assembly\GAC_MSIL';$refs=@()
foreach($n in @('Version','System','SystemUI','Geometry','Display','Carto','Output','Geodatabase','DataSourcesGDB','DataSourcesRaster')){$p=Get-ChildItem -LiteralPath (Join-Path $base "ESRI.ArcGIS.$n") -Recurse -Filter '*.dll' | Select-Object -First 1 -ExpandProperty FullName;[void][Reflection.Assembly]::LoadFrom($p);$refs+=$p}
$ole=Get-ChildItem -LiteralPath (Join-Path $base 'stdole') -Recurse -Filter '*.dll' -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName;if(!$ole){$ole=Get-ChildItem -LiteralPath 'C:\Windows\assembly\GAC\stdole' -Recurse -Filter '*.dll' | Select-Object -First 1 -ExpandProperty FullName};[void][Reflection.Assembly]::LoadFrom($ole);$refs+=@($ole,'System.Web.Extensions.dll');Add-Type -Path (Join-Path $PSScriptRoot 'NativePortable.cs') -ReferencedAssemblies $refs;[NativePortable]::Run($Folder,$Report)
