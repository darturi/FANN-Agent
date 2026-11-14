#include "postgres.h"

#include <errno.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <math.h>
#include <sys/stat.h>
#include <unistd.h>

#include "access/xact.h"
#include "access/genam.h"
#include "access/table.h"
#include "access/tableam.h"
#include "commands/defrem.h"
#include "catalog/index.h"
#include "catalog/pg_am.h"
#include "common/int.h"
#include "executor/executor.h"
#include "fmgr.h"
#include "executor/spi.h"
#include "lib/stringinfo.h"
#include "miscadmin.h"
#include "portability/instr_time.h"
#include "utils/builtins.h"
#include "utils/lsyscache.h"
#include "utils/hsearch.h"
#include "utils/memutils.h"
#include "utils/rel.h"
#include "utils/snapmgr.h"

#include "fannbench.h"

#define FANNBENCH_MODE_MAX 32
#define FANNBENCH_NONCE_MAX 80
#define FANNBENCH_HASH_MAX 96
#define FANNBENCH_ERROR_MAX 160
#define FANNBENCH_ARGUMENT_MAX 64
#define FANNBENCH_CHECKPOINT_INTERVAL 64
#define FANNBENCH_MAX_INSTRUCTIONS 1024
#define FANNBENCH_MAX_STACK 512
#define FANNBENCH_QUEUE_STAT_COUNT 7
#define FANNBENCH_MAX_SCANS 16

typedef struct FannbenchTopKEntry
{
	int64 id;
	double distance;
} FannbenchTopKEntry;

typedef struct FannbenchScanEntry
{
	IndexScanDesc scan;
	int64 serial;
	int64 generation;
	bool pending;
	ItemPointerData heapTid;
	BlockNumber graphBlock;
	OffsetNumber graphOffset;
	double distance;
} FannbenchScanEntry;

typedef enum FannbenchOpcode
{
	FANNBENCH_FEATURE,
	FANNBENCH_INT,
	FANNBENCH_FLOAT,
	FANNBENCH_BOOL,
	FANNBENCH_OP,
	FANNBENCH_JIF,
	FANNBENCH_RETURN
} FannbenchOpcode;

typedef struct FannbenchInstruction
{
	FannbenchOpcode opcode;
	char		argument[FANNBENCH_ARGUMENT_MAX];
	int64		intValue;
	double		floatValue;
	int32		target;
} FannbenchInstruction;

typedef enum FannbenchValueType
{
	FANNBENCH_UNAVAILABLE,
	FANNBENCH_VALUE_INT,
	FANNBENCH_VALUE_FLOAT,
	FANNBENCH_VALUE_BOOL
} FannbenchValueType;

typedef struct FannbenchValue
{
	FannbenchValueType type;
	int64		intValue;
	double		floatValue;
	bool		boolValue;
} FannbenchValue;

typedef struct FannbenchFeatures
{
	int64		k;
	int64		predicateLeafCount;
	int64		checkpointIndex;
	int64		distanceEvaluations;
	int64		distanceSinceCheckpoint;
	int64		completedExpansions;
} FannbenchFeatures;


typedef struct ShadowObservation
{
	int checkpoint;
	int count;
	double tenth;
	uint64 nanos;
	uint64 top_tids[10];
	int turnover;
} ShadowObservation;

typedef struct FannbenchExecutionState
{
	ShadowObservation shadow[3];
	bool		active;
	char		mode[FANNBENCH_MODE_MAX];
	char		nonce[FANNBENCH_NONCE_MAX];
	char		policyHash[FANNBENCH_HASH_MAX];
	bool		hasPolicyHash;
	int64		fixedBudget;
	int32		requestedK;
	int32		predicateLeafCount;
	int64		queryPredicateThreshold;
	bool		queryContextEnabled;
    bool localFilterEnabled;
    bool progressFilterEnabled;
    int progressWindow,progressNodeCount,progressRowCount,progressFetches[8];
    BlockNumber progressBlocks[64]; OffsetNumber progressOffsets[64];
    int progressWindows[64]; int64 progressIds[64],progressVotes[64];
    bool progressNulls[64],progressPassed[64]; double progressDistances[64];
    int localProbeNodes, localProbeExamined, localProbePassed;
    BlockNumber localProbeBlocks[64];
    OffsetNumber localProbeOffsets[64];
    int64 localProbeIds[64], localProbeVotes[64];
    bool localProbeNulls[64];
	int32		returnedCount;
	bool		hnswReached;
	int64		distanceEvaluations;
	int64		upperDistanceEvaluations;
	int64		distanceAtLastCheckpoint;
	int64		checkpointCount;
	int64		featureCollectionCount;
	int64		featureCollectionNanos;
	int64		frontierSnapshotCount;
	int64		frontierValuesCopied;
	int64		frontierMaximumCount;
	int64		frontierTraversalNanos;
	int64		frontierStatisticsNanos;
	int64		frontierSortCount;
	int64		frontierSortNanos;
	int64		frontierQuantileNanos;
	int64		policyEvaluationCount;
	int64		policyEvaluationNanos;
	int64		completedExpansions;
	int64		uniqueDiscoveries;
	int64		queuePops;
	int64		adjacencyEntriesExamined;
	int64		executorTuplePassCount;
	int64		executorTupleFailCount;
	int64		unattributedVectorEvaluations;
	bool		insideGraphScorer;
	bool		auditMembership;
	bool		progressEnabled;
	bool		hasExecutorFeedback;
	FannbenchTopKEntry *topK;
	int32		topKCount;
	int64		topKInsertions;
	int64		topKReplacements;
	bool		previousTopKFull;
	double		previousTopKWorst;
	int64		traceSequence;
	int64		lastObservationSequence;
	FannbenchScanEntry scans[FANNBENCH_MAX_SCANS];
	int64		nextScanSerial;
	char		componentId[64];
	int64		componentLayer0Start;
	int64		componentUpperStart;
	int64		componentUniqueStart;
	int32		retainedCapacity;
	int32		retainedCount;
	bool		hasTopKStats;
	double		topKStats[FANNBENCH_QUEUE_STAT_COUNT];
	bool		hasWorstImprovement;
	double		worstImprovement;
	Oid			hnswAmOid;
	int64		nextCheckpointTarget;
	int64		lastCheckpointTarget;
	int64		frontierCount;
	double		frontierBestDistance;
	bool		hasFrontier;
	bool		queueStatsEnabled;
	bool		queueQuantilesEnabled;
	bool		hasFrontierStats;
	double		frontierStats[FANNBENCH_QUEUE_STAT_COUNT];
	double		entryDistance;
	bool		hasEntryDistance;
	char		traceLevel[16];
	char		registryHash[FANNBENCH_HASH_MAX];
	char		featureSetHash[FANNBENCH_HASH_MAX];
	int64		traceMaxBytes;
	int64		traceBytes;
	bool		traceTruncated;
	bool		traceComplete;
	FILE	   *traceFile;
	char		tracePath[MAXPGPATH];
	bool		fixedBudgetStopped;
	bool		policyStopped;
	bool		policyFallback;
	char		policyRuntimeError[FANNBENCH_ERROR_MAX];
} FannbenchExecutionState;

static FannbenchExecutionState executionState;
static FannbenchInstruction installedProgram[FANNBENCH_MAX_INSTRUCTIONS];
static int32 installedInstructionCount;
static char installedPolicyHash[FANNBENCH_HASH_MAX];
static bool installedPolicy;
static bool installedPolicyV2;
static bool installedQueueStatsRequired;

/* The pinned PostgreSQL 17.11 executor patch exports this optional hook. */
typedef void (*FannbenchScanQualHook) (ScanState *node, TupleTableSlot *slot,
											bool passed);
extern PGDLLIMPORT FannbenchScanQualHook fannbench_scan_qual_hook;
static char completedTrace[MAXPGPATH];
static char completedLocalProbe[16384];
static char completedProgressProbe[24576];
static char completedNonce[FANNBENCH_NONCE_MAX];
static Oid boundRelation = InvalidOid;
static Oid boundIndex = InvalidOid;
static AttrNumber boundId = InvalidAttrNumber;

static void TraceLine(const char *line, bool terminal);
static void RefreshTopKStats(void);

static void
FannbenchScanQual(ScanState *node, TupleTableSlot *slot, bool passed)
{
	IndexScanState *indexScan;
	Relation indexRelation;
	FannbenchScanEntry *candidate = NULL;
	Datum idDatum;
	bool idNull;
	AttrNumber idAtt;
	int64 logicalId = 0;
	bool hasId = false;
	StringInfoData observation;

	if (!executionState.active || strcmp(executionState.mode, "native") == 0 ||
		!executionState.hnswReached || executionState.hnswAmOid == InvalidOid ||
		!IsA(node, IndexScanState) || TupIsNull(slot))
		return;
	indexScan = (IndexScanState *) node;
	indexRelation = indexScan->iss_RelationDesc;
	if (indexRelation == NULL || indexRelation->rd_rel->relam != executionState.hnswAmOid)
		return;
	for (int i = 0; i < FANNBENCH_MAX_SCANS; i++)
		if (executionState.scans[i].scan == indexScan->iss_ScanDesc &&
			executionState.scans[i].pending)
		{
			candidate = &executionState.scans[i];
			break;
		}
	if (candidate == NULL)
		return;
	if (passed)
		executionState.executorTuplePassCount++;
	else
		executionState.executorTupleFailCount++;
	executionState.hasExecutorFeedback = true;
	/* A HOT update can change the visible tuple TID while retaining the root TID. */
	candidate->pending = false;
	if (OidIsValid(boundIndex) && RelationGetRelid(indexRelation) != boundIndex)
        return;
    idAtt = RelationGetRelid(indexScan->ss.ss_currentRelation) == boundRelation ?
        boundId : get_attnum(indexScan->ss.ss_currentRelation->rd_id, "id");
	if (idAtt != InvalidAttrNumber)
	{
		idDatum = slot_getattr(slot, idAtt, &idNull);
		if (!idNull && TupleDescAttr(slot->tts_tupleDescriptor, idAtt - 1)->atttypid == INT8OID)
		{
			logicalId = DatumGetInt64(idDatum);
			hasId = true;
		}
	}
	if (passed && hasId && executionState.requestedK > 0)
	{
		int worst = -1;
		for (int i = 0; i < executionState.topKCount; i++)
		{
			if (executionState.topK[i].id == logicalId)
				goto trace_observation;
			if (worst < 0 || executionState.topK[i].distance > executionState.topK[worst].distance ||
				(executionState.topK[i].distance == executionState.topK[worst].distance &&
				 executionState.topK[i].id > executionState.topK[worst].id))
				worst = i;
		}
		if (executionState.topKCount < executionState.requestedK)
		{
			executionState.topK[executionState.topKCount].id = logicalId;
			executionState.topK[executionState.topKCount].distance = 1.0 + candidate->distance;
			executionState.topKCount++;
			executionState.topKInsertions++;
		}
		else if (worst >= 0 &&
			(1.0 + candidate->distance < executionState.topK[worst].distance ||
			 (1.0 + candidate->distance == executionState.topK[worst].distance &&
			  logicalId < executionState.topK[worst].id)))
		{
			executionState.topK[worst].id = logicalId;
			executionState.topK[worst].distance = 1.0 + candidate->distance;
			executionState.topKReplacements++;
		}
	}
trace_observation:
	if (executionState.traceFile == NULL ||
		strcmp(executionState.traceLevel, "checkpoints") != 0)
		return;
	initStringInfo(&observation);
	appendStringInfo(&observation,
		"{\"type\":\"executor_observation\",\"component_id\":\"pgvector-scan-" INT64_FORMAT
		"-" INT64_FORMAT "\",\"scan_serial\":" INT64_FORMAT
		",\"rescan_generation\":" INT64_FORMAT
		",\"graph_block\":%u,\"graph_offset\":%u,\"heap_block\":%u,\"heap_offset\":%u,"
		"\"passed\":%s,\"distance\":%.17g,\"identity\":",
		candidate->serial, candidate->generation, candidate->serial,
		candidate->generation, candidate->graphBlock, candidate->graphOffset,
		ItemPointerGetBlockNumber(&candidate->heapTid),
		ItemPointerGetOffsetNumber(&candidate->heapTid),
		passed ? "true" : "false", 1.0 + candidate->distance);
	if (hasId)
		appendStringInfo(&observation, "\"" INT64_FORMAT "\"", logicalId);
	else
		appendStringInfoString(&observation, "null");
	appendStringInfoChar(&observation, '}');
	TraceLine(observation.data, false);
	executionState.lastObservationSequence = executionState.traceSequence;
	pfree(observation.data);
	if (executionState.auditMembership)
	{
		initStringInfo(&observation);
		appendStringInfo(&observation,
						 "{\"type\":\"audit_tuple_membership\",\"component_id\":\"pgvector-scan-" INT64_FORMAT
						 "-" INT64_FORMAT "\",\"physical_id\":\"%u:%u\","
						 "\"heap_tid\":\"%u:%u\",\"matched\":%s,\"logical_id\":",
						 candidate->serial, candidate->generation,
						 candidate->graphBlock, candidate->graphOffset,
						 ItemPointerGetBlockNumber(&candidate->heapTid),
						 ItemPointerGetOffsetNumber(&candidate->heapTid),
						 passed ? "true" : "false");
		if (hasId)
			appendStringInfo(&observation, INT64_FORMAT, logicalId);
		else
			appendStringInfoString(&observation, "null");
		appendStringInfoChar(&observation, '}');
		TraceLine(observation.data, false);
		pfree(observation.data);
	}
}


