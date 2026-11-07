"""Audit proxy detour against a sample of shortest paths on the mapped road graph.
Road classes do not include turn restrictions/access, so this remains a diagnostic.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'audit'))
from baseline import *
from scipy.spatial import cKDTree
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components,dijkstra
OUT=ROOT/'docs/organic-stage-b'
if __name__=='__main__':
 t=time.monotonic();roads=readgz(ROOT/'assets/JKT/roads.geojson.gz');coordinates=[];starts=[];ends=[];offset=0
 for f in roads['features']:
  lines=f['geometry']['coordinates']if f['geometry']['type']=='MultiLineString'else [f['geometry']['coordinates']]
  for coords in lines:
   line=np.array(coords);coordinates.append(line);starts.append(np.arange(offset,offset+len(line)-1));ends.append(np.arange(offset+1,offset+len(line)));offset+=len(line)
 loc=np.concatenate(coordinates);del roads,coordinates;rounded=np.rint(loc*1e7).astype(np.int64);unique,inverse=np.unique(rounded,axis=0,return_inverse=True);xy=np.array(Transformer.from_crs(4326,32748,always_xy=True).transform(*(unique/1e7).T)).T;u=inverse[np.concatenate(starts)];v=inverse[np.concatenate(ends)];length=np.linalg.norm(xy[u]-xy[v],axis=1);keep=(u!=v)&(length>0);u=u[keep];v=v[keep];length=length[keep]
 # Deduplicate undirected edges using minimum length, not summation.
 lo=np.minimum(u,v);hi=np.maximum(u,v);keys=lo.astype(np.int64)*len(xy)+hi;order=np.argsort(keys);keys=keys[order];first=np.r_[0,np.flatnonzero(np.diff(keys))+1];uu=lo[order][first];vv=hi[order][first];ww=np.minimum.reduceat(length[order],first);graph=csr_matrix((np.r_[ww,ww],(np.r_[uu,vv],np.r_[vv,uu])),shape=(len(xy),len(xy)));ncomp,comp=connected_components(graph,directed=False);a=np.load(OUT/'proposed_arrays.npz');pairs=np.load(OUT/'od_pairs.npz');rng=np.random.default_rng(20261107);choose=rng.choice(len(pairs['units']),size=min(96,len(pairs['units'])),replace=False,p=pairs['units']/pairs['units'].sum());oi=pairs['origin'][choose];di=pairs['destination'][choose];access,nn=cKDTree(xy).query(a['xy']);records=[]
 for q,(o,d)in enumerate(zip(oi,di)):
  straight=float(np.linalg.norm(a['xy'][o]-a['xy'][d]));same=comp[nn[o]]==comp[nn[d]];route=None
  if same:
   dd=dijkstra(graph,directed=False,indices=int(nn[o]),limit=150000);val=dd[int(nn[d])]
   if np.isfinite(val):route=float(val+access[o]+access[d])
  records.append({'origin_index':int(o),'destination_index':int(d),'straight_m':straight,'mapped_road_m':route,'same_component':bool(same),'origin_access_m':float(access[o]),'destination_access_m':float(access[d]),'ratio':route/straight if route and straight>=1000 else None})
  if q%16==0:print('routed sample',q,flush=True)
 ratios=[r['ratio']for r in records if r['ratio']is not None];result={'sample_method':'96 demand-weighted distinct OD pairs,seed20261107','graph_nodes':len(xy),'graph_undirected_edges':len(uu),'graph_components':ncomp,'sample_pairs':records,'reachable_pairs':sum(x['mapped_road_m']is not None for x in records),'detour_ratio_median_p90':np.quantile(ratios,[.5,.9]).tolist()if ratios else None,'seconds':time.monotonic()-t,'limitations':['All packaged minor roads admitted; driving access and turn restrictions unavailable','Bridges/tunnels share only exactly coincident mapped coordinate vertices; no geometric crossing insertion','Nearest graph vertex introduces access distance','Sample diagnostics do not imply every generated drivingDistance is road-routed','No measured congestion; engine time remains explicit proxy1.35/24kmh+180s']};(OUT/'route_sample.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='sample_pairs'},indent=2))
