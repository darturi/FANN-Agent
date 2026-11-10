"""Add bounded layer-zero progress observations to a copied qualified engine."""
import json
from contract import EXTRA,digest


def replace(text,old,new):
    if text.count(old)!=1:raise ValueError('Native source anchor differs: '+old[:100])
    return text.replace(old,new)


C=r'''
/* At most eight heap-fetch attempts before each of eight ordinal checkpoints.
 * Only already-scored, loaded layer-zero candidates enter this observation.
 * Native graph traversal and its own stop condition are never changed. */
void
FannbenchProgressProbe(Relation index, BlockNumber block, OffsetNumber offset,
                       ItemPointer tids, int count, double distance)
{
    static const int checkpoints[8] = {1,2,4,8,16,32,64,128};
    int window = -1;
    Relation heap;
    TupleTableSlot *slot;
    IndexFetchTableData *fetch;
    AttrNumber votesAtt;
    instr_time started, elapsed;
    if (!executionState.active || !executionState.progressFilterEnabled ||
        strcmp(executionState.mode,"native") == 0 || count <= 0) return;
    for (int w=0; w<8; w++)
        if (executionState.checkpointCount+1 == checkpoints[w]) window=w;
    if (window < 0 || executionState.progressFetches[window] >= 8 ||
        executionState.progressNodeCount >= 64) return;
    if (!OidIsValid(boundIndex) || RelationGetRelid(index) != boundIndex || !isfinite(distance))
        ereport(ERROR,(errmsg("progress probe requires bound index and finite scored distance")));
    for (int n=0; n<executionState.progressNodeCount; n++)
        if (executionState.progressBlocks[n]==block && executionState.progressOffsets[n]==offset) return;
    INSTR_TIME_SET_CURRENT(started);
    executionState.progressBlocks[executionState.progressNodeCount]=block;
    executionState.progressOffsets[executionState.progressNodeCount++]=offset;
    executionState.progressWindow=checkpoints[window];
    heap=table_open(index->rd_index->indrelid,AccessShareLock);
    if (RelationGetRelid(heap)!=boundRelation)
        ereport(ERROR,(errmsg("progress probe relation differs")));
    votesAtt=get_attnum(RelationGetRelid(heap),"total_votes");
    if (votesAtt==InvalidAttrNumber || TupleDescAttr(RelationGetDescr(heap),votesAtt-1)->atttypid!=INT8OID)
        ereport(ERROR,(errmsg("progress probe requires total_votes bigint")));
    slot=table_slot_create(heap,NULL);fetch=table_index_fetch_begin(heap);
    for (int t=0; t<count && executionState.progressFetches[window]<8; t++)
    {
        bool again=false,dead=false;
        ItemPointerData visible=tids[t];
        if (!ItemPointerIsValid(&visible)) continue;
        do
        {
            executionState.progressFetches[window]++;
            if (table_index_fetch_tuple(fetch,&visible,GetActiveSnapshot(),slot,&again,&dead))
            {
                bool nullVote,nullId;
                Datum vote=slot_getattr(slot,votesAtt,&nullVote);
                Datum id=slot_getattr(slot,boundId,&nullId);
                int n=executionState.progressRowCount++;
                bool passed=executionState.predicateLeafCount==0 ||
                    (!nullVote && DatumGetInt64(vote)>=executionState.queryPredicateThreshold);
                if (nullId || n>=64) ereport(ERROR,(errmsg("invalid progress probe receipt")));
                executionState.progressWindows[n]=checkpoints[window];
                executionState.progressIds[n]=DatumGetInt64(id);
                executionState.progressVotes[n]=nullVote?0:DatumGetInt64(vote);
                executionState.progressNulls[n]=nullVote;
                executionState.progressPassed[n]=passed;
                executionState.progressDistances[n]=distance;
                ExecClearTuple(slot);
            }
        } while (again && executionState.progressFetches[window]<8);
        table_index_fetch_reset(fetch);
    }
    table_index_fetch_end(fetch);ExecDropSingleTupleTableSlot(slot);table_close(heap,AccessShareLock);
    INSTR_TIME_SET_CURRENT(elapsed);INSTR_TIME_SUBTRACT(elapsed,started);
    executionState.featureCollectionNanos+=INSTR_TIME_GET_NANOSEC(elapsed);
}

static FannbenchValue
ProgressFeature(const char *name)
{
    FannbenchValue value={0};
    int examined=executionState.progressRowCount,passed=0,recent=0,recentPassed=0;
    double sum=0,min=0,previousMin=0;
    bool hasPrevious=false;
    value.type=FANNBENCH_UNAVAILABLE;
    if (!executionState.progressFilterEnabled) return value;
    for (int i=0;i<examined;i++)
    {
        bool inRecent=executionState.progressWindows[i]==executionState.progressWindow;
        if (inRecent) recent++;
        if (executionState.progressPassed[i])
        {
            double d=executionState.progressDistances[i];
            if (!passed || d<min) min=d;
            sum+=d;passed++;
            if (inRecent) recentPassed++;
            else if (!hasPrevious || d<previousMin) {previousMin=d;hasPrevious=true;}
        }
    }
    if (strcmp(name,"progress_has_valid")==0)
    {value.type=FANNBENCH_VALUE_BOOL;value.boolValue=passed>0;}
    else if (strcmp(name,"progress_window_checkpoint")==0 || strcmp(name,"progress_probe_examined")==0 ||
             strcmp(name,"progress_probe_passed")==0 || strcmp(name,"progress_recent_examined")==0 ||
             strcmp(name,"progress_recent_passed")==0)
    {
        value.type=FANNBENCH_VALUE_INT;
        value.intValue=strcmp(name,"progress_window_checkpoint")==0?executionState.progressWindow:
            strcmp(name,"progress_probe_examined")==0?examined:
            strcmp(name,"progress_probe_passed")==0?passed:
            strcmp(name,"progress_recent_examined")==0?recent:recentPassed;
    }
    else
    {
        value.type=FANNBENCH_VALUE_FLOAT;
        if (strcmp(name,"progress_probe_pass_ratio")==0) value.floatValue=examined?(double)passed/examined:0;
        else if (strcmp(name,"progress_recent_pass_ratio")==0) value.floatValue=recent?(double)recentPassed/recent:0;
        else if (strcmp(name,"progress_valid_distance_min_or_zero")==0) value.floatValue=passed?min:0;
        else if (strcmp(name,"progress_valid_distance_mean_or_zero")==0) value.floatValue=passed?sum/passed:0;
        else if (strcmp(name,"progress_valid_min_improvement_or_zero")==0) value.floatValue=hasPrevious && passed?Max(0,previousMin-min):0;
        else value.type=FANNBENCH_UNAVAILABLE;
    }
    return value;
}

static char *
ProgressProbeJson(void)
{
    StringInfoData out;initStringInfo(&out);
    appendStringInfo(&out,"{\"nonce\":\"%s\",\"enabled\":%s,\"nodes\":%d,\"fetches\":[",
        executionState.nonce,executionState.progressFilterEnabled?"true":"false",executionState.progressNodeCount);
    for (int w=0;w<8;w++) appendStringInfo(&out,"%s%d",w?",":"",executionState.progressFetches[w]);
    appendStringInfoString(&out,"],\"rows\":[");
    for (int i=0;i<executionState.progressRowCount;i++)
        appendStringInfo(&out,"%s[%d," INT64_FORMAT "," INT64_FORMAT ",%s,%.17g]",i?",":"",
            executionState.progressWindows[i],executionState.progressIds[i],executionState.progressVotes[i],
            executionState.progressNulls[i]?"true":"false",executionState.progressDistances[i]);
    appendStringInfoString(&out,"]}");return out.data;
}

PG_FUNCTION_INFO_V1(fannbench_progress_probe);
Datum fannbench_progress_probe(PG_FUNCTION_ARGS)
{
    PG_RETURN_TEXT_P(cstring_to_text(completedProgressProbe[0]?completedProgressProbe:
        "{\"enabled\":false,\"nodes\":0,\"fetches\":[0,0,0,0,0,0,0,0],\"rows\":[]}"));
}
'''


