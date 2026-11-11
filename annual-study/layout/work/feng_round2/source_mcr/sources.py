"""Build connected patch graph and area and dPC alternative masks. Distances are measured pixel-centre to pixel-centre at patch edges."""
import numpy as np, rasterio as rio, csv,json
from scipy import ndimage as nd
from scipy.spatial import cKDTree
from scipy.sparse.csgraph import shortest_path
from pathlib import Path
from prepare import D,save
with rio.open(D/'sources_area.tif') as s: src=s.read(1);p=s.profile
mask=src>0; border=mask & ~nd.binary_erosion(mask,structure=np.ones((3,3)),border_value=0)
n=int(src.max()); arrays=[np.column_stack(np.where(border&(src==i)))*30. for i in range(1,n+1)]
trees=[cKDTree(x) for x in arrays]
ed=np.zeros((n,n))
for i in range(n):
    for j in range(i):
        small,large=(i,j) if len(arrays[i])<=len(arrays[j]) else (j,i)
        ed[i,j]=ed[j,i]=np.min(trees[large].query(arrays[small])[0])
areas=np.bincount(src.ravel())[1:]*900.
def numerator(M,ar):
    return ar @ (np.exp(-np.log(2)*shortest_path(M,directed=False)/1000.)) @ ar
allnum=numerator(ed,areas);dpc=[]
for i in range(n):
    keep=np.arange(n)!=i
    dpc.append(100*(allnum-numerator(ed[np.ix_(keep,keep)],areas[keep]))/allnum)
score=np.r_[0,np.asarray(dpc)]; sel=score>0.5
with (D/'source_dPC.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['source_id','area_m2','dPC_percent','retained_pc_scenario','touches_background_edge'])
    edge=np.unique(np.r_[src[0],src[-1],src[:,0],src[:,-1]])
    for i in range(n):w.writerow([i+1,areas[i],dpc[i],sel[i+1],(i+1) in edge])
save('sources_dpc.tif',np.where(sel[src],src,0).astype('int32'),0,p)
np.savetxt(D/'edge_distances_m.csv',ed,delimiter=',',fmt='%.6f')
with rio.open(D/'cost5.tif') as s:cost=s.read(1)
cost.tofile(D/'cost.f32');src.astype('int32').tofile(D/'area.i32')
np.where(sel[src],src,0).astype('int32').tofile(D/'dpc.i32')
print('n_area',n,'n_dPC',np.sum(sel),flush=True)
