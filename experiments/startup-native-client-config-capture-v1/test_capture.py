"""Local capture verification. Every Slurm identity/RPC is a fixture."""
import contextlib, hashlib, importlib.util, io, json, os, resource, signal, socket, subprocess, sys, textwrap, time, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import capture as M

ROOT = Path('/Users/danielarturi/Developer/JinyangLiWork')
PACKET = ROOT / 'trials/torch-reviews-startup-native-site-compatibility-v1/torch-startup-native-integrated-qualification-v1'
sys.path.insert(0, str(PACKET / 'readiness'))
import site_control as S
REAL_POPEN = subprocess.Popen
REAL_LIMIT = resource.setrlimit
REAL_GET_LIMIT = resource.getrlimit

FIXTURE = r'''
import os, signal, subprocess, sys, time
from pathlib import Path
mode = MODE
args = sys.argv[1:]
base = Path(__file__).parent
assert args[0] == '--local'
assert 'TEST_ENV_SECRET' not in os.environ
if args[1:] == ['--version']:
    print('slurm 25.05.3' if mode == 'version' else 'slurm 25.05.4')
elif args[1:] == ['show', 'config']:
    text = 'AuthType = auth/munge\nClusterName = torch\nSlurmctldHost[0] = slurm-controller-0\nSlurmctldPort = 6817\nUnused = PRIVATE_FIXTURE_VALUE\n'
    marker = base / 'export-path'
    if mode == 'endpoint' or (mode == 'post-endpoint' and marker.exists()):
        text = text.replace('slurm-controller-0', 'foreign-controller')
    if mode == 'auth': text = text.replace('auth/munge', 'auth/none')
    if mode == 'post-change' and marker.exists():
        with Path(marker.read_text()).open('ab') as f: f.write(b'# changed\n')
    print(text, end='')
elif len(args) == 4 and args[1:3] == ['write', 'config']:
    target = Path(args[3] + '.2026-11-03T12:00:00')
    assert target.parent.is_dir() and target.parent.name == 'export'
    assert target.parent.parent.name.startswith('a3-client-config-capture.')
    (base / 'export-path').write_text(str(target))
    if mode == 'permission':
        print('permission denied', file=sys.stderr); sys.exit(1)
    if mode == 'zero-no-file':
        print('Could not create configuration', file=sys.stderr); sys.exit(0)
    if mode == 'timeout':
        print('partial before timeout', flush=True); time.sleep(30)
    if mode == 'descendant':
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        (base / 'child-pid').write_text(str(child.pid))
        print('owned child holding pipe', flush=True); sys.exit(0)
    if mode == 'noisy':
        os.write(1, b'X' * 70000); sys.exit(0)
    if mode == 'directory':
        target.mkdir(); sys.exit(0)
    if mode == 'symlink':
        target.symlink_to(base / 'fixture.py'); sys.exit(0)
    data = b'# captured fixture\nClusterName=torch\nNodeName=cs624\nPartitionName=cs Nodes=cs624\n'
    if mode == 'empty': data = b''
    if mode == 'binary': data += b'\0'
    if mode == 'utf8': data += b'\xff'
    if mode == 'truncated-line': data = data.rstrip(b'\n')
    if mode == 'size-cap': data = b'A' * 1048576
    if mode == 'oversize': data = b'A' * 2097152
    with target.open('wb') as f: f.write(data)
    if mode == 'duplicate': (target.parent / 'slurm.conf.extra').write_bytes(data)
    if mode == 'hardlink': os.link(target, base / 'extra-link')
    if mode == 'mode': target.chmod(0o644)
    if mode == 'name': target.rename(target.parent / 'unexpected.conf')
    print('Slurm config saved to ' + str(target))
else:
    raise AssertionError(args)
'''

