"""Preserve old campaigns; only hashes of consumed confirmation are consulted."""
from contract import read, sha
from legacy_protected import check as previous_check
from preservation import capture


def check(root, package):
    result = previous_check(root, package)
    for name, pin in read(package / 'additional-protected.json').items():
        actual = capture(root / name)
        for path, expected in pin.items():
            if actual.get(path) != expected: raise ValueError('Protected result changed: ' + name + '/' + path)
        result[name] = actual
    return result
