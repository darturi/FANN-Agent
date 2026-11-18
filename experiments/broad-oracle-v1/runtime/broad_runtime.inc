/* Versioned bounded VM. Immutable program data; query-local state; no I/O. */
typedef struct V3Node {int op,a,b,c; double value;} V3Node;
typedef struct V3Update {int slot,root;} V3Update;
typedef struct V3Step {int mask,root,update,count,previous;} V3Step;
typedef struct V3Program {int arm,filter,step,last,fuel,slots,force;} V3Program;
#include "compiled_v3.inc"
#define V3_COUNT 1
#define V3_DISTANCE 2
#define V3_TURNOVER 4
#define V3_PREVIOUS 8
#define V3_DECIDE 16
#define V3_FRONTIER 32
#define V3_FEATURES 13
typedef struct V3Value {double value; bool available;} V3Value;
typedef struct V3Frame {
 int cp,mask,remaining,countUnits; bool exhausted,fault,decision;
 V3Value features[V3_FEATURES]; double state[32]; uint64 tids[10];
} V3Frame;
static const V3Program *v3Program;
static double v3Registers[32];
static int v3Remaining,v3PreviousCheckpoint,v3CurrentArm,v3FrameCount;
static bool v3Exhausted,v3Fault,v3AuditEnabled,v3PreviousFull;
static uint64 v3PreviousTids[10];
static V3Value v3PreviousCount,v3PreviousTenth,v3PreviousGap;
static V3Frame v3Frames[4096];
static V3Value V3Missing(void) {V3Value x={0,false};return x;}
static V3Value V3Number(double n) {V3Value x={n,true};return x;}
static bool V3Charge(int units) {
 if(v3Exhausted||v3Fault) return false;
 if(units<0||v3Remaining<units) {v3Exhausted=true;return false;}
 v3Remaining-=units;return true;
}
bool FannbenchV3ArmDeclared(int arm) {return V3ArmDeclared(arm);}
void FannbenchV3Begin(int arm,int filter) {
 v3Program=NULL;v3CurrentArm=arm;v3FrameCount=0;v3Remaining=0;
 v3Exhausted=false;v3Fault=false;v3PreviousFull=false;v3PreviousCheckpoint=0;
 v3PreviousCount=V3Missing();v3PreviousTenth=V3Missing();v3PreviousGap=V3Missing();
 memset(v3Registers,0,sizeof(v3Registers));
 for(Size i=0;i<lengthof(v3Programs);i++)
  if(v3Programs[i].arm==arm&&v3Programs[i].filter==filter) {
   v3Program=&v3Programs[i];v3Remaining=v3Program->fuel;break;
  }
}
bool FannbenchV3Enabled(void) {return v3Program!=NULL;}
int FannbenchV3Last(void) {return v3Program?v3Program->last:0;}

static V3Value V3Eval(int index,const V3Value values[V3_FEATURES],int depth) {
 const V3Node *n;V3Value a,b;double result=0;
 if(!V3Charge(1)) return V3Missing();
 if(index<0||(Size)index>=lengthof(v3Nodes)||depth>64) {v3Fault=true;return V3Missing();}
 n=&v3Nodes[index];
 if(n->op<=1) return V3Number(n->value);
 if(n->op==2) return values[n->a];
 if(n->op==3) return V3Number(v3Registers[n->a]);
 a=V3Eval(n->a,values,depth+1);
 if(n->op==19) return V3Number(a.available);
 if(n->op==18) return a.available?V3Number(!a.value):V3Missing();
 if(n->op==20) return a.available?V3Eval(a.value?n->b:n->c,values,depth+1):V3Missing();
 if((n->op==16&&a.available&&!a.value)||(n->op==17&&a.available&&a.value)) return a;
 if(n->op==21&&a.available) return a;
 if(n->op==10) return a.available?V3Number(fabs(a.value)):V3Missing();
 b=V3Eval(n->b,values,depth+1);
 if(n->op==21) return b;
 if(n->op==16) {
  if(b.available&&!b.value) return V3Number(0);
  return a.available&&b.available?V3Number(1):V3Missing();
 }
 if(n->op==17) {
  if(b.available&&b.value) return V3Number(1);
  return a.available&&b.available?V3Number(0):V3Missing();
 }
 if(!a.available||!b.available) return V3Missing();
 switch(n->op) {
  case 4:result=a.value+b.value;break;
  case 5:result=a.value-b.value;break;
  case 6:result=a.value*b.value;break;
  case 7:if(b.value==0) {v3Fault=true;return V3Missing();}result=a.value/b.value;break;
  case 8:result=Min(a.value,b.value);break;
  case 9:result=Max(a.value,b.value);break;
  case 11:result=a.value<b.value;break;
  case 12:result=a.value<=b.value;break;
  case 13:result=a.value>b.value;break;
  case 14:result=a.value>=b.value;break;
  case 15:result=a.value==b.value;break;
  default:v3Fault=true;return V3Missing();
 }
 if(!isfinite(result)) {v3Fault=true;return V3Missing();}
 return V3Number(result);
}

