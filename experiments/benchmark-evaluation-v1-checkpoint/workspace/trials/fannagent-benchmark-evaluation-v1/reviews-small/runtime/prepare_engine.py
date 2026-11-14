"""Stage an isolated all-predicate qualification variant of the retained engine."""
from pathlib import Path
import argparse,sys
ROOT=Path(__file__).resolve().parents[4]
OLD=ROOT/'agent/experiments/reviews-persistent-batch-v1'
sys.path[:0]=[str(OLD/'qualified-shared'),str(OLD)]
from prepare_shared import stage

def replace(p,old,new):
 s=p.read_text();assert s.count(old)==1,(p,old,s.count(old));p.write_text(s.replace(old,new))
def prepare(dest):
 stage(dest);c=dest/'src/fannbench.c';h=dest/'src/hnswutils.c'
 replace(c,'static Oid confirmationIndex = InvalidOid;','static int studyThreshold = -2;\nstatic Oid confirmationIndex = InvalidOid;')
 replace(c,'if (!shadowMembers || !executionState.active ||','if ((!shadowMembers && !confirmMap) || !executionState.active ||')
 replace(c,'executionState.requestedK != 10 || executionState.predicateLeafCount != 1 ||\n\t\texecutionState.queryPredicateThreshold != 108 ||','executionState.requestedK != 10 ||\n        executionState.predicateLeafCount != (studyThreshold < 0 ? 0 : 1) ||\n        executionState.queryPredicateThreshold != (studyThreshold < 0 ? 0 : studyThreshold) ||')
 replace(c,'if (!shadowMembers || executionState.active ||','if ((!shadowMembers && !confirmMap) || executionState.active ||')
 replace(c,'int arm = PG_GETARG_INT32(2);\n\tchar *path', 'int threshold = PG_GETARG_INT32(2);\n    int arm = PG_GETARG_INT32(3);\n    int expectedPassing = PG_GETARG_INT32(4);\n\tchar *path')
 replace(c,'psprintf("%s/../votes108-membership.bin", DataDir)','psprintf("%s/../membership-%d.bin", DataDir, threshold)')
 replace(c,'uint32 expected[4] = {heap, index, 247286, 49498};','uint32 expected[4] = {heap, index, 247286, expectedPassing};')
 replace(c,'if ((arm != 1 && arm != 2) || IndexGetRelation(index, false) != heap ||','if (arm < 0 || arm > 6 || expectedPassing < 0 || expectedPassing > 247286 ||\n        (threshold != -1 && threshold != 743 && threshold != 527 && threshold != 310 &&\n         threshold != 192 && threshold != 108 && threshold != 32) ||\n        IndexGetRelation(index, false) != heap ||')
 replace(c,'HASH_ELEM | HASH_BLOBS | HASH_CONTEXT);\n\tconfirmationIndex = index;', 'HASH_ELEM | HASH_BLOBS | HASH_CONTEXT);\n    shadowRelation = heap;\n    studyThreshold = threshold;\n\tconfirmationIndex = index;')
 # Avoid declaration-order problems: map declarations must precede observer functions.
 s=c.read_text();block='static unsigned char *confirmMap;\nstatic size_t confirmMapBytes;\nstatic HTAB *confirmSeen;\n'
 assert s.count(block)==1;s=s.replace(block,'');s=s.replace('static int studyThreshold = -2;',block+'\nstatic int studyThreshold = -2;');c.write_text(s)
 replace(h,'int confirmLast = confirmArm == 1 ? 32 : 64;','int confirmLast = 64;')
 replace(h,'if ((confirmCheckpoint == 32 ||\n\t\t\t\t\t(confirmArm == 2 && (confirmCheckpoint == 16 || confirmCheckpoint == 64))) &&','if ((confirmCheckpoint == 16 || confirmCheckpoint == 32 || confirmCheckpoint == 64) &&')
 start=h.read_text().index('static bool\nConfirmationRule(');end=h.read_text().index('/* Same resident result heap',start)
 s=h.read_text();s=s[:start]+'''static bool
ConfirmationRule(int arm, int checkpoint, double gap, double tenth)
{
    if (arm == 1) return checkpoint == 32 && gap >= 0.05;
    if (arm == 2) return (checkpoint == 16 && gap >= 0.02 && tenth <= 0.44) ||
        (checkpoint == 32 && gap >= 0.025 && tenth <= 0.38) ||
        (checkpoint == 64 && gap >= 0.05);
    if (arm >= 3 && arm <= 5) return checkpoint == (arm == 3 ? 16 : arm == 4 ? 32 : 64);
    return false; /* arm 6 collects all decision features and always continues */
}

'''+s[end:];h.write_text(s)
 # Local membership reference uses the identical snapshot/filter semantics.
 replace(c,'Oid relation = PG_GETARG_OID(0);\n\tchar *name;', 'Oid relation = PG_GETARG_OID(0);\n    int threshold = PG_GETARG_INT32(1);\n    int expectedPassing = PG_GETARG_INT32(2);\n\tchar *name;')
 replace(c,'query = psprintf("SELECT ctid, coalesce(total_votes >= 108, false) FROM ONLY %s",\n\t\t\t\t\t quote_qualified_identifier(namespace, name));', 'studyThreshold = threshold;\n    query = psprintf("SELECT ctid, %s FROM ONLY %s",\n        threshold < 0 ? "true" : psprintf("coalesce(total_votes >= %d, false)", threshold),\n        quote_qualified_identifier(namespace, name));')
 replace(c,'if (passing != 49498)', 'if (passing != expectedPassing)')
 # Future agent compiler gets the same causal turnover value as shadow capture.
 replace(h,'ConfirmationRule(int arm, int checkpoint, double gap, double tenth)', 'ConfirmationRule(int arm, int checkpoint, double gap, double tenth, int turnover)')
 replace(h,'/* Same resident result heap and cosine conversion as the qualified shadow. */', 'static uint64 studyPreviousTids[10];\nstatic bool studyPreviousFull;\n\n/* Same resident result heap and cosine conversion as the qualified shadow. */')
 replace(h,'int count = 0;\n\tdouble frontier;', 'int count = 0;\n    int turnover = -1;\n\tdouble frontier;')
 replace(h,'\tif (count < 10)\n\t\treturn false;\n\treturn ConfirmationRule(arm, checkpoint, frontier - top[9], top[9]);',
     '\tif (count >= 10 && studyPreviousFull)\n    {\n        turnover = 0;\n        for (int i = 0; i < 10; i++)\n        {\n            bool found = false;\n            for (int j = 0; j < 10; j++) found |= tids[i] == studyPreviousTids[j];\n            turnover += !found;\n        }\n    }\n    studyPreviousFull = count >= 10;\n    memcpy(studyPreviousTids, tids, sizeof(tids));\n    if (count < 10) return false;\n    return ConfirmationRule(arm, checkpoint, frontier - top[9], top[9], turnover);')
 replace(h,'\tif (confirmArm)\n\t{', '\tif (confirmArm)\n\t{\n        studyPreviousFull = false;')
 # Fix endpoint consistency with the qualified SQL/retained cosine scorer.
 replace(h,'frontier = 1.0 + HnswGetSearchCandidate(c_node, pairingheap_first(pending))->distance;','frontier = Max(0.0, Min(2.0, 1.0 + HnswGetSearchCandidate(c_node, pairingheap_first(pending))->distance));')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('destination',type=Path);prepare(p.parse_args().destination)
