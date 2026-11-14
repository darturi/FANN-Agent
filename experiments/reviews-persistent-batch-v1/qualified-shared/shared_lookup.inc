#define CONFIRM_PAGE_BYTES 128
#define CONFIRM_HEADER_BYTES 24
#define CONFIRM_MAX_BYTES (256 * 1024 * 1024)

static unsigned char *confirmMap;
static size_t confirmMapBytes;
static HTAB *confirmSeen;

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
