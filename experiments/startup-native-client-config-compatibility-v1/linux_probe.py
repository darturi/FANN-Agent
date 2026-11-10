"""Real Linux kernel checks using fixture children, never a native Slurm client."""
import argparse
import ast
import fcntl
import hashlib
import json
import mmap
import os
from pathlib import Path
import platform
import subprocess
import sys
import unittest
from unittest.mock import patch

import compatibility as M

HERE = Path(__file__).resolve().parent
DATA = (HERE / "candidate.conf").read_bytes()
REAL_POPEN = subprocess.Popen
OUT = None

CHILD = r'''
import fcntl,hashlib,os,stat,sys
from pathlib import Path
p=os.environ['SLURM_CONF']; fd=int(p.rsplit('/',1)[1]); expected=sys.argv[1]
assert stat.S_ISREG(os.stat(p).st_mode) and os.stat(p).st_size==16647
assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==expected
seals=fcntl.F_SEAL_WRITE|fcntl.F_SEAL_GROW|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_SEAL
assert fcntl.fcntl(fd,fcntl.F_GET_SEALS)&seals==seals
assert 'SLURM_JWT' not in os.environ and 'SLURM_SACK_KEY' not in os.environ
try: os.fstat(200)
except OSError: pass
else: raise AssertionError('Unrelated FD leaked')
try:
    w=os.open(p,os.O_RDWR)
    try: os.write(w,b'X')
    finally: os.close(w)
except PermissionError: pass
else: raise AssertionError('Sealed bytes changed')
role=sys.argv[2]
if role=='version': print('slurm 25.05.4')
elif role=='configuration':
    print('AuthType = auth/munge\nClusterName = torch\nSlurmctldHost[0] = slurm-controller-0\nSlurmctldPort = 6817')
elif role=='partition': print('PartitionName=cs State=UP')
elif role=='associations': print('torch|dar579|torch_pr_288_courant||normal|normal')
else: raise AssertionError('Unknown fixture role')
'''


