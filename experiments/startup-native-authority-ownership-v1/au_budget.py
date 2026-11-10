"""One anonymous ledger across all serial owners; original read/byte ceilings."""

import fcntl
import os
import struct

MAX_READS = 500000
MAX_BYTES = 512 * 1024**2


class ReadBudget:
    def __init__(self, fd=None):
        if fd is None:
            fd = os.memfd_create("a3-owned-read-ledger", os.MFD_CLOEXEC)
            os.write(fd, struct.pack("!QQ", 0, 0))
        if os.fstat(fd).st_size != 16:
            raise ValueError("Invalid inherited read ledger")
        self.fd = fd

    def reserve(self, reads=0, bytes=0):
        if type(reads) is not int or type(bytes) is not int or reads < 0:
            raise ValueError("Strict read accounting")
        fcntl.lockf(self.fd, fcntl.LOCK_EX)
        try:
            r, b = struct.unpack("!QQ", os.pread(self.fd, 16, 0))
            r += reads
            b += bytes
            if not 0 <= r <= MAX_READS or not 0 <= b <= MAX_BYTES:
                raise RuntimeError("Original combined proc read/byte budget exhausted")
            if os.pwrite(self.fd, struct.pack("!QQ", r, b), 0) != 16:
                raise RuntimeError("Read ledger write incomplete")
        finally:
            fcntl.lockf(self.fd, fcntl.LOCK_UN)

    def usage(self):
        fcntl.lockf(self.fd, fcntl.LOCK_SH)
        try:
            r, b = struct.unpack("!QQ", os.pread(self.fd, 16, 0))
            return {"reads": r, "bytes": b, "max_reads": MAX_READS, "max_bytes": MAX_BYTES}
        finally:
            fcntl.lockf(self.fd, fcntl.LOCK_UN)
