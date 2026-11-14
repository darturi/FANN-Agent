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
	if (!shadowMembers || executionState.active || !XactReadOnly ||
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
