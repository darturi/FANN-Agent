"""Fixed two-by-two warm-up and mirrored A/B schedule for the 60 sealed queries."""

from analyze import ARMS, BATCHES, SIZE
from rb_plan import WILLIAMS_ROW

CELLS = ((0, False), (2, False), (0, True), (2, True))
# Each pair of consecutive batches reverses cell order and complements both factors.
ORDER = (
    (0, 1, 2, 3),
    (3, 2, 1, 0),
    (1, 3, 0, 2),
    (2, 0, 3, 1),
    (0, 2, 1, 3),
    (3, 1, 2, 0),
)


def schedule():
    for batch, cell_order in enumerate(ORDER):
        scored = range(batch * SIZE, (batch + 1) * SIZE)
        start = ((batch + 1) % BATCHES) * SIZE + batch
        for cell in cell_order:
            count, mirror = CELLS[cell]
            warmup = range(start, start + count)
            for slot, label in enumerate(WILLIAMS_ROW):
                arm = ARMS[((label + batch) % len(ARMS)) ^ int(mirror)]
                yield batch, count, mirror, slot, arm, warmup, scored
