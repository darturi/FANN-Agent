"""Observed per-condition request-time reductions, not confirmed causal speedups."""
import csv,hashlib,json,os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/fannagent-heatmap-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap,TwoSlopeNorm
import numpy as np
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[2];RESULTS=BASE/'returns/job-23045686/results'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
verification=RESULTS/'local-verification.json';freeze=json.loads((BASE/'freeze/unguarded-development-assessment-v1.json').read_text());assert sha(verification)==freeze['verification_sha256']
v=json.loads(verification.read_text());elig=json.loads((RESULTS/'eligibility.json').read_text());receipt=json.loads((RESULTS/'receipt.json').read_text());assert sha(RESULTS/'eligibility.json')==receipt['raw_sha256']['eligibility.json']
cols=('-1','32','108','192','310','527','743')
names=('native640','noop640','conservative_a','moderate_b_fixed','broad_c_fixed')
labels=('Native640\n(baseline)','Always continue\n(control)','Conservative','Moderate','Broad')
count=len(elig['-1']);means=np.array([[v['metrics'][n]['per_condition'][t]['mean_ms'] for t in cols] for n in names]);reduction=100*(1-means/means[0]);assert np.allclose(reduction[0],0)
rows=[]
for i,n in enumerate(names):
 for j,t in enumerate(cols):rows.append({'search':n,'filter':'No_filter' if t=='-1' else 'total_votes >= '+t,'eligible_records':len(elig[t]),'eligible_percent':100*len(elig[t])/count,'mean_ms':float(means[i,j]),'native640_mean_ms':float(means[0,j]),'latency_reduction_percent':float(reduction[i,j]),'latency_ratio_to_native640':float(means[i,j]/means[0,j])})
with (HERE/'latency-heatmap-data.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.fonttype':'none'})
fig=plt.figure(figsize=(16,6.8),facecolor='white');ax=fig.add_axes([.155,.245,.76,.51]);cax=fig.add_axes([.934,.245,.013,.51])
cmap=LinearSegmentedColormap.from_list('slower_neutral_faster',['#c66b35','#fffdf8','#2674a5']);norm=TwoSlopeNorm(vmin=-20,vcenter=0,vmax=20)
im=ax.imshow(reduction,cmap=cmap,norm=norm,aspect='auto')
ax.set_yticks(range(5),labels=labels);ax.tick_params(axis='y',length=0,pad=12,labelsize=12)
xticks=[('No_filter' if t=='-1' else 'total_votes ≥ '+t)+'\n'+f'{100*len(elig[t])/count:.1f}% eligible' for t in cols]
ax.set_xticks(range(7),labels=xticks);ax.tick_params(axis='x',length=0,pad=12,labelsize=10.5)
ax.set_xticks(np.arange(-.5,7,1),minor=True);ax.set_yticks(np.arange(-.5,5,1),minor=True);ax.grid(which='minor',color='white',linewidth=2.5);ax.tick_params(which='minor',bottom=False,left=False)
for s in ax.spines.values():s.set_visible(False)
for i in range(5):
 for j in range(7):
  value=reduction[i,j];color='white' if value>=13 else '#163040'
  text='0.0%' if i==0 else f'{value:+.1f}%'
  ax.text(j,i-.12,text,ha='center',va='center',fontsize=15,fontweight='bold',color=color)
  ax.text(j,i+.20,f'{means[i,j]:.2f} ms',ha='center',va='center',fontsize=10.5,color=color)
cb=fig.colorbar(im,cax=cax,ticks=[-20,-10,0,10,20]);cb.outline.set_visible(False);cb.ax.tick_params(length=0,labelsize=10,pad=5);cb.set_label('Latency reduction (%)',labelpad=10,fontsize=11)
fig.text(.155,.92,'Observed latency reduction by filter condition',fontsize=22,fontweight='bold',color='#173247')
fig.text(.155,.868,'Compared with native640 in the same column  ·  Positive = faster; negative = slower',fontsize=12,color='#415568')
fig.text(.155,.81,'Cell labels: reduction (%) and mean query time (ms)',fontsize=10.5,color='#596875')
fig.text(.535,.11,'Filter becomes more restrictive → fewer records qualify',ha='center',fontsize=11.5,color='#334c5f')
fig.text(.155,.055,'Unguarded development run 23045686 · 450 groups per condition · Exact search used only for offline recall scoring',fontsize=10,color='#596875')
fig.text(.155,.021,'Timing controls did not establish equivalence. These are descriptive measurements, not confirmed speedups.',fontsize=10.5,color='#9b472b',fontweight='medium')
for ext in ('png','svg'):fig.savefig(HERE/('latency-reduction-heatmap.'+ext),dpi=200,facecolor='white')
plt.close(fig)
(HERE/'plot-metadata.json').write_text(json.dumps({'source_verification_sha256':sha(verification),'eligibility_sha256':sha(RESULTS/'eligibility.json'),'job':'23045686','definition':'100 * (1 - search mean latency / native640 mean latency in same filter condition)','columns':list(cols),'rows':list(names),'order':'unfiltered then increasing restriction, total_votes>=32/108/192/310/527/743','limits':'single development allocation; controls do not establish equivalence; not confirmed causal speedups','groups':450,'all_six_filters_retained':True,'validation_test_outcomes_opened':False,'values':rows},indent=2)+'\n')
print(json.dumps({'png':str(HERE/'latency-reduction-heatmap.png'),'values_percent':np.round(reduction,2).tolist()},indent=2))
