"""Extra source/retention/replay guards; no adaptive native release."""

from pathlib import Path

from adaptive_reference import static


def code_map(package):
    from pc_common import sha

    p = Path(package)
    return {
        str(f.relative_to(p)): sha(f) for f in sorted([*p.glob("*.py"), *(p / "a3").glob("*.py")])
    }


def activate_fixture(package):
    from pc_common import protocol, read

    p = Path(package)
    cfg = read(p / "experiment.json")
    if cfg["synthetic_fixture"] is not True:
        raise RuntimeError("Adaptive activation is an offline synthetic fixture only")
    cfg.update(protocol("adaptive"))
    cfg["adaptive_code_sha256"] = code_map(p)
    (p / "experiment.json").write_text(__import__("json").dumps(cfg, sort_keys=True) + "\n")
    from experiment import reseal

    reseal(p)


def verify(package, cfg):
    from pc_common import HERE

    p = Path(package)
    static(p)
    if cfg["adaptive_code_sha256"] != code_map(p) or code_map(p) != code_map(HERE):
        raise ValueError("Adaptive startup source/guard map differs")


def replay(campaign, package):
    from pc_common import read, sha

    p, run = Path(package), Path(campaign) / "run"
    cfg = read(p / "experiment.json")
    verify(p, cfg)
    pre = read(run / "ev-runtime-preflight.json")
    if (
        pre["startup_codec"] != "adaptive"
        or pre["adaptive_code_sha256"] != code_map(p)
        or pre["adaptive_target_reference_sha256"] != sha(p / "TARGET-REFERENCE.json")
        or pre["adaptive_origins"]
        != {
            "exact_codec": "/patch/exact_codec.py",
            "adaptive_integration": "/patch/adaptive_integration.py",
            "adaptive_reference": "/patch/adaptive_reference.py",
        }
        or pre["native_correction_qualified"] is not False
    ):
        raise ValueError("Adaptive source/origin/target proof differs")
    literal = read(run / "adaptive-preflight.json")
    integer_fields = (
        "cases",
        "compact_cases",
        "raw64_cases",
        "original_numeric_bytes",
        "ANN_searches",
        "exact_searches",
        "real_SQL",
    )
    if (
        any(type(literal[k]) is not int or literal[k] < 0 for k in integer_fields)
        or literal["original_numeric_bytes"] != 8 * 768 * 8
        or type(literal["cpu_seconds"]) not in (int, float)
    ):
        raise ValueError("Adaptive literal count/type/byte proof differs")
    if (
        literal["status"] != "pass"
        or type(literal["cases"]) is not int
        or literal["cases"] != 8
        or literal["compact_cases"] + literal["raw64_cases"] != 8
        or not 0 <= literal["cpu_seconds"] <= 1
        or literal["codec_sha256"] != sha(p / "exact_codec.py")
        or literal["helper_sha256"] != sha(p / "adaptive_reference.py")
        or literal["target_reference_sha256"] != sha(p / "TARGET-REFERENCE.json")
        or literal["ANN_searches"] != 0
        or literal["exact_searches"] != 0
        or literal["real_SQL"] != 0
    ):
        raise ValueError("Adaptive pre-restore literal proof differs")
    retained = read(run / "ev-retention.json")
    for record in retained["records"]:
        extra = record["adaptive"]
        keys = {"compact", "raw64", "payload_bytes", "matrix_bytes"}
        if set(extra) != keys or any(type(extra[k]) is not int or extra[k] < 0 for k in keys):
            raise ValueError("Adaptive retention counts/types differ")
        if (
            extra["compact"] + extra["raw64"] != record["rows"]
            or extra["payload_bytes"] != extra["compact"] * 3072 + extra["raw64"] * 6144
            or extra["matrix_bytes"] != record["rows"] * 768 * 4
        ):
            raise ValueError("Adaptive payload/matrix lifetime proof differs")
    stream = read(run / "identity-stream.json")
    if stream["adaptive_code_sha256"] != code_map(p) or stream["startup_codec"] != "adaptive":
        raise ValueError("Adaptive identity delegation source differs")
    return dict(
        status="pass",
        scope="offline adaptive startup reconstruction only",
        native_correction_qualified=False,
        native_memory_qualified=False,
    )
