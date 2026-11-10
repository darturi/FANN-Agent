"""Offline adversarial tests; scheduler paths are never executed."""
import hashlib
import json
import os
from pathlib import Path
import stat
import signal
import struct
import subprocess
import sys
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import compatibility as M

HERE = Path(__file__).resolve().parent
OUT = Path(os.environ["A3_COMPAT_TEST_OUT"])
DATA = (HERE / "candidate.conf").read_bytes()
REAL_POPEN = subprocess.Popen


def elf(needed=("libfixture.so.1",), *, machine=62, rpath=None, runpath=None, interpreter=True):
    """Small independent ELF layout with interpreter and DT_STRTAB mapping."""
    data = bytearray(2048)
    data[:16] = b"\x7fELF\x02\x01\x01" + b"\0" * 9
    struct.pack_into("<HHIQQQIHHHHHH", data, 16, 3, machine, 1, 0, 64, 0, 0, 64, 56, 3, 0, 0, 0)
    struct.pack_into("<IIQQQQQQ", data, 64, 1, 5, 0, 0x400000, 0, 2048, 2048, 4096)
    interp = b"/lib64/ld-linux-x86-64.so.2\0"
    struct.pack_into("<IIQQQQQQ", data, 120, 3, 4, 256, 0, 0, len(interp), len(interp), 1)
    if not interpreter:
        struct.pack_into("<I", data, 120, 0)
    data[256:256 + len(interp)] = interp
    strings = bytearray(b"\0")
    entries = []
    for value, tag in [(v, 1) for v in needed] + [("libfixture.so.1", 14)] + ([(rpath, 15)] if rpath else []) + ([(runpath, 29)] if runpath else []):
        entries.append((tag, len(strings)))
        strings.extend(value.encode() + b"\0")
    data[1024:1024 + len(strings)] = strings
    entries = [(5, 0x400000 + 1024), (10, len(strings)), *entries, (30, 8), (0, 0)]
    struct.pack_into("<IIQQQQQQ", data, 176, 2, 4, 512, 0, 0, 16 * len(entries), 16 * len(entries), 8)
    for i, pair in enumerate(entries):
        struct.pack_into("<qQ", data, 512 + 16 * i, *pair)
    return bytes(data)


