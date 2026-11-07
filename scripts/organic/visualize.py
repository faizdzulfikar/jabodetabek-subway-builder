"""Evidence-based, static Stage-A diagnostics; no game writes."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'audit'))
from baseline import *
OUT=ROOT/'docs/organic-stage-b'
def dump(name,x):(OUT/name).write_text(json.dumps(x,indent=2)+'\n')
import sqlite3,zlib,shapely,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib.colors import LogNorm
from matplotlib.collections import PolyCollection
from scipy.spatial import cKDTree
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})

def scatter(ax,loc,w,bbox):
 x0,y0,x1,y1=bbox;m=(loc[:,0]>=x0)&(loc[:,0]<=x1)&(loc[:,1]>=y0)&(loc[:,1]<=y1)&(w>0);x=loc[m];z=w[m]
 im=ax.scatter(x[:,0],x[:,1],s=np.clip(np.sqrt(z)*.35,1.5,80),c=z,cmap='magma',norm=LogNorm(100,100000),alpha=.8,lw=0,rasterized=True);ax.set_xlim(x0,x1);ax.set_ylim(y0,y1);ax.set_aspect(1/np.cos(np.radians(-6.3)));ax.tick_params(labelsize=8);ax.ticklabel_format(style='plain',useOffset=False);ax.xaxis.set_major_locator(MaxNLocator(4));return im

if __name__=='__main__':
 a=np.load(OUT/'proposed_arrays.npz');b=np.load(ROOT/'docs/organic-stage-a/baseline_arrays.npz');inp=readgz(ROOT/'assets/JKT/government_inputs.json.gz');vs=inp['villages'];names=b['names'].tolist();db=sqlite3.connect(sys.argv[1]);centers=[]
 for pr,name,box in CENTERS:
  x0,y0,x1,y1=box;row={'priority':pr,'center':name,'diagnostic_bbox':box}
  for label,d in [('before',b),('proposal',a)]:
   loc=d['locations'];m=(loc[:,0]>=x0)&(loc[:,0]<=x1)&(loc[:,1]>=y0)&(loc[:,1]<=y1);row[label+'_jobs']=int(d['jobs'][m].sum());row[label+'_model_residents']=int(d['home'][m].sum());row[label+'_points']=int(m.sum())
  centers.append(row)
 dump('center_comparison.json',centers)
 with (OUT/'employment_centers.csv').open('w')as f:
  w=csv.writer(f,lineterminator='\n');w.writerow(['priority','center','jobs_before','jobs_proposal','origins_before','origins_proposal','points_before','points_proposal']);w.writerows([[r['priority'],r['center'],r['before_jobs'],r['proposal_jobs'],r['before_model_residents'],r['proposal_model_residents'],r['before_points'],r['proposal_points']]for r in centers])
 # Full regional capacities and reliable administrative populations.
 ledger={p['admin_id']:p for p in readgz(OUT/'proposed_allocations.json.gz')['unlocated_allocations']}
 with (OUT/'proposed_village_allocations.csv').open('w')as f:
  w=csv.writer(f,lineterminator='\n');w.writerow(['admin_id','region','kecamatan','kelurahan','population_status','source_year','population_located','population_unlocated','population_total','model_residents_located','model_residents_unlocated','jobs','anchors','baseline_model_residents','baseline_jobs'])
  for v,row in enumerate(vs):
   m=a['villages']==v;bm=b['villageids']==v;w.writerow([row['id'],row['region'],row['kecamatan'],row['kelurahan'],row['population_status'],row['year'],int(a['population'][m].sum()),ledger.get(row['id'],{}).get('population',0),int(a['population'][m].sum())+ledger.get(row['id'],{}).get('population',0),int(a['home'][m].sum()),ledger.get(row['id'],{}).get('model_residents',0),int(a['jobs'][m].sum()),int(m.sum()),int(b['home'][bm].sum()),int(b['jobs'][bm].sum())])
 # Regional overview same scale for both scenarios.
 fig,axs=plt.subplots(2,2,figsize=(13,12),layout='constrained');box=[106.3,-6.85,107.35,-5.9]
 for ax,d,field,title in [(axs[0,0],b,'home','Existing — working residents'),(axs[0,1],a,'home','Organic v4 — working residents'),(axs[1,0],b,'jobs','Existing — jobs'),(axs[1,1],a,'jobs','Organic v4 — jobs')]:
  im=scatter(ax,d['locations'],d[field],box);ax.set_title(title);fig.colorbar(im,ax=ax,shrink=.65,label='Persons per point (log scale)')
 fig.suptitle('Stage B v4 — all population located; exact worker margins',fontsize=15);fig.savefig(OUT/'metro_before_after.png',dpi=170);plt.close(fig)
 # Actual footprints give local context; select by SQLite anchor bounding boxes.
 focuses=[('CBD / Kuningan',[106.805,-6.235,106.84,-6.19]),('Cikarang industrial',[107.105,-6.325,107.155,-6.285]),('BSD mixed urban fabric',[106.635,-6.31,106.685,-6.27]),('Dense kampung: Tambora',[106.79,-6.155,106.815,-6.135]),('Peri-urban south Bogor',[106.785,-6.72,106.835,-6.68])]
 for title,box in focuses:
  x0,y0,x1,y1=box;polys=[]
  for blob, in db.execute('SELECT geometry FROM buildings WHERE lon BETWEEN ? AND ? AND lat BETWEEN ? AND ?',(x0,x1,y0,y1)):
   g=shapely.from_wkb(zlib.decompress(blob))
   for p in (g.geoms if hasattr(g,'geoms') else [g]):
    if hasattr(p,'exterior'):polys.append(np.asarray(p.exterior.coords))
  fig,axs=plt.subplots(2,2,figsize=(12,10),layout='constrained')
  for ax,d,field,label in [(axs[0,0],b,'home','Existing origins'),(axs[0,1],a,'home','Organic v4 origins'),(axs[1,0],b,'jobs','Existing jobs'),(axs[1,1],a,'jobs','Organic v4 jobs')]:
   ax.add_collection(PolyCollection(polys,facecolors='#d9dfe4',edgecolors='none',alpha=.85,zorder=0));im=scatter(ax,d['locations'],d[field],box);ax.set_title(label);fig.colorbar(im,ax=ax,shrink=.65,label='Persons / point')
  fig.suptitle(title+' — actual OSM footprints in grey; equal point scales',fontsize=14);slug=title.split(':')[0].split('/')[0].strip().lower().replace(' ','_');fig.savefig(OUT/f'focus_{slug}.png',dpi=180);plt.close(fig)
 # Grid phase and distance-to-neighbor diagnostics, not a beauty score.
 fig,axs=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
 for d,label,col in [(b,'Existing','#af5f34'),(a,'Organic v4','#207a83')]:
  phase=(d['xy']%500).ravel();axs[0].hist(phase,bins=np.arange(0,501,25),weights=np.ones(len(phase))/len(phase),histtype='step',lw=2,label=label,color=col);dd,_=cKDTree(d['xy']).query(d['xy'],k=2);s=np.sort(dd[:,1]);axs[1].plot(s,np.arange(1,len(s)+1)/len(s),label=label,color=col)
 axs[0].set(xlabel='UTM coordinate modulo 500 m',ylabel='Fraction of coordinate axes',title='Inherited 500 m phase signature');axs[1].set(xlabel='Nearest other point (m)',ylabel='Cumulative fraction',xlim=(0,500),title='Spacing reflects buildings and aggregation');axs[0].legend();axs[1].legend();fig.savefig(OUT/'geometry_diagnostics.png',dpi=180);plt.close(fig)
 # Discover additional clusters numerically; no geographic labels invented from coordinates.
 xy=a['xy'];w=a['jobs'];tree=cKDTree(xy);nb=tree.query_ball_point(xy,500);density=np.array([w[idx].sum() for idx in nb]);order=np.argsort(-density);selected=[]
 for i in order:
  if density[i]<=0:break
  if selected and np.linalg.norm(xy[selected]-xy[i],axis=1).min()<2500:continue
  selected.append(int(i))
  if len(selected)==30:break
 clusters=[]
 for i in selected:
  lon,lat=a['locations'][i];covered=[n for _,n,(x0,y0,x1,y1) in CENTERS if x0<=lon<=x1 and y0<=lat<=y1];v=vs[int(a['villages'][i])];clusters.append({'location':[float(lon),float(lat)],'jobs_within_500m':int(density[i]),'region':v['region'],'kelurahan':v['kelurahan'],'inside_audit_windows':covered,'status':'model-derived cluster requiring review; overlapping radius totals not additive'})
 dump('discovered_clusters.json',clusters)
 print('visualizations and comparison tables complete')
