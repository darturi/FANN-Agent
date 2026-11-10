"""Pin the four completed campaigns without modifying any source files."""
import json
from pathlib import Path

from preservation import capture, digest as file_digest


def check(root, patch):
    pins = json.loads((patch / 'protected-campaigns.json').read_text())
    result = {}
    for name, pin in pins.items():
        campaign = root / name
        actual = capture(campaign)
        for relative, digest in pin['files'].items():
            if actual.get(relative) != digest:
                raise ValueError('Completed campaign differs: ' + name + '/' + relative)
        for block in range(3):
            folder = campaign / 'blocks' / ('block-' + str(block))
            status = json.loads((folder / 'status.json').read_text())
            exit_record = json.loads((folder / 'job-exit.json').read_text())
            if status['status'] != 'complete' or status['provider_calls'] != 0 or exit_record['exit_code'] != 0:
                raise ValueError('Protected campaign did not finish successfully')
        result[name] = actual
        if 'archive_sha256' in pin:
            archive = root / (name + '.tar.gz')
            if archive.is_symlink() or not archive.is_file() or file_digest(archive) != pin['archive_sha256']:
                raise ValueError('Completed campaign archive differs: ' + name)
    return result


if __name__ == '__main__':
    import sys
    try:
        result = check(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
        print(json.dumps({'protected_campaigns': len(result), 'protected_files': sum(len(x) for x in result.values())}))
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit('Completed-run verification failed: ' + str(error))