PG_FUNCTION_INFO_V1(fannagent_take_trace);
Datum
fannagent_take_trace(PG_FUNCTION_ARGS)
{
    char *nonce = text_to_cstring(PG_GETARG_TEXT_PP(0));
    FILE *file;
    long length;
    char *data;
    text *result;
    if (strcmp(nonce, completedNonce) != 0 || completedTrace[0] == '\0')
        ereport(ERROR, (errmsg("trace unavailable for this session nonce")));
    file = fopen(completedTrace, "rb");
    if (file == NULL || fseek(file, 0, SEEK_END) != 0)
        ereport(ERROR, (errmsg("cannot read completed trace")));
    length = ftell(file);
    if (length < 0 || length > 64 * 1024 * 1024)
        ereport(ERROR, (errmsg("invalid trace length")));
    rewind(file);
    data = palloc(length + 1);
    if (fread(data, 1, length, file) != length)
        ereport(ERROR, (errmsg("incomplete trace read")));
    data[length] = '\0';
    fclose(file);
    (void) unlink(completedTrace);
    completedTrace[0] = '\0';
    result = cstring_to_text_with_len(data, length);
    pfree(data);
    pfree(nonce);
    PG_RETURN_TEXT_P(result);
}

PG_FUNCTION_INFO_V1(fannagent_bind_target);
Datum
fannagent_bind_target(PG_FUNCTION_ARGS)
{
    Oid relationId = PG_GETARG_OID(0);
    char *idName = text_to_cstring(PG_GETARG_TEXT_PP(1));
    char *vectorName = text_to_cstring(PG_GETARG_TEXT_PP(2));
    Oid indexId = PG_GETARG_OID(3);
    Relation relation = table_open(relationId, AccessShareLock);
    Relation index = index_open(indexId, AccessShareLock);
    AttrNumber idAtt = get_attnum(relationId, idName);
    AttrNumber vectorAtt = get_attnum(relationId, vectorName);
    if (idAtt <= 0 || vectorAtt <= 0 ||
        TupleDescAttr(RelationGetDescr(relation), idAtt - 1)->atttypid != INT8OID ||
        index->rd_index->indrelid != relationId || index->rd_index->indnkeyatts != 1 ||
        index->rd_index->indkey.values[0] != vectorAtt ||
        index->rd_rel->relam != get_am_oid("hnsw", false))
        ereport(ERROR, (errmsg("incompatible fannagent target binding")));
    boundRelation = relationId;
    boundIndex = indexId;
    boundId = idAtt;
    index_close(index, AccessShareLock);
    table_close(relation, AccessShareLock);
    pfree(idName);
    pfree(vectorName);
    PG_RETURN_OID(indexId);
}

PG_FUNCTION_INFO_V1(fannbench_install_policy);
PG_FUNCTION_INFO_V1(fannbench_begin_execution);
PG_FUNCTION_INFO_V1(fannbench_observe_result);
PG_FUNCTION_INFO_V1(fannbench_last_execution);

static void
ResetExecutionState(void)
{
	if (executionState.topK != NULL)
		pfree(executionState.topK);
	if (executionState.traceFile != NULL)
		fclose(executionState.traceFile);
	if (executionState.tracePath[0] != '\0' && !executionState.traceComplete)
		(void) unlink(executionState.tracePath);
	MemSet(&executionState, 0, sizeof(executionState));
}

static void
TraceLine(const char *line, bool terminal)
{
	Size length;
	StringInfoData framed;
	int64 limit;

	if (executionState.traceFile == NULL ||
		(executionState.traceTruncated && !terminal))
		return;
	length = strlen(line);
	if (length == 0 || line[length - 1] != '}')
	{
		executionState.traceTruncated = true;
		return;
	}
	initStringInfo(&framed);
	appendStringInfo(&framed,
					 "%.*s,\"sequence\":" INT64_FORMAT
					 ",\"request_nonce\":\"%s\",\"feature_registry_hash\":\"%s\"}",
					 (int) length - 1, line, executionState.traceSequence + 1,
					 executionState.nonce, executionState.registryHash);
	length = framed.len;
	limit = executionState.traceMaxBytes;
	if (!terminal)
		limit -= Min((int64) 8192, executionState.traceMaxBytes / 4);
	if (executionState.traceBytes + length + 1 > limit)
	{
		executionState.traceTruncated = true;
		pfree(framed.data);
		return;
	}
	if (fwrite(framed.data, 1, length, executionState.traceFile) != length ||
		fputc('\n', executionState.traceFile) == EOF)
	{
		executionState.traceTruncated = true;
		pfree(framed.data);
		return;
	}
	executionState.traceBytes += length + 1;
	executionState.traceSequence++;
	pfree(framed.data);
}

bool
FannbenchHnswAuditEnabled(void)
{
	return executionState.active && executionState.auditMembership &&
		executionState.traceFile != NULL && !executionState.traceTruncated &&
		strcmp(executionState.mode, "native") != 0;
}

static void
AuditGraphEvent(const char *type, BlockNumber block, OffsetNumber offset)
{
	StringInfoData line;

	if (!FannbenchHnswAuditEnabled())
		return;
	initStringInfo(&line);
	appendStringInfo(&line,
					 "{\"type\":\"%s\",\"component_id\":\"%s\","
					 "\"physical_id\":\"%u:%u\"}",
					 type, executionState.componentId, block, offset);
	TraceLine(line.data, false);
	pfree(line.data);
}

void
FannbenchHnswAuditDiscovery(BlockNumber block, OffsetNumber offset)
{
	AuditGraphEvent("audit_discovery", block, offset);
}

void
FannbenchHnswAuditFrontier(BlockNumber block, OffsetNumber offset, bool inserted)
{
	AuditGraphEvent(inserted ? "audit_frontier_add" : "audit_frontier_remove",
					block, offset);
}

void
FannbenchHnswAuditFrontierReset(void)
{
	StringInfoData line;
	if (!FannbenchHnswAuditEnabled())
		return;
	initStringInfo(&line);
	appendStringInfo(&line,
					 "{\"type\":\"audit_frontier_reset\",\"component_id\":\"%s\"}",
					 executionState.componentId);
	TraceLine(line.data, false);
	pfree(line.data);
}

void
FannbenchHnswAuditIdentity(Relation index, BlockNumber block,
								OffsetNumber offset, ItemPointer heaptids, int count)
{
	Relation heap;
	TupleTableSlot *slot;
    IndexFetchTableData *fetch;
	AttrNumber idAtt;
	StringInfoData line;
	bool first = true;

	if (!FannbenchHnswAuditEnabled() || index == NULL)
		return;
	heap = table_open(index->rd_index->indrelid, AccessShareLock);
	idAtt = RelationGetRelid(heap) == boundRelation ? boundId :
        get_attnum(RelationGetRelid(heap), "id");
	slot = table_slot_create(heap, NULL);
    fetch = table_index_fetch_begin(heap);
	initStringInfo(&line);
	appendStringInfo(&line,
					 "{\"type\":\"audit_identity\",\"component_id\":\"%s\","
					 "\"physical_id\":\"%u:%u\",\"logical_ids\":[",
					 executionState.componentId, block, offset);
	for (int i = 0; i < count; i++)
	{
		Datum value;
		bool isNull;
        bool callAgain = false;
        bool allDead = false;
        ItemPointerData visibleTid = heaptids[i];
        if (idAtt == InvalidAttrNumber || !ItemPointerIsValid(&heaptids[i]))
            continue;
        do
        {
            if (!table_index_fetch_tuple(fetch, &visibleTid, GetActiveSnapshot(), slot,
                                         &callAgain, &allDead))
                continue;
        value = slot_getattr(slot, idAtt, &isNull);
		if (!isNull && TupleDescAttr(slot->tts_tupleDescriptor, idAtt - 1)->atttypid == INT8OID)
		{
			appendStringInfo(&line, "%s" INT64_FORMAT, first ? "" : ",",
						 DatumGetInt64(value));
			first = false;
		}
        ExecClearTuple(slot);
        } while (callAgain);
        table_index_fetch_reset(fetch);
    }
	appendStringInfo(&line, "],\"heap_tuple_count\":%d}", count);
	TraceLine(line.data, false);
	pfree(line.data);
	table_index_fetch_end(fetch);
    ExecDropSingleTupleTableSlot(slot);
	table_close(heap, AccessShareLock);
}


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

static void
TraceCheckpoint(const char *decision)
{
	StringInfoData line;

	if (strcmp(executionState.traceLevel, "checkpoints") != 0)
		return;
	initStringInfo(&line);
	appendStringInfo(&line,
					 "{\"type\":\"checkpoint\",\"index\":" INT64_FORMAT
					 ",\"target\":" INT64_FORMAT
					 ",\"actual_layer0_distances\":" INT64_FORMAT
					 ",\"observation_watermark\":" INT64_FORMAT
					 ",\"component_id\":\"%s\","
					 "\"route\":\"postgresql_pgvector_hnsw\","
					 "\"features\":{"
					 "\"k\":%d,"
					 "\"predicate_leaf_count\":%d,"
					 "\"checkpoint_index\":" INT64_FORMAT ","
					 "\"checkpoint_target\":" INT64_FORMAT ","
					 "\"checkpoint_overshoot\":" INT64_FORMAT ","
					 "\"layer0_distance_evaluations\":" INT64_FORMAT ","
					 "\"upper_distance_evaluations\":" INT64_FORMAT ","
					 "\"layer0_distance_since_checkpoint\":" INT64_FORMAT ","
					 "\"completed_expansions\":" INT64_FORMAT ","
					 "\"unique_discoveries\":" INT64_FORMAT ","
					 "\"queue_pops\":" INT64_FORMAT ","
					 "\"adjacency_entries_examined\":" INT64_FORMAT ","
					 "\"frontier_count\":" INT64_FORMAT,
					 executionState.checkpointCount,
					 executionState.lastCheckpointTarget,
					 executionState.distanceEvaluations,
					 executionState.lastObservationSequence,
					 executionState.componentId[0] ? executionState.componentId : "pgvector-layer0",
					 executionState.requestedK,
					 executionState.predicateLeafCount,
					 executionState.checkpointCount,
					 executionState.lastCheckpointTarget,
					 executionState.distanceEvaluations - executionState.lastCheckpointTarget,
					 executionState.distanceEvaluations,
					 executionState.upperDistanceEvaluations,
					 executionState.distanceEvaluations - executionState.distanceAtLastCheckpoint,
					 executionState.completedExpansions,
					 executionState.uniqueDiscoveries,
					 executionState.queuePops,
					 executionState.adjacencyEntriesExamined,
					 executionState.frontierCount);
    if (executionState.progressFilterEnabled)
    {
        {FannbenchValue v=ProgressFeature("progress_window_checkpoint");appendStringInfo(&line,",\"progress_window_checkpoint\":" INT64_FORMAT,v.intValue);}
        {FannbenchValue v=ProgressFeature("progress_probe_examined");appendStringInfo(&line,",\"progress_probe_examined\":" INT64_FORMAT,v.intValue);}
        {FannbenchValue v=ProgressFeature("progress_probe_passed");appendStringInfo(&line,",\"progress_probe_passed\":" INT64_FORMAT,v.intValue);}
        {FannbenchValue v=ProgressFeature("progress_probe_pass_ratio");appendStringInfo(&line,",\"progress_probe_pass_ratio\":%.17g",v.floatValue);}
        {FannbenchValue v=ProgressFeature("progress_recent_examined");appendStringInfo(&line,",\"progress_recent_examined\":" INT64_FORMAT,v.intValue);}
        {FannbenchValue v=ProgressFeature("progress_recent_passed");appendStringInfo(&line,",\"progress_recent_passed\":" INT64_FORMAT,v.intValue);}
        {FannbenchValue v=ProgressFeature("progress_recent_pass_ratio");appendStringInfo(&line,",\"progress_recent_pass_ratio\":%.17g",v.floatValue);}
        {FannbenchValue v=ProgressFeature("progress_has_valid");appendStringInfo(&line,",\"progress_has_valid\":%s",v.boolValue?"true":"false");}
        {FannbenchValue v=ProgressFeature("progress_valid_distance_min_or_zero");appendStringInfo(&line,",\"progress_valid_distance_min_or_zero\":%.17g",v.floatValue);}
        {FannbenchValue v=ProgressFeature("progress_valid_distance_mean_or_zero");appendStringInfo(&line,",\"progress_valid_distance_mean_or_zero\":%.17g",v.floatValue);}
        {FannbenchValue v=ProgressFeature("progress_valid_min_improvement_or_zero");appendStringInfo(&line,",\"progress_valid_min_improvement_or_zero\":%.17g",v.floatValue);}
    }
    if (executionState.localFilterEnabled)
    {
        appendStringInfo(&line, ",\"local_probe_examined\":%d,\"local_probe_passed\":%d",
            executionState.localProbeExamined, executionState.localProbePassed);
        if (executionState.localProbeExamined > 0)
            appendStringInfo(&line, ",\"local_probe_pass_ratio\":%.17g",
                (double) executionState.localProbePassed / executionState.localProbeExamined);
    }
	if (executionState.queryContextEnabled)
		appendStringInfo(&line, ",\"query_predicate_threshold\":" INT64_FORMAT,
					 executionState.queryPredicateThreshold);
	if (executionState.executorTuplePassCount + executionState.executorTupleFailCount > 0)
		appendStringInfo(&line,
					 ",\"executor_tuple_pass_count\":" INT64_FORMAT
					 ",\"executor_tuple_fail_count\":" INT64_FORMAT,
					 executionState.executorTuplePassCount,
					 executionState.executorTupleFailCount);
	appendStringInfo(&line,
					 ",\"component_layer0_distance_evaluations\":" INT64_FORMAT
					 ",\"component_upper_distance_evaluations\":" INT64_FORMAT
					 ",\"component_unique_discoveries\":" INT64_FORMAT
					 ",\"unattributed_vector_evaluations\":" INT64_FORMAT
					 ",\"retained_result_count\":%d,\"retained_result_capacity\":%d",
					 executionState.distanceEvaluations - executionState.componentLayer0Start,
					 executionState.upperDistanceEvaluations - executionState.componentUpperStart,
					 executionState.uniqueDiscoveries - executionState.componentUniqueStart,
					 executionState.unattributedVectorEvaluations,
					 executionState.retainedCount, executionState.retainedCapacity);
	if (executionState.hasExecutorFeedback)
	{
		appendStringInfo(&line,
						 ",\"qualified_topk_count\":%d,\"recent_topk_insertions\":" INT64_FORMAT
						 ",\"recent_topk_replacements\":" INT64_FORMAT,
						 executionState.topKCount, executionState.topKInsertions,
						 executionState.topKReplacements);
		if (executionState.hasTopKStats)
			appendStringInfo(&line,
						 ",\"qualified_topk_distance_min\":%.17g,\"qualified_topk_distance_max\":%.17g,"
						 "\"qualified_topk_distance_mean\":%.17g,\"qualified_topk_distance_variance\":%.17g,"
						 "\"qualified_topk_distance_p25\":%.17g,\"qualified_topk_distance_p50\":%.17g,"
						 "\"qualified_topk_distance_p75\":%.17g",
						 executionState.topKStats[0], executionState.topKStats[1],
						 executionState.topKStats[2], executionState.topKStats[3],
						 executionState.topKStats[4], executionState.topKStats[5],
						 executionState.topKStats[6]);
		if (executionState.hasWorstImprovement)
			appendStringInfo(&line, ",\"worst_topk_distance_improvement\":%.17g",
							 executionState.worstImprovement);
	}
	if (executionState.hasEntryDistance)
		appendStringInfo(&line, ",\"entry_distance\":%.17g",
					 executionState.entryDistance);
	if (executionState.hasFrontier)
		appendStringInfo(&line, ",\"frontier_distance_min\":%.17g",
					 executionState.frontierBestDistance);
	if (executionState.hasFrontierStats)
	{
		appendStringInfo(&line,
					 ",\"frontier_distance_max\":%.17g,"
					 "\"frontier_distance_mean\":%.17g,"
					 "\"frontier_distance_variance\":%.17g",
					 executionState.frontierStats[1],
					 executionState.frontierStats[2],
					 executionState.frontierStats[3]);
		if (executionState.queueQuantilesEnabled ||
			strcmp(executionState.traceLevel, "checkpoints") == 0)
			appendStringInfo(&line,
						 ",\"frontier_distance_p25\":%.17g,"
						 "\"frontier_distance_p50\":%.17g,"
						 "\"frontier_distance_p75\":%.17g",
						 executionState.frontierStats[4],
						 executionState.frontierStats[5],
						 executionState.frontierStats[6]);
	}
	appendStringInfo(&line, "},\"decision\":\"%s\"}", decision);
	TraceLine(line.data, false);
	pfree(line.data);
}