def patch_engine(directory):
    path=directory/'src/fannbench.c';s=path.read_text()
    s=replace(s,'static char completedLocalProbe[16384];','static char completedLocalProbe[16384];\nstatic char completedProgressProbe[24576];')
    s=replace(s,'    bool localFilterEnabled;', '''    bool localFilterEnabled;
    bool progressFilterEnabled;
    int progressWindow,progressNodeCount,progressRowCount,progressFetches[8];
    BlockNumber progressBlocks[64]; OffsetNumber progressOffsets[64];
    int progressWindows[64]; int64 progressIds[64],progressVotes[64];
    bool progressNulls[64],progressPassed[64]; double progressDistances[64];''')
    s=replace(s,'static void\nTraceCheckpoint(const char *decision)',C+'\nstatic void\nTraceCheckpoint(const char *decision)')
    s=replace(s,"    else completedLocalProbe[0] = '\\0';\n    ResetExecutionState();",'''    else completedLocalProbe[0] = '\\0';
    if (executionState.progressFilterEnabled && strcmp(executionState.traceLevel,"off")!=0)
    {char *receipt=ProgressProbeJson();strlcpy(completedProgressProbe,receipt,sizeof(completedProgressProbe));pfree(receipt);}
    else completedProgressProbe[0]='\\0';
    ResetExecutionState();''')
    s=replace(s,'        if (strcmp(group, "local_filter") == 0)', '''        if (strcmp(group,"progress_filter")==0)
        {executionState.progressFilterEnabled=true;executionState.queryContextEnabled=true;}
        else if (strcmp(group, "local_filter") == 0)''')
    s=replace(s,'    else if (strcmp(name, "local_probe_examined") == 0 || strcmp(name, "local_probe_passed") == 0)',
      '    else if (strncmp(name,"progress_",9)==0) value=ProgressFeature(name);\n    else if (strcmp(name, "local_probe_examined") == 0 || strcmp(name, "local_probe_passed") == 0)')
    s=replace(s,'\t\t"local_probe_examined", "local_probe_passed", "local_probe_pass_ratio",',
      '\t\t'+', '.join('"'+n+'"' for n in EXTRA)+',\n\t\t"local_probe_examined", "local_probe_passed", "local_probe_pass_ratio",')
    trace='''    if (executionState.progressFilterEnabled)
    {
'''
    for name in EXTRA:
        trace+='        {FannbenchValue v=ProgressFeature("'+name+'");'
        if name=='progress_has_valid':trace+='appendStringInfo(&line,",\\\"'+name+'\\\":%s",v.boolValue?"true":"false");}\n'
        elif name in ('progress_window_checkpoint','progress_probe_examined','progress_probe_passed','progress_recent_examined','progress_recent_passed'):
            trace+='appendStringInfo(&line,",\\\"'+name+'\\\":" INT64_FORMAT,v.intValue);}\n'
        else:trace+='appendStringInfo(&line,",\\\"'+name+'\\\":%.17g",v.floatValue);}\n'
    trace+='    }\n'
    s=replace(s,'    if (executionState.localFilterEnabled)\n    {\n        appendStringInfo(&line,',trace+'    if (executionState.localFilterEnabled)\n    {\n        appendStringInfo(&line,')
    path.write_text(s)
    h=directory/'src/fannbench.h';h.write_text(h.read_text()+'\nvoid FannbenchProgressProbe(Relation index, BlockNumber block, OffsetNumber offset, ItemPointer tids, int count, double distance);\n')
    p=directory/'src/hnswutils.c';u=p.read_text()
    anchor='\t\t\tif (eElement == NULL)\n\t\t\t\tcontinue;\n\t\t\tif (auditBlock != InvalidBlockNumber)'
    u=replace(u,anchor,'''\t\t\tif (eElement == NULL)
\t\t\t\tcontinue;
            if (lc==0 && !inserting && index!=NULL)
                FannbenchProgressProbe(index,eElement->blkno,eElement->offno,
                    eElement->heaptids,eElement->heaptidsLength,1.0+eDistance);
\t\t\tif (auditBlock != InvalidBlockNumber)''')
    p.write_text(u)


