param([string] $Folder=$PSScriptRoot)
$ErrorActionPreference = 'Stop'
$excel=$null
$book=$null
$xlsx=Join-Path $Folder '三阶段统计图_可编辑.xlsx'
$ver=''
try {
    $excel=New-Object -ComObject Excel.Application
    $excel.DisplayAlerts=$false
    $excel.Visible=$false
    $excel.AutomationSecurity=3
    $ver=$excel.Version
    $book=$excel.Workbooks.Open($xlsx,0,$true)
    foreach ($topic in @('A_转折与地段','B_水面产品对照','C_植被分组与覆盖')) {
        $s=$book.Worksheets.Item($topic)
        if ($s.ChartObjects().Count -ne 2) { throw "意外的原生图表数: $topic"}
        $s.ExportAsFixedFormat(0,(Join-Path $Folder ($topic+'.pdf')),0,$true,$false)
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($s)
    }
} finally {
    if ($book) {$book.Close($false);[void][Runtime.InteropServices.Marshal]::ReleaseComObject($book)}
    if ($excel) {$excel.Quit();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)}
}
Write-Output "Excel $ver"

