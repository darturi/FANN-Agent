"""Blocked-before-exec gate. Its single-use pipe never reaches science code."""

import os
import select
import sys
import time


def main():
    fd, end = int(sys.argv[1]), float(sys.argv[2])
    while time.monotonic() < end:
        if select.select([fd], [], [], min(0.05, end - time.monotonic()))[0]:
            value = os.read(fd, 2)
            os.close(fd)
            if value != b"1":
                raise RuntimeError("Exec registration was not released")
            argv = sys.argv[3:]
            os.execvpe(argv[0], argv, os.environ)
    raise TimeoutError("Exec gate deadline")


if __name__ == "__main__":
    main()
