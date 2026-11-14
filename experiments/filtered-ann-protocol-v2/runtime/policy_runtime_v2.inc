/* Versioned causal checkpoint execution. No references, labels or exact reader. */
#define V2_COUNT 1
#define V2_DISTANCE 2
#define V2_TURNOVER 4
#define V2_DECIDE 8
static uint64 v2PreviousTids[10];
static bool v2PreviousFull;
static int v2PreviousCheckpoint;
static int v2CurrentArm;
static bool v2AuditEnabled;
typedef struct V2Frame {
 int cp, mask, count, turnover;
 double tenth, gap;
 bool full, hasgap, hasturn, decision;
} V2Frame;
static V2Frame v2Frames[3];
static int v2FrameCount;

bool FannbenchV2ArmDeclared(int arm) { return V2ArmDeclared(arm); }
bool FannbenchV2EnabledForPredicate(int arm,int filter) {
 return V2Mask(arm,filter,16) || V2Mask(arm,filter,32) || V2Mask(arm,filter,64);
}
void FannbenchV2Begin(int arm) {
 v2PreviousFull=false;v2PreviousCheckpoint=0;v2CurrentArm=arm;v2FrameCount=0;
}

static void V2RetainedNode(pairingheap_node *node,char *base,int mask,int *count,double top[10],uint64 tids[10]) {
 while(node) {
  HnswSearchCandidate *candidate=HnswGetSearchCandidate(w_node,node);
  HnswElement element=HnswPtrAccess(base,candidate->element);
  for(int i=0;i<element->heaptidsLength;i++) {
   ItemPointer tid=&element->heaptids[i];
   if(!FannbenchShadowQualifies(tid)) continue;
   if(mask & V2_DISTANCE) {
    double distance=Max(0.0,Min(2.0,1.0+candidate->distance));
    uint64 key=((uint64)ItemPointerGetBlockNumber(tid)<<16)|ItemPointerGetOffsetNumber(tid);
    int pos=Min(*count,9);
    if(!isfinite(distance)) elog(ERROR,"nonfinite v2 retained distance");
    if(*count<10 || distance<top[9] || (distance==top[9] && key<tids[9])) {
     while(pos>0 && (distance<top[pos-1] || (distance==top[pos-1] && key<tids[pos-1]))) {top[pos]=top[pos-1];tids[pos]=tids[pos-1];pos--;}
     top[pos]=distance;tids[pos]=key;
    }
   }
   (*count)++;
  }
  V2RetainedNode(node->first_child,base,mask,count,top,tids);node=node->next_sibling;
 }
}
static bool V2Stop(int arm,int cp,pairingheap *pending,pairingheap *retained,char *base) {
 int mask=V2Mask(arm,FannbenchStudyThreshold(),cp),count=0,turnover=0;
 double top[10]={0},gap=0;uint64 tids[10]={0};bool full=false,hasgap=false,hasturn=false;
 volatile bool decision=false; /* force-continue controls still execute the comparisons */
 if(!mask) return false;
 if(mask & V2_COUNT) {FannbenchShadowStart();V2RetainedNode(retained->ph_root,base,mask,&count,top,tids);}
 full=(mask & V2_DISTANCE) && count>=10;
 if(full && !pairingheap_is_empty(pending)) {
  double frontier=Max(0.0,Min(2.0,1.0+HnswGetSearchCandidate(c_node,pairingheap_first(pending))->distance));
  if(!isfinite(frontier)) elog(ERROR,"nonfinite v2 frontier");
  gap=frontier-top[9];hasgap=true;
 }
 hasturn=(mask & V2_TURNOVER) && full && v2PreviousFull && v2PreviousCheckpoint==(cp==64?32:cp==32?16:0) && cp!=16;
 if(hasturn) for(int i=0;i<10;i++) {bool found=false;for(int j=0;j<10;j++) found|=tids[i]==v2PreviousTids[j];turnover+=!found;}
 if(mask & V2_DISTANCE) {v2PreviousFull=full;v2PreviousCheckpoint=cp;memcpy(v2PreviousTids,tids,sizeof(tids));}
 if(mask & V2_DECIDE) decision=V2Decision(arm,FannbenchStudyThreshold(),cp,count,top[9],gap,turnover,full,hasgap,hasturn);
 if(v2AuditEnabled) {
  V2Frame *f;
  if(v2FrameCount>=3) elog(ERROR,"v2 checkpoint frame overflow");
  f=&v2Frames[v2FrameCount++];f->cp=cp;f->mask=mask;f->count=count;f->tenth=top[9];f->gap=gap;f->turnover=turnover;f->full=full;f->hasgap=hasgap;f->hasturn=hasturn;f->decision=decision;
 }
 return decision && !V2ForceContinue(arm);
}
PG_FUNCTION_INFO_V1(fannbench_v2_audit_enable);
Datum fannbench_v2_audit_enable(PG_FUNCTION_ARGS) {v2AuditEnabled=PG_GETARG_BOOL(0);v2FrameCount=0;PG_RETURN_VOID();}
PG_FUNCTION_INFO_V1(fannbench_v2_audit_read);
Datum fannbench_v2_audit_read(PG_FUNCTION_ARGS) {
 StringInfoData out;initStringInfo(&out);appendStringInfo(&out,"{\"arm\":%d,\"frames\":[",v2CurrentArm);
 for(int i=0;i<v2FrameCount;i++) {
  V2Frame *f=&v2Frames[i];if(i) appendStringInfoChar(&out,',');
  appendStringInfo(&out,"{\"checkpoint\":%d,\"mask\":%d,\"qualifying_count\":",f->cp,f->mask);
  if(f->mask & V2_COUNT) appendStringInfo(&out,"%d",f->count);else appendStringInfoString(&out,"null");
  appendStringInfoString(&out,",\"tenth_distance\":");if(f->full) appendStringInfo(&out,"%.17g",f->tenth);else appendStringInfoString(&out,"null");
  appendStringInfoString(&out,",\"frontier_gap\":");if(f->hasgap) appendStringInfo(&out,"%.17g",f->gap);else appendStringInfoString(&out,"null");
  appendStringInfoString(&out,",\"top10_new_since_previous\":");if(f->hasturn) appendStringInfo(&out,"%d",f->turnover);else appendStringInfoString(&out,"null");
  appendStringInfo(&out,",\"decision\":%s}",f->decision?"true":"false");
 }
 appendStringInfoString(&out,"]}");PG_RETURN_TEXT_P(cstring_to_text(out.data));
}
