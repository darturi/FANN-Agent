"""Login-only bounded configuration capture; never admits or launches work."""
import hashlib, json, os, re, resource, selectors, signal, socket, stat, subprocess, sys, tempfile, time
from itertools import islice
from pathlib import Path

PACKAGE = Path('/scratch/dar579/torch-reviews/a3-site-compatibility-packages-619d4288ca7a/torch-startup-native-integrated-qualification-v1')
BASE = Path('/home/dar579/torch-reviews-results')
PLAN_SHA = '08a9293c3c4e4386118be6a354476efe27ec61749c421bf85136c426585526b0'
CLIENT_SHA = 'ed806e144b8de806ee88e5fc066e0aed6c42ab281abf457315fca3e9af82b238'
EXPECTED_UID = 3213387
ANCHOR = {'AuthType': 'auth/munge', 'ClusterName': 'torch', 'SlurmctldHost[0]': 'slurm-controller-0', 'SlurmctldPort': '6817'}
FILE_CAP, OUTPUT_CAP = 1048576, 65536

def stamp(s):
    return (s.st_dev, s.st_ino, s.st_mode, s.st_uid, s.st_gid, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns)

def read_private(path, cap):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid() or
                stat.S_IMODE(before.st_mode) != 0o600 or before.st_nlink != 1 or before.st_size > cap):
            raise ValueError('Private bounded single-link regular file required')
        data = bytearray()
        while len(data) <= cap:
            block = os.read(fd, min(65536, cap + 1 - len(data)))
            if not block:
                break
            data.extend(block)
        if len(data) > cap or stamp(before) != stamp(os.fstat(fd)) or stamp(before) != stamp(path.lstat()):
            raise RuntimeError('Capture file changed or exceeded its bound')
        return bytes(data), stamp(before)
    finally:
        os.close(fd)