def patch_adapter(directory):
    p=directory/'native/registry.json';r=json.loads(p.read_text());template=r['definitions']['local_probe_examined']
    for name in EXTRA:
        d=dict(template);kind='bool' if name=='progress_has_valid' else 'int' if name in ('progress_window_checkpoint','progress_probe_examined','progress_probe_passed','progress_recent_examined','progress_recent_passed') else 'float'
        d.update(name=name,kind=kind,group='progress_filter',source='layer0_progress_v1',
          units='boolean' if kind=='bool' else 'checkpoint_ordinal' if name=='progress_window_checkpoint' else 'tuples' if kind=='int' else 'fraction' if name.endswith('ratio') else 'cosine_distance',
          population='bounded_scored_loaded_layer0_candidates',availability='enabled',
          description='Layer-zero progress observation; empty summaries are explicitly zero, exposed by counts/has_valid: '+name,
          collection_cost='at_most_64_additional_heap_fetch_attempts_per_request_spread_8_per_eligible_window')
        r['definitions'][name]=d;r['capabilities']['pgvector']['checkpoint_fields'].append(name)
    r['registry_hash']=digest({'base_registry':r['registry_hash'],'progress_filter_v1':{n:r['definitions'][n] for n in EXTRA}})
    p.write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
    p=directory/'profiles.py';s=p.read_text().replace('/local-filter-v1",','/local-filter-v1/progress-filter-v1",')
    s=replace(s,'        "local_filter",','        "local_filter",\n        "progress_filter",');p.write_text(s)
    p=directory/'backend.py';s=p.read_text()+'''
FUNCTIONS += """
CREATE OR REPLACE FUNCTION fannagent.progress_probe()
 RETURNS text AS '$libdir/vector','fannbench_progress_probe'
 LANGUAGE C VOLATILE PARALLEL UNSAFE;
"""
''';p.write_text(s)
    p=directory/'native/transport.py';s=p.read_text()
    s=replace(s,'''                        if isinstance(value, bool) or not isinstance(value, (int, float)):
                            raise ValueError(f"feature {name} is not numeric")''','''                        if definition.kind == "bool":
                            if not isinstance(value, bool):
                                raise ValueError(f"feature {name} is not Boolean")
                        elif isinstance(value, bool) or not isinstance(value, (int, float)):
                            raise ValueError(f"feature {name} is not numeric")''')
    p.write_text(s)
