/* Observation only. These functions cannot request a stop or alter candidates. */
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
