#ifndef FANNBENCH_H
#define FANNBENCH_H

#include "postgres.h"
#include "access/genam.h"

void		FannbenchInit(void);
void		FannbenchHnswRouteReached(void);
void		FannbenchHnswLayerStart(int64 entryCount, double entryDistance);
void		FannbenchHnswQueuePop(void);
void		FannbenchHnswAdjacencyExamined(void);
void		FannbenchHnswUpperDistance(int64 count);
void		FannbenchHnswLayer0EntryDistance(void);
void		FannbenchHnswLayerScore(int level);
void		FannbenchHnswScoring(bool inside);
void		FannbenchVectorDistanceComputed(void);
void		FannbenchHnswRetained(int count, int capacity);
bool		FannbenchHnswAuditEnabled(void);
void		FannbenchHnswAuditDiscovery(BlockNumber block, OffsetNumber offset);
void		FannbenchHnswAuditFrontier(BlockNumber block, OffsetNumber offset, bool inserted);
void		FannbenchHnswAuditFrontierReset(void);
void		FannbenchHnswAuditIdentity(Relation index, BlockNumber block,
										 OffsetNumber offset, ItemPointer heaptids, int count);
void		FannbenchHnswScanReset(IndexScanDesc scan);
void		FannbenchHnswScanEnded(IndexScanDesc scan);
void		FannbenchHnswCandidateReturned(IndexScanDesc scan, BlockNumber block,
										 OffsetNumber offset, ItemPointer heapTid,
										 double distance);
bool		FannbenchHnswQueueSnapshotNeeded(int64 upcomingDistances);
void		FannbenchHnswSetFrontierDistances(double *distances, int count,
									 int64 traversalNanos);

int FannbenchConfirmArm(Relation index);
void FannbenchConfirmStopped(int checkpoint);
int FannbenchShadowCheckpoint(Relation index);
void FannbenchShadowStart(void);
bool FannbenchShadowQualifies(ItemPointer tid);
void FannbenchShadowRecord(int checkpoint, int count, double tenth,
                           const uint64 top_tids[10], uint64 nanos);

bool		FannbenchHnswObserveDistances(int64 count, int64 frontierCount,
										 bool hasFrontier, double frontierBestDistance);

#endif

bool FannbenchLocalProbeEnabled(void);
void FannbenchLocalProbe(Relation index, BlockNumber block, OffsetNumber offset, ItemPointer tids, int count);

void FannbenchProgressProbe(Relation index, BlockNumber block, OffsetNumber offset, ItemPointer tids, int count, double distance);
