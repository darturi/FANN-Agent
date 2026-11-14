"""Counters at existing observer hooks only. This module is NEVER used for timing."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'runtime-agent-v1/engine'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=(OLD/'src/fannbench.c').read_text();anchor='#include "utils/snapmgr.h"';assert source.count(anchor)==1
source=source.replace(anchor,anchor+'\n#include <sched.h>\n#include <sys/syscall.h>\n#include "diagnostic_counters.inc"')
hooks={'FannbenchHnswQueuePop(void)':'diagQueuePops++;','FannbenchHnswLayerScore(int level)':'if (level == 0) diagLayer0Scores++; else diagUpperScores++;','FannbenchVectorDistanceComputed(void)':'diagVectorCalls++;','FannbenchHnswAdjacencyExamined(void)':'diagAdjacency++;','FannbenchShadowStart(void)':'diagFeaturePasses++;','FannbenchShadowQualifies(ItemPointer tid)':'diagMembershipProbes++;'}
for signature,statement in hooks.items():
 needle=signature+'\n{';assert source.count(needle)==1;source=source.replace(needle,needle+'\n    if (diagnosticEnabled) { '+statement+' }')
(HERE/'engine/src/fannbench.c').write_text(source)
include=r'''/* Observation only. These functions cannot request a stop or alter candidates. */
static bool diagnosticEnabled;
static uint64 diagVectorCalls, diagLayer0Scores, diagUpperScores, diagQueuePops;
static uint64 diagAdjacency, diagFeaturePasses, diagMembershipProbes;
static int diagStartCpu;
static int DiagnosticCpu(void)
{
    unsigned int cpu;
    if (syscall(SYS_getcpu, &cpu, NULL, NULL) != 0)
        elog(ERROR, "cannot observe diagnostic CPU through kernel syscall");
    return (int) cpu;
}
PG_FUNCTION_INFO_V1(fannbench_diagnostic_reset);
Datum
fannbench_diagnostic_reset(PG_FUNCTION_ARGS)
{
    if (diagnosticEnabled) elog(ERROR, "previous diagnostic not consumed");
    diagVectorCalls = diagLayer0Scores = diagUpperScores = diagQueuePops = 0;
    diagAdjacency = diagFeaturePasses = diagMembershipProbes = 0;
    diagStartCpu = DiagnosticCpu();
    if (diagStartCpu < 0) elog(ERROR, "cannot observe diagnostic CPU");
    diagnosticEnabled = true;
    PG_RETURN_VOID();
}
PG_FUNCTION_INFO_V1(fannbench_diagnostic_read);
Datum
fannbench_diagnostic_read(PG_FUNCTION_ARGS)
{
    StringInfoData result;
    int endCpu;
    if (!diagnosticEnabled) elog(ERROR, "diagnostic not enabled");
    endCpu = DiagnosticCpu();
    if (endCpu < 0) elog(ERROR, "cannot observe diagnostic CPU");
    diagnosticEnabled = false;
    initStringInfo(&result);
    appendStringInfo(&result,
        "{\"pid\":%d,\"start_cpu\":%d,\"end_cpu\":%d,"
        "\"vector_calls\":" UINT64_FORMAT ",\"layer0_neighbor_scores\":" UINT64_FORMAT
        ",\"upper_neighbor_scores\":" UINT64_FORMAT ",\"layer0_queue_pops\":" UINT64_FORMAT
        ",\"layer0_adjacencies_examined\":" UINT64_FORMAT ",\"feature_passes\":" UINT64_FORMAT
        ",\"membership_probes\":" UINT64_FORMAT "}",
        MyProcPid, diagStartCpu, endCpu, diagVectorCalls, diagLayer0Scores,
        diagUpperScores, diagQueuePops, diagAdjacency, diagFeaturePasses, diagMembershipProbes);
    PG_RETURN_TEXT_P(cstring_to_text(result.data));
}
'''
(HERE/'engine/src/diagnostic_counters.inc').write_text(include)
for p in OLD.rglob('*'):
 if p.is_file() and p.suffix in ('.c','.h','.inc') and p.name!='fannbench.c':assert p.read_bytes()==(HERE/'engine'/p.relative_to(OLD)).read_bytes()
(HERE/'work-source-change.json').write_text(json.dumps({'schema':'diagnostic-observers-only.v1','changed_existing_source':{'src/fannbench.c':{'before':sha(OLD/'src/fannbench.c'),'after':sha(HERE/'engine/src/fannbench.c')}},'added_include_sha256':sha(HERE/'engine/src/diagnostic_counters.inc'),'hooks':hooks,'search_algorithm_changes':False,'policy_changes':False,'timing_module':'original job23045686 binary; instrumentation module only for separate work-count stage','counter_definitions':{'vector_calls':'all negative-inner-product/cosine vector score function calls in one search SELECT, including graph and SQL result scoring','layer0_neighbor_scores':'non-entry neighbor scores recorded by existing HnswLayerScore(level0) hook','upper_neighbor_scores':'non-entry scores at upper HNSW layers','layer0_queue_pops':'existing layer0 queue-pop hook, including terminal pop','layer0_adjacencies_examined':'layer0 neighbor TIDs examined before visited dedup','feature_passes':'checkpoint retained-heap feature passes','membership_probes':'retained-TID predicate/dedup membership checks'}},indent=2,sort_keys=True)+'\n')
print('Prepared observation-only module; original timing module preserved.')
