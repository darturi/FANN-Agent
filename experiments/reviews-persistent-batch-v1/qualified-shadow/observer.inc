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
static uint64 shadowGeneration;
static bool shadowCallbackRegistered;

static uint64
ShadowTidKey(ItemPointer tid)
{
	return ((uint64) ItemPointerGetBlockNumber(tid) << 16) |
		ItemPointerGetOffsetNumber(tid);
}

static void
ShadowEndTransaction(XactEvent event, void *arg)
{
	if (event == XACT_EVENT_COMMIT || event == XACT_EVENT_ABORT ||
		event == XACT_EVENT_PREPARE || event == XACT_EVENT_PARALLEL_ABORT ||
		event == XACT_EVENT_PARALLEL_COMMIT)
	{
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
	query = psprintf("SELECT ctid, coalesce(total_votes >= 108, false) FROM ONLY %s",
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
	if (passing != 49498)
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

	if (!shadowMembers || !executionState.active ||
		executionState.distanceEvaluations < executionState.nextCheckpointTarget ||
		strcmp(executionState.mode, "native") == 0)
		return 0;
	if (!XactReadOnly || !IsolationUsesXactSnapshot() ||
		GetCurrentTransactionNestLevel() != 1 ||
		executionState.requestedK != 10 || executionState.predicateLeafCount != 1 ||
		executionState.queryPredicateThreshold != 108 ||
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
	ShadowMember *member = hash_search(shadowMembers, &key, HASH_FIND, NULL);

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

	if (!shadowMembers || executionState.active ||
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
