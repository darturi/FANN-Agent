"""Build the immutable physical-TID lookup for one locked Reviews restore."""

import os
import struct

from rb_plan import file_sha, require

FILENAME = "votes108-membership.bin"
PAGE_BYTES = 128
ROWS = 247286
QUALIFYING = 49498
MAX_BYTES = 256 * 1024 * 1024


def publish(path, heap, index, rows):
    # One 2-bit slot per possible CTID offset. 0 = absent, 1 = ineligible, 3 = eligible.
    decoded = []
    for tid, qualifies in rows:
        if isinstance(tid, bytes):
            tid = tid.decode("ascii")
        block, offset = (int(i) for i in tid[1:-1].split(","))
        require(0 <= block and 1 <= offset <= PAGE_BYTES * 4, "Invalid heap TID")
        decoded.append((block, offset - 1, qualifies))
    require(
        len(decoded) == ROWS and sum(flag for _, _, flag in decoded) == QUALIFYING,
        "Unexpected membership cohort",
    )
    pages = (max(block for block, _, _ in decoded) + 1) * PAGE_BYTES
    header = struct.pack("<8sIIII", b"V108MAP1", heap, index, ROWS, QUALIFYING)
    require(len(header) + pages <= MAX_BYTES, "Shared lookup size exceeds limit")
    contents = bytearray(pages)
    for block, offset, qualifies in decoded:
        byte = block * PAGE_BYTES + offset // 4
        shift = (offset % 4) * 2
        require(not contents[byte] & (3 << shift), "Duplicate heap TID")
        contents[byte] |= (3 if qualifies else 1) << shift
    temp = path.with_suffix(".pending")
    require(not path.exists(), "Lookup already published")
    try:
        with temp.open("xb") as out:
            out.write(header)
            out.write(contents)
            out.flush()
            os.fchmod(out.fileno(), 0o400)
            os.fsync(out.fileno())
        temp.rename(path)
    finally:
        temp.unlink(missing_ok=True)
    return {
        "rows": ROWS,
        "qualifying": QUALIFYING,
        "bytes": path.stat().st_size,
        "sha256": file_sha(path),
    }
