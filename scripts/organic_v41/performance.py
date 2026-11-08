"""Fresh-process offline parse costs; NOT game rendering/memory benchmark."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'docs/organic-v41'
code="""import sys,json,gzip,time,resource;from pathlib import Path;p=Path(sys.argv[1]);t=time.monotonic();d=json.load(gzip.open(p,'rt'));print(json.dumps({'gzip_bytes':p.stat().st_size,'points':len(d['points']),'groups':len(d['pops']),'parse_seconds':time.monotonic()-t,'python_peak_rss_bytes_macos':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))"""
rr={}
for label,p in [('current',ROOT/'assets/JKT/demand_data.json.gz'),('S0_OD30_candidate',OUT/'candidate-demand.json.gz'),('S0_OD40_control',OUT/'od40/candidate-demand.json.gz')]:rr[label]=json.loads(subprocess.check_output([sys.executable,'-c',code,str(p)],text=True))
rr['scope']='Single fresh Python process per file; warm OS cache, macOS ru_maxrss bytes. No FPS, network simulation or proposed game-runtime claim.';rr['baseline_runtime_evidence']='../organic-stage-b/runtime_verification.json';rr['candidate_runtime']='Not run, StageA does not install assets';(OUT/'performance.json').write_text(json.dumps(rr,indent=2)+'\n');print(json.dumps(rr,indent=2))