class CaptureCases(unittest.TestCase):
    def run_case(self, mode='valid', env=None, main_error=False):
        folder = Path(os.environ['A3_CAPTURE_TEST_OUT']) / self._testMethodName
        folder.mkdir(mode=0o700)
        results = folder / 'results'; results.mkdir(mode=0o700)
        prior = results / 'protected-old-state'; prior.mkdir(mode=0o700)
        old = prior / 'submission.json'; old.write_bytes(b'preserve spent dispatch evidence\n')
        before_old = M.stamp(old.stat())
        fixture = folder / 'fixture.py'
        fixture.write_text(textwrap.dedent(FIXTURE).replace('MODE', repr(mode)))
        calls, trust_calls = [], []
        plan = json.loads((PACKET / 'PLAN.json').read_text())
        def trusted(path):
            trust_calls.append(path)
            value = {'path': '/opt/slurm/bin/scontrol', 'sha256': M.CLIENT_SHA, 'inode': 1}
            if mode == 'client-sha': value['sha256'] = '0' * 64
            if mode == 'client-change' and len(trust_calls) >= 3: value['inode'] = 2
            return value
        def popen(argv, **kwargs):
            calls.append(argv)
            self.assertEqual(argv[0:2], ['/opt/slurm/bin/scontrol', '--local'])
            allowed = argv[2:] in [['--version'], ['show', 'config']] or (len(argv) == 5 and argv[2:4] == ['write', 'config'])
            self.assertTrue(allowed)
            def file_limit():
                _, hard = REAL_GET_LIMIT(resource.RLIMIT_FSIZE)
                REAL_LIMIT(resource.RLIMIT_FSIZE, (M.FILE_CAP, hard))
            kwargs['preexec_fn'] = file_limit
            return REAL_POPEN([sys.executable, '-B', str(fixture), *argv[1:]], **kwargs)
        selected_env = {k: v for k, v in os.environ.items() if k not in
                        ('SLURM_JOB_ID', 'SLURM_JOBID', 'SLURM_STEP_ID', 'SLURM_CONF', 'SLURM_CONF_SERVER', 'SLURM_CONFIG', 'LD_PRELOAD', 'PYTHONHOME', 'LD_LIBRARY_PATH')}
        selected_env.update(TORCH_RESULTS_ROOT=str(results), TEST_ENV_SECRET='not-for-child')
        selected_env.update(env or {})
        output = io.StringIO()
        prior_umask = os.umask(0o077)
        try:
            with contextlib.ExitStack() as stack:
                for owner, name, value in [(M, 'PACKAGE', PACKET), (M, 'BASE', results),
                        (M, 'EXPECTED_UID', os.getuid()), (M.os, 'uname', lambda: SimpleNamespace(sysname='Linux', machine='x86_64')),
                        (M.socket, 'gethostname', lambda: 'torch-login.fixture'),
                        (S.C, 'verify', lambda p: plan), (S.C, 'quota', lambda p: {'fixture': 'original quota check mocked'}),
                        (S.T, 'trusted_binary', trusted), (M.subprocess, 'Popen', popen),
                        (M.resource, 'setrlimit', lambda *args: None)]:
                    stack.enter_context(patch.object(owner, name, value))
                stack.enter_context(patch.dict(os.environ, selected_env, clear=True))
                stack.enter_context(contextlib.redirect_stdout(output))
                if mode == 'plan': stack.enter_context(patch.object(S, 'sha', lambda p: 'wrong'))
                if mode == 'quota': stack.enter_context(patch.object(S.C, 'quota', side_effect=RuntimeError('Quota held')))
                if main_error:
                    with self.assertRaises((ValueError, RuntimeError)): M.main()
                    return calls, None, output.getvalue()
                code = M.main()
        finally:
            os.umask(prior_umask)
        self.assertEqual(old.read_bytes(), b'preserve spent dispatch evidence\n')
        self.assertEqual(M.stamp(old.stat()), before_old)
        dirs = [p for p in results.iterdir() if p.name != 'protected-old-state']; self.assertEqual(len(dirs), 1)
        out = dirs[0]; receipt = json.loads((out / 'receipt.json').read_text())
        self.assertNotIn('PRIVATE_FIXTURE_VALUE', output.getvalue())
        self.assertFalse(receipt['configuration_admitted']); self.assertFalse(receipt['native_qualification'])
        self.assertEqual(receipt['new_allocations'], 0); self.assertEqual(receipt['ANN_searches'], 0); self.assertEqual(receipt['exact_searches'], 0)
        self.assertFalse(receipt['retry'])
        files = [p for p in out.rglob('*') if p.is_file() and not p.is_symlink()]
        self.assertLessEqual(len(files), 16)
        self.assertLessEqual(sum(p.stat().st_size for p in files), 2 * M.FILE_CAP)
        exports = [a for a in calls if a[2:4] == ['write', 'config']]
        self.assertLessEqual(len(exports), 1)
        if mode == 'valid':
            self.assertEqual(code, 0); self.assertEqual(len(calls), 5)
            data = Path(receipt['configuration']).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), receipt['sha256'])
            manifest = json.loads((out / 'manifest.json').read_text())
            for name, row in manifest.items():
                b = (out / name).read_bytes(); self.assertEqual(len(b), row['bytes']); self.assertEqual(hashlib.sha256(b).hexdigest(), row['sha256'])
        else:
            self.assertEqual(code, 1); self.assertEqual(receipt['status'], 'held')
        return calls, out, output.getvalue()

    def test_valid_capture_hashes_and_private_logs(self): self.run_case()
    def test_actual_packet_and_exact_reference_verify(self):
        plan = S.C.verify(PACKET)
        self.assertEqual(S.sha(PACKET / 'PLAN.json'), M.PLAN_SHA)
        self.assertEqual(plan['limits']['physical_cpus'], 4)
        self.assertEqual(plan['limits']['memory_gib'], 32)
    def test_changed_plan_no_queries(self): self.assertEqual(self.run_case('plan')[0], [])
    def test_quota_failure_no_queries(self): self.assertEqual(self.run_case('quota')[0], [])
    def test_foreign_client_no_queries(self): self.assertEqual(self.run_case('client-sha')[0], [])
    def test_client_generation_race_holds_before_export(self): self.assertEqual(len(self.run_case('client-change')[0]), 1)
    def test_wrong_version_holds_before_export(self): self.assertEqual(len(self.run_case('version')[0]), 2)
    def test_wrong_endpoint_holds_before_export(self): self.assertEqual(len(self.run_case('endpoint')[0]), 2)
    def test_wrong_authentication_holds_before_export(self): self.assertEqual(len(self.run_case('auth')[0]), 2)
    def test_post_endpoint_change_holds(self): self.run_case('post-endpoint')
    def test_post_export_mutation_holds(self): self.run_case('post-change')
    def test_permission_failure_retains_error_log(self):
        _, out, _ = self.run_case('permission'); self.assertIn(b'permission denied', (out / 'query-2.log').read_bytes())
    def test_writer_zero_exit_without_file_holds(self): self.run_case('zero-no-file')
    def test_duplicate_export_holds(self): self.run_case('duplicate')
    def test_symlink_export_holds(self): self.run_case('symlink')
    def test_hardlink_export_holds(self): self.run_case('hardlink')
    def test_wrong_file_mode_holds(self): self.run_case('mode')
    def test_directory_export_holds(self): self.run_case('directory')
    def test_empty_export_holds(self): self.run_case('empty')
    def test_binary_export_holds(self): self.run_case('binary')
    def test_non_utf8_export_holds(self): self.run_case('utf8')
    def test_incomplete_final_line_holds(self): self.run_case('truncated-line')
    def test_unexpected_export_name_holds(self): self.run_case('name')
    def test_exact_file_cap_is_held_as_possible_truncation(self): self.run_case('size-cap')
    def test_kernel_file_size_limit_enforced(self):
        _, out, _ = self.run_case('oversize'); files = list((out / 'export').iterdir()); self.assertLessEqual(files[0].stat().st_size, M.FILE_CAP)
    def test_output_bound_retains_prefix_and_marks_incomplete(self):
        _, out, _ = self.run_case('noisy'); events = json.loads((out / 'commands.json').read_text()); self.assertTrue(events[-1]['output_incomplete']); self.assertEqual((out / 'query-2.log').stat().st_size, M.OUTPUT_CAP)
    def test_actual_ten_second_deadline_retains_partial_log(self):
        start = time.monotonic(); _, out, _ = self.run_case('timeout'); self.assertLess(time.monotonic() - start, 12); self.assertIn(b'partial before timeout', (out / 'query-2.log').read_bytes())
    def test_owned_descendant_holding_pipe_is_killed(self):
        start = time.monotonic(); self.run_case('descendant'); self.assertLess(time.monotonic() - start, 12)
        pid = int((Path(os.environ['A3_CAPTURE_TEST_OUT']) / self._testMethodName / 'child-pid').read_text())
        try: os.kill(pid, 0)
        except ProcessLookupError: return
        # A killed orphan may briefly remain a zombie until the OS reaps it.
        observed = subprocess.run(['/bin/ps', '-o', 'stat=', '-p', str(pid)], capture_output=True, text=True).stdout.strip()
        self.assertTrue(not observed or observed.startswith('Z'), observed)
    def test_loader_override_never_reaches_client(self): self.assertEqual(self.run_case('override', {'LD_PRELOAD': '/untrusted'})[0], [])
    def test_inside_allocation_is_rejected(self): self.assertEqual(self.run_case(env={'SLURM_JOB_ID': '21756110'}, main_error=True)[0], [])
    def test_existing_spent_state_preserved(self): self.run_case()
    def test_file_changes_while_reading_are_rejected(self):
        folder = Path(os.environ['A3_CAPTURE_TEST_OUT']) / self._testMethodName; folder.mkdir()
        path = folder / 'file'; path.write_bytes(b'original\n'); path.chmod(0o600)
        real_read = os.read
        def changed(fd, n):
            data = real_read(fd, n)
            if data:
                with path.open('ab') as f: f.write(b'changed\n')
            return data
        with patch.object(M.os, 'read', changed), self.assertRaises(RuntimeError):
            M.read_private(path, 32)

if __name__ == '__main__':
    unittest.main()