static void V3Retained(pairingheap_node *node,char *base,int mask,int *count,int *total,
                       int *countUnits,double top[10],uint64 tids[10]) {
 while(node&&!v3Exhausted&&!v3Fault) {
  HnswSearchCandidate *candidate=HnswGetSearchCandidate(w_node,node);
  HnswElement element=HnswPtrAccess(base,candidate->element);
  if(!V3Charge(1)) return;
  (*countUnits)++;
  for(int i=0;i<element->heaptidsLength;i++) {
   ItemPointer tid=&element->heaptids[i];
   if(!V3Charge(1)) return;
   (*countUnits)++;(*total)++;
   if(!FannbenchShadowQualifies(tid)) continue;
   if(mask&V3_DISTANCE) {
    double distance=Max(0.0,Min(2.0,1.0+candidate->distance));
    uint64 key=((uint64)ItemPointerGetBlockNumber(tid)<<16)|ItemPointerGetOffsetNumber(tid);
    int pos=Min(*count,9);
    /* Fixed conservative charge covers the bounded top-ten insertion. */
    if(!V3Charge(16)) return;
    if(!isfinite(distance)) {v3Fault=true;return;}
    if(*count<10||distance<top[9]||(distance==top[9]&&key<tids[9])) {
     while(pos>0&&(distance<top[pos-1]||(distance==top[pos-1]&&key<tids[pos-1]))) {
      top[pos]=top[pos-1];tids[pos]=tids[pos-1];pos--;
     }
     top[pos]=distance;tids[pos]=key;
    }
   }
   (*count)++;
  }
  V3Retained(node->first_child,base,mask,count,total,countUnits,top,tids);
  node=node->next_sibling;
 }
}