static void
CopyTextArgument(text *value, char *destination, Size destinationSize, const char *name)
{
	char	   *source = text_to_cstring(value);

	if (strlen(source) >= destinationSize)
		ereport(ERROR,
				(errcode(ERRCODE_PROGRAM_LIMIT_EXCEEDED),
				 errmsg("fannbench %s is too long", name)));
	strlcpy(destination, source, destinationSize);
	pfree(source);
}

static void
ValidateToken(const char *value, const char *name)
{
	const char *cursor;

	if (*value == '\0')
		ereport(ERROR,
				(errcode(ERRCODE_INVALID_PARAMETER_VALUE),
				 errmsg("fannbench %s must not be empty", name)));
	for (cursor = value; *cursor != '\0'; cursor++)
		if (!(isalnum((unsigned char) *cursor) || *cursor == '_' || *cursor == '-'))
			ereport(ERROR,
					(errcode(ERRCODE_INVALID_PARAMETER_VALUE),
					 errmsg("fannbench %s contains an invalid character", name)));
}

static bool
KnownFeature(const char *name)
{
	static const char *features[] = {
		"progress_window_checkpoint", "progress_probe_examined", "progress_probe_passed", "progress_probe_pass_ratio", "progress_recent_examined", "progress_recent_passed", "progress_recent_pass_ratio", "progress_has_valid", "progress_valid_distance_min_or_zero", "progress_valid_distance_mean_or_zero", "progress_valid_min_improvement_or_zero",
		"local_probe_examined", "local_probe_passed", "local_probe_pass_ratio",
		"k", "predicate_leaf_count", "query_predicate_threshold", "checkpoint_index",
		"distance_evaluations", "distance_evaluations_since_checkpoint",
		"unique_discoveries", "completed_expansions", "qualified_candidate_count",
		"best_qualified_distance", "worst_qualified_top_k_distance",
		"recent_distance_improvement", "recent_result_improvement",
		"frontier_best_distance", "checkpoint_target", "checkpoint_overshoot",
		"layer0_distance_evaluations", "layer0_distance_since_checkpoint",
		"component_layer0_distance_evaluations", "component_upper_distance_evaluations",
		"component_unique_discoveries",
		"unattributed_vector_evaluations",
		"retained_result_count", "retained_result_capacity",
		"queue_pops", "executor_tuple_pass_count", "executor_tuple_fail_count",
		"frontier_count", "frontier_distance_min",
		"upper_distance_evaluations", "exact_distance_evaluations",
		"auxiliary_distance_evaluations", "total_distance_evaluations",
		"adjacency_entries_examined", "predicate_evaluations",
		"checked_unique_candidates", "matched_unique_candidates",
		"visited_match_fraction", "checked_match_fraction",
		"checked_coverage", "queued_match_fraction",
		"acorn_two_hop_entries_examined", "acorn_duplicate_encounters",
		"entry_distance", "qualified_topk_count",
		"recent_topk_insertions", "recent_topk_replacements",
		"worst_topk_distance_improvement", "frontier_distance_max",
		"frontier_distance_mean", "frontier_distance_variance",
		"frontier_distance_p25", "frontier_distance_p50",
		"frontier_distance_p75", "qualified_topk_distance_min",
		"qualified_topk_distance_max", "qualified_topk_distance_mean",
		"qualified_topk_distance_variance", "qualified_topk_distance_p25",
		"qualified_topk_distance_p50", "qualified_topk_distance_p75"
	};
	int			i;

	for (i = 0; i < lengthof(features); i++)
		if (strcmp(name, features[i]) == 0)
			return true;
	return false;
}

static bool
KnownOperator(const char *name)
{
	static const char *operators[] = {
		"not", "is_available", "and", "or", "add", "sub", "mul", "div",
		"eq", "lt", "lte", "gt", "gte"
	};
	int			i;

	for (i = 0; i < lengthof(operators); i++)
		if (strcmp(name, operators[i]) == 0)
			return true;
	return false;
}

static void
FannbenchXactCallback(XactEvent event, void *arg)
{
	if (event == XACT_EVENT_COMMIT || event == XACT_EVENT_ABORT ||
		event == XACT_EVENT_PARALLEL_COMMIT || event == XACT_EVENT_PARALLEL_ABORT)
		ResetExecutionState();
}

void
FannbenchInit(void)
{
	ResetExecutionState();
	installedPolicy = false;
	installedInstructionCount = 0;
	installedQueueStatsRequired = false;
	RegisterXactCallback(FannbenchXactCallback, NULL);
	fannbench_scan_qual_hook = FannbenchScanQual;
}

Datum
fannbench_install_policy(PG_FUNCTION_ARGS)
{
	char	   *hash = text_to_cstring(PG_GETARG_TEXT_PP(0));
	char	   *program = text_to_cstring(PG_GETARG_TEXT_PP(1));
	char	   *lineSave = NULL;
	char	   *line;
	int32		count = 0;
	int32		i;

	if (strlen(hash) != 64)
		ereport(ERROR,
				(errcode(ERRCODE_INVALID_PARAMETER_VALUE),
				 errmsg("fannbench policy hash must contain 64 hexadecimal characters")));
	ValidateToken(hash, "policy hash");
	line = strtok_r(program, "\n", &lineSave);
	installedPolicyV2 = line != NULL && strcmp(line, "FANNBENCH_POLICY_V2\t64") == 0;
	if (line == NULL || (!installedPolicyV2 &&
		strcmp(line, "FANNBENCH_POLICY_V1\t64") != 0))
		ereport(ERROR,
				(errcode(ERRCODE_INVALID_PARAMETER_VALUE),
				 errmsg("unsupported fannbench policy bytecode header")));

	while ((line = strtok_r(NULL, "\n", &lineSave)) != NULL)
	{
		char	   *separator;
		char	   *argument;
		FannbenchInstruction *instruction;

		if (count >= FANNBENCH_MAX_INSTRUCTIONS)
			ereport(ERROR,
					(errcode(ERRCODE_PROGRAM_LIMIT_EXCEEDED),
					 errmsg("fannbench policy exceeds %d instructions",
							FANNBENCH_MAX_INSTRUCTIONS)));
		separator = strchr(line, '\t');
		if (separator == NULL || separator == line || separator[1] == '\0')
			ereport(ERROR,
					(errcode(ERRCODE_INVALID_PARAMETER_VALUE),
					 errmsg("invalid fannbench policy instruction")));
		*separator = '\0';
		argument = separator + 1;
		instruction = &installedProgram[count];
		MemSet(instruction, 0, sizeof(*instruction));

		if (strcmp(line, "FEATURE") == 0)
		{
			if (!KnownFeature(argument))
				ereport(ERROR,
						(errcode(ERRCODE_INVALID_PARAMETER_VALUE),
						 errmsg("unknown fannbench feature: %s", argument)));
			instruction->opcode = FANNBENCH_FEATURE;
		}
		else if (strcmp(line, "INT") == 0)
		{
			instruction->opcode = FANNBENCH_INT;
			instruction->intValue = pg_strtoint64(argument);
		}
		else if (strcmp(line, "FLOAT") == 0)
		{
			char	   *end = NULL;

			errno = 0;
			instruction->opcode = FANNBENCH_FLOAT;
			instruction->floatValue = strtod(argument, &end);
			if (errno != 0 || end == argument || *end != '\0' ||
				!isfinite(instruction->floatValue))
				ereport(ERROR,
						(errcode(ERRCODE_INVALID_PARAMETER_VALUE),
						 errmsg("invalid fannbench float literal")));
		}
		else if (strcmp(line, "BOOL") == 0)
		{
			if (strcmp(argument, "0") != 0 && strcmp(argument, "1") != 0)
				ereport(ERROR,
						(errcode(ERRCODE_INVALID_PARAMETER_VALUE),
						 errmsg("invalid fannbench Boolean literal")));
			instruction->opcode = FANNBENCH_BOOL;
			instruction->intValue = strcmp(argument, "1") == 0;
		}
		else if (strcmp(line, "OP") == 0)
		{
			if (!KnownOperator(argument))
				ereport(ERROR,
						(errcode(ERRCODE_INVALID_PARAMETER_VALUE),
						 errmsg("unknown fannbench policy operator: %s", argument)));
			instruction->opcode = FANNBENCH_OP;
		}
		else if (strcmp(line, "JIF") == 0)
		{
			instruction->opcode = FANNBENCH_JIF;
			instruction->target = pg_strtoint32(argument);
		}
		else if (strcmp(line, "RETURN") == 0)
		{
			if (strcmp(argument, "stop") != 0 && strcmp(argument, "continue") != 0)
				ereport(ERROR,
						(errcode(ERRCODE_INVALID_PARAMETER_VALUE),
						 errmsg("unknown fannbench policy decision: %s", argument)));
			instruction->opcode = FANNBENCH_RETURN;
		}
		else
			ereport(ERROR,
					(errcode(ERRCODE_INVALID_PARAMETER_VALUE),
					 errmsg("unknown fannbench policy instruction: %s", line)));

		if (strlen(argument) >= sizeof(instruction->argument))
			ereport(ERROR,
					(errcode(ERRCODE_PROGRAM_LIMIT_EXCEEDED),
					 errmsg("fannbench policy instruction argument is too long")));
		strlcpy(instruction->argument, argument, sizeof(instruction->argument));
		count++;
	}
	if (count == 0)
		ereport(ERROR,
				(errcode(ERRCODE_INVALID_PARAMETER_VALUE),
				 errmsg("fannbench policy program must not be empty")));
	for (i = 0; i < count; i++)
		if (installedProgram[i].opcode == FANNBENCH_JIF &&
			(installedProgram[i].target < 0 || installedProgram[i].target >= count))
			ereport(ERROR,
					(errcode(ERRCODE_INVALID_PARAMETER_VALUE),
					 errmsg("fannbench policy jump target is outside the program")));

	strlcpy(installedPolicyHash, hash, sizeof(installedPolicyHash));
	installedInstructionCount = count;
	installedQueueStatsRequired = false;
	for (i = 0; i < count; i++)
		if (installedProgram[i].opcode == FANNBENCH_FEATURE &&
			strncmp(installedProgram[i].argument, "frontier_distance_", 18) == 0 &&
			strcmp(installedProgram[i].argument, "frontier_distance_min") != 0)
			installedQueueStatsRequired = true;
	installedPolicy = true;
	pfree(hash);
	pfree(program);
	PG_RETURN_TEXT_P(cstring_to_text(installedPolicyHash));
}

