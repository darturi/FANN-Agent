"""Opt-in, bounded observations of heap metadata for already scored graph nodes.

Transforms copied source only. No graph queue, score, visit order or native stop
condition is changed. All heap reads occur synchronously inside the query timer.
"""
from contract import EXTRA, digest


def replace(text, old, new):
    if text.count(old) != 1: raise ValueError('Native source anchor differs: ' + old[:100])
    return text.replace(old, new)


PROBE = r'''
/* Research-only local-filter-v1: first 64 distinct, already scored graph nodes.
 * Heap visibility uses the query snapshot. No nearest-neighbor truth is read. */
bool
FannbenchLocalProbeEnabled(void)
{
    return executionState.active && executionState.localFilterEnabled &&
        strcmp(executionState.mode, "native") != 0 && executionState.localProbeNodes < 64;
}

void
FannbenchLocalProbe(Relation index, BlockNumber block, OffsetNumber offset,
                   ItemPointer tids, int count)
{
    Relation heap;
    TupleTableSlot *slot;
    IndexFetchTableData *fetch;
    AttrNumber votesAtt;
    instr_time started, elapsed;
    if (!FannbenchLocalProbeEnabled()) return;
    if (!OidIsValid(boundIndex) || RelationGetRelid(index) != boundIndex)
        ereport(ERROR, (errmsg("local probe requires the bound HNSW index")));
    for (int i = 0; i < executionState.localProbeNodes; i++)
        if (executionState.localProbeBlocks[i] == block && executionState.localProbeOffsets[i] == offset)
            return;
    INSTR_TIME_SET_CURRENT(started);
    executionState.localProbeBlocks[executionState.localProbeNodes] = block;
    executionState.localProbeOffsets[executionState.localProbeNodes++] = offset;
    heap = table_open(index->rd_index->indrelid, AccessShareLock);
    if (RelationGetRelid(heap) != boundRelation)
        ereport(ERROR, (errmsg("local probe relation differs")));
    votesAtt = get_attnum(RelationGetRelid(heap), "total_votes");
    if (votesAtt == InvalidAttrNumber || TupleDescAttr(RelationGetDescr(heap), votesAtt - 1)->atttypid != INT8OID)
        ereport(ERROR, (errmsg("local probe requires total_votes bigint")));
    slot = table_slot_create(heap, NULL);
    fetch = table_index_fetch_begin(heap);
    for (int i = 0; i < count && executionState.localProbeExamined < 64; i++)
    {
        bool again = false, dead = false;
        ItemPointerData visible = tids[i];
        if (!ItemPointerIsValid(&visible)) continue;
        do
        {
            if (table_index_fetch_tuple(fetch, &visible, GetActiveSnapshot(), slot, &again, &dead))
            {
                bool nullVote, nullId;
                Datum vote = slot_getattr(slot, votesAtt, &nullVote);
                Datum id = slot_getattr(slot, boundId, &nullId);
                int n = executionState.localProbeExamined++;
                bool passed = executionState.predicateLeafCount == 0 ||
                    (!nullVote && DatumGetInt64(vote) >= executionState.queryPredicateThreshold);
                if (nullId) ereport(ERROR, (errmsg("local probe ID is null")));
                executionState.localProbeIds[n] = DatumGetInt64(id);
                executionState.localProbeVotes[n] = nullVote ? 0 : DatumGetInt64(vote);
                executionState.localProbeNulls[n] = nullVote;
                if (passed) executionState.localProbePassed++;
                ExecClearTuple(slot);
            }
        } while (again && executionState.localProbeExamined < 64);
        table_index_fetch_reset(fetch);
    }
    table_index_fetch_end(fetch);
    ExecDropSingleTupleTableSlot(slot);
    table_close(heap, AccessShareLock);
    INSTR_TIME_SET_CURRENT(elapsed);
    INSTR_TIME_SUBTRACT(elapsed, started);
    executionState.featureCollectionNanos += INSTR_TIME_GET_NANOSEC(elapsed);
}

/* Qualification-only receipt; serialize only traced executions, never serving. */
static char *
LocalProbeJson(void)
{
    StringInfoData out;
    initStringInfo(&out);
    appendStringInfo(&out, "{\"nonce\":\"%s\",\"enabled\":%s,\"nodes\":%d,\"examined\":%d,\"passed\":%d,\"rows\":[",
        executionState.nonce, executionState.localFilterEnabled ? "true" : "false", executionState.localProbeNodes,
        executionState.localProbeExamined, executionState.localProbePassed);
    for (int i = 0; i < executionState.localProbeExamined; i++)
        appendStringInfo(&out, "%s[" INT64_FORMAT "," INT64_FORMAT ",%s]", i ? "," : "",
            executionState.localProbeIds[i], executionState.localProbeVotes[i],
            executionState.localProbeNulls[i] ? "true" : "false");
    appendStringInfoString(&out, "]}");
    return out.data;
}

PG_FUNCTION_INFO_V1(fannbench_local_probe);
Datum
fannbench_local_probe(PG_FUNCTION_ARGS)
{
    PG_RETURN_TEXT_P(cstring_to_text(completedLocalProbe[0] ? completedLocalProbe :
        "{\"enabled\":false,\"nodes\":0,\"examined\":0,\"passed\":0,\"rows\":[]}"));
}
'''


