param([string]$InputMxd,[string]$OutputMxd,[string]$Config,[switch]$ExportOnly)
$ErrorActionPreference='Stop'
if([IntPtr]::Size -ne 4){throw 'Requires 32-bit Windows PowerShell'}
$assemblyRoot='C:\Windows\Microsoft.NET\assembly\GAC_MSIL'
$assemblyRefs=@()
foreach($assemblyName in @('Version','System','SystemUI','Geometry','Display','Carto','Output','Geodatabase','DataSourcesGDB','DataSourcesRaster')){
 $assemblyPath=Get-ChildItem -LiteralPath (Join-Path $assemblyRoot "ESRI.ArcGIS.$assemblyName") -Recurse -Filter *.dll | Select-Object -First 1 -ExpandProperty FullName
 [void][System.Reflection.Assembly]::LoadFrom($assemblyPath);$assemblyRefs+=$assemblyPath
}
$olePath=Get-ChildItem -LiteralPath (Join-Path $assemblyRoot 'stdole') -Recurse -Filter *.dll -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
if(!$olePath){$olePath=Get-ChildItem -LiteralPath 'C:\Windows\assembly\GAC\stdole' -Recurse -Filter *.dll | Select-Object -First 1 -ExpandProperty FullName}
[void][System.Reflection.Assembly]::LoadFrom($olePath);$assemblyRefs+=@($olePath,'System.Web.Extensions.dll')
Add-Type -Path (Join-Path $PSScriptRoot 'NativeAppendix.cs') -ReferencedAssemblies $assemblyRefs
if($ExportOnly){[NativeAppendix]::Export($InputMxd,$Config)}else{[NativeAppendix]::Modify($InputMxd,$Config)}
