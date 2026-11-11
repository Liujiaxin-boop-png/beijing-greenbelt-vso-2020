using System;
using System.IO;
// Multi-source, two-distinct-label Dijkstra for an isotropic symmetric raster graph.
// Sources comprise every pixel of each retained ecological core. An edge costs the
// arithmetic mean of its endpoint resistances times horizontal or diagonal length.
class TwoSource {
 struct Entry { public int pixel,id; public double d; public Entry(int p,int i,double v){pixel=p;id=i;d=v;} }
 sealed class MinHeap {
  Entry[] h=new Entry[32768]; int used=0; public int Count{get{return used;}}
  public void Push(Entry e){if(used==h.Length)Array.Resize(ref h,h.Length*2); int i=used++;while(i>0){int j=(i-1)/2;if(h[j].d<=e.d)break;h[i]=h[j];i=j;}h[i]=e;}
  public Entry Pop(){Entry ret=h[0],last=h[--used];if(used>0){int i=0;while(i*2+1<used){int j=i*2+1;if(j+1<used&&h[j+1].d<h[j].d)j++;if(last.d<=h[j].d)break;h[i]=h[j];i=j;}h[i]=last;}return ret;}
 }
 static MinHeap queue=new MinHeap(); static double[] d1,d2; static int[] k1,k2;
 static void Offer(int p,int k,double v){
    if(k==k1[p]){if(v>=d1[p])return;d1[p]=v;}
    else if(v<d1[p]){d2[p]=d1[p];k2[p]=k1[p];d1[p]=v;k1[p]=k;}
    else if(v<d2[p]){d2[p]=v;k2[p]=k;}
    else return;
    queue.Push(new Entry(p,k,v));
 }
 static void Main(string[] args){
    string folder=args[0],scheme=args[1];int width=int.Parse(args[2]),height=int.Parse(args[3]);double cell=double.Parse(args[4],System.Globalization.CultureInfo.InvariantCulture);int n=width*height;
    float[] cost=new float[n];int[] source=new int[n];Buffer.BlockCopy(File.ReadAllBytes(Path.Combine(folder,"cost.f32")),0,cost,0,4*n);Buffer.BlockCopy(File.ReadAllBytes(Path.Combine(folder,scheme+".i32")),0,source,0,4*n);
    d1=new double[n];d2=new double[n];k1=new int[n];k2=new int[n];int[] dx={1,-1,0,0,1,1,-1,-1},dy={0,0,1,-1,1,-1,1,-1};double[] fac={.5*cell,.5*cell,.5*cell,.5*cell,.5*cell*Math.Sqrt(2),.5*cell*Math.Sqrt(2),.5*cell*Math.Sqrt(2),.5*cell*Math.Sqrt(2)};
    for(int p=0;p<n;p++){d1[p]=d2[p]=Double.PositiveInfinity;int s=source[p];if(s<=0||cost[p]<=0)continue;d1[p]=0;k1[p]=s;int x=p%width,y=p/width;bool bd=false;
      for(int j=0;j<8;j++){int xx=x+dx[j],yy=y+dy[j];if(xx>=0&&xx<width&&yy>=0&&yy<height&&source[yy*width+xx]!=s){bd=true;break;}}if(bd)queue.Push(new Entry(p,s,0));}
    while(queue.Count>0){Entry e=queue.Pop();int p=e.pixel;if(!(k1[p]==e.id&&d1[p]==e.d)&&!(k2[p]==e.id&&d2[p]==e.d))continue;int x=p%width,y=p/width;double cp=cost[p];
      for(int j=0;j<8;j++){int xx=x+dx[j],yy=y+dy[j];if(xx<0||xx>=width||yy<0||yy>=height)continue;int q=yy*width+xx;if(cost[q]<=0)continue;Offer(q,e.id,e.d+(cp+cost[q])*fac[j]);}}
    using(var f=new BinaryWriter(File.Open(Path.Combine(folder,"surface_"+scheme+".f32"),FileMode.Create))){for(int p=0;p<n;p++)f.Write(double.IsInfinity(d2[p])?-9999f:(float)(d1[p]+d2[p]));}
 }
}