def patch_engine(directory):
    cpath = directory / 'src/fannbench.c'; c = cpath.read_text()
    c = replace(c, 'static char completedTrace[MAXPGPATH];', 'static char completedTrace[MAXPGPATH];\nstatic char completedLocalProbe[16384];')
    c = replace(c, '\tbool\t\tqueryContextEnabled;', '''\tbool\t\tqueryContextEnabled;
    bool localFilterEnabled;
    int localProbeNodes, localProbeExamined, localProbePassed;
    BlockNumber localProbeBlocks[64];
    OffsetNumber localProbeOffsets[64];
    int64 localProbeIds[64], localProbeVotes[64];
    bool localProbeNulls[64];''')
    anchor = 'static void\nTraceCheckpoint(const char *decision)'
    c = replace(c, anchor, PROBE + '\n' + anchor)
    c = replace(c, '    ResetExecutionState();\n\tpfree(nonce);\n\tPG_RETURN_TEXT_P(cstring_to_text(result.data));', '''    if (executionState.localFilterEnabled && strcmp(executionState.traceLevel, "off") != 0)
    {
        char *receipt = LocalProbeJson();
        strlcpy(completedLocalProbe, receipt, sizeof(completedLocalProbe));
        pfree(receipt);
    }
    else completedLocalProbe[0] = '\\0';
    ResetExecutionState();
\tpfree(nonce);
\tPG_RETURN_TEXT_P(cstring_to_text(result.data));''')
    c = replace(c, '\tif (executionState.queryContextEnabled)\n\t\tappendStringInfo', '''    if (executionState.localFilterEnabled)
    {
        appendStringInfo(&line, ",\\\"local_probe_examined\\\":%d,\\\"local_probe_passed\\\":%d",
            executionState.localProbeExamined, executionState.localProbePassed);
        if (executionState.localProbeExamined > 0)
            appendStringInfo(&line, ",\\\"local_probe_pass_ratio\\\":%.17g",
                (double) executionState.localProbePassed / executionState.localProbeExamined);
    }
\tif (executionState.queryContextEnabled)
\t\tappendStringInfo''')
    c = replace(c, '"k", "predicate_leaf_count", "query_predicate_threshold", "checkpoint_index",',
        '"local_probe_examined", "local_probe_passed", "local_probe_pass_ratio",\n\t\t"k", "predicate_leaf_count", "query_predicate_threshold", "checkpoint_index",')
    c = replace(c, '\t\tif (strcmp(group, "query_context") == 0)', '''        if (strcmp(group, "local_filter") == 0)
        {
            executionState.localFilterEnabled = true;
            executionState.queryContextEnabled = true;
        }
\t\telse if (strcmp(group, "query_context") == 0)''')
    c = replace(c, '\telse if (strcmp(name, "checkpoint_index") == 0)', '''    else if (strcmp(name, "local_probe_examined") == 0 || strcmp(name, "local_probe_passed") == 0)
    {
        if (executionState.localFilterEnabled)
        {
            value.type = FANNBENCH_VALUE_INT;
            value.intValue = strcmp(name, "local_probe_examined") == 0 ?
                executionState.localProbeExamined : executionState.localProbePassed;
        }
    }
    else if (strcmp(name, "local_probe_pass_ratio") == 0)
    {
        if (executionState.localFilterEnabled && executionState.localProbeExamined > 0)
        {
            value.type = FANNBENCH_VALUE_FLOAT;
            value.floatValue = (double) executionState.localProbePassed / executionState.localProbeExamined;
        }
    }
\telse if (strcmp(name, "checkpoint_index") == 0)''')
    cpath.write_text(c)
    hpath = directory / 'src/fannbench.h'
    hpath.write_text(hpath.read_text() + '\nbool FannbenchLocalProbeEnabled(void);\nvoid FannbenchLocalProbe(Relation index, BlockNumber block, OffsetNumber offset, ItemPointer tids, int count);\n')
    upath = directory / 'src/hnswutils.c'; u = upath.read_text()
    anchor = '    /* Development audit must include scored nodes rejected by the retained heap. */'
    u = replace(u, anchor, '''    /* Observe only an element whose distance was just computed. */
    if (distance != NULL && FannbenchLocalProbeEnabled())
    {
        int n = 0;
        while (n < HNSW_HEAPTIDS && ItemPointerIsValid(&etup->heaptids[n])) n++;
        FannbenchLocalProbe(index, blkno, offno, etup->heaptids, n);
    }
''' + anchor)
    upath.write_text(u)


