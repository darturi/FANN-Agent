"""The private startup backend exposes connection/snapshot work, no search methods."""

import time

from pc_interface import Factory as PriorFactory
from pc_interface import bound_class


def prohibited(*args, **kwargs):
    raise RuntimeError("ANN/exact search entry point prohibited in startup-only resource study")


def startup_class(base, cell, target):
    class StartupBackend(bound_class(base, cell, target)):
        _statement = execute_probe = exact_reference = _exact_reference = _qualify = prohibited
        execute = query = run = prepare = prohibited

    return StartupBackend


class Factory(PriorFactory):
    def __init__(self, base, bundle, works, targets, observer, budget, emit):
        super().__init__(base, bundle, works, targets, observer, budget, emit)
        self.classes = {c: startup_class(base, c, targets[c]) for c in works}

    def create(self, cell, role):
        reader = super().create(cell, role)
        self.emit(
            "lifecycle", dict(kind="open", reader=role, cell=cell, time_ns=time.monotonic_ns())
        )
        original = reader.close

        def close():
            live = not reader.closed
            original()
            if live:
                self.emit(
                    "lifecycle",
                    dict(kind="close", reader=role, cell=cell, time_ns=time.monotonic_ns()),
                )

        reader.close = close
        return reader