class KernelCases(unittest.TestCase):
    def setUp(self):
        self.folder = OUT / self._testMethodName
        self.folder.mkdir(mode=0o700)

    def test_actual_full_seals_and_pread(self):
        with M.SealedConfiguration(DATA) as s:
            s.check()
            self.assertFalse(os.get_inheritable(s.fd))
            self.assertEqual(os.pread(s.fd, len(DATA) + 1, 0), DATA)
            self.assertEqual(fcntl.fcntl(s.fd, fcntl.F_GET_SEALS) & s.seals, s.seals)

    def test_write_and_pwrite_denied(self):
        with M.SealedConfiguration(DATA) as s:
            for operation in (lambda: os.write(s.fd, b'X'), lambda: os.pwrite(s.fd, b'X', 0)):
                with self.assertRaises(PermissionError): operation()
            s.check()

    def test_grow_and_shrink_denied(self):
        with M.SealedConfiguration(DATA) as s:
            for length in (0, len(DATA) - 1, len(DATA) + 1):
                with self.assertRaises(PermissionError): os.ftruncate(s.fd, length)
            s.check()

    def test_shared_writable_mapping_denied(self):
        with M.SealedConfiguration(DATA) as s:
            with self.assertRaises(PermissionError): mmap.mmap(s.fd, len(DATA), flags=mmap.MAP_SHARED, prot=mmap.PROT_READ | mmap.PROT_WRITE)
            s.check()

    def test_seal_set_cannot_change(self):
        with M.SealedConfiguration(DATA) as s:
            with self.assertRaises(PermissionError): fcntl.fcntl(s.fd, fcntl.F_ADD_SEALS, s.seals)
            s.check()

    def test_reopened_proc_path_stable(self):
        with M.SealedConfiguration(DATA) as s:
            with open(f'/proc/self/fd/{s.fd}', 'rb') as f:
                self.assertEqual(f.read(), DATA)
            s.check()

    def test_fd_closed_after_exception(self):
        fd = None
        with self.assertRaisesRegex(RuntimeError, 'fixture exception'):
            with M.SealedConfiguration(DATA) as s:
                fd = s.fd
                raise RuntimeError('fixture exception')
        with self.assertRaises(OSError): os.fstat(fd)

    def test_sealing_failure_closes_fd(self):
        before = set(os.listdir('/proc/self/fd'))
        with patch.object(M.fcntl, 'fcntl', side_effect=OSError('fixture sealing failure')), self.assertRaises(OSError):
            with M.SealedConfiguration(DATA): pass
        self.assertEqual(set(os.listdir('/proc/self/fd')), before)

    def test_repeated_lifecycle_no_leak(self):
        before = set(os.listdir('/proc/self/fd'))
        for _ in range(64):
            with M.SealedConfiguration(DATA) as s: s.check()
        self.assertEqual(set(os.listdir('/proc/self/fd')), before)

    def fixture_queries(self, fail_post=False):
        fixture = self.folder / 'child.py'
        fixture.write_text(CHILD)
        calls, events, verified = [], [], []
        def popen(argv, **kwargs):
            self.assertIn(tuple(argv), [M.query_spec(role) for role in ('version', 'configuration', 'partition', 'associations')])
            self.assertFalse(kwargs.get('shell', False))
            self.assertEqual(len(kwargs['pass_fds']), 1)
            role = next(role for role in ('version', 'configuration', 'partition', 'associations') if tuple(argv) == M.query_spec(role))
            calls.append(role)
            return REAL_POPEN([sys.executable, '-B', str(fixture), M.CONFIG_SHA, role], **kwargs)
        def verify():
            verified.append(1)
            if fail_post and len(verified) == 2: raise RuntimeError('fixture dependency generation changed')
        fd = os.open('/dev/null', os.O_RDONLY | os.O_CLOEXEC)
        extra = fcntl.fcntl(fd, fcntl.F_DUPFD_CLOEXEC, 200)
        self.assertEqual(extra, 200)
        try:
            with patch.object(M.subprocess, 'Popen', popen), patch.dict(os.environ, {'SLURM_JWT': 'fixture-secret', 'SLURM_SACK_KEY': 'fixture-secret'}, clear=True):
                for role in ('version', 'configuration', 'partition', 'associations'):
                    M.query_candidate(role, DATA, verify, self.folder / (role + '.log'), events)
        finally:
            os.close(extra); os.close(fd)
            (self.folder / 'commands.json').write_text(json.dumps(events, indent=2))
        self.assertEqual(len(calls), 4); self.assertEqual(len(verified), 8)

    def test_real_pass_fds_only_and_all_query_roles(self):
        before = set(os.listdir('/proc/self/fd'))
        self.fixture_queries()
        self.assertEqual(set(os.listdir('/proc/self/fd')), before)

    def test_dependency_change_holds_after_child_and_closes(self):
        before = set(os.listdir('/proc/self/fd'))
        with self.assertRaisesRegex(RuntimeError, 'dependency generation changed'): self.fixture_queries(fail_post=True)
        self.assertEqual(set(os.listdir('/proc/self/fd')), before)
        rows = json.loads((self.folder / 'commands.json').read_text())
        self.assertEqual(rows[-1]['status'], 'held')
        self.assertEqual(rows[-1]['verification_error_type'], 'RuntimeError')

    def test_reply_verification_failure_holds_and_closes(self):
        before = set(os.listdir('/proc/self/fd'))
        events = []
        with patch.object(M, 'bounded_process', return_value='slurm 25.05.3\n') as runner:
            def run(*args, **kwargs):
                events.append({'status': 'pass'})
                return 'slurm 25.05.3\n'
            runner.side_effect = run
            with self.assertRaises(ValueError): M.query_candidate('version', DATA, lambda: None, self.folder / 'unused', events)
        self.assertEqual(events[-1]['status'], 'held')
        self.assertEqual(set(os.listdir('/proc/self/fd')), before)

    def test_descriptor_missing_in_nonpassed_child(self):
        with M.SealedConfiguration(DATA) as s:
            code = 'import os,sys\ntry: os.fstat(int(sys.argv[1]))\nexcept OSError: sys.exit(0)\nsys.exit(1)\n'
            result = subprocess.run([sys.executable, '-B', '-c', code, str(s.fd)], close_fds=True, timeout=2, check=False)
            self.assertEqual(result.returncode, 0)
            s.check()

    def test_relative_aux_path_is_not_original_directory(self):
        with M.SealedConfiguration(DATA) as s:
            parent = Path(f'/proc/self/fd/{s.fd}').parent
            self.assertNotEqual(str(parent), '/opt/slurm/etc')
            self.assertFalse((parent / 'gres.conf').exists())
            self.assertFalse(M.REVIEWED_NATIVE_CLOSURES)

    def test_actual_local_elf_parser_and_root_chain(self):
        raw, proof = M.installed(sys.executable)
        parsed = M.elf64(raw, machines=(62, 183))
        self.assertIn(parsed['machine'], (62, 183))
        self.assertEqual(proof['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertTrue(parsed['interpreter'])


def main():
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if sys.platform != 'linux' or os.getuid() == 0:
        raise RuntimeError('Run real Linux kernel checks as a nonroot container user')
    OUT = args.output
    OUT.mkdir(mode=0o700)
    os.umask(0o077)
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.iterdir() if p.is_file()}
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(KernelCases)
    actual = [t.id() for t in suite]
    expected = {__name__ + '.KernelCases.' + f.name for c in ast.parse(Path(__file__).read_text()).body
                if isinstance(c, ast.ClassDef) for f in c.body if isinstance(f, ast.FunctionDef) and f.name.startswith('test_')}
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.iterdir() if p.is_file()}
    good = result.wasSuccessful() and not result.skipped and set(actual) == expected and before == after
    receipt = {'status': 'pass' if good else 'failed', 'tests_run': result.testsRun, 'test_ids': actual,
               'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped),
               'kernel': platform.release(), 'machine': platform.machine(), 'python': sys.version,
               'uid': os.getuid(), 'code_sha256': before, 'source_unchanged': before == after,
               'scope': 'real local Linux kernel with fixture children; no deployed Slurm/native x86 qualification',
               'new_allocations': 0, 'ANN_searches': 0, 'exact_searches': 0, 'native_Slurm_executed': False}
    (OUT / 'verification.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return not good


if __name__ == '__main__':
    raise SystemExit(main())
