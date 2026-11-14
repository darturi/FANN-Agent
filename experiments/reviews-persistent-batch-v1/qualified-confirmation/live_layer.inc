/* Same resident result heap and cosine conversion as the qualified shadow. */
static bool
ConfirmStop(int arm, int checkpoint, pairingheap *pending, pairingheap *retained, char *base)
{
	double top[10] = {0};
	uint64 tids[10] = {0};
	int count = 0;
	double frontier;

	if (pairingheap_is_empty(pending))
		return false;
	frontier = 1.0 + HnswGetSearchCandidate(c_node, pairingheap_first(pending))->distance;
	if (!isfinite(frontier))
		elog(ERROR, "nonfinite confirmation frontier");
	FannbenchShadowStart();
	ShadowRetainedNode(retained->ph_root, base, &count, top, tids);
	if (count < 10)
		return false;
	return ConfirmationRule(arm, checkpoint, frontier - top[9], top[9]);
}