static bool V3Stop(int cp,int work,pairingheap *pending,pairingheap *retained,char *base) {
 const V3Step *step;int mask,count=0,total=0,countUnits=0,turnover=0;
 double top[10]={0},next[32],frontier=0;uint64 tids[10]={0};
 bool full=false,hasFrontier=false,hasTurn=false,samePrevious=false;
 V3Value values[V3_FEATURES],result=V3Missing();volatile bool decision=false;
 if(!v3Program||v3Exhausted||v3Fault||cp<1||cp>v3Program->last) return false;
 step=&v3Steps[v3Program->step+cp];mask=step->mask;
 if(!mask) return false;
 for(int i=0;i<V3_FEATURES;i++) values[i]=V3Missing();
 values[0]=V3Number(cp);values[1]=V3Number(work);
 if(mask&V3_COUNT) {
  FannbenchShadowStart();V3Retained(retained->ph_root,base,mask,&count,&total,&countUnits,top,tids);
  if(!v3Exhausted&&!v3Fault) {values[2]=V3Number(count);values[9]=V3Number(total);}
 }
 full=(mask&V3_DISTANCE)&&count>=10;
 if((mask&(V3_DISTANCE|V3_FRONTIER))&&V3Charge(1)) {
  if(!pairingheap_is_empty(pending)) {
   frontier=Max(0.0,Min(2.0,1.0+HnswGetSearchCandidate(c_node,pairingheap_first(pending))->distance));
   hasFrontier=isfinite(frontier);if(!hasFrontier) v3Fault=true;
   else values[8]=V3Number(frontier);
  }
 }
 if(mask&V3_DISTANCE) {
  if(count>=1) values[6]=V3Number(top[0]);
  if(count>=5) values[7]=V3Number(top[4]);
  if(full) values[3]=V3Number(top[9]);
  if(full&&hasFrontier) values[4]=V3Number(frontier-top[9]);
 }
 samePrevious=v3PreviousCheckpoint==step->previous&&step->previous>0;
 if((mask&V3_PREVIOUS)&&samePrevious) {
  values[10]=v3PreviousCount;values[11]=v3PreviousTenth;values[12]=v3PreviousGap;
 }
 hasTurn=(mask&V3_TURNOVER)&&full&&v3PreviousFull&&samePrevious;
 if(hasTurn&&V3Charge(100)) {
  for(int i=0;i<10;i++) {bool found=false;for(int j=0;j<10;j++) found|=tids[i]==v3PreviousTids[j];turnover+=!found;}
  values[5]=V3Number(turnover);
 }
 if(mask&V3_COUNT) {
  v3PreviousCount=values[2];v3PreviousTenth=values[3];v3PreviousGap=values[4];
  v3PreviousCheckpoint=cp;v3PreviousFull=full;memcpy(v3PreviousTids,tids,sizeof(tids));
 }
 if((mask&V3_DECIDE)&&!v3Exhausted&&!v3Fault) {
  result=V3Eval(step->root,values,0);
  memcpy(next,v3Registers,sizeof(next));
  for(int i=0;i<step->count;i++) {
   const V3Update *update=&v3Updates[step->update+i];
   V3Value value=V3Eval(update->root,values,0);
   if(value.available) next[update->slot]=value.value;
  }
  if(!v3Exhausted&&!v3Fault) {
   memcpy(v3Registers,next,sizeof(next));decision=result.available&&result.value!=0;
  }
 }
 if(v3AuditEnabled) {
  V3Frame *frame;
  if(v3FrameCount>=4096) elog(ERROR,"v3 audit frame overflow");
  frame=&v3Frames[v3FrameCount++];frame->cp=cp;frame->mask=mask;frame->remaining=v3Remaining;
  frame->countUnits=countUnits;frame->decision=decision;frame->exhausted=v3Exhausted;frame->fault=v3Fault;
  memcpy(frame->features,values,sizeof(values));memcpy(frame->state,v3Registers,sizeof(v3Registers));
  memcpy(frame->tids,tids,sizeof(tids));
 }
 return decision&&!v3Program->force;
}
PG_FUNCTION_INFO_V1(fannbench_v3_audit_enable);
Datum fannbench_v3_audit_enable(PG_FUNCTION_ARGS) {v3AuditEnabled=PG_GETARG_BOOL(0);v3FrameCount=0;PG_RETURN_VOID();}
PG_FUNCTION_INFO_V1(fannbench_v3_audit_read);
Datum fannbench_v3_audit_read(PG_FUNCTION_ARGS) {
 StringInfoData out;initStringInfo(&out);
 appendStringInfo(&out,"{\"arm\":%d,\"exhausted\":%s,\"fault\":%s,\"frames\":[",v3CurrentArm,v3Exhausted?"true":"false",v3Fault?"true":"false");
 for(int i=0;i<v3FrameCount;i++) {
  V3Frame *f=&v3Frames[i];if(i) appendStringInfoChar(&out,',');
  appendStringInfo(&out,"{\"checkpoint\":%d,\"mask\":%d,\"remaining\":%d,\"count_units\":%d,\"decision\":%s,\"exhausted\":%s,\"fault\":%s,\"values\":[",f->cp,f->mask,f->remaining,f->countUnits,f->decision?"true":"false",f->exhausted?"true":"false",f->fault?"true":"false");
  for(int j=0;j<V3_FEATURES;j++) {if(j) appendStringInfoChar(&out,',');if(f->features[j].available) appendStringInfo(&out,"%.17g",f->features[j].value);else appendStringInfoString(&out,"null");}
  appendStringInfoString(&out,"],\"top_tids\":[");
  for(int j=0;j<((f->mask&V3_DISTANCE)?Min(10,(int)f->features[2].value):0);j++) {
   if(j) appendStringInfoChar(&out,',');
   appendStringInfo(&out,"\"" UINT64_FORMAT "\"",f->tids[j]);
  }
  appendStringInfoString(&out,"],\"state\":[");
  for(int j=0;j<(v3Program?v3Program->slots:0);j++) {if(j) appendStringInfoChar(&out,',');appendStringInfo(&out,"%.17g",f->state[j]);}
  appendStringInfoString(&out,"]}");
 }
 appendStringInfoString(&out,"]}");PG_RETURN_TEXT_P(cstring_to_text(out.data));
}