Datum
fannbench_begin_execution(PG_FUNCTION_ARGS)
{
	text	   *mode = PG_GETARG_TEXT_PP(0);
	text	   *nonce = PG_GETARG_TEXT_PP(3);
	char		groups[256];
	char	   *group;

	ResetExecutionState();
	CopyTextArgument(mode, executionState.mode, sizeof(executionState.mode), "mode");
	CopyTextArgument(nonce, executionState.nonce, sizeof(executionState.nonce), "nonce");
	ValidateToken(executionState.nonce, "nonce");

	if (strcmp(executionState.mode, "native") != 0 &&
		strcmp(executionState.mode, "policy_noop") != 0 &&
		strcmp(executionState.mode, "fixed_budget") != 0 &&
		strcmp(executionState.mode, "policy_agent") != 0)
		ereport(ERROR,
				(errcode(ERRCODE_INVALID_PARAMETER_VALUE),
				 errmsg("unsupported fannbench mode: %s", executionState.mode)));

	if (!PG_ARGISNULL(1))
	{
		CopyTextArgument(PG_GETARG_TEXT_PP(1), executionState.policyHash,
						 sizeof(executionState.policyHash), "policy hash");
		ValidateToken(executionState.policyHash, "policy hash");
		executionState.hasPolicyHash = true;
	}
	if (strcmp(executionState.mode, "policy_agent") == 0)
	{
		if (!executionState.hasPolicyHash)
			ereport(ERROR,
					(errcode(ERRCODE_INVALID_PARAMETER_VALUE),
					 errmsg("policy_agent mode requires a policy hash")));
		if (!installedPolicy || strcmp(executionState.policyHash, installedPolicyHash) != 0)
			ereport(ERROR,
					(errcode(ERRCODE_UNDEFINED_OBJECT),
					 errmsg("fannbench policy hash is not installed")));
	}
	else if (executionState.hasPolicyHash)
		ereport(ERROR,
				(errcode(ERRCODE_INVALID_PARAMETER_VALUE),
				 errmsg("policy hash is not valid for mode %s", executionState.mode)));

	executionState.fixedBudget = PG_ARGISNULL(2) ? 0 : PG_GETARG_INT64(2);
	if (strcmp(executionState.mode, "fixed_budget") == 0)
	{
		if (executionState.fixedBudget <= 0)
			ereport(ERROR,
					(errcode(ERRCODE_INVALID_PARAMETER_VALUE),
					 errmsg("fixed_budget mode requires a positive budget")));
	}
	else if (executionState.fixedBudget != 0)
		ereport(ERROR,
				(errcode(ERRCODE_INVALID_PARAMETER_VALUE),
				 errmsg("fixed budget is only valid in fixed_budget mode")));

	executionState.requestedK = PG_GETARG_INT32(4);
	executionState.predicateLeafCount = PG_GETARG_INT32(5);
	executionState.hnswAmOid = get_am_oid("hnsw", true);
	executionState.nextCheckpointTarget = FANNBENCH_CHECKPOINT_INTERVAL;
	CopyTextArgument(PG_GETARG_TEXT_PP(6), executionState.traceLevel,
					 sizeof(executionState.traceLevel), "trace level");
	if (strcmp(executionState.traceLevel, "off") != 0 &&
		strcmp(executionState.traceLevel, "summary") != 0 &&
		strcmp(executionState.traceLevel, "checkpoints") != 0)
		ereport(ERROR, (errmsg("invalid fannbench trace level")));
	executionState.traceMaxBytes = PG_GETARG_INT64(7);
	if (executionState.traceMaxBytes <= 0 ||
		executionState.traceMaxBytes > 512 * 1024 * 1024)
		ereport(ERROR, (errmsg("invalid fannbench trace byte cap")));
	CopyTextArgument(PG_GETARG_TEXT_PP(8), executionState.registryHash,
					 sizeof(executionState.registryHash), "registry hash");
	CopyTextArgument(PG_GETARG_TEXT_PP(9), executionState.featureSetHash,
					 sizeof(executionState.featureSetHash), "feature set hash");
	ValidateToken(executionState.registryHash, "registry hash");
	ValidateToken(executionState.featureSetHash, "feature set hash");
	CopyTextArgument(PG_GETARG_TEXT_PP(10), groups, sizeof(groups), "feature groups");
	for (group = strtok(groups, ","); group != NULL; group = strtok(NULL, ","))
	{
        if (strcmp(group,"progress_filter")==0)
        {executionState.progressFilterEnabled=true;executionState.queryContextEnabled=true;}
        else if (strcmp(group, "local_filter") == 0)
        {
            executionState.localFilterEnabled = true;
            executionState.queryContextEnabled = true;
        }
		else if (strcmp(group, "query_context") == 0)
			executionState.queryContextEnabled = true;
		else if (strcmp(group, "queue") == 0)
			executionState.queueStatsEnabled = true;
		else if (strcmp(group, "queue_quantiles") == 0)
		{
			executionState.queueStatsEnabled = true;
			executionState.queueQuantilesEnabled = true;
		}
	}
	/* This opt-in value is a request constant, never inferred from identities or
	 * from executor feedback. ResetExecutionState clears it on every request. */
	if (executionState.queryContextEnabled)
	{
		if (PG_NARGS() != 13 || PG_ARGISNULL(12))
			ereport(ERROR, (errmsg("query_context requires an explicit predicate threshold")));
		executionState.queryPredicateThreshold = PG_GETARG_INT64(12);
		if (executionState.queryPredicateThreshold < 0 ||
			executionState.predicateLeafCount > 1 ||
			(executionState.predicateLeafCount == 0 && executionState.queryPredicateThreshold != 0))
			ereport(ERROR, (errmsg("invalid predicate-context-v1 binding")));
	}
	else if (PG_NARGS() > 12)
		ereport(ERROR, (errmsg("predicate threshold requires query_context group")));
	if (strcmp(executionState.traceLevel, "off") != 0)
	{
		char directory[MAXPGPATH];

		snprintf(directory, sizeof(directory), "%s/fannbench-traces", DataDir);
		if (mkdir(directory, 0700) != 0 && errno != EEXIST)
			ereport(ERROR, (errmsg("cannot create fannbench trace directory: %m")));
		snprintf(executionState.tracePath, sizeof(executionState.tracePath),
				 "%s/%s.jsonl", directory, executionState.nonce);
		executionState.traceFile = fopen(executionState.tracePath, "wx");
		if (executionState.traceFile == NULL)
			ereport(ERROR, (errmsg("cannot create fannbench trace file: %m")));
	}
	if (executionState.requestedK <= 0 || executionState.predicateLeafCount < 0)
		ereport(ERROR,
				(errcode(ERRCODE_INVALID_PARAMETER_VALUE),
				 errmsg("requested k must be positive and predicate count nonnegative")));
	executionState.topK = MemoryContextAllocZero(TopMemoryContext,
									 sizeof(FannbenchTopKEntry) * executionState.requestedK);
	executionState.auditMembership = PG_NARGS() > 11 && !PG_ARGISNULL(11) && PG_GETARG_BOOL(11);
	executionState.active = true;

	PG_RETURN_TEXT_P(cstring_to_text(executionState.nonce));
}

Datum
fannbench_observe_result(PG_FUNCTION_ARGS)
{
	if (!executionState.active)
		ereport(ERROR,
				(errcode(ERRCODE_OBJECT_NOT_IN_PREREQUISITE_STATE),
				 errmsg("no active fannbench execution")));
	executionState.returnedCount++;
	PG_RETURN_BOOL(true);
}

static FannbenchFeatures
CollectPolicyFeatures(void)
{
	FannbenchFeatures features = {
		executionState.requestedK,
		executionState.predicateLeafCount,
		executionState.checkpointCount,
		executionState.distanceEvaluations,
		executionState.distanceEvaluations - executionState.distanceAtLastCheckpoint,
		executionState.completedExpansions
	};

	return features;
}

