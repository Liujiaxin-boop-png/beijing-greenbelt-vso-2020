$ErrorActionPreference='Stop'
$fig=Join-Path (Split-Path $PSScriptRoot -Parent) '新增图件与可编辑源文件'
$app=New-Object -ComObject PowerPoint.Application
try {
 foreach($name in @('研究技术路线','格网尺度比较','四类镇街管护核查')){
  $inp=Join-Path $fig ($name+'.pptx')
  $pr=$app.Presentations.Open($inp,-1,0,0)
  try {
    $slide=$pr.Slides.Item(1)
    $width=2280
    $height=[int]($width*$pr.PageSetup.SlideHeight/$pr.PageSetup.SlideWidth)
    $slide.Export((Join-Path $fig ($name+'.png')),'PNG',$width,$height)
    $pr.SaveAs((Join-Path $fig ($name+'.pdf')),32)
   } finally {$pr.Close()}
 }
}finally{$app.Quit()}
