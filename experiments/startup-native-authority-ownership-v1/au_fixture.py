"""Linux-only benign lifecycle fixtures; no data, SQL, provider or search code."""

import os
import signal
import sys
import threading
import time


def linger(ignore=False):
    if ignore:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    while True:
        time.sleep(0.05)


def main():
    mode = sys.argv[1]
    if mode == "normal":
        return
    if mode == "nonzero":
        raise SystemExit(42)
    if mode == "linger":
        linger()
    if mode == "ignore":
        linger(True)
    if mode in ("orphan", "setsid", "doublefork", "threadfork"):

        def fork():
            child = os.fork()
            if child == 0:
                if mode in ("setsid", "doublefork"):
                    os.setsid()
                if mode == "doublefork":
                    if os.fork() != 0:
                        os._exit(0)
                linger()

        if mode == "threadfork":
            t = threading.Thread(target=fork)
            t.start()
            t.join()
        else:
            fork()
        os._exit(0)
    raise ValueError("Unknown fixed lifecycle fixture")


if __name__ == "__main__":
    main()