static FannbenchValue
FeatureValue(const char *name, const FannbenchFeatures *features)
{
	FannbenchValue value = {0};

	if (strcmp(name, "k") == 0)
	{
		value.type = FANNBENCH_VALUE_INT;
		value.intValue = features->k;
	}
	else if (strcmp(name, "predicate_leaf_count") == 0)
	{
		value.type = FANNBENCH_VALUE_INT;
		value.intValue = features->predicateLeafCount;
	}
	else if (strcmp(name, "query_predicate_threshold") == 0)
	{
		if (executionState.queryContextEnabled)
		{
			value.type = FANNBENCH_VALUE_INT;
			value.intValue = executionState.queryPredicateThreshold;
		}
	}
    else if (strncmp(name,"progress_",9)==0) value=ProgressFeature(name);
    else if (strcmp(name, "local_probe_examined") == 0 || strcmp(name, "local_probe_passed") == 0)
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
	else if (strcmp(name, "checkpoint_index") == 0)
	{
		value.type = FANNBENCH_VALUE_INT;
		value.intValue = features->checkpointIndex;
	}
	else if (strcmp(name, "distance_evaluations") == 0)
	{
		value.type = FANNBENCH_VALUE_INT;
		value.intValue = features->distanceEvaluations;
	}
	else if (strcmp(name, "distance_evaluations_since_checkpoint") == 0)
	{
		value.type = FANNBENCH_VALUE_INT;
		value.intValue = features->distanceSinceCheckpoint;
	}
	else if (strcmp(name, "completed_expansions") == 0)
	{
		value.type = FANNBENCH_VALUE_INT;
		value.intValue = features->completedExpansions;
	}
	else if (installedPolicyV2 && strcmp(name, "layer0_distance_evaluations") == 0)
	{
		value.type = FANNBENCH_VALUE_INT;
		value.intValue = executionState.distanceEvaluations;
	}
	else if (installedPolicyV2 && strcmp(name, "upper_distance_evaluations") == 0)
	{
		value.type = FANNBENCH_VALUE_INT;
		value.intValue = executionState.upperDistanceEvaluations;
	}
	else if (installedPolicyV2 && strcmp(name, "component_layer0_distance_evaluations") == 0)
	{
		value.type = FANNBENCH_VALUE_INT;
		value.intValue = executionState.distanceEvaluations - executionState.componentLayer0Start;
	}
	else if (installedPolicyV2 && strcmp(name, "component_upper_distance_evaluations") == 0)
	{
		value.type = FANNBENCH_VALUE_INT;
		value.intValue = executionState.upperDistanceEvaluations - executionState.componentUpperStart;
	}
	else if (installedPolicyV2 && strcmp(name, "component_unique_discoveries") == 0)
	{
		value.type = FANNBENCH_VALUE_INT;
		value.intValue = executionState.uniqueDiscoveries - executionState.componentUniqueStart;
	}
	else if (installedPolicyV2 && strcmp(name, "unattributed_vector_evaluations") == 0)
	{
		value.type = FANNBENCH_VALUE_INT;
		value.intValue = executionState.unattributedVectorEvaluations;
	}
	else if (installedPolicyV2 && strcmp(name, "retained_result_count") == 0)
	{
		value.type = FANNBENCH_VALUE_INT;
		value.intValue = executionState.retainedCount;
	}
	else if (installedPolicyV2 && strcmp(name, "retained_result_capacity") == 0)
	{
		value.type = FANNBENCH_VALUE_INT;
		value.intValue = executionState.retainedCapacity;
	}
	else if (installedPolicyV2 && executionState.hasExecutorFeedback &&
			(strcmp(name, "qualified_topk_count") == 0 ||
			 strcmp(name, "recent_topk_insertions") == 0 ||
			 strcmp(name, "recent_topk_replacements") == 0))
	{
		value.type = FANNBENCH_VALUE_INT;
		value.intValue = strcmp(name, "qualified_topk_count") == 0 ? executionState.topKCount :
			strcmp(name, "recent_topk_insertions") == 0 ? executionState.topKInsertions :
			executionState.topKReplacements;
	}
	else if (installedPolicyV2 && executionState.hasWorstImprovement &&
			 strcmp(name, "worst_topk_distance_improvement") == 0)
	{
		value.type = FANNBENCH_VALUE_FLOAT;
		value.floatValue = executionState.worstImprovement;
	}
	else if (installedPolicyV2 && executionState.hasTopKStats &&
			 strncmp(name, "qualified_topk_distance_", 24) == 0)
	{
		static const char *const names[FANNBENCH_QUEUE_STAT_COUNT] = {
			"qualified_topk_distance_min", "qualified_topk_distance_max",
			"qualified_topk_distance_mean", "qualified_topk_distance_variance",
			"qualified_topk_distance_p25", "qualified_topk_distance_p50",
			"qualified_topk_distance_p75"
		};
		value.type = FANNBENCH_UNAVAILABLE;
		for (int i = 0; i < FANNBENCH_QUEUE_STAT_COUNT; i++)
			if (strcmp(name, names[i]) == 0)
			{
				value.type = FANNBENCH_VALUE_FLOAT;
				value.floatValue = executionState.topKStats[i];
				break;
			}
	}
	else if (installedPolicyV2 && strcmp(name, "layer0_distance_since_checkpoint") == 0)
	{
		value.type = FANNBENCH_VALUE_INT;
		value.intValue = executionState.distanceEvaluations - executionState.distanceAtLastCheckpoint;
	}
	else if (installedPolicyV2 && strcmp(name, "checkpoint_target") == 0)
	{
		value.type = FANNBENCH_VALUE_INT;
		value.intValue = executionState.lastCheckpointTarget;
	}
	else if (installedPolicyV2 && strcmp(name, "checkpoint_overshoot") == 0)
	{
		value.type = FANNBENCH_VALUE_INT;
		value.intValue = executionState.distanceEvaluations - executionState.lastCheckpointTarget;
	}
	else if (installedPolicyV2 && strcmp(name, "queue_pops") == 0)
	{
		value.type = FANNBENCH_VALUE_INT;
		value.intValue = executionState.queuePops;
	}
	else if (installedPolicyV2 && strcmp(name, "unique_discoveries") == 0)
	{
		value.type = FANNBENCH_VALUE_INT;
		value.intValue = executionState.uniqueDiscoveries;
	}
	else if (installedPolicyV2 && strcmp(name, "frontier_count") == 0)
	{
		value.type = FANNBENCH_VALUE_INT;
		value.intValue = executionState.frontierCount;
	}
	else if (installedPolicyV2 && strcmp(name, "entry_distance") == 0 &&
		 executionState.hasEntryDistance)
	{
		value.type = FANNBENCH_VALUE_FLOAT;
		value.floatValue = executionState.entryDistance;
	}
	else if (installedPolicyV2 && strcmp(name, "frontier_distance_min") == 0 &&
		 executionState.hasFrontier)
	{
		value.type = FANNBENCH_VALUE_FLOAT;
		value.floatValue = executionState.frontierBestDistance;
	}
	else if (installedPolicyV2 && executionState.hasFrontierStats &&
			 strncmp(name, "frontier_distance_", 18) == 0)
	{
		static const char *const names[FANNBENCH_QUEUE_STAT_COUNT] = {
			"frontier_distance_min", "frontier_distance_max",
			"frontier_distance_mean", "frontier_distance_variance",
			"frontier_distance_p25", "frontier_distance_p50",
			"frontier_distance_p75"
		};

		value.type = FANNBENCH_UNAVAILABLE;
		for (int i = 0; i < FANNBENCH_QUEUE_STAT_COUNT; i++)
			if (strcmp(name, names[i]) == 0)
			{
				if (i >= 4 && !executionState.queueQuantilesEnabled &&
					strcmp(executionState.traceLevel, "checkpoints") != 0)
					break;
				value.type = FANNBENCH_VALUE_FLOAT;
				value.floatValue = executionState.frontierStats[i];
				break;
			}
	}
	else if (installedPolicyV2 && strcmp(name, "executor_tuple_pass_count") == 0 &&
		 executionState.executorTuplePassCount + executionState.executorTupleFailCount > 0)
	{
		value.type = FANNBENCH_VALUE_INT;
		value.intValue = executionState.executorTuplePassCount;
	}
	else if (installedPolicyV2 && strcmp(name, "executor_tuple_fail_count") == 0 &&
		 executionState.executorTuplePassCount + executionState.executorTupleFailCount > 0)
	{
		value.type = FANNBENCH_VALUE_INT;
		value.intValue = executionState.executorTupleFailCount;
	}
	else
		value.type = FANNBENCH_UNAVAILABLE;
	return value;
}

static void
SetPolicyError(const char *message)
{
	executionState.policyFallback = true;
	if (executionState.policyRuntimeError[0] == '\0')
		strlcpy(executionState.policyRuntimeError, message,
				sizeof(executionState.policyRuntimeError));
}

static bool
EvaluatePolicy(const FannbenchFeatures *features, bool *stop)
{
	FannbenchValue stack[FANNBENCH_MAX_STACK];
	int32		stackSize = 0;
	int32		pc = 0;

	while (pc < installedInstructionCount)
	{
		FannbenchInstruction *instruction = &installedProgram[pc];

		if (instruction->opcode == FANNBENCH_FEATURE)
		{
			if (stackSize >= FANNBENCH_MAX_STACK)
				goto stack_error;
			stack[stackSize++] = FeatureValue(instruction->argument, features);
			pc++;
		}
		else if (instruction->opcode == FANNBENCH_INT ||
				 instruction->opcode == FANNBENCH_FLOAT ||
				 instruction->opcode == FANNBENCH_BOOL)
		{
			FannbenchValue value = {0};

			if (stackSize >= FANNBENCH_MAX_STACK)
				goto stack_error;
			if (instruction->opcode == FANNBENCH_INT)
			{
				value.type = FANNBENCH_VALUE_INT;
				value.intValue = instruction->intValue;
			}
			else if (instruction->opcode == FANNBENCH_FLOAT)
			{
				value.type = FANNBENCH_VALUE_FLOAT;
				value.floatValue = instruction->floatValue;
			}
			else
			{
				value.type = FANNBENCH_VALUE_BOOL;
				value.boolValue = instruction->intValue != 0;
			}
			stack[stackSize++] = value;
			pc++;
		}
		else if (instruction->opcode == FANNBENCH_OP)
		{
			FannbenchValue left = {0};
			FannbenchValue right = {0};
			FannbenchValue result = {0};
			bool		unary = strcmp(instruction->argument, "not") == 0 ||
				strcmp(instruction->argument, "is_available") == 0;

			if (stackSize < (unary ? 1 : 2))
				goto stack_error;
			right = stack[--stackSize];
			if (!unary)
				left = stack[--stackSize];

			if (strcmp(instruction->argument, "is_available") == 0)
			{
				result.type = FANNBENCH_VALUE_BOOL;
				result.boolValue = right.type != FANNBENCH_UNAVAILABLE;
			}
			else if (right.type == FANNBENCH_UNAVAILABLE ||
					 (!unary && left.type == FANNBENCH_UNAVAILABLE))
				result.type = FANNBENCH_UNAVAILABLE;
			else if (strcmp(instruction->argument, "not") == 0)
			{
				if (right.type != FANNBENCH_VALUE_BOOL)
					goto type_error;
				result.type = FANNBENCH_VALUE_BOOL;
				result.boolValue = !right.boolValue;
			}
			else if (strcmp(instruction->argument, "and") == 0 ||
					 strcmp(instruction->argument, "or") == 0)
			{
				if (left.type != FANNBENCH_VALUE_BOOL || right.type != FANNBENCH_VALUE_BOOL)
					goto type_error;
				result.type = FANNBENCH_VALUE_BOOL;
				result.boolValue = strcmp(instruction->argument, "and") == 0 ?
					(left.boolValue && right.boolValue) : (left.boolValue || right.boolValue);
			}
			else if (strcmp(instruction->argument, "add") == 0 ||
					 strcmp(instruction->argument, "sub") == 0 ||
					 strcmp(instruction->argument, "mul") == 0)
			{
				if (left.type != right.type ||
					(left.type != FANNBENCH_VALUE_INT && left.type != FANNBENCH_VALUE_FLOAT))
					goto type_error;
				result.type = left.type;
				if (left.type == FANNBENCH_VALUE_INT)
				{
					bool overflow;

					if (strcmp(instruction->argument, "add") == 0)
						overflow = pg_add_s64_overflow(left.intValue, right.intValue,
												  &result.intValue);
					else if (strcmp(instruction->argument, "sub") == 0)
						overflow = pg_sub_s64_overflow(left.intValue, right.intValue,
												  &result.intValue);
					else
						overflow = pg_mul_s64_overflow(left.intValue, right.intValue,
												  &result.intValue);
					if (overflow)
					{
						SetPolicyError("policy int64 arithmetic overflow");
						return false;
					}
				}
				else
				{
					if (strcmp(instruction->argument, "add") == 0)
						result.floatValue = left.floatValue + right.floatValue;
					else if (strcmp(instruction->argument, "sub") == 0)
						result.floatValue = left.floatValue - right.floatValue;
					else
						result.floatValue = left.floatValue * right.floatValue;
					if (!isfinite(result.floatValue))
					{
						SetPolicyError("policy float operation produced a non-finite value");
						return false;
					}
				}
			}
			else if (strcmp(instruction->argument, "div") == 0)
			{
				double leftValue;
				double rightValue;

				if (left.type != right.type ||
					(left.type != FANNBENCH_VALUE_INT && left.type != FANNBENCH_VALUE_FLOAT))
					goto type_error;
				leftValue = left.type == FANNBENCH_VALUE_INT ?
					(double) left.intValue : left.floatValue;
				rightValue = right.type == FANNBENCH_VALUE_INT ?
					(double) right.intValue : right.floatValue;
				if (rightValue == 0 ||
					(left.type == FANNBENCH_VALUE_INT &&
					 (left.intValue > 9007199254740992LL ||
					  left.intValue < -9007199254740992LL ||
					  right.intValue > 9007199254740992LL ||
					  right.intValue < -9007199254740992LL)))
				{
					SetPolicyError(rightValue == 0 ? "policy division by zero" :
								   "policy integer division would lose float64 precision");
					return false;
				}
				result.type = FANNBENCH_VALUE_FLOAT;
				result.floatValue = leftValue / rightValue;
				if (!isfinite(result.floatValue))
				{
					SetPolicyError("policy float operation produced a non-finite value");
					return false;
				}
			}
			else
			{
				bool comparison;

				if (left.type != right.type)
					goto type_error;
				if (strcmp(instruction->argument, "eq") == 0)
				{
					if (left.type == FANNBENCH_VALUE_INT)
						comparison = left.intValue == right.intValue;
					else if (left.type == FANNBENCH_VALUE_FLOAT)
						comparison = left.floatValue == right.floatValue;
					else if (left.type == FANNBENCH_VALUE_BOOL)
						comparison = left.boolValue == right.boolValue;
					else
						goto type_error;
				}
				else
				{
					if (left.type == FANNBENCH_VALUE_INT)
					{
						if (strcmp(instruction->argument, "lt") == 0)
							comparison = left.intValue < right.intValue;
						else if (strcmp(instruction->argument, "lte") == 0)
							comparison = left.intValue <= right.intValue;
						else if (strcmp(instruction->argument, "gt") == 0)
							comparison = left.intValue > right.intValue;
						else
							comparison = left.intValue >= right.intValue;
					}
					else if (left.type == FANNBENCH_VALUE_FLOAT)
					{
						if (strcmp(instruction->argument, "lt") == 0)
							comparison = left.floatValue < right.floatValue;
						else if (strcmp(instruction->argument, "lte") == 0)
							comparison = left.floatValue <= right.floatValue;
						else if (strcmp(instruction->argument, "gt") == 0)
							comparison = left.floatValue > right.floatValue;
						else
							comparison = left.floatValue >= right.floatValue;
					}
					else
						goto type_error;
				}
				result.type = FANNBENCH_VALUE_BOOL;
				result.boolValue = comparison;
			}
			stack[stackSize++] = result;
			pc++;
		}
		else if (instruction->opcode == FANNBENCH_JIF)
		{
			FannbenchValue condition;

			if (stackSize < 1)
				goto stack_error;
			condition = stack[--stackSize];
			if (condition.type == FANNBENCH_UNAVAILABLE)
			{
				SetPolicyError("policy condition depends on an unavailable feature");
				return false;
			}
			if (condition.type != FANNBENCH_VALUE_BOOL)
				goto type_error;
			pc = condition.boolValue ? pc + 1 : instruction->target;
		}
		else if (instruction->opcode == FANNBENCH_RETURN)
		{
			*stop = strcmp(instruction->argument, "stop") == 0;
			return true;
		}
	}
	SetPolicyError("policy program ended without a decision");
	return false;

stack_error:
	SetPolicyError("policy stack contract was violated");
	return false;
type_error:
	SetPolicyError("policy value type contract was violated");
	return false;
}

void
FannbenchHnswRouteReached(void)
{
	if (executionState.active)
		executionState.hnswReached = true;
}

