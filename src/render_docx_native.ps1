param([Parameter(Mandatory=$true)][string]$Docx,[Parameter(Mandatory=$true)][string]$OutputDir)
$ErrorActionPreference='Stop'
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$taskPDF=Join-Path $OutputDir 'native_render.pdf'
$taskApp=$null;$taskDoc=$null;$taskInitialDocs=0
$taskBefore=(Get-FileHash -LiteralPath $Docx -Algorithm SHA256).Hash
try {
 $taskApp=[Runtime.InteropServices.Marshal]::GetActiveObject('Word.Application')
 $taskInitialDocs=$taskApp.Documents.Count
 $taskOldAlerts=$taskApp.DisplayAlerts
 $taskOldSecurity=$taskApp.AutomationSecurity
 if($taskInitialDocs -eq 0){$taskApp.Visible=$false}
 $taskApp.DisplayAlerts=0;$taskApp.AutomationSecurity=3
 $taskDoc=$taskApp.Documents.Open($Docx,$false,$true,$false)
 $taskDoc.PrintRevisions=$false
 $taskDoc.Repaginate()
 $taskDoc.ExportAsFixedFormat($taskPDF,17,$false,0,0,1,9999,0,$true,$true,1,$true,$true,$false)
 $taskLog=[ordered]@{docx=$Docx;pdf=$taskPDF;pages=$taskDoc.ComputeStatistics(2);words=$taskDoc.ComputeStatistics(0);characters=$taskDoc.ComputeStatistics(3);tables=$taskDoc.Tables.Count;comments=$taskDoc.Comments.Count;native_equations=$taskDoc.OMaths.Count;engine=$taskApp.Name;engine_version=$taskApp.Version;engine_path=$taskApp.Path;read_only=$true;sha256=$taskBefore;existing_docs_count=$taskInitialDocs;status='NATIVE_RENDER_COMPLETE_PAGE_REVIEW_PENDING'}
} finally {
 if($null -ne $taskDoc){$taskDoc.Close(0);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($taskDoc)}
 if($null -ne $taskApp){
  $taskApp.DisplayAlerts=$taskOldAlerts;$taskApp.AutomationSecurity=$taskOldSecurity
  [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($taskApp)
 }
}
if((Get-FileHash -LiteralPath $Docx -Algorithm SHA256).Hash -ne $taskBefore){throw 'Read-only render changed DOCX'}
$taskLog | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $OutputDir 'native_render.json') -Encoding utf8
$taskLog | ConvertTo-Json -Compress