class Cases(unittest.TestCase):
    def setUp(self):
        self.folder = OUT / self._testMethodName
        self.folder.mkdir(mode=0o700)

    def fixture(self, body):
        path = self.folder / "fixture.py"
        path.write_text(body)
        return [sys.executable, "-B", str(path)]

    def process(self, body, timeout=1, maximum=M.OUTPUT_CAP):
        events = []
        try:
            value = M.bounded_process(self.fixture(body), {"PATH": "/usr/bin:/bin"}, (), self.folder / "raw.log", events,
                                      timeout=timeout, maximum=maximum)
            return value, events
        finally:
            (self.folder / "events.json").write_text(json.dumps(events, indent=2))

    def test_candidate_actual_pin(self):
        self.assertEqual(len(M.candidate(DATA)), 16647)
        self.assertEqual(hashlib.sha256(DATA).hexdigest(), M.CONFIG_SHA)

    def test_candidate_same_size_change(self):
        with self.assertRaises(ValueError): M.candidate(b"X" + DATA[1:])

    def test_candidate_empty(self):
        with self.assertRaises(ValueError): M.candidate(b"")

    def test_candidate_wrong_size(self):
        with self.assertRaises(ValueError): M.candidate(DATA + b"\n")

    def test_json_duplicate(self):
        with self.assertRaises(ValueError): M.decode(b'{"x":1,"x":2}')

    def test_json_nonfinite(self):
        with self.assertRaises(ValueError): M.decode(b'{"x":NaN}')

    def test_private_good(self):
        p = self.folder / "input"; p.write_bytes(DATA); p.chmod(0o600)
        raw, generation = M.bounded_file(p, M.FILE_CAP, private=True)
        self.assertEqual(raw, DATA); self.assertEqual(generation, M.stamp(p.stat()))

    def test_private_symlink(self):
        p = self.folder / "link"; p.symlink_to(HERE / "candidate.conf")
        with self.assertRaises(OSError): M.bounded_file(p, M.FILE_CAP, private=True)

    def test_private_hardlink(self):
        p = self.folder / "input"; p.write_bytes(DATA); p.chmod(0o600); os.link(p, self.folder / "second")
        with self.assertRaises(ValueError): M.bounded_file(p, M.FILE_CAP, private=True)

    def test_private_mode(self):
        p = self.folder / "input"; p.write_bytes(DATA); p.chmod(0o644)
        with self.assertRaises(ValueError): M.bounded_file(p, M.FILE_CAP, private=True)

    def test_private_fifo(self):
        p = self.folder / "fifo"; os.mkfifo(p)
        with self.assertRaises(ValueError): M.bounded_file(p, M.FILE_CAP)

    def test_private_size_bound(self):
        p = self.folder / "input"; p.write_bytes(b"ABCDE")
        with self.assertRaises(ValueError): M.bounded_file(p, 4)

    def test_private_generation_change(self):
        p = self.folder / "input"; p.write_bytes(DATA)
        old = M.stamp
        calls = []
        def changed(s):
            result = old(s); calls.append(1)
            if len(calls) > 1: result[-1] += 1
            return result
        with patch.object(M, "stamp", changed), self.assertRaises(RuntimeError): M.bounded_file(p, M.FILE_CAP)

    def test_elf_valid_independent_layout(self):
        result = M.elf64(elf(rpath="$ORIGIN/../lib", runpath="/opt/slurm/lib64"))
        self.assertEqual(result["needed"], ["libfixture.so.1"])
        self.assertEqual(result["interpreter"], "/lib64/ld-linux-x86-64.so.2")
        self.assertEqual(result["rpath"], ["$ORIGIN/../lib"])
        self.assertEqual(result["runpath"], ["/opt/slurm/lib64"])

    def test_elf_machine(self):
        with self.assertRaises(ValueError): M.elf64(elf(machine=183))

    def test_elf_short_header(self):
        with self.assertRaises(ValueError): M.elf64(elf()[:63])

    def test_elf_program_out_of_bounds(self):
        raw = bytearray(elf()); struct.pack_into("<Q", raw, 32, len(raw) - 1)
        with self.assertRaises(ValueError): M.elf64(raw)

    def test_elf_string_out_of_bounds(self):
        raw = bytearray(elf()); struct.pack_into("<Q", raw, 520, 0x900000)
        with self.assertRaises(ValueError): M.elf64(raw)

    def test_elf_unterminated_dynamic(self):
        raw = bytearray(elf()); struct.pack_into("<QQ", raw, 512 + 5 * 16, 30, 8)
        with self.assertRaises(ValueError): M.elf64(raw)

    def test_elf_duplicate_needed(self):
        with self.assertRaises(ValueError): M.elf64(elf(("libx.so", "libx.so")))

    def test_elf_big_endian(self):
        raw = bytearray(elf()); raw[5] = 2
        with self.assertRaises(ValueError): M.elf64(raw)

    def test_elf_never_executes(self):
        with patch.object(M.subprocess, "Popen", side_effect=AssertionError("ELF executed")):
            M.elf64(elf())

    def test_environment_filters_auth_and_unrelated(self):
        with patch.dict(os.environ, {"HOME": "/home/dar579", "SLURM_CONF": "/untrusted/old",
                    "SLURM_JWT": "SECRET", "SLURM_SACK_KEY": "SECRET", "SLURM_SACK_JWKS": "SECRET",
                    "MUNGE_SOCKET": "/wrong", "SLURM_CONFIG_FETCH": "1", "TEST_ENV_SECRET": "SECRET"}, clear=True):
            env = M.capability_environment(7)
        self.assertEqual(env, {"HOME": "/home/dar579", "PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "SLURM_CONF": "/proc/self/fd/7"})

    def test_environment_rejects_loader(self):
        with patch.dict(os.environ, {"LD_LIBRARY_PATH": "/tmp"}, clear=True), self.assertRaises(ValueError): M.capability_environment(7)

    def test_environment_rejects_overrides(self):
        for key in ("SLURM_CONF_SERVER", "SLURM_CONFIG", "LD_PRELOAD", "PYTHONHOME"):
            with self.subTest(key=key), patch.dict(os.environ, {key: "bad"}, clear=True), self.assertRaises(ValueError): M.capability_environment(7)

    def test_query_allowlist(self):
        for role in ("version", "configuration", "partition", "associations"):
            argv = M.query_spec(role)
            self.assertIn(Path(argv[0]).name, ("scontrol", "sacctmgr"))
            self.assertFalse(any(word in argv for word in ("sbatch", "srun", "write", "update", "delete")))
        self.assertIn("user=dar579", M.query_spec("associations"))

    def test_query_injection_denied_before_activity(self):
        with patch.object(M, "SealedConfiguration", side_effect=AssertionError("FD created")), patch.object(M.subprocess, "Popen", side_effect=AssertionError("spawned")):
            for role in ("write config", "submit", "version; sbatch", "show job 21756110", "", "associations user=root"):
                with self.subTest(role=role), self.assertRaises(ValueError):
                    M.query_candidate(role, DATA, lambda: None, self.folder / "log", [])

    def test_replay_closed_before_every_action(self):
        self.assertEqual(M.REVIEWED_NATIVE_CLOSURES, {})
        with patch.object(M, "require_login", side_effect=AssertionError("login probe")), patch.object(M.subprocess, "Popen", side_effect=AssertionError("spawned")):
            for profile in ("21756110", "approved", "true", M.CONFIG_SHA):
                with self.subTest(profile=profile), self.assertRaises(RuntimeError): M.replay(profile)

    def test_boolean_approval_cannot_open_replay(self):
        with patch.dict(M.REVIEWED_NATIVE_CLOSURES, {"fake": {"dependency_closure_verified": True}}), self.assertRaises(ValueError): M.replay("fake")

    def test_login_guard_wrong_machine(self):
        with patch.object(M.os, "uname", return_value=SimpleNamespace(sysname="Linux", machine="aarch64")), self.assertRaises(RuntimeError): M.require_login()

    def test_login_guard_allocation(self):
        with patch.object(M.os, "uname", return_value=SimpleNamespace(sysname="Linux", machine="x86_64")), patch.object(M.os, "getuid", return_value=3213387), patch.object(M.socket, "gethostname", return_value="torch-login-a-0"), patch.dict(os.environ, {"SLURM_JOB_ID": "21756110"}), self.assertRaises(RuntimeError): M.require_login()

    def test_trust_rejects_relative_and_privileged(self):
        with self.assertRaises(ValueError): M.trusted_path("relative")
        with patch.object(M.os, "getuid", return_value=0), self.assertRaises(ValueError): M.trusted_path("/usr/bin/true")
        with patch.object(M.os, "getuid", return_value=1001), self.assertRaises(ValueError): M.trusted_path("/usr/bin/true")

    def fake_chain(self, changes=None, links=None):
        changes, links = changes or {}, links or {}
        def lstat(path):
            name = str(path)
            mode = stat.S_IFDIR | 0o755
            uid, gid = (1001, 1001) if name == "/opt/slurm" else (0, 0)
            if name.endswith(".so"): mode = stat.S_IFREG | 0o644
            if name in links: mode = stat.S_IFLNK | 0o777
            fields = dict(st_mode=mode, st_uid=uid, st_gid=gid, st_dev=1, st_ino=sum(map(ord, name)), st_nlink=1,
                          st_size=4, st_mtime_ns=1, st_ctime_ns=1)
            fields.update(changes.get(name, {}))
            return SimpleNamespace(**fields)
        return (patch.object(Path, "lstat", lstat), patch.object(M.os, "getuid", return_value=3213387),
                patch.object(M.os, "access", return_value=False), patch.object(M.os, "readlink", lambda p: links[str(p)]))

    def trust(self, path, changes=None, links=None):
        a, b, c, d = self.fake_chain(changes, links)
        with a, b, c, d: return M.trusted_path(path)

    def test_trust_frozen_prefix_root_leaf(self):
        path, rows = self.trust("/opt/slurm/lib64/slurm/auth_munge.so")
        self.assertEqual(str(path), "/opt/slurm/lib64/slurm/auth_munge.so")
        self.assertIn("/opt/slurm", [r["path"] for r in rows])

    def test_trust_nonroot_leaf_denied(self):
        with self.assertRaises(ValueError): self.trust("/opt/slurm/lib64/libx.so", {"/opt/slurm/lib64/libx.so": {"st_uid": 1001}})

    def test_trust_other_nonroot_ancestor_denied(self):
        with self.assertRaises(ValueError): self.trust("/opt/slurm/lib64/libx.so", {"/opt/slurm/lib64": {"st_uid": 1001}})

    def test_trust_group_write_denied(self):
        with self.assertRaises(ValueError): self.trust("/opt/slurm/lib64/libx.so", {"/opt/slurm/lib64": {"st_mode": stat.S_IFDIR | 0o775}})

    def test_trust_exact_prefix_mode_denied(self):
        with self.assertRaises(ValueError): self.trust("/opt/slurm/lib64/libx.so", {"/opt/slurm": {"st_mode": stat.S_IFDIR | 0o750}})

    def test_trust_intermediate_symlink_target_checked(self):
        with self.assertRaises(ValueError): self.trust("/opt/slurm/lib64/libx.so", {"/bad": {"st_uid": 3213387}}, {"/opt/slurm/lib64": "/bad/link", "/bad/link": "/usr/lib64"})

    def test_trust_root_symlink_canonical_and_recorded(self):
        path, rows = self.trust("/lib64/libx.so", links={"/lib64": "/usr/lib64"})
        self.assertEqual(str(path), "/usr/lib64/libx.so")
        self.assertEqual(next(r["link"] for r in rows if r["path"] == "/lib64"), "/usr/lib64")

    def test_inspector_budget_before_read(self):
        scanner = M.Inspector(); scanner.bytes = M.TOTAL_READ_CAP
        p = self.folder / "library"; p.write_bytes(elf())
        with patch.object(M, "trusted_path", return_value=(p, [])), patch.object(M, "installed", side_effect=AssertionError("overbudget read")), self.assertRaises(ValueError): scanner.add(p)

    def test_inspector_object_bound(self):
        scanner = M.Inspector(); scanner.objects = {str(i): {} for i in range(M.OBJECT_CAP)}
        p = self.folder / "library"; p.write_bytes(elf())
        with patch.object(M, "trusted_path", return_value=(p, [])), patch.object(M, "installed", side_effect=AssertionError("overbudget read")), self.assertRaises(ValueError): scanner.add(p)

    def test_inspector_deadline(self):
        scanner = M.Inspector(); scanner.deadline = 0
        with self.assertRaises(TimeoutError): scanner.tick()

    def test_inspector_never_claims_closure(self):
        result = M.Inspector().evidence()
        self.assertFalse(result["dependency_closure_verified"])
        self.assertFalse(result["configuration_admitted"])
        self.assertFalse(result["native_qualification"])

    def test_native_reply_controller_change(self):
        good = "\n".join(k + " = " + v for k, v in M.ANCHOR.items())
        self.assertEqual(M.stable_configuration(good), M.ANCHOR)
        with self.assertRaises(ValueError): M.stable_configuration(good.replace("torch", "foreign"))

    def test_native_reply_duplicate_anchor(self):
        good = "\n".join(k + " = " + v for k, v in M.ANCHOR.items())
        with self.assertRaises(ValueError): M.stable_configuration(good + "\nAuthType = auth/munge")

    def test_native_reply_version_change(self):
        M.check_reply("version", "slurm 25.05.4\n")
        with self.assertRaises(ValueError): M.check_reply("version", "slurm 25.05.3\n")

    def test_native_reply_foreign_associations(self):
        M.check_reply("associations", "torch|dar579|torch_pr_288_courant||normal|normal\n")
        with self.assertRaises(ValueError): M.check_reply("associations", "torch|root|torch_pr_288_courant||normal|normal\n")
        with self.assertRaises(ValueError): M.check_reply("associations", "torch|dar579|users||normal|normal\n")

    def test_native_reply_partition_change(self):
        M.check_reply("partition", "PartitionName=cs State=UP\n")
        with self.assertRaises(ValueError): M.check_reply("partition", "PartitionName=gpu State=UP\n")

    def test_process_combined_output(self):
        text, rows = self.process("import os\nos.write(1,b'out\\n');os.write(2,b'err\\n')\n")
        self.assertEqual(text, "out\nerr\n"); self.assertEqual(rows[0]["status"], "pass")

    def test_process_nonzero_retains_output(self):
        with self.assertRaises(RuntimeError): self.process("import sys\nprint('retained failure');sys.exit(7)\n")
        self.assertEqual((self.folder / "raw.log").read_text(), "retained failure\n")

    def test_process_output_exact_boundary(self):
        text, rows = self.process("import os\nos.write(1,b'X'*65536)\n")
        self.assertEqual(len(text), 65536); self.assertFalse(rows[0]["output_incomplete"])

    def test_process_overflow_retains_prefix(self):
        with self.assertRaises(ValueError): self.process("import os\nos.write(1,b'X'*70000)\n")
        self.assertEqual((self.folder / "raw.log").stat().st_size, 65536)

    def test_process_deadline(self):
        started = time.monotonic()
        with self.assertRaises(TimeoutError): self.process("import time\nprint('before wait',flush=True);time.sleep(30)\n", timeout=0.2)
        self.assertLess(time.monotonic() - started, 2)
        self.assertEqual((self.folder / "raw.log").read_text(), "before wait\n")

    def test_process_descendant_pipe_cleanup(self):
        pidfile = self.folder / "pid"
        body = "import subprocess,sys\nfrom pathlib import Path\np=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])\nPath(" + repr(str(pidfile)) + ").write_text(str(p.pid))\nprint('descendant',flush=True)\n"
        with self.assertRaises(TimeoutError): self.process(body, timeout=0.3)
        pid = int(pidfile.read_text())
        # A killed orphan may remain a zombie briefly on Linux; it cannot execute.
        self.assertTrue(not_alive(pid))

    def test_process_invalid_utf8(self):
        with self.assertRaises(UnicodeDecodeError): self.process("import os\nos.write(1,b'\\xff')\n")

    def test_process_binary_output(self):
        with self.assertRaises(ValueError): self.process("import os\nos.write(1,b'bad\\0')\n")

    def test_process_no_limit_increase(self):
        with self.assertRaises(ValueError): self.process("pass\n", timeout=11)
        with self.assertRaises(ValueError): self.process("pass\n", maximum=65537)

    def test_process_failure_to_spawn(self):
        with patch.object(M.subprocess, "Popen", side_effect=OSError("fixture failed")), self.assertRaises(OSError): self.process("pass\n")

    def test_sealing_refuses_non_linux(self):
        with patch.object(M.sys, "platform", "darwin"), self.assertRaises(RuntimeError):
            with M.SealedConfiguration(DATA): pass

    def test_evidence_write_bound(self):
        with self.assertRaises(ValueError): M.save(self.folder / "too-large.json", "X" * M.FILE_CAP)

    def test_outer_deadline_interrupts_blocked_operation_and_restores(self):
        handler = signal.getsignal(signal.SIGALRM)
        started = time.monotonic()
        with self.assertRaises(TimeoutError):
            with M.hard_deadline(0.1): time.sleep(30)
        self.assertLess(time.monotonic() - started, 1)
        self.assertEqual(signal.getsignal(signal.SIGALRM), handler)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))

    def test_outer_deadline_does_not_replace_existing_timer(self):
        signal.setitimer(signal.ITIMER_REAL, 10)
        handler = signal.getsignal(signal.SIGALRM)
        try:
            with self.assertRaises(RuntimeError):
                with M.hard_deadline(): pass
            self.assertGreater(signal.getitimer(signal.ITIMER_REAL)[0], 9)
            self.assertEqual(signal.getsignal(signal.SIGALRM), handler)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)

    def test_outer_deadline_cannot_increase(self):
        with self.assertRaises(ValueError):
            with M.hard_deadline(121): pass

    def test_inspector_cycle_and_missing_edge_are_only_candidates(self):
        scanner = M.Inspector()
        a, b = self.folder / "liba.so", self.folder / "libb.so"
        a.write_bytes(elf(("libb.so", "missing.so"), interpreter=False)); b.write_bytes(elf(("liba.so",), interpreter=False))
        def trusted(path): return Path(path), []
        def installed(path, cap):
            data = Path(path).read_bytes()
            self.assertLessEqual(len(data), cap)
            return data, {"path": str(path), "resolved": str(path), "sha256": M.sha(data), "bytes": len(data)}
        with patch.object(M, "ROOTS", (self.folder,)), patch.object(M, "trusted_path", trusted), patch.object(M, "installed", installed):
            scanner.add(a)
        self.assertEqual(len(scanner.objects), 2)
        missing = next(e for e in scanner.edges if e["needed"] == "missing.so")
        self.assertEqual(missing["candidates"], [])
        self.assertFalse(scanner.evidence()["dependency_closure_verified"])

    def test_inspector_ambiguous_edges_never_admitted(self):
        scanner = M.Inspector()
        roots = [self.folder / "one", self.folder / "two"]
        for p in roots: p.mkdir(); (p / "libx.so").write_bytes(elf((), interpreter=False))
        a = self.folder / "client"; a.write_bytes(elf(("libx.so",), interpreter=False))
        def installed(path, cap):
            data = Path(path).read_bytes()
            self.assertLessEqual(len(data), cap)
            return data, {"path": str(path), "resolved": str(path), "sha256": M.sha(data), "bytes": len(data)}
        with patch.object(M, "ROOTS", roots), patch.object(M, "trusted_path", lambda p: (Path(p), [])), patch.object(M, "installed", installed):
            scanner.add(a)
        self.assertEqual(len(scanner.edges[0]["candidates"]), 2)
        self.assertFalse(scanner.evidence()["configuration_admitted"])

    def test_plugin_inventory_does_not_read_private_keys(self):
        scanner = M.Inspector(); added = []
        def directory(path):
            return ["auth_munge.so", "cred_munge.so", "hash_k12.so", "jwt_hs256.key", "jwks.json", "jobcomp_filetxt.so"]
        with patch.object(M, "CLIENTS", {}), patch.object(M, "ROOTS", ()), patch.object(scanner, "directory", directory), patch.object(scanner, "add", lambda p: added.append(str(p))), patch.object(Path, "exists", return_value=False), patch.object(Path, "is_symlink", return_value=False), patch.object(M, "trusted_path", return_value=(Path("/etc"), [])):
            result = scanner.collect()
        self.assertEqual({Path(p).name for p in added}, {"auth_munge.so", "cred_munge.so", "hash_k12.so"})
        self.assertFalse(result["dependency_closure_verified"])

    def test_no_slurm_execution_through_inspection(self):
        # Test the complete inspect workflow using bounded fixture observations.
        quota = {"fixture": "conservative original verification mocked"}
        with patch.object(M, "require_login"), patch.object(M, "verify_original", return_value=quota), patch.object(M, "load_capture", return_value=DATA), patch.object(M, "RESULTS", self.folder), patch.object(M.Inspector, "collect", return_value=M.Inspector().evidence()), patch.object(M.subprocess, "Popen", side_effect=AssertionError("Slurm executed")), patch.dict(os.environ, {}, clear=True):
            self.assertFalse(M.inspect())
        out = next(self.folder.glob("a3-client-config-dependencies.*"))
        result = json.loads((out / "inspection.json").read_text())
        self.assertEqual(result["status"], "metadata_captured_pending_dependency_review")
        self.assertFalse(result["configuration_admitted"])
        self.assertLess(sum(p.stat().st_size for p in out.iterdir()), M.RAW_CAP)

    def test_inspection_failure_keeps_partial_evidence(self):
        with patch.object(M, "require_login"), patch.object(M, "verify_original", return_value={}), patch.object(M, "load_capture", return_value=DATA), patch.object(M, "RESULTS", self.folder), patch.object(M.Inspector, "collect", side_effect=ValueError("fixture root metadata changed")), patch.dict(os.environ, {}, clear=True):
            self.assertTrue(M.inspect())
        out = next(self.folder.glob("a3-client-config-dependencies.*"))
        result = json.loads((out / "inspection.json").read_text())
        self.assertEqual(result["status"], "held")
        self.assertEqual(result["error_type"], "ValueError")
        self.assertFalse(result["native_qualification"])

    def test_inspector_growth_race_stays_inside_remaining_read_bound(self):
        p = self.folder / "library"; p.write_bytes(b"A")
        scanner = M.Inspector(); scanner.bytes = M.TOTAL_READ_CAP - 1
        limits = []
        def grown(path, cap):
            limits.append(cap)
            # The real bounded_file holds on fstat size > cap before reading.
            p.write_bytes(elf())
            return M.bounded_file(p, cap)
        with patch.object(M, "trusted_path", return_value=(p, [])), patch.object(M, "installed", grown), self.assertRaises(ValueError): scanner.add(p)
        self.assertEqual(limits, [1])
        self.assertEqual(scanner.bytes, M.TOTAL_READ_CAP - 1)

    def packet_fixture(self):
        package = self.folder / 'packet'; package.mkdir()
        (package / 'PLAN.json').write_bytes(b'{}')
        (package / 'site_control.py').write_bytes(b'raise RuntimeError("must not execute")\n')
        files = {p.name: M.sha(p.read_bytes()) for p in package.iterdir()}
        raw = json.dumps({'files': files}).encode()
        (package / 'manifest.json').write_bytes(raw)
        return package, raw

    def test_preimport_positive_boundary_never_executes_packet(self):
        p, raw = self.packet_fixture()
        with patch.object(M, 'PACKAGE_MANIFEST_SHA', M.sha(raw)), patch.object(M, 'PLAN_SHA', M.sha(b'{}')):
            M.verify_import_boundary(p)

    def test_preimport_manifest_tamper(self):
        p, raw = self.packet_fixture()
        with self.assertRaises(ValueError): M.verify_import_boundary(p)

    def test_preimport_source_tamper(self):
        p, raw = self.packet_fixture(); (p / 'site_control.py').write_text('raise RuntimeError("modified")\n')
        with patch.object(M, 'PACKAGE_MANIFEST_SHA', M.sha(raw)), patch.object(M, 'PLAN_SHA', M.sha(b'{}')), self.assertRaises(ValueError): M.verify_import_boundary(p)

    def test_preimport_added_module_or_link(self):
        p, raw = self.packet_fixture(); extra = p / 'ni_site.so'; extra.write_bytes(b'shadow module')
        with patch.object(M, 'PACKAGE_MANIFEST_SHA', M.sha(raw)), self.assertRaises(ValueError): M.verify_import_boundary(p)
        extra.unlink(); (p / 'linked').symlink_to(p, target_is_directory=True)
        with patch.object(M, 'PACKAGE_MANIFEST_SHA', M.sha(raw)), self.assertRaises(ValueError): M.verify_import_boundary(p)

    def test_preimport_failure_precedes_old_module_import(self):
        with patch.object(M, 'verify_import_boundary', side_effect=ValueError('before import')), self.assertRaisesRegex(ValueError, 'before import'):
            M.verify_original()


def not_alive(pid):
    for _ in range(40):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        proc = Path(f"/proc/{pid}/stat")
        if proc.exists() and proc.read_text().split(")", 1)[1].split()[0] == "Z":
            return True
        time.sleep(0.01)
    return False
