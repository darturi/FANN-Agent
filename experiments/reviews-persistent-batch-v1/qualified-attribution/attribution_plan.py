"""Balance the three native readers across six batches and six epochs."""

from itertools import permutations

from analyze import BATCHES, SIZE

ARMS = ("native-A", "native-B", "native-C")
ORDERS = tuple(permutations(ARMS))


def schedule():
    for epoch in range(len(ORDERS)):
        for slot in range(BATCHES):
            batch = (2 * epoch + slot) % BATCHES
            # Every batch and every chronological slot sees all six reader orders.
            order = ORDERS[(batch - epoch) % len(ORDERS)]
            offset = epoch
            requests = [batch * SIZE + (i + offset) % SIZE for i in range(SIZE)]
            for arm in order:
                yield epoch, batch, arm, requests
