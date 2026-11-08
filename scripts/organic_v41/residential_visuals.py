"""Before/after inhabitants maps at real anchors; visual-only change magnitudes."""
from pathlib import Path
import numpy as np,json,gzip,shapely
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib.colors import LogNorm,TwoSlopeNorm
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'docs/organic-v41'
a=np.load(OUT/'proposed_arrays.npz');b=np.load(ROOT/'docs/organic-stage-b/proposed_arrays.npz');loc=a['locations'];old=np.r_[b['population'],np.zeros(len(loc)-len(b['population']))];new=a['population'];delta=new-old;geo=json.load(gzip.open(OUT/'audit_boundaries.geojson.gz','rt'))
for tag,bb in [('bsd_residential',(106.59,-6.35,106.71,-6.21)),('bekasi_residential',(106.94,-6.42,107.23,-6.18)),('bogor_residential',(106.70,-6.65,106.99,-6.38)),('airport_residential',(106.62,-6.16,106.70,-6.09))]:
 win=(loc[:,0]>=bb[0])&(loc[:,0]<=bb[2])&(loc[:,1]>=bb[1])&(loc[:,1]<=bb[3]);maxval=max(2,old[win].max(),new[win].max());fig,axs=plt.subplots(1,3,figsize=(17,6),layout='constrained')
 for ax,v,title in zip(axs,[old,new,delta],['v4 all inhabitants (audit stock)','Proposed S0 inhabitants','Relocation: proposed minus current']):
  changed='minus'in title;ids=win&(v!=0 if changed else v>0)
  if changed:
   lim=max(1,abs(delta[win]).max());im=ax.scatter(*loc[ids].T,c=v[ids],s=np.clip(np.sqrt(abs(v[ids])),3,40),norm=TwoSlopeNorm(vmin=-lim,vcenter=0,vmax=lim),cmap='RdBu',linewidths=0)
  else:im=ax.scatter(*loc[ids].T,c=v[ids],s=np.clip(np.sqrt(v[ids])/3,1,25),norm=LogNorm(vmin=1,vmax=maxval),cmap='viridis',alpha=.7,linewidths=0,rasterized=True)
  for f in geo['features']:
   if f['properties']['kind']not in ['residential_admin','airport']:continue
   g=shapely.geometry.shape(f['geometry'])
   if not g.intersects(shapely.box(*bb)):continue
   for poly in g.geoms if hasattr(g,'geoms')else[g]:
    if poly.geom_type=='Polygon':x,y=poly.exterior.xy;ax.plot(x,y,c='#858585',lw=.4,zorder=0)
  ax.set_xlim(bb[0],bb[2]);ax.set_ylim(bb[1],bb[3]);ax.set_aspect(1.006);ax.ticklabel_format(useOffset=False,style='plain');ax.xaxis.set_major_locator(MaxNLocator(4));ax.yaxis.set_major_locator(MaxNLocator(5));ax.set_title(title);fig.colorbar(im,ax=ax,shrink=.65,label='Inhabitants / anchor'if not changed else'Inhabitants relocated / anchor')
 fig.suptitle(tag.replace('_',' ')+' — totals per village unchanged; not game Residents layer');fig.savefig(OUT/f'{tag}.png',dpi=150);plt.close(fig)
print('Four residential before/after maps complete')
