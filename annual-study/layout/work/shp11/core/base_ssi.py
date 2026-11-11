from compute import *
g=cells(500);d=pd.read_csv(W/'六项逐格逐年原值与得分.csv.gz').drop(columns='ALLDIST')
new=[]
for y in Y:
 f=field(A/f'landscape/{y}/fields_500_0.bin',g)
 new.append(g[['grid_id']].assign(year=y,SSI=f[:,4]))
d=d.merge(pd.concat(new),on=['grid_id','year'],validate='1:1')
save(d,'基准及SSI.csv.gz')