void
FannbenchHnswLayerStart(int64 entryCount, double entryDistance)
{
	if (!executionState.active || strcmp(executionState.mode, "native") == 0)
		return;
	executionState.uniqueDiscoveries += entryCount;
	if (entryCount > 0)
	{
		/* Convert pgvector's internal negative cosine similarity to cosine distance. */
		executionState.entryDistance = 1.0 + entryDistance;
		executionState.hasEntryDistance = true;
	}
}

void
FannbenchHnswQueuePop(void)
{
	if (executionState.active && strcmp(executionState.mode, "native") != 0)
		executionState.queuePops++;
}

void
FannbenchHnswUpperDistance(int64 count)
{
	if (executionState.active && strcmp(executionState.mode, "native") != 0)
		executionState.upperDistanceEvaluations += count;
}

void
FannbenchHnswLayer0EntryDistance(void)
{
	if (executionState.active && strcmp(executionState.mode, "native") != 0)
		executionState.distanceEvaluations++;
}

void
FannbenchHnswLayerScore(int level)
{
	if (!executionState.active || strcmp(executionState.mode, "native") == 0)
		return;
	if (level == 0)
		executionState.distanceEvaluations++;
	else
		executionState.upperDistanceEvaluations++;
}

void
FannbenchHnswScoring(bool inside)
{
	if (executionState.active)
		executionState.insideGraphScorer = inside;
}

void
FannbenchVectorDistanceComputed(void)
{
	if (executionState.active && strcmp(executionState.mode, "native") != 0 &&
		!executionState.insideGraphScorer)
		executionState.unattributedVectorEvaluations++;
}

void
FannbenchHnswRetained(int count, int capacity)
{
	if (executionState.active && strcmp(executionState.mode, "native") != 0)
	{
		executionState.retainedCount = count;
		executionState.retainedCapacity = capacity;
	}
}

static FannbenchScanEntry *
FindScan(IndexScanDesc scan, bool create)
{
	FannbenchScanEntry *freeEntry = NULL;

	for (int i = 0; i < FANNBENCH_MAX_SCANS; i++)
	{
		if (executionState.scans[i].scan == scan)
			return &executionState.scans[i];
		if (freeEntry == NULL && executionState.scans[i].scan == NULL)
			freeEntry = &executionState.scans[i];
	}
	if (!create || freeEntry == NULL)
		return NULL;
	freeEntry->scan = scan;
	freeEntry->serial = ++executionState.nextScanSerial;
	return freeEntry;
}

void
FannbenchHnswScanReset(IndexScanDesc scan)
{
	FannbenchScanEntry *entry;
	StringInfoData event;
	if (!executionState.active || strcmp(executionState.mode, "native") == 0)
		return;
	if (OidIsValid(boundIndex) && RelationGetRelid(scan->indexRelation) != boundIndex)
        ereport(ERROR, (errmsg("query used an HNSW index outside its target binding")));
    entry = FindScan(scan, true);
	if (entry == NULL)
		return;
	entry->generation++;
	entry->pending = false;
	snprintf(executionState.componentId, sizeof(executionState.componentId),
			 "pgvector-scan-" INT64_FORMAT "-" INT64_FORMAT,
			 entry->serial, entry->generation);
	executionState.topKCount = 0;
	executionState.topKInsertions = 0;
	executionState.topKReplacements = 0;
	executionState.previousTopKFull = false;
	executionState.hasExecutorFeedback = false;
	executionState.componentLayer0Start = executionState.distanceEvaluations;
	executionState.componentUpperStart = executionState.upperDistanceEvaluations;
	executionState.componentUniqueStart = executionState.uniqueDiscoveries;
	if (executionState.traceFile != NULL)
	{
		initStringInfo(&event);
		appendStringInfo(&event,
					 "{\"type\":\"component_start\",\"component_id\":\"%s\","
					 "\"route\":\"postgresql_pgvector_hnsw\",\"scan_serial\":" INT64_FORMAT
					 ",\"rescan_generation\":" INT64_FORMAT "}",
					 executionState.componentId, entry->serial, entry->generation);
		TraceLine(event.data, false);
		pfree(event.data);
	}
}

void
FannbenchHnswScanEnded(IndexScanDesc scan)
{
	FannbenchScanEntry *entry = FindScan(scan, false);
	if (entry != NULL)
	{
		if (executionState.traceFile != NULL)
		{
			StringInfoData event;
			initStringInfo(&event);
			appendStringInfo(&event,
						 "{\"type\":\"component_end\",\"component_id\":\"pgvector-scan-" INT64_FORMAT
						 "-" INT64_FORMAT "\",\"route\":\"postgresql_pgvector_hnsw\"}",
						 entry->serial, entry->generation);
			TraceLine(event.data, false);
			pfree(event.data);
		}
		entry->scan = NULL;
	}
}

void
FannbenchHnswCandidateReturned(IndexScanDesc scan, BlockNumber block,
								 OffsetNumber offset, ItemPointer heapTid, double distance)
{
	FannbenchScanEntry *entry;
	if (!executionState.active || strcmp(executionState.mode, "native") == 0)
		return;
	entry = FindScan(scan, true);
	if (entry == NULL)
		return;
	entry->pending = true;
	entry->heapTid = *heapTid;
	entry->graphBlock = block;
	entry->graphOffset = offset;
	entry->distance = distance;
}

bool
FannbenchHnswQueueSnapshotNeeded(int64 upcomingDistances)
{
	return executionState.active && strcmp(executionState.mode, "native") != 0 &&
		((executionState.queueStatsEnabled &&
		  (strcmp(executionState.mode, "policy_agent") != 0 ||
		   !installedPolicyV2 || installedQueueStatsRequired)) ||
		 strcmp(executionState.traceLevel, "checkpoints") == 0) &&
		executionState.distanceEvaluations + upcomingDistances >=
		executionState.nextCheckpointTarget;
}

static int
CompareQueueDistance(const void *left, const void *right)
{
	double		a = *((const double *) left);
	double		b = *((const double *) right);

	return a < b ? -1 : a > b ? 1 : 0;
}

static double
QueuePercentile(const double *values, int count, double fraction)
{
	double		position = (count - 1) * fraction;
	int			lower = (int) floor(position);
	int			upper = (int) ceil(position);

	return values[lower] + (position - lower) * (values[upper] - values[lower]);
}

static void
RefreshTopKStats(void)
{
	double *distances;
	double mean = 0;
	double variance = 0;

	executionState.hasTopKStats = false;
	executionState.hasWorstImprovement = false;
	if (executionState.topKCount == 0)
		return;
	distances = palloc(sizeof(double) * executionState.topKCount);
	for (int i = 0; i < executionState.topKCount; i++)
	{
		distances[i] = executionState.topK[i].distance;
		mean += distances[i];
	}
	mean /= executionState.topKCount;
	for (int i = 0; i < executionState.topKCount; i++)
	{
		double delta = distances[i] - mean;
		variance += delta * delta;
	}
	variance /= executionState.topKCount;
	qsort(distances, executionState.topKCount, sizeof(double), CompareQueueDistance);
	executionState.topKStats[0] = distances[0];
	executionState.topKStats[1] = distances[executionState.topKCount - 1];
	executionState.topKStats[2] = mean;
	executionState.topKStats[3] = variance;
	for (int i = 4; i < FANNBENCH_QUEUE_STAT_COUNT; i++)
		executionState.topKStats[i] = QueuePercentile(distances,
									 executionState.topKCount, (i - 3) * 0.25);
	executionState.hasTopKStats = true;
	if (executionState.topKCount == executionState.requestedK)
	{
		if (executionState.previousTopKFull)
		{
			executionState.hasWorstImprovement = true;
			executionState.worstImprovement = executionState.previousTopKWorst - executionState.topKStats[1];
		}
		executionState.previousTopKFull = true;
		executionState.previousTopKWorst = executionState.topKStats[1];
	}
	else
		executionState.previousTopKFull = false;
	pfree(distances);
}

void
FannbenchHnswSetFrontierDistances(double *distances, int count,
									int64 traversalNanos)
{
	double		mean = 0;
	double		variance = 0;
	double		minimum;
	double		maximum;
	bool		needQuantiles;
	instr_time	started;
	instr_time	phaseStarted;
	instr_time	phaseElapsed;
	instr_time	elapsed;

	executionState.hasFrontierStats = false;
	executionState.featureCollectionNanos += traversalNanos;
	if (!executionState.active)
		return;
	executionState.frontierSnapshotCount++;
	executionState.frontierTraversalNanos += traversalNanos;
	if (count <= 0)
		return;
	executionState.frontierValuesCopied += count;
	if (count > executionState.frontierMaximumCount)
		executionState.frontierMaximumCount = count;
	INSTR_TIME_SET_CURRENT(started);
	minimum = maximum = distances[0];
	for (int i = 0; i < count; i++)
	{
		if (!isfinite(distances[i]))
			return;
		mean += distances[i];
		if (distances[i] < minimum)
			minimum = distances[i];
		if (distances[i] > maximum)
			maximum = distances[i];
	}
	mean /= count;
	for (int i = 0; i < count; i++)
	{
		double		delta = distances[i] - mean;

		variance += delta * delta;
	}
	variance /= count;
	/* Keep the original two-pass reduction order for mean and variance. */
	executionState.frontierStats[0] = minimum;
	executionState.frontierStats[1] = maximum;
	executionState.frontierStats[2] = mean;
	executionState.frontierStats[3] = variance;
	INSTR_TIME_SET_CURRENT(phaseElapsed);
	INSTR_TIME_SUBTRACT(phaseElapsed, started);
	executionState.frontierStatisticsNanos += INSTR_TIME_GET_NANOSEC(phaseElapsed);
	needQuantiles = executionState.queueQuantilesEnabled ||
		strcmp(executionState.traceLevel, "checkpoints") == 0;
	if (needQuantiles)
	{
		INSTR_TIME_SET_CURRENT(phaseStarted);
		qsort(distances, count, sizeof(double), CompareQueueDistance);
		INSTR_TIME_SET_CURRENT(phaseElapsed);
		INSTR_TIME_SUBTRACT(phaseElapsed, phaseStarted);
		executionState.frontierSortCount++;
		executionState.frontierSortNanos += INSTR_TIME_GET_NANOSEC(phaseElapsed);
		INSTR_TIME_SET_CURRENT(phaseStarted);
		/* Preserve sorted boundary values, including equal-valued trace ties. */
		executionState.frontierStats[0] = distances[0];
		executionState.frontierStats[1] = distances[count - 1];
		executionState.frontierStats[4] = QueuePercentile(distances, count, 0.25);
		executionState.frontierStats[5] = QueuePercentile(distances, count, 0.5);
		executionState.frontierStats[6] = QueuePercentile(distances, count, 0.75);
		INSTR_TIME_SET_CURRENT(phaseElapsed);
		INSTR_TIME_SUBTRACT(phaseElapsed, phaseStarted);
		executionState.frontierQuantileNanos += INSTR_TIME_GET_NANOSEC(phaseElapsed);
	}
	executionState.hasFrontierStats = true;
	INSTR_TIME_SET_CURRENT(elapsed);
	INSTR_TIME_SUBTRACT(elapsed, started);
	executionState.featureCollectionNanos += INSTR_TIME_GET_NANOSEC(elapsed);
}

void
FannbenchHnswAdjacencyExamined(void)
{
	if (executionState.active && strcmp(executionState.mode, "native") != 0)
		executionState.adjacencyEntriesExamined++;
}
/* Included by fannbench.c. The map lives in one read-only snapshot transaction. */
typedef struct ShadowMember
{
	uint64 key;
	uint64 seen;
	bool qualifies;
} ShadowMember;

static ShadowObservation completedShadow[3];
static HTAB *shadowMembers;
static Oid shadowRelation = InvalidOid;

static unsigned char *confirmMap;
static size_t confirmMapBytes;
static HTAB *confirmSeen;

static int studyThreshold = -2;
static Oid confirmationIndex = InvalidOid;
static int confirmationArm;
static int confirmationStop;
static uint64 shadowGeneration;
static bool shadowCallbackRegistered;

static uint64
ShadowTidKey(ItemPointer tid)
{
	return ((uint64) ItemPointerGetBlockNumber(tid) << 16) |
		ItemPointerGetOffsetNumber(tid);
}

#define CONFIRM_PAGE_BYTES 128
#define CONFIRM_HEADER_BYTES 24
#define CONFIRM_MAX_BYTES (256 * 1024 * 1024)


static void
ConfirmUnmap(void)
{
	if (confirmMap)
		munmap(confirmMap, confirmMapBytes);
	confirmMap = NULL;
	confirmMapBytes = 0;
	confirmSeen = NULL;
}

