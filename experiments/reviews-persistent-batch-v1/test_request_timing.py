"""Check the diagnostic's protocol framing and subtraction on numeric fixtures."""

import unittest

from rb_persistent import REQUESTS
from rb_request_timing import NATIVE_PREFIX, request_components, server_timings


class RequestTimingTests(unittest.TestCase):
    def test_prepared_protocol_and_unlogged_reader(self):
        lines = []
        for request in range(REQUESTS):
            for phase, milliseconds in (
                (("parse", "0.010"), ("bind", "0.100"), ("execute", "2.003"))
                if request == 0
                else (("bind", "0.100"), ("execute", "2.003"))
            ):
                lines.append(
                    f"reviews_diag 123 {len(lines) + 1} LOG:  duration: {milliseconds} ms  "
                    f"{phase} _pg3_0: ".encode()
                    + NATIVE_PREFIX
                    + b"WHERE true"
                )
        log = b"\n".join(lines)
        timings = server_timings(log, {123: True, 456: False})
        self.assertEqual(timings[123][0], [10, 100, 2003])
        self.assertEqual(timings[123][1:], [[None, 100, 2003]] * (REQUESTS - 1))
        with self.assertRaisesRegex(ValueError, "Unexpected native server timing"):
            server_timings(log, {123: False})
        with self.assertRaisesRegex(ValueError, "Incomplete server duration"):
            server_timings(b"\n".join(lines[:-1]), {123: True})

    def test_parts_cover_request_and_enforce_timing_boundary(self):
        row = {
            "request_ns": [0, 4_000_000],
            "execute_ns": [200_000, 3_400_000],
            "fetchall_ns": [3_500_000, 3_800_000],
            "server_us": [None, 100, 2000],
        }
        parts = request_components(row, True)
        self.assertEqual(parts["server_total"], 2.1)
        self.assertAlmostEqual(parts["client_execute_residual"], 1.1)
        self.assertAlmostEqual(
            parts["server_total"]
            + parts["client_execute_residual"]
            + parts["fetchall_decode"]
            + parts["outside_execute_and_fetch"],
            parts["request"],
        )
        with self.assertRaisesRegex(ValueError, "Unlogged reader"):
            request_components(row, False)
        with self.assertRaisesRegex(ValueError, "escaped the request"):
            request_components({**row, "fetchall_ns": [3_500_000, 4_000_001]}, True)


if __name__ == "__main__":
    unittest.main()
