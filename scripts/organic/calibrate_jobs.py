"""Bound floor-capacity inflation before assigning remaining unclassified local work.
This is a modelling regularizer, not a claim of measured staffing or home-working.
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'audit'))
from baseline import *
# apportion is pure but importing propose would open DB from argv, so use local helper.
def apportion(w,total):
 q=np.asarray(w,float)/sum(w)*int(total);a=np.floor(q).astype(np.int64);left=int(total-a.sum());a[np.argsort(-(q-a),kind='stable')[:left]]+=1;return a
OUT=ROOT/'docs/organic-stage-b'
if __name__=='__main__':
 a=np.load(OUT/'proposed_arrays.npz');arrays={k:a[k]for k in a.files};alloc=readgz(OUT/'proposed_allocations.json.gz');points=alloc['points'];base=np.load(ROOT/'docs/organic-stage-a/baseline_arrays.npz');reg=a['regions'];res=np.array([p['relative_residential_capacity']for p in points]);cap=np.array([p['relative_employment_capacity']for p in points]);jobs=np.zeros(len(points),np.int64);report=[]
 for r,name in enumerate(base['names']):
  ids=np.flatnonzero(reg==r);total=int(base['od'].sum(0)[r]);initial=.8*total*cap[ids]/cap[ids].sum();bounded=np.minimum(initial,cap[ids]*2);residual=total-bounded.sum();local=res[ids]/res[ids].sum();expected=bounded+residual*local;jobs[ids]=apportion(expected,total//100)*100;report.append({'region':str(name),'jobs':total,'initial_capacity_normalization':float(.8*total/cap[ids].sum()),'floor_component_ceiling_multiplier':2,'unclassified_neighborhood_component_share':float(residual/total),'interpretation':'Residual spatial prior for missing neighborhood/mixed-use workplaces; not observed informal employment or homeworking share'})
 for p,j in zip(points,jobs):p['jobs']=int(j)
 check=json.loads((OUT/'proposal_checks.json').read_text());check['largest_anchor_jobs']=int(jobs.max());check['top_1percent_job_share']=float(np.sort(jobs)[-max(1,len(jobs)//100):].sum()/jobs.sum());check['employment_calibration']='bounded floor component + explicit residual prior; see employment_capacity_regularization.json';check['limitations']=[x for x in check['limitations']if not x.startswith('Twenty percent')];check['limitations'].append('Unclassified neighborhood-work component adaptive by region; not observed informal/homeworking share');(OUT/'proposal_checks.json').write_text(json.dumps(check,indent=2))
 arrays['jobs']=jobs;np.savez_compressed(OUT/'proposed_arrays.npz',**arrays)
 with gzip.GzipFile(filename=str(OUT/'proposed_allocations.json.gz'),mode='wb',mtime=0)as f:f.write(json.dumps(alloc,separators=(',',':')).encode())
 (OUT/'employment_capacity_regularization.json').write_text(json.dumps({'rule':'min(0.8*regional_jobs*relative_capacity/sum_capacity,2*relative_capacity); remainder through residential/mixed activity capacity','rationale':'Avoid magnifying one sparse mapped mall into tens of thousands of staff solely to fill a historical regional control. Threshold2 corresponds roughly to the low-area/high-intensity end of StageA function-prior ranges.','large_unknown_morphology_prior':'footprint>=800m2 without observed function -> mixed use:60% residential/40% employment; employment90m2 per relative worker; remains inferred','regions':report,'max_anchor_jobs':int(jobs.max())},indent=2));print(json.dumps(report,indent=2))
