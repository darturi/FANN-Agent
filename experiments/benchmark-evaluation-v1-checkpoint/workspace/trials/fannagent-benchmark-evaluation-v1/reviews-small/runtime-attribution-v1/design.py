"""Fixed complete reader/role/CPU crossover; no data-driven schedule choices."""
import hashlib
FAMILIES=('native640','noop640','conservative_a','moderate_b_fixed','broad_c_fixed')
ARMS={'native640':None,'noop640':6,'conservative_a':7,'moderate_b_fixed':8,'broad_c_fixed':9}
SEED='reviews-reader-cpu-attribution-v1'
# Two mirrored five-rotation Latin cycles: every backend runs every family twice.
BLOCKS=tuple((0,r) for r in range(5))+tuple((1,r) for r in reversed(range(5)))
BASE=(0,1,19,2,18,3,17,4,16,5,15,6,14,7,13,8,12,9,11,10)
TIMING_REQUESTS=630000;WARMUPS=14000
TIMING_ATTEMPTS=666050;WORK_ATTEMPTS=18900;TOTAL_ATTEMPTS=684950

def role(reader,rotation):return FAMILIES[(reader%5+rotation)%5]
def cpu_for(reader,ti,cpus):return cpus[(reader//5+ti)%4]
def order_for(j,cycle,rotation,ti):
 offset=(j+rotation+ti)%20;order=[(v+offset)%20 for v in BASE]
 return list(reversed(order)) if cycle else order

def ordered(queries,t,cycle,rotation):
 from common import threshold
 cases=sorted((q for q in queries if threshold(q)==t),key=lambda q:hashlib.sha256((SEED+':'+str(rotation)+':'+q['id'].rsplit('-',1)[0]).encode()).hexdigest())
 return list(reversed(cases)) if cycle else cases

def forward_index(j,cycle,n):return n-1-j if cycle else j