static bool
ConfirmQualifies(ItemPointer tid)
{
	OffsetNumber offset = ItemPointerGetOffsetNumber(tid);
	BlockNumber block = ItemPointerGetBlockNumber(tid);
	size_t byte;
	unsigned int flags;
	uint64 key;
	bool found;
	ShadowMember *member;

	if (offset < 1 || offset > CONFIRM_PAGE_BYTES * 4)
		elog(ERROR, "invalid heap offset in shared confirmation lookup");
	byte = CONFIRM_HEADER_BYTES + (size_t) block * CONFIRM_PAGE_BYTES + (offset - 1) / 4;
	if (byte >= confirmMapBytes)
		elog(ERROR, "index heap TID absent from shared confirmation lookup");
	flags = (confirmMap[byte] >> (((offset - 1) % 4) * 2)) & 3;
	if (flags != 1 && flags != 3)
		elog(ERROR, "index heap TID absent from shared confirmation lookup");
	if (flags == 1)
		return false;

	key = ShadowTidKey(tid);
	member = hash_search(confirmSeen, &key, HASH_ENTER, &found);
	if (found && member->seen == shadowGeneration)
		return false;
	member->seen = shadowGeneration;
	return true;
}
static void
ShadowEndTransaction(XactEvent event, void *arg)
{
	if (event == XACT_EVENT_COMMIT || event == XACT_EVENT_ABORT ||
		event == XACT_EVENT_PREPARE || event == XACT_EVENT_PARALLEL_ABORT ||
		event == XACT_EVENT_PARALLEL_COMMIT)
	{

		confirmationIndex = InvalidOid;
		confirmationArm = 0;
		confirmationStop = -1;
		ConfirmUnmap();
		shadowMembers = NULL;
		shadowRelation = InvalidOid;
		shadowGeneration = 0;
	}
}

PG_FUNCTION_INFO_V1(fannbench_shadow_bind);
Datum
fannbench_shadow_bind(PG_FUNCTION_ARGS)
{
	Oid relation = PG_GETARG_OID(0);
    int threshold = PG_GETARG_INT32(1);
    int expectedPassing = PG_GETARG_INT32(2);
	char *name;
	char *namespace;
	char *query;
	HASHCTL ctl = {0};
	HTAB *members;
	uint64 i;
	int passing = 0;

	if (shadowMembers || !XactReadOnly || !IsolationUsesXactSnapshot() ||
		GetCurrentTransactionNestLevel() != 1 || executionState.active)
		elog(ERROR, "shadow map requires a fresh read-only snapshot transaction");

	name = get_rel_name(relation);
	namespace = get_namespace_name(get_rel_namespace(relation));
	if (!name || !namespace || get_rel_relkind(relation) != RELKIND_RELATION)
		elog(ERROR, "shadow map requires an ordinary heap relation");
	studyThreshold = threshold;
    query = psprintf("SELECT ctid, %s FROM ONLY %s",
        threshold < 0 ? "true" : psprintf("coalesce(total_votes >= %d, false)", threshold),
        quote_qualified_identifier(namespace, name));

	if (SPI_connect() != SPI_OK_CONNECT || SPI_execute(query, true, 247287) != SPI_OK_SELECT ||
		SPI_processed != 247286)
		elog(ERROR, "unexpected shadow heap cohort");

	ctl.keysize = sizeof(uint64);
	ctl.entrysize = sizeof(ShadowMember);
	ctl.hcxt = TopTransactionContext;
	members = hash_create("votes108 shadow membership", 247286, &ctl,
						  HASH_ELEM | HASH_BLOBS | HASH_CONTEXT);
	for (i = 0; i < SPI_processed; i++)
	{
		bool tidNull, passNull, found;
		HeapTuple row = SPI_tuptable->vals[i];
		TupleDesc desc = SPI_tuptable->tupdesc;
		Datum tid = SPI_getbinval(row, desc, 1, &tidNull);
		Datum pass = SPI_getbinval(row, desc, 2, &passNull);
		uint64 key;
		ShadowMember *member;

		if (tidNull || passNull)
			elog(ERROR, "null shadow membership row");
		key = ShadowTidKey((ItemPointer) DatumGetPointer(tid));
		member = hash_search(members, &key, HASH_ENTER, &found);
		if (found)
			elog(ERROR, "duplicate shadow heap TID");
		member->seen = 0;
		member->qualifies = DatumGetBool(pass);
		passing += member->qualifies;
	}
	if (passing != expectedPassing)
		elog(ERROR, "unexpected votes108 membership count");
	if (SPI_finish() != SPI_OK_FINISH)
		elog(ERROR, "could not finish shadow membership scan");
	if (!shadowCallbackRegistered)
	{
		RegisterXactCallback(ShadowEndTransaction, NULL);
		shadowCallbackRegistered = true;
	}
	shadowRelation = relation;
	shadowMembers = members;
	PG_RETURN_INT32(247286);
}

int
FannbenchShadowCheckpoint(Relation index)
{
	int next;

	if ((!shadowMembers && !confirmMap) || !executionState.active ||
		executionState.distanceEvaluations < executionState.nextCheckpointTarget ||
		strcmp(executionState.mode, "native") == 0)
		return 0;
	if (!XactReadOnly || !IsolationUsesXactSnapshot() ||
		GetCurrentTransactionNestLevel() != 1 ||
		executionState.requestedK != 10 ||
        executionState.predicateLeafCount != (studyThreshold < 0 ? 0 : 1) ||
        executionState.queryPredicateThreshold != (studyThreshold < 0 ? 0 : studyThreshold) ||
		boundRelation != shadowRelation || boundIndex != RelationGetRelid(index))
		elog(ERROR, "shadow observation outside bound votes108 request");

	next = executionState.checkpointCount + 1;
	return next == 16 || next == 32 || next == 64 ? next : 0;
}

void
FannbenchShadowStart(void)
{
	if (++shadowGeneration == 0)
		elog(ERROR, "shadow observation generation exhausted");
}

bool
FannbenchShadowQualifies(ItemPointer tid)
{
	uint64 key = ShadowTidKey(tid);
	ShadowMember *member;

	if (confirmMap)
		return ConfirmQualifies(tid);
	member = hash_search(shadowMembers, &key, HASH_FIND, NULL);

	/* A HOT root or an invisible/unmapped TID invalidates this qualification. */
	if (!member)
		elog(ERROR, "index heap TID absent from shadow snapshot map");
	if (!member->qualifies || member->seen == shadowGeneration)
		return false;
	member->seen = shadowGeneration;
	return true;
}

void
FannbenchShadowRecord(int checkpoint, int count, double tenth, const uint64 top_tids[10], uint64 nanos)
{
	int slot = checkpoint == 16 ? 0 : checkpoint == 32 ? 1 : 2;

	ShadowObservation *current = &executionState.shadow[slot];
	instr_time started, elapsed;

	INSTR_TIME_SET_CURRENT(started);
	current->checkpoint = checkpoint;
	current->count = count;
	current->tenth = tenth;
	memcpy(current->top_tids, top_tids, sizeof(current->top_tids));
	current->turnover = -1;
	if (slot && count >= 10 && executionState.shadow[slot - 1].count >= 10)
	{
		const uint64 *previous = executionState.shadow[slot - 1].top_tids;

		current->turnover = 0;
		for (int i = 0; i < 10; i++)
		{
			bool found = false;

			for (int j = 0; j < 10; j++)
				if (top_tids[i] == previous[j])
				{
					found = true;
					break;
				}
			current->turnover += !found;
		}
	}
	INSTR_TIME_SET_CURRENT(elapsed);
	INSTR_TIME_SUBTRACT(elapsed, started);
	current->nanos = nanos + INSTR_TIME_GET_NANOSEC(elapsed);
}

PG_FUNCTION_INFO_V1(fannbench_shadow_read);
Datum
fannbench_shadow_read(PG_FUNCTION_ARGS)
{
	StringInfoData result;

	if ((!shadowMembers && !confirmMap) || executionState.active ||
		strcmp(text_to_cstring(PG_GETARG_TEXT_PP(0)), completedNonce) != 0)
		elog(ERROR, "no completed shadow execution for this nonce");
	initStringInfo(&result);
	appendStringInfoChar(&result, '[');
	for (int i = 0; i < 3; i++)
	{
		int count = completedShadow[i].count;
		int checkpoint = completedShadow[i].checkpoint;

		if (!checkpoint)
			continue;
		appendStringInfo(&result,
						 "%s{\"checkpoint\":%d,\"qualifying_count\":%d,\"tenth_distance\":",
						 result.len > 1 ? "," : "", checkpoint, count);
		if (count < 10)
			appendStringInfoString(&result, "null");
		else
			appendStringInfo(&result, "%.17g", completedShadow[i].tenth);
		appendStringInfoString(&result, ",\"top10_new_since_previous\":");
		if (completedShadow[i].turnover < 0)
			appendStringInfoString(&result, "null");
		else
			appendStringInfo(&result, "%d", completedShadow[i].turnover);
		appendStringInfo(&result, ",\"collection_ns\":" UINT64_FORMAT ",\"extra_heap_fetches\":0}",
						 completedShadow[i].nanos);
	}
	appendStringInfoChar(&result, ']');
	PG_RETURN_TEXT_P(cstring_to_text(result.data));
}
/* Confirmation-only entry points. The timed SELECT uses the normal SQL path. */
PG_FUNCTION_INFO_V1(fannbench_confirm_bind);
Datum
fannbench_confirm_bind(PG_FUNCTION_ARGS)
{
	Oid heap = PG_GETARG_OID(0);
	Oid index = PG_GETARG_OID(1);
	int arm = PG_GETARG_INT32(2);
	Datum count;

	if ((arm != 1 && arm != 2) || IndexGetRelation(index, false) != heap)
		elog(ERROR, "invalid confirmation arm or index binding");
	count = DirectFunctionCall1(fannbench_shadow_bind, ObjectIdGetDatum(heap));
	confirmationIndex = index;
	confirmationArm = arm;
	confirmationStop = -1;
	PG_RETURN_DATUM(count);
}

PG_FUNCTION_INFO_V1(fannbench_confirm_attach);
Datum
fannbench_confirm_attach(PG_FUNCTION_ARGS)
{
	Oid heap = PG_GETARG_OID(0);
	Oid index = PG_GETARG_OID(1);
	int threshold = PG_GETARG_INT32(2);
    int arm = PG_GETARG_INT32(3);
    int expectedPassing = PG_GETARG_INT32(4);
	char *path = psprintf("%s/../membership-%d.bin", DataDir, threshold);
	uint32 expected[4] = {heap, index, 247286, expectedPassing};
	HASHCTL ctl = {0};
	struct stat st;
	void *mapping;
	int fd;

	if (arm < 0 || arm > 9 || expectedPassing < 0 || expectedPassing > 247286 ||
        (threshold != -1 && threshold != 743 && threshold != 527 && threshold != 310 &&
         threshold != 192 && threshold != 108 && threshold != 32) ||
        IndexGetRelation(index, false) != heap ||
		confirmMap || shadowMembers || !XactReadOnly || !IsolationUsesXactSnapshot() ||
		GetCurrentTransactionNestLevel() != 1 || executionState.active)
		elog(ERROR, "shared confirmation requires a fresh read-only snapshot and matching index");

	fd = open(path, O_RDONLY | O_NOFOLLOW);
	if (fd < 0)
		elog(ERROR, "cannot open shared confirmation lookup: %m");
	if (fstat(fd, &st) != 0 || !S_ISREG(st.st_mode) || st.st_uid != geteuid() ||
		(st.st_mode & 0222) || st.st_size < CONFIRM_HEADER_BYTES + CONFIRM_PAGE_BYTES ||
		st.st_size > CONFIRM_MAX_BYTES ||
		(st.st_size - CONFIRM_HEADER_BYTES) % CONFIRM_PAGE_BYTES != 0)
	{
		close(fd);
		elog(ERROR, "invalid shared confirmation lookup file");
	}
	if (!shadowCallbackRegistered)
	{
		RegisterXactCallback(ShadowEndTransaction, NULL);
		shadowCallbackRegistered = true;
	}
	mapping = mmap(NULL, st.st_size, PROT_READ, MAP_SHARED, fd, 0);
	close(fd);
	if (mapping == MAP_FAILED)
		elog(ERROR, "cannot map shared confirmation lookup: %m");

	confirmMap = mapping;
	confirmMapBytes = st.st_size;
	/* Both the writer and the verified Torch runtime are little-endian x86-64. */
	if (memcmp(confirmMap, "V108MAP1", 8) != 0 ||
		memcmp(confirmMap + 8, expected, sizeof(expected)) != 0)
		elog(ERROR, "shared lookup belongs to a different relation, index or cohort");

	ctl.keysize = sizeof(uint64);
	ctl.entrysize = sizeof(ShadowMember);
	ctl.hcxt = TopTransactionContext;
	confirmSeen = hash_create("votes108 per-connection deduplication", 1024, &ctl,
							 HASH_ELEM | HASH_BLOBS | HASH_CONTEXT);
    shadowRelation = heap;
    studyThreshold = threshold;
	confirmationIndex = index;
	confirmationArm = arm;
	confirmationStop = -1;
	PG_RETURN_INT32(247286);
}
PG_FUNCTION_INFO_V1(fannbench_confirm_last);
Datum
fannbench_confirm_last(PG_FUNCTION_ARGS)
{
	if (!confirmationArm || confirmationStop < 0)
		elog(ERROR, "no completed confirmation scan");
	PG_RETURN_INT32(confirmationStop);
}

