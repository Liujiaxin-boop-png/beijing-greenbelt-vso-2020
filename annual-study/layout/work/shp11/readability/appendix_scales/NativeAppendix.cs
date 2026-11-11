using System;using System.IO;using Path=System.IO.Path;using System.Collections;using System.Collections.Generic;using System.Web.Script.Serialization;
using ESRI.ArcGIS;using ESRI.ArcGIS.Carto;using ESRI.ArcGIS.Display;using ESRI.ArcGIS.Geometry;using ESRI.ArcGIS.Geodatabase;using ESRI.ArcGIS.DataSourcesGDB;using ESRI.ArcGIS.DataSourcesRaster;using ESRI.ArcGIS.esriSystem;using ESRI.ArcGIS.Output;
public static class NativeAppendix { [System.Runtime.InteropServices.DllImport("user32.dll")] static extern IntPtr GetDesktopWindow();
 static IAoInitialize lic;static object miss=Type.Missing;static string font="SimHei";static Dictionary<string,IFeatureWorkspace> spaces=new Dictionary<string,IFeatureWorkspace>();
 static Dictionary<string,object>D(object x){return (Dictionary<string,object>)x;}
 static string S(Dictionary<string,object>d,string k,string z=""){return d.ContainsKey(k)?Convert.ToString(d[k]):z;}
 static double N(Dictionary<string,object>d,string k,double z=0){return d.ContainsKey(k)?Convert.ToDouble(d[k]):z;}
 static bool B(Dictionary<string,object>d,string k,bool z=false){return d.ContainsKey(k)?Convert.ToBoolean(d[k]):z;}
 static IColor C(string h,double opacity=1){IRgbColor c=new RgbColorClass();if(h=="none"||h=="transparent"){c.Transparency=0;return c;}h=h.TrimStart('#');c.Red=Convert.ToInt32(h.Substring(0,2),16);c.Green=Convert.ToInt32(h.Substring(2,2),16);c.Blue=Convert.ToInt32(h.Substring(4,2),16);c.Transparency=(byte)Math.Round(255*opacity);return c;}
 static ISimpleLineSymbol L(string h,double w,bool dash=false){ISimpleLineSymbol l=new SimpleLineSymbolClass();l.Color=C(h);l.Width=w;l.Style=h=="none"?esriSimpleLineStyle.esriSLSNull:(dash?esriSimpleLineStyle.esriSLSDash:esriSimpleLineStyle.esriSLSSolid);return l;}
 static IFillSymbol F(string h,string st="none",double w=0){ISimpleFillSymbol f=new SimpleFillSymbolClass();f.Color=C(h);f.Outline=L(st,w);if(h=="none")f.Style=esriSimpleFillStyle.esriSFSNull;return f;}
 static IPoint P(double x,double y){IPoint p=new PointClass();p.PutCoords(x,y);return p;}
 static IEnvelope E(double x,double y,double w,double h){IEnvelope e=new EnvelopeClass();e.PutCoords(x,y,x+w,y+h);return e;}
 static void Name(IElement e,string n){((IElementProperties3)e).Name=n;((IElementProperties3)e).AnchorPoint=esriAnchorPointEnum.esriBottomLeftCorner;}
 static ITextSymbol T(Dictionary<string,object>s){stdole.IFontDisp f=(stdole.IFontDisp)new stdole.StdFontClass();f.Name=S(s,"font",font);f.Bold=B(s,"bold");ITextSymbol t=new TextSymbolClass();t.Font=f;t.Size=N(s,"size",10);t.Color=C(S(s,"color","#1F2528"));string a=S(s,"align","left");t.HorizontalAlignment=a=="center"?esriTextHorizontalAlignment.esriTHACenter:a=="right"?esriTextHorizontalAlignment.esriTHARight:esriTextHorizontalAlignment.esriTHALeft;t.VerticalAlignment=S(s,"valign","bottom")=="top"?esriTextVerticalAlignment.esriTVATop:S(s,"valign","bottom")=="center"?esriTextVerticalAlignment.esriTVACenter:esriTextVerticalAlignment.esriTVABottom;return t;}
 static ISymbol Sym(Dictionary<string,object>s,string color){string k=S(s,"kind","polygon");if(k=="line")return(ISymbol)L(color,N(s,"width",.3),B(s,"dash"));if(k=="point"||k=="marker"){ISimpleMarkerSymbol m=new SimpleMarkerSymbolClass();m.Style=S(s,"shape","circle")=="square"?esriSimpleMarkerStyle.esriSMSSquare:esriSimpleMarkerStyle.esriSMSCircle;m.Size=N(s,"size",2);m.Color=C(color,N(s,"opacity",1));m.Outline=S(s,"stroke","none")!="none";m.OutlineColor=C(S(s,"stroke","none"));m.OutlineSize=N(s,"width",0);return(ISymbol)m;}return(ISymbol)F(color,S(s,"stroke","none"),N(s,"width",0));}

