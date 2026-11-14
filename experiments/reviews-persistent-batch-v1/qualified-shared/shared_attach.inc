PG_FUNCTION_INFO_V1(fannbench_confirm_attach);
Datum
fannbench_confirm_attach(PG_FUNCTION_ARGS)
{
	Oid heap = PG_GETARG_OID(0);
	Oid index = PG_GETARG_OID(1);
	int arm = PG_GETARG_INT32(2);
	char *path = psprintf("%s/../votes108-membership.bin", DataDir);
	uint32 expected[4] = {heap, index, 247286, 49498};
	HASHCTL ctl = {0};
	struct stat st;
	void *mapping;
	int fd;

	if ((arm != 1 && arm != 2) || IndexGetRelation(index, false) != heap ||
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
	confirmationIndex = index;
	confirmationArm = arm;
	confirmationStop = -1;
	PG_RETURN_INT32(247286);
}
