/* Generated from frozen model-authored JSON; do not edit thresholds. */
static bool CompiledStudyRule(int arm, int filter, int cp, int count, double gap, double tenth, int turnover)
{
  if (count < 10) return false;
  if (arm == 7 && filter == -1 && cp == 64 && gap >= 0x1.3333333333333p-3 && tenth <= 0x1.70a3d70a3d70ap-2) return true;
  if (arm == 7 && filter == 32 && cp == 64 && gap >= 0x1.eb851eb851eb8p-4 && tenth <= 0x1.7ae147ae147aep-2) return true;
  if (arm == 8 && filter == -1 && cp == 32 && gap >= 0x1.3333333333333p-3 && tenth <= 0x1.5c28f5c28f5c3p-2 && turnover >= 0 && turnover <= 0x0.0p+0) return true;
  if (arm == 8 && filter == -1 && cp == 64 && gap >= 0x1.3333333333333p-3 && tenth <= 0x1.70a3d70a3d70ap-2) return true;
  if (arm == 8 && filter == 108 && cp == 64 && gap >= 0x1.47ae147ae147bp-4 && tenth <= 0x1.851eb851eb852p-2 && turnover >= 0 && turnover <= 0x0.0p+0) return true;
  if (arm == 8 && filter == 192 && cp == 64 && gap >= 0x1.1eb851eb851ecp-4 && tenth <= 0x1.70a3d70a3d70ap-2 && turnover >= 0 && turnover <= 0x0.0p+0) return true;
  if (arm == 8 && filter == 32 && cp == 32 && gap >= 0x1.999999999999ap-4 && tenth <= 0x1.6666666666666p-2 && turnover >= 0 && turnover <= 0x0.0p+0) return true;
  if (arm == 8 && filter == 32 && cp == 64 && gap >= 0x1.47ae147ae147bp-4 && tenth <= 0x1.851eb851eb852p-2 && turnover >= 0 && turnover <= 0x0.0p+0) return true;
  if (arm == 9 && filter == -1 && cp == 16 && gap >= 0x1.3333333333333p-3 && tenth <= 0x1.51eb851eb851fp-2) return true;
  if (arm == 9 && filter == -1 && cp == 32 && gap >= 0x1.3333333333333p-3 && tenth <= 0x1.5c28f5c28f5c3p-2 && turnover >= 0 && turnover <= 0x0.0p+0) return true;
  if (arm == 9 && filter == 108 && cp == 64 && gap >= 0x1.eb851eb851eb8p-5 && tenth <= 0x1.999999999999ap-2 && turnover >= 0 && turnover <= 0x0.0p+0) return true;
  if (arm == 9 && filter == 192 && cp == 64 && gap >= 0x1.999999999999ap-5 && tenth <= 0x1.851eb851eb852p-2 && turnover >= 0 && turnover <= 0x0.0p+0) return true;
  if (arm == 9 && filter == 310 && cp == 64 && gap >= 0x1.999999999999ap-5 && tenth <= 0x1.999999999999ap-2 && turnover >= 0 && turnover <= 0x0.0p+0) return true;
  if (arm == 9 && filter == 32 && cp == 32 && gap >= 0x1.47ae147ae147bp-4 && tenth <= 0x1.7ae147ae147aep-2 && turnover >= 0 && turnover <= 0x0.0p+0) return true;
  if (arm == 9 && filter == 32 && cp == 64 && gap >= 0x1.eb851eb851eb8p-5 && tenth <= 0x1.999999999999ap-2 && turnover >= 0 && turnover <= 0x0.0p+0) return true;
  if (arm == 9 && filter == 527 && cp == 64 && gap >= 0x1.eb851eb851eb8p-6 && tenth <= 0x1.ae147ae147ae1p-2 && turnover >= 0 && turnover <= 0x0.0p+0) return true;
  return false;
}