 public static void Modify(string input,string config){
  if(!RuntimeManager.Bind(ProductCode.Desktop))throw new Exception("Desktop bind failed");
  lic=new AoInitializeClass();var ls=lic.Initialize(esriLicenseProductCode.esriLicenseProductCodeAdvanced);
  if(ls!=esriLicenseStatus.esriLicenseCheckedOut&&ls!=esriLicenseStatus.esriLicenseAlreadyInitialized)throw new Exception("License="+ls);
  JavaScriptSerializer js=new JavaScriptSerializer();
  var c=js.Deserialize<Dictionary<string,object>>(File.ReadAllText(config));
  var s=D(c["scale"]);
  IMapDocument d=new MapDocumentClass();d.Open(input,"");
  if(d.PageLayout.Page.Units!=esriUnits.esriCentimeters)throw new Exception("unexpected page units");
  var gc=(IGraphicsContainer)d.PageLayout;var frames=new Dictionary<string,IMapFrame>();var old=new List<IElement>();IElement z;
  gc.Reset();
  while((z=gc.Next())!=null){
   if(z is IMapFrame){var f=(IMapFrame)z;frames.Add(f.Map.Name,f);}
   if(z is IMapSurroundFrame && ((IMapSurroundFrame)z).MapSurround is IScaleBar)old.Add(z);
  }
  if(old.Count!=1)throw new Exception("expected one source scale, got "+old.Count);
  foreach(var eOld in old)gc.DeleteElement(eOld);
  var frame=frames[S(s,"map")];var sb=(IScaleBar)new ScaleLineClass();
  sb.Map=frame.Map;sb.Units=esriUnits.esriKilometers;sb.UnitLabel="km";
  sb.DivisionsBeforeZero=0;sb.Divisions=1;sb.Subdivisions=2;
  sb.ResizeHint=esriScaleBarResizeHint.esriScaleBarFixed;double total=N(s,"km");
  sb.Division=total;sb.LabelFrequency=esriScaleBarFrequency.esriScaleBarDivisionsAndFirstMidpoint;
  sb.LabelPosition=esriVertPosEnum.esriAbove;sb.UnitLabelPosition=esriScaleBarPos.esriScaleBarAfterLabels;
  sb.LabelGap=1;sb.UnitLabelGap=2;
  var spec=new Dictionary<string,object>{{"font","Arial"},{"size",N(s,"font_size",7.5)},{"color","#000000"}};
  sb.LabelSymbol=T(spec);sb.UnitLabelSymbol=T(spec);sb.BarColor=C("#000000");
  ((IScaleLine)sb).LineSymbol=L("#000000",0.7);
  var marks=(IScaleMarks)sb;marks.DivisionMarkSymbol=L("#000000",.7);marks.SubdivisionMarkSymbol=L("#000000",.7);
  marks.MarkFrequency=esriScaleBarFrequency.esriScaleBarMajorDivisions;marks.MarkPosition=esriVertPosEnum.esriAbove;
  marks.DivisionMarkHeight=4.5;marks.SubdivisionMarkHeight=0;
  IMapSurroundFrame sf=new MapSurroundFrameClass();sf.MapSurround=(IMapSurround)sb;sf.MapFrame=frame;IElement e=(IElement)sf;
  e.Geometry=E(N(s,"x"),N(s,"y"),N(s,"w"),N(s,"h",.18));Name(e,S(s,"name"));gc.AddElement(e,0);sb.Division=total;
  d.ReplaceContents((IMxdContents)d.PageLayout);d.SetActiveView((IActiveView)d.PageLayout);d.Save(true,false);d.Close();lic.Shutdown();
 }
 public static void Export(string input,string config){
  if(!RuntimeManager.Bind(ProductCode.Desktop))throw new Exception("Desktop bind failed");lic=new AoInitializeClass();var ls=lic.Initialize(esriLicenseProductCode.esriLicenseProductCodeAdvanced);if(ls!=esriLicenseStatus.esriLicenseCheckedOut&&ls!=esriLicenseStatus.esriLicenseAlreadyInitialized)throw new Exception("License="+ls);
  JavaScriptSerializer js=new JavaScriptSerializer();js.MaxJsonLength=Int32.MaxValue;var cfg=js.Deserialize<Dictionary<string,object>>(File.ReadAllText(config));string stem=S(cfg,"export_stem");int dpi=(int)N(cfg,"dpi",600);IMapDocument d=new MapDocumentClass();d.Open(input,"");for(int ai=0;ai<d.MapCount;ai++)((IActiveView)d.get_Map(ai)).Activate(GetDesktopWindow().ToInt32());((IActiveView)d.PageLayout).Activate(GetDesktopWindow().ToInt32());var checks=new ArrayList();int expected=(int)N(cfg,"expected_maps",((ArrayList)cfg["maps"]).Count);if(d.MapCount!=expected)throw new Exception("MapCount "+d.MapCount+" != "+expected);
  for(int i=0;i<d.MapCount;i++){IMap m=d.get_Map(i);for(int j=0;j<m.LayerCount;j++)if(!m.get_Layer(j).Valid)throw new Exception("Broken layer "+m.Name+"/"+m.get_Layer(j).Name);IEnvelope ex=((IActiveView)m).Extent;checks.Add(new{name=m.Name,layers=m.LayerCount,extent=new[]{ex.XMin,ex.YMin,ex.XMax,ex.YMax},rotation=((IActiveView)m).ScreenDisplay.DisplayTransformation.Rotation});}
  double pw,ph;d.PageLayout.Page.QuerySize(out pw,out ph);if(d.PageLayout.Page.Units!=esriUnits.esriCentimeters)throw new Exception("Unexpected page units");int width=(int)Math.Round(pw/2.54*dpi),height=(int)Math.Round(ph/2.54*dpi);tagRECT rect=new tagRECT();rect.left=0;rect.top=0;rect.right=width;rect.bottom=height;IActiveView view=(IActiveView)d.PageLayout;
  foreach(string ext in new[]{"png","pdf","svg"}){IExport exp=ext=="png"?(IExport)new ExportPNGClass():ext=="pdf"?(IExport)new ExportPDFClass():(IExport)new ExportSVGClass();exp.ExportFileName=stem+"."+ext;exp.Resolution=dpi;exp.PixelBounds=E(0,0,width,height);int hdc=exp.StartExporting();view.Output(hdc,dpi,ref rect,null,null);exp.FinishExporting();exp.Cleanup();if(!File.Exists(stem+"."+ext)||new FileInfo(stem+"."+ext).Length<1000)throw new Exception("Missing export "+ext);Console.WriteLine("EXPORTED "+ext);}
  var elementChecks=new ArrayList();IGraphicsContainer gc=(IGraphicsContainer)d.PageLayout;gc.Reset();IElement el;while((el=gc.Next())!=null){if(el is ITextElement){ITextElement t=(ITextElement)el;elementChecks.Add(new{type="text",name=((IElementProperties)el).Name,text=t.Text,font=t.Symbol.Font.Name,size=t.Symbol.Size});}else if(el is IMapSurroundFrame){var sf=(IMapSurroundFrame)el;if(sf.MapSurround is IScaleBar){var sb=(IScaleBar)sf.MapSurround;elementChecks.Add(new{type="scale",name=((IElementProperties)el).Name,map=sb.Map.Name,units=sb.Units.ToString(),division=sb.Division,divisions=sb.Divisions});}}}
  File.WriteAllText(Path.ChangeExtension(config,"export_receipt.json"),js.Serialize(new{status="ARCMAP_NATIVE_REOPEN_EXPORTED_VISUAL_PENDING",input=input,engine="ArcObjects Desktop10.8",dpi=dpi,pixels=new[]{width,height},page_cm=new[]{pw,ph},map_count=d.MapCount,maps=checks,elements=elementChecks,broken_layers=0}));d.Close();lic.Shutdown();Console.WriteLine("PASS_ARCMAP_NATIVE_EXPORT "+stem);
 }
}