int
FannbenchConfirmArm(Relation index)
{
	if (!confirmationArm)
		return 0;
	if ((!shadowMembers && !confirmMap) || executionState.active || !XactReadOnly ||
		!IsolationUsesXactSnapshot() || GetCurrentTransactionNestLevel() != 1 ||
		RelationGetRelid(index) != confirmationIndex)
		elog(ERROR, "unexpected confirmation scan");
	confirmationStop = 0;
	return confirmationArm;
}

void
FannbenchConfirmStopped(int checkpoint)
{
	confirmationStop = checkpoint;
}

bool
FannbenchHnswObserveDistances(int64 count, int64 frontierCount,
							 bool hasFrontier, double frontierBestDistance)
{
	if (!executionState.active)
		return false;
	executionState.hnswReached = true;
	if (strcmp(executionState.mode, "native") == 0)
		return false;
	executionState.completedExpansions++;
	executionState.uniqueDiscoveries += count;
	executionState.frontierCount = frontierCount;
	executionState.hasFrontier = hasFrontier;
	/* The HNSW cosine opclass stores negative similarity internally. */
	executionState.frontierBestDistance = hasFrontier ? 1.0 + frontierBestDistance : 0.0;
	if (executionState.distanceEvaluations >= executionState.nextCheckpointTarget)
	{
		bool		stop = false;
		FannbenchFeatures features;
		instr_time	started;
		instr_time	elapsed;

		executionState.checkpointCount++;
		RefreshTopKStats();
		executionState.lastCheckpointTarget = executionState.nextCheckpointTarget;
		executionState.nextCheckpointTarget =
		(executionState.distanceEvaluations / FANNBENCH_CHECKPOINT_INTERVAL + 1)
		* FANNBENCH_CHECKPOINT_INTERVAL;
		if (strcmp(executionState.mode, "policy_noop") == 0 ||
			strcmp(executionState.mode, "policy_agent") == 0)
		{
			INSTR_TIME_SET_CURRENT(started);
			features = CollectPolicyFeatures();
			INSTR_TIME_SET_CURRENT(elapsed);
			INSTR_TIME_SUBTRACT(elapsed, started);
			executionState.featureCollectionCount++;
			executionState.featureCollectionNanos += INSTR_TIME_GET_NANOSEC(elapsed);
			if (strcmp(executionState.mode, "policy_agent") == 0 &&
				!executionState.policyFallback)
			{
				INSTR_TIME_SET_CURRENT(started);
				executionState.policyEvaluationCount++;
				if (EvaluatePolicy(&features, &stop) && stop)
					executionState.policyStopped = true;
				INSTR_TIME_SET_CURRENT(elapsed);
				INSTR_TIME_SUBTRACT(elapsed, started);
				executionState.policyEvaluationNanos += INSTR_TIME_GET_NANOSEC(elapsed);
			}
		}
		if (strcmp(executionState.mode, "fixed_budget") == 0 &&
			executionState.distanceEvaluations >= executionState.fixedBudget)
			executionState.fixedBudgetStopped = true;
		TraceCheckpoint(executionState.policyStopped ? "stop" :
			executionState.fixedBudgetStopped ? "fixed_budget" :
			strcmp(executionState.mode, "policy_noop") == 0 ? "noop" : "continue");
		executionState.distanceAtLastCheckpoint = executionState.distanceEvaluations;
		executionState.topKInsertions = 0;
		executionState.topKReplacements = 0;
	}
	return executionState.fixedBudgetStopped || executionState.policyStopped;
}

Datum
fannbench_last_execution(PG_FUNCTION_ARGS)
{
	char	   *nonce;
	StringInfoData result;
	const char *path;
	const char *stopReason;
	bool		opportunity;
	bool		observationApplied;
	bool		policyApplied;
	bool		nativeMode;

	if (!executionState.active)
		ereport(ERROR,
				(errcode(ERRCODE_OBJECT_NOT_IN_PREREQUISITE_STATE),
				 errmsg("no active fannbench execution")));
	if (PG_NARGS() == 2)
    {
        int32 count = PG_GETARG_INT32(1);
        if (count < 0 || count > executionState.requestedK)
            ereport(ERROR, (errmsg("invalid client completion count")));
        executionState.returnedCount = count;
    }
    nonce = text_to_cstring(PG_GETARG_TEXT_PP(0));
	if (strcmp(nonce, executionState.nonce) != 0)
		ereport(ERROR,
				(errcode(ERRCODE_INVALID_PARAMETER_VALUE),
				 errmsg("fannbench execution nonce does not match")));

	path = executionState.hnswReached ?
		"postgresql_pgvector_hnsw" : "postgresql_non_hnsw";
	if (executionState.policyStopped)
		stopReason = "policy_stop";
	else if (executionState.fixedBudgetStopped)
		stopReason = "fixed_budget_stop";
	else if (executionState.returnedCount >= executionState.requestedK)
		stopReason = "native_limit";
	else
		stopReason = "exhausted";
	opportunity = executionState.checkpointCount > 0;
	observationApplied = executionState.featureCollectionCount > 0;
	policyApplied = executionState.policyEvaluationCount > 0 &&
		strcmp(executionState.mode, "policy_agent") == 0;
	nativeMode = strcmp(executionState.mode, "native") == 0;
	if (executionState.traceFile != NULL)
	{
		StringInfoData terminal;

		initStringInfo(&terminal);
		appendStringInfo(&terminal,
					 "{\"type\":\"terminal\",\"route\":\"%s\","
					 "\"stop_reason\":\"%s\","
					 "\"layer0_distance_evaluations\":" INT64_FORMAT ","
					 "\"upper_distance_evaluations\":" INT64_FORMAT ","
					 "\"unattributed_vector_evaluations\":" INT64_FORMAT ","
					 "\"executor_tuple_pass_count\":" INT64_FORMAT ","
					 "\"executor_tuple_fail_count\":" INT64_FORMAT ","
					 "\"work_at_stop\":",
					 path, stopReason, executionState.distanceEvaluations,
					 executionState.upperDistanceEvaluations,
					 executionState.unattributedVectorEvaluations,
					 executionState.executorTuplePassCount,
					 executionState.executorTupleFailCount);
		if (executionState.policyStopped || executionState.fixedBudgetStopped)
			appendStringInfo(&terminal,
						 "{\"layer0_distance_evaluations\":" INT64_FORMAT ","
						 "\"upper_distance_evaluations\":" INT64_FORMAT "}",
						 executionState.distanceAtLastCheckpoint,
						 executionState.upperDistanceEvaluations);
		else
			appendStringInfoString(&terminal, "null");
		if (executionState.policyStopped || executionState.fixedBudgetStopped)
			appendStringInfo(&terminal,
						 ",\"finalization_work\":{\"layer0_distance_evaluations\":" INT64_FORMAT "},"
						 "\"finalization_work_coverage\":\"layer0_only\"}",
						 executionState.distanceEvaluations - executionState.distanceAtLastCheckpoint);
		else
			appendStringInfoString(&terminal,
						 ",\"finalization_work\":null,"
						 "\"finalization_work_reason\":\"no_early_stop\"}");
		TraceLine(terminal.data, true);
		pfree(terminal.data);
		if (fclose(executionState.traceFile) != 0)
			executionState.traceTruncated = true;
		executionState.traceFile = NULL;
		executionState.traceComplete = true;
	}

	initStringInfo(&result);
	appendStringInfo(&result,
					 "{\"protocol\":\"same_execution_v4\","
					 "\"request_nonce\":\"%s\",\"effective_mode\":\"%s\","
					 "\"policy_hash\":",
					 executionState.nonce, executionState.mode);
	if (executionState.hasPolicyHash)
		appendStringInfo(&result, "\"%s\"", executionState.policyHash);
	else
		appendStringInfoString(&result, "null");
	appendStringInfo(&result,
					 ",\"observation_applied\":%s,\"policy_applied\":%s,"
					 "\"policy_opportunity\":",
					 observationApplied ? "true" : "false",
					 policyApplied ? "true" : "false");
	if (nativeMode)
		appendStringInfoString(&result, "null");
	else
		appendStringInfoString(&result, opportunity ? "true" : "false");
	appendStringInfo(&result,
					 ",\"executed_path\":\"%s\",\"stop_reason\":\"%s\","
					 "\"checkpoint_count\":",
					 path, stopReason);
	if (nativeMode)
		appendStringInfoString(&result, "null,\"work_counters\":{}");
	else
		appendStringInfo(&result,
						 INT64_FORMAT ",\"work_counters\":{"
						 "\"layer0_distance_evaluations\":" INT64_FORMAT ","
						 "\"upper_distance_evaluations\":" INT64_FORMAT ","
						 "\"unattributed_vector_evaluations\":" INT64_FORMAT ","
						 "\"completed_expansions\":" INT64_FORMAT ","
						 "\"unique_discoveries\":" INT64_FORMAT ","
						 "\"queue_pops\":" INT64_FORMAT ","
						 "\"adjacency_entries_examined\":" INT64_FORMAT ","
						 "\"executor_tuple_pass_count\":" INT64_FORMAT ","
						 "\"executor_tuple_fail_count\":" INT64_FORMAT ","
						 "\"feature_collection_count\":" INT64_FORMAT ","
						 "\"feature_collection_ns\":" INT64_FORMAT ","
						 "\"frontier_snapshot_count\":" INT64_FORMAT ","
						 "\"frontier_values_copied\":" INT64_FORMAT ","
						 "\"frontier_maximum_count\":" INT64_FORMAT ","
						 "\"frontier_traversal_ns\":" INT64_FORMAT ","
						 "\"frontier_statistics_ns\":" INT64_FORMAT ","
						 "\"frontier_sort_count\":" INT64_FORMAT ","
						 "\"frontier_sort_ns\":" INT64_FORMAT ","
						 "\"frontier_quantile_ns\":" INT64_FORMAT ","
						 "\"policy_evaluation_count\":" INT64_FORMAT ","
						 "\"policy_evaluation_ns\":" INT64_FORMAT "}",
						 executionState.checkpointCount,
						 executionState.distanceEvaluations,
						 executionState.upperDistanceEvaluations,
						 executionState.unattributedVectorEvaluations,
						 executionState.completedExpansions,
						 executionState.uniqueDiscoveries,
						 executionState.queuePops,
						 executionState.adjacencyEntriesExamined,
						 executionState.executorTuplePassCount,
						 executionState.executorTupleFailCount,
						 executionState.featureCollectionCount,
						 executionState.featureCollectionNanos,
						 executionState.frontierSnapshotCount,
						 executionState.frontierValuesCopied,
						 executionState.frontierMaximumCount,
						 executionState.frontierTraversalNanos,
						 executionState.frontierStatisticsNanos,
						 executionState.frontierSortCount,
						 executionState.frontierSortNanos,
						 executionState.frontierQuantileNanos,
						 executionState.policyEvaluationCount,
						 executionState.policyEvaluationNanos);
	appendStringInfo(&result,
					 ",\"policy_fallback\":%s,\"policy_runtime_error\":",
					 executionState.policyFallback ? "true" : "false");
	if (executionState.policyRuntimeError[0] != '\0')
		appendStringInfo(&result, "\"%s\"", executionState.policyRuntimeError);
	else
		appendStringInfoString(&result, "null");
	if (strcmp(executionState.traceLevel, "off") != 0)
		appendStringInfo(&result,
					 ",\"trace_descriptor\":{\"file\":\"%s.jsonl\","
					 "\"bytes\":" INT64_FORMAT ",\"truncated\":%s,"
					 "\"feature_registry_hash\":\"%s\","
					 "\"feature_set_hash\":\"%s\"}",
					 executionState.nonce, executionState.traceBytes,
					 executionState.traceTruncated ? "true" : "false",
					 executionState.registryHash, executionState.featureSetHash);
	else
		appendStringInfoString(&result, ",\"trace_descriptor\":null");
	appendStringInfo(&result,
        ",\"returned_count\":%d,\"returned_count_source\":\"%s\","
        "\"stop_scope\":\"hnsw_scan\",\"target_index_oid\":%u",
        executionState.returnedCount, PG_NARGS() == 2 ? "client_reported" : "wrapper_observed",
        boundIndex);
    appendStringInfoChar(&result, '}');
	strlcpy(completedTrace, executionState.tracePath, sizeof(completedTrace));
    strlcpy(completedNonce, executionState.nonce, sizeof(completedNonce));
    if (executionState.localFilterEnabled && strcmp(executionState.traceLevel, "off") != 0)
    {
        char *receipt = LocalProbeJson();
        strlcpy(completedLocalProbe, receipt, sizeof(completedLocalProbe));
        pfree(receipt);
    }
    else completedLocalProbe[0] = '\0';
    if (executionState.progressFilterEnabled && strcmp(executionState.traceLevel,"off")!=0)
    {char *receipt=ProgressProbeJson();strlcpy(completedProgressProbe,receipt,sizeof(completedProgressProbe));pfree(receipt);}
    else completedProgressProbe[0]='\0';
    memcpy(completedShadow, executionState.shadow, sizeof(completedShadow));
    ResetExecutionState();
	pfree(nonce);
	PG_RETURN_TEXT_P(cstring_to_text(result.data));
}

int
FannbenchStudyThreshold(void)
{
    return studyThreshold;
}
