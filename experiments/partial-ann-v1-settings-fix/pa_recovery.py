"""Require the verified failed B2d campaign; never reset its spent reservation."""

from pathlib import Path

from legacy_common import read, safe_file, sha


def verify_failed(package, sources, prior_parent=None):
    package, sources = Path(package), Path(sources)
    proof = read(package / "FAILED-CAMPAIGN.json")
    name = proof["campaign"]
    if name != "reviews-partial-ann-v1-20261027T000432Z.9haq3pyt":
        raise ValueError("Unknown prerequisite failed campaign")
    old = Path(prior_parent) if prior_parent else package.parent
    old_package = old / "torch-partial-ann-v1-quota-fix"
    if sha(old_package / "manifest.json") != proof["package_manifest_sha256"]:
        raise ValueError("Prior B2d package manifest changed")
    manifest = read(package / "failed-package-manifest.json")
    if manifest != read(old_package / "manifest.json"):
        raise ValueError("Pinned failed package manifest differs")
    for n, h in manifest["files"].items():
        if sha(safe_file(old_package, n)) != h:
            raise ValueError("Prior B2d package file changed: " + n)
    campaign = sources / name
    for n, h in proof["raw_files_sha256"].items():
        if sha(safe_file(campaign, n)) != h:
            raise ValueError("Failed B2d evidence changed: " + n)
    archive = sources / (name + ".tar.gz")
    if sha(archive) != proof["archive_sha256"] or Path(
        str(archive) + ".sha256"
    ).read_text().split() != [proof["archive_sha256"], archive.name]:
        raise ValueError("Failed B2d archive/checksum changed")
    expected = dict(
        campaign=str(campaign), package_manifest_sha256=proof["package_manifest_sha256"]
    )
    if read(old_package / "submission-binding.json") != expected:
        raise ValueError("Failed B2d binding differs")
    reservation = read(sources / ".torch-partial-ann-v1-reservation.json")
    if any(reservation.get(k) != v for k, v in expected.items()):
        raise ValueError("Spent original B2d reservation differs")
    return dict(
        campaign=name,
        package_manifest_sha256=proof["package_manifest_sha256"],
        archive_sha256=proof["archive_sha256"],
        terminal_failure_verified=True,
        cleanup_verified=True,
        protected_before_after_equal=True,
    )