def patch_adapter(directory):
    """Keep the original timer/transport; extend request binding and trace registry."""
    import json
    registry = directory / 'native/registry.json'; r = json.loads(registry.read_text())
    template = r['definitions']['predicate_leaf_count']
    for name in EXTRA:
        d = dict(template)
        d.update(name=name, kind='float' if name.endswith('ratio') else 'int', group='local_filter',
            units='fraction' if name.endswith('ratio') else 'predicate_scalar' if name=='query_predicate_threshold' else 'tuples',
            population='query_predicate' if name=='query_predicate_threshold' else 'bounded_encountered_visible_tuples',scope='request',
            description='Bounded causal local-filter-v1 observation: ' + name,
            source='local_filter_v1', availability='enabled_query_constant' if name=='query_predicate_threshold' else 'enabled_and_observed',
            collection_cost='bounded_64_heap_metadata_reads_charged_inside_query')
        r['definitions'][name] = d
        r['capabilities']['pgvector']['checkpoint_fields'].append(name)
    r['registry_hash'] = digest({'base_registry': r['registry_hash'], 'local_filter_v1': {n:r['definitions'][n] for n in EXTRA}})
    registry.write_text(json.dumps(r, sort_keys=True, indent=2) + '\n')
    profile = directory / 'profiles.py'; s = profile.read_text()
    s = replace(s, 'name="pgvector_same_execution_v4/v1",', 'name="pgvector_same_execution_v4/v1/local-filter-v1",')
    s = replace(s, 'n: FeatureDefinition(**vars(f), provenance="server_observed")',
        'n: FeatureDefinition(**vars(f), provenance="validated_query_predicate" if n == "query_predicate_threshold" else "server_observed")')
    s = replace(s, '        "distances",', '        "distances",\n        "local_filter",')
    profile.write_text(s)
    backend = directory / 'backend.py'; s = backend.read_text()
    anchor = '        # Select transport before sending execution commands.'
    s = replace(s, anchor, '''        if "local_filter" in groups:
            predicate = query.get("filter")
            if predicate is None:
                threshold = 0
            elif (isinstance(predicate, dict) and set(predicate) == {"field", "op", "value"}
                  and predicate["field"] == "m_000000" and predicate["op"] == "gte"
                  and type(predicate["value"]) is int and 0 <= predicate["value"] < 2**63):
                threshold = predicate["value"]
            else:
                raise AgentError("local-filter-v1 requires the declared votes predicate")
            begin_sql = begin_sql[:-1] + ",%s::bigint)"
            begin_params = (*begin_params, threshold)
''' + anchor)
    s += '''\nFUNCTIONS += """
CREATE OR REPLACE FUNCTION fannagent.begin_execution(
 text,text,bigint,text,integer,integer,text,bigint,text,text,text,boolean,bigint)
 RETURNS text AS '$libdir/vector','fannbench_begin_execution'
 LANGUAGE C VOLATILE PARALLEL UNSAFE;
CREATE OR REPLACE FUNCTION fannagent.local_probe()
 RETURNS text AS '$libdir/vector','fannbench_local_probe'
 LANGUAGE C VOLATILE PARALLEL UNSAFE;
"""\n'''
    backend.write_text(s)
