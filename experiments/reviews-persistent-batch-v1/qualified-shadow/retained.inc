/* Traverse W without consuming or modifying the pairing heap. */
static void
ShadowRetainedNode(pairingheap_node *node, char *base, int *count, double top[10], uint64 tids[10])
{
	while (node)
	{
		HnswSearchCandidate *candidate = HnswGetSearchCandidate(w_node, node);
		HnswElement element = HnswPtrAccess(base, candidate->element);
		double distance = 1.0 + candidate->distance;

		if (!isfinite(distance))
			elog(ERROR, "nonfinite shadow cosine distance: %.17g", distance);
		/* Normalized float vectors can round outside the cosine range.
		 * Apply the same endpoint clamp as the SQL cosine operator. */
		distance = Max(0.0, Min(2.0, distance));
		for (int i = 0; i < element->heaptidsLength; i++)
		{
			int pos;
			ItemPointer tid = &element->heaptids[i];
			uint64 key;

			if (!FannbenchShadowQualifies(tid))
				continue;
			key = ((uint64) ItemPointerGetBlockNumber(tid) << 16) | ItemPointerGetOffsetNumber(tid);
			pos = Min(*count, 9);
			if (*count < 10 || distance < top[9] || (distance == top[9] && key < tids[9]))
			{
				while (pos > 0 && (distance < top[pos - 1] ||
					   (distance == top[pos - 1] && key < tids[pos - 1])))
				{
					top[pos] = top[pos - 1];
					tids[pos] = tids[pos - 1];
					pos--;
				}
				top[pos] = distance;
				tids[pos] = key;
			}
			(*count)++;
		}
		ShadowRetainedNode(node->first_child, base, count, top, tids);
		node = node->next_sibling;
	}
}

static void
ShadowRetained(Relation index, pairingheap *retained, char *base)
{
	int checkpoint = FannbenchShadowCheckpoint(index);
	int count = 0;
	double top[10] = {0};
	uint64 tids[10] = {0};
	instr_time start, elapsed;

	if (!checkpoint)
		return;
	INSTR_TIME_SET_CURRENT(start);
	FannbenchShadowStart();
	ShadowRetainedNode(retained->ph_root, base, &count, top, tids);
	INSTR_TIME_SET_CURRENT(elapsed);
	INSTR_TIME_SUBTRACT(elapsed, start);
	FannbenchShadowRecord(checkpoint, count, top[9], tids, INSTR_TIME_GET_NANOSEC(elapsed));
}
