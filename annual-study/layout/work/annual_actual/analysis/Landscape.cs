using System;
using System.IO;
using System.Globalization;
// Input bytes are on the common native CLCD lattice. Row order for the output is south to north.
public class Landscape {
 static int[] group={0,1,2,2,3,4,0,5,6,4};
 static double[] recovery={0,.5,1,.8,.7,1,0,.1,.4,.9};
 static readonly int[] dx={1,-1,0,0,1,1,-1,-1},dy={0,0,1,-1,-1,1,-1,1};
 static int[] queue=new int[1600];static bool[] seen=new bool[1600];static byte[] cells=new byte[1600];
 static float[] greenDistance; static byte[] land; static int width,height;static double tx,ty;
 static double[] calculate(int left,int bottom,int s) {
  int col0=(int)Math.Floor((left-tx)/30),col1=(int)Math.Ceiling((left+s-tx)/30);
  int row0=(int)Math.Floor((ty-bottom-s)/30),row1=(int)Math.Ceiling((ty-bottom)/30);
  if(col0<0||row0<0||col1>width||row1>height) throw new Exception("Outside raster");
  int w=col1-col0,ht=row1-row0,count=w*ht,ncent=0,np=0,nBuilt=0;
  double[] byClass=new double[7];double area=0,lri=0,squareSum=0,sumDist=0;
  Array.Clear(seen,0,count);
  for(int row=0;row<ht;row++) {
   double y=ty-30*(row+row0), wy=Math.Min(y,bottom+s)-Math.Max(y-30,bottom);
   for(int col=0;col<w;col++) {
    double x=tx+30*(col+col0),wx=Math.Min(x+30,left+s)-Math.Max(x,left);
    int idx=row*w+col,p=(row+row0)*width+col+col0,c=land[p];
    if(c>=group.Length||group[c]==0)throw new Exception("Unexpected class in study window: "+c);
    int g=group[c];double a=wx*wy;byClass[g]+=a;area+=a;lri+=a*recovery[c];
    bool center=x+15>=left&&x+15<left+s&&y-15>bottom&&y-15<=bottom+s;
    cells[idx]=center?(byte)g:(byte)0;if(center)ncent++;
   }
  }
  for(int i=0;i<count;i++){
   if(cells[i]==0||seen[i])continue;byte v=cells[i];seen[i]=true;int at=0,end=1;queue[0]=i;
   while(at<end){int q=queue[at++],rx=q%w,ry=q/w;for(int z=0;z<8;z++){
    int x=rx+dx[z],y=ry+dy[z];if(x<0||x>=w||y<0||y>=ht)continue;int j=y*w+x;
    if(!seen[j]&&cells[j]==v){seen[j]=true;queue[end++]=j;}
   }}np++;squareSum+=(double)end*end;
  }
  Array.Clear(seen,0,count);
  for(int i=0;i<count;i++){
   int lrow=i/w,lcol=i%w;int p=(lrow+row0)*width+col0+lcol;
   if(land[p]!=8||seen[i])continue;seen[i]=true;int at=0,end=1;queue[0]=i;float nearest=greenDistance[p];
   while(at<end){int q=queue[at++],rx=q%w,ry=q/w;
    nearest=Math.Min(nearest,greenDistance[(row0+ry)*width+col0+rx]);
    for(int z=0;z<8;z++){int x=rx+dx[z],y=ry+dy[z];if(x<0||x>=w||y<0||y>=ht)continue;
     int j=y*w+x;if(!seen[j]&&land[(y+row0)*width+col0+x]==8){seen[j]=true;queue[end++]=j;}
    }
   }nBuilt++;sumDist+=nearest;
  }
  double entropy=0;for(int k=1;k<=6;k++){double p=byClass[k]/area;if(p>0)entropy-=p*Math.Log(p);}
  double simpson=squareSum/(ncent*(double)ncent);
  if(Math.Abs(area-(double)s*s)>0.1)throw new Exception("Area closure");
  return new double[]{Math.Max(entropy,0),np/(ncent*.0009),1/simpson,1-simpson,nBuilt>0?sumDist/nBuilt:Double.NaN,lri/area,byClass[2]/area,byClass[3]/area,byClass[4]/area,byClass[6]/area};
 }
 public static void Main(string[] a){
  width=int.Parse(a[2]);height=int.Parse(a[3]);tx=Double.Parse(a[4],CultureInfo.InvariantCulture);ty=Double.Parse(a[5],CultureInfo.InvariantCulture);
  land=File.ReadAllBytes(a[0]);greenDistance=new float[width*height];Buffer.BlockCopy(File.ReadAllBytes(a[1]),0,greenDistance,0,4*greenDistance.Length);
  if(land.Length!=width*height)throw new Exception("Shape mismatch");
  int[] box={int.Parse(a[7]),int.Parse(a[8]),int.Parse(a[9]),int.Parse(a[10])};
  foreach(int s in new int[]{200,500,1000})foreach(int shift in new int[]{0,1,2,3}){
   int ox=(shift&1)*s/2,oy=((shift>>1)&1)*s/2;
   int x0=(int)Math.Floor((box[0]-ox)/(double)s),y0=(int)Math.Floor((box[1]-oy)/(double)s);
   int x1=(int)Math.Ceiling((box[2]-ox)/(double)s),y1=(int)Math.Ceiling((box[3]-oy)/(double)s);
   string f=Path.Combine(a[6],"fields_"+s+"_"+shift+".bin");
   using(var writer=new BinaryWriter(new BufferedStream(File.Open(f,FileMode.Create),65536))){
    writer.Write(x0);writer.Write(y0);writer.Write(x1);writer.Write(y1);
    for(int iy=y0;iy<y1;iy++)for(int ix=x0;ix<x1;ix++){double[] v=calculate(ix*s+ox,iy*s+oy,s);foreach(double d in v)writer.Write(d);}
   }
  }
 }
}