using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using ESRI.ArcGIS;
using ESRI.ArcGIS.Carto;
using ESRI.ArcGIS.Display;
using ESRI.ArcGIS.Geometry;
using ESRI.ArcGIS.esriSystem;
public static class MainScale {
  static IAoInitialize lic;
  static IColor Black(){ IRgbColor c=new RgbColorClass(); c.Red=0; c.Green=0; c.Blue=0; return c; }
  static ILineSymbol Line(){ ISimpleLineSymbol l=new SimpleLineSymbolClass();l.Style=esriSimpleLineStyle.esriSLSSolid;l.Width=.7;l.Color=Black();return l; }
  public static void Run(string file,string config,string audit){
    if(!RuntimeManager.Bind(ProductCode.Desktop)) throw new Exception("ArcGIS Desktop bind failed");
    lic=new AoInitializeClass(); var st=lic.Initialize(esriLicenseProductCode.esriLicenseProductCodeAdvanced); if(st!=esriLicenseStatus.esriLicenseCheckedOut && st!=esriLicenseStatus.esriLicenseAlreadyInitialized) throw new Exception(st.ToString());
    var js=new JavaScriptSerializer(); var spec=js.Deserialize<Dictionary<string,object>>(File.ReadAllText(config));var ss=new Dictionary<string,Dictionary<string,object>>();foreach(object e in(ArrayList)spec["scales"]){var x=(Dictionary<string,object>)e;ss[(string)x["name"]]=x;}
    IMapDocument d=new MapDocumentClass(); d.Open(file,""); IGraphicsContainer gc=(IGraphicsContainer)d.PageLayout;gc.Reset();IElement e0;var edits=new ArrayList();
    while((e0=gc.Next())!=null){IMapSurroundFrame frame=e0 as IMapSurroundFrame;if(frame==null || !(frame.MapSurround is IScaleBar))continue;
      string name=((IElementProperties)e0).Name;var def=ss[name];IScaleBar old=(IScaleBar)frame.MapSurround;double full=Convert.ToDouble(def["division_km"])*Convert.ToDouble(def["divisions"]);
      var geo=e0.Geometry;
      if(def.ContainsKey("shift_x_cm"))((ITransform2D)geo).Move(Convert.ToDouble(def["shift_x_cm"]),0);
      ITextSymbol labels=old.LabelSymbol;labels.Color=Black();var f=labels.Font;f.Name="Arial";labels.Font=f;
      var sb=new ScaleLineClass();sb.Map=frame.MapFrame.Map;sb.Units=esriUnits.esriKilometers;sb.UnitLabel="km";sb.UnitLabelPosition=esriScaleBarPos.esriScaleBarAfterLabels;sb.UnitLabelGap=2.2;sb.LabelPosition=esriVertPosEnum.esriAbove;sb.LabelGap=1.2;sb.LabelSymbol=labels;sb.UnitLabelSymbol=labels;
      sb.BarColor=Black();sb.LineSymbol=Line();sb.DivisionMarkSymbol=Line();sb.SubdivisionMarkSymbol=Line();sb.DivisionMarkHeight=4.5;sb.SubdivisionMarkHeight=0;sb.MarkPosition=esriVertPosEnum.esriAbove;
      sb.Divisions=1;sb.DivisionsBeforeZero=0;sb.Subdivisions=2;sb.LabelFrequency=esriScaleBarFrequency.esriScaleBarDivisionsAndFirstMidpoint;sb.MarkFrequency=esriScaleBarFrequency.esriScaleBarMajorDivisions;sb.ResizeHint=esriScaleBarResizeHint.esriScaleBarFixed;sb.Division=full;
      frame.MapSurround=(IMapSurround)sb;e0.Geometry=geo;sb.Division=full; edits.Add(new{name=name,map=frame.MapFrame.Map.Name,fullkm=full});
    }
    if(edits.Count!=ss.Count)throw new Exception("Missing map scale");d.Save(true,false);d.Close();lic.Shutdown();File.WriteAllText(audit,js.Serialize(edits));
  }
}