def save(path, value):
    data = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
    if len(data) > OUTPUT_CAP:
        raise ValueError('Capture metadata bound')
    with path.open('xb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())

def query(S, binary, args, out, events):
    row = {'argv': [binary['path'], '--local', *args], 'log': f'query-{len(events)}.log', 'output_incomplete': False}
    events.append(row)
    started = time.monotonic()
    process, reaped = None, False
    selector = selectors.DefaultSelector()
    try:
        if S.T.trusted_binary(binary['path']) != binary:
            raise RuntimeError('Scheduler client generation changed')
        env = S.T.clean_environment()
        with (out / row['log']).open('xb', buffering=0) as log:
            process = subprocess.Popen(row['argv'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       env=env, start_new_session=True)
            end = started + 10
            selector.register(process.stdout, selectors.EVENT_READ)
            os.set_blocking(process.stdout.fileno(), False)
            data = bytearray()
            while selector.get_map():
                if time.monotonic() >= end:
                    row['output_incomplete'] = True
                    raise TimeoutError('Ten-second scheduler command deadline')
                for key, _ in selector.select(min(0.05, max(0, end - time.monotonic()))):
                    block = os.read(key.fd, min(8192, OUTPUT_CAP + 1 - len(data)))
                    if not block:
                        selector.unregister(key.fileobj)
                        continue
                    keep = block[:OUTPUT_CAP - len(data)]
                    log.write(keep)
                    data.extend(keep)
                    if len(keep) != len(block):
                        row.update(output_incomplete=True, overflow_byte_hex=block[len(keep):].hex())
                        raise ValueError('Scheduler output bound; prefix retained')
            code = process.wait(timeout=max(0.001, end - time.monotonic()))
            reaped = True
            row['exit_code'] = code
            os.fsync(log.fileno())
        if S.T.trusted_binary(binary['path']) != binary:
            raise RuntimeError('Scheduler client changed during command')
        if code:
            raise RuntimeError('Scheduler command failed; complete bounded output retained privately')
        row['status'] = 'pass'
        return bytes(data).decode('utf-8', 'strict')
    except BaseException as e:
        row.update(status='held', error_type=type(e).__name__, error=str(e))
        raise
    finally:
        if process is not None:
            if not reaped:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=1)
            process.stdout.close()
        selector.close()
        row['elapsed_seconds'] = time.monotonic() - started

def capture(S, out, events):
    plan = S.C.verify(PACKAGE)
    if (S.sha(PACKAGE / 'PLAN.json') != PLAN_SHA or
            Path(S.__file__).resolve() != PACKAGE / 'readiness/site_control.py' or
            S.sha(Path(S.__file__)) != plan['admission_control_sha256'] or
            S.sha(Path(S.T.__file__)) != plan['site_trust_sha256'] or S.T.POLICY != plan['site_trust_policy']):
        raise RuntimeError('Original packet, plan or admission policy differs')
    S.T.install()
    save(out / 'quota.json', S.C.quota(PACKAGE))
    binary = S.T.trusted_binary('/opt/slurm/bin/scontrol')
    if binary['path'] != '/opt/slurm/bin/scontrol' or binary['sha256'] != CLIENT_SHA:
        raise RuntimeError('Observed scheduler client differs')
    def probe():
        version = query(S, binary, ['--version'], out, events).strip()
        text = query(S, binary, ['show', 'config'], out, events)
        if version != 'slurm 25.05.4' or S.stable_configuration(text) != ANCHOR:
            raise RuntimeError('Authenticated controller/version/cluster differs')
    probe()
    export = out / 'export'
    export.mkdir(mode=0o700)
    query(S, binary, ['write', 'config', str(export / 'slurm.conf')], out, events)
    entries = list(islice(export.iterdir(), 17))
    if len(entries) != 1 or not re.fullmatch(r'slurm\.conf\.\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d', entries[0].name):
        raise ValueError('Exactly one timestamp-suffixed export required; no retry')
    path = entries[0]
    data, generation = read_private(path, FILE_CAP)
    if not data or len(data) >= FILE_CAP or b'\x00' in data or not data.endswith(b'\n'):
        raise ValueError('Empty, binary or possibly size-limited export; preserve for review')
    data.decode('utf-8', 'strict')
    digest = hashlib.sha256(data).hexdigest()
    probe()
    again, after = read_private(path, FILE_CAP)
    if generation != after or hashlib.sha256(again).hexdigest() != digest:
        raise RuntimeError('Export changed during post-check')
    return {'status': 'captured_pending_configuration_review', 'configuration': str(path),
            'sha256': digest, 'bytes': len(data), 'client': binary,
            'anchor': ANCHOR, 'configuration_admitted': False, 'native_qualification': False,
            'syntax_verified': False, 'dependency_closure_verified': False}

def main():
    os.umask(0o077)
    host = socket.gethostname()
    u = os.uname()
    if (u.sysname != 'Linux' or u.machine != 'x86_64' or os.getuid() != EXPECTED_UID or
            not re.fullmatch(r'torch-login(?:-[a-z]-[0-9]+)?', host.split('.')[0]) or
            any(os.environ.get(k) for k in ('SLURM_JOB_ID', 'SLURM_JOBID', 'SLURM_STEP_ID'))):
        raise RuntimeError('Run only as dar579 on the Torch x86 login node, outside any allocation')
    if os.environ.get('TORCH_RESULTS_ROOT') != str(BASE) or BASE.resolve(strict=True) != BASE:
        raise ValueError('Original owned results root required')
    s = BASE.lstat()
    if not stat.S_ISDIR(s.st_mode) or s.st_uid != os.getuid() or s.st_mode & 0o022:
        raise ValueError('Owned non-writable-by-others results directory required')
    soft, hard = resource.getrlimit(resource.RLIMIT_FSIZE)
    if soft != resource.RLIM_INFINITY and soft < FILE_CAP:
        raise ValueError('Existing file-size limit is below the capture ceiling; no limits raised')
    out = Path(tempfile.mkdtemp(prefix='a3-client-config-capture.', dir=BASE))
    print(json.dumps({'capture_directory': str(out), 'phase': 'preflight', 'new_allocations': 0}), flush=True)
    resource.setrlimit(resource.RLIMIT_FSIZE, (FILE_CAP, hard))
    events, result = [], {'status': 'held', 'configuration_admitted': False, 'native_qualification': False}
    try:
        sys.path.insert(0, str(PACKAGE / 'readiness'))
        import site_control as S
        result = capture(S, out, events)
    except BaseException as e:
        result.update(status='held', error_type=type(e).__name__, error=str(e))
    finally:
        result.update(capture_directory=str(out), host=host, new_allocations=0,
                      ANN_searches=0, exact_searches=0, retry=False)
        save(out / 'commands.json', events)
        try:
            files = [p for p in islice(out.iterdir(), 17) if p.name != 'export']
            if (out / 'export').exists():
                files.extend(islice((out / 'export').iterdir(), 17))
            if len(files) + 2 > 16:
                raise ValueError('Capture file-count bound')
            manifest = {}
            for path in files:
                data, _ = read_private(path, FILE_CAP)
                manifest[str(path.relative_to(out))] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            if sum(x['bytes'] for x in manifest.values()) + 2 * OUTPUT_CAP > 2 * FILE_CAP:
                raise ValueError('Whole capture byte bound')
            save(out / 'manifest.json', manifest)
            result['manifest_sha256'] = hashlib.sha256(read_private(out / 'manifest.json', OUTPUT_CAP)[0]).hexdigest()
        except BaseException as e:
            result.update(status='held', retention_complete=False, retention_error_type=type(e).__name__, retention_error=str(e))
        save(out / 'receipt.json', result)
        print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'captured_pending_configuration_review' else 1

if __name__ == '__main__':
    raise SystemExit(main())
