from importlib.metadata import entry_points

from ..api import (
    Backend,
    BackendExtension,
    ExtensionManifest,
    IncompatibleExtension,
    UnsupportedTarget,
    validate_capabilities,
)


def discover():
    found = {}
    for point in entry_points(group="fannagent.backends"):
        if point.name in found:
            raise IncompatibleExtension(f"duplicate backend extension name: {point.name}")
        found[point.name] = point
    return found


def extension(name):
    point = discover().get(name)
    if point is None:
        raise UnsupportedTarget(
            f"backend extension is not installed: {name}; "
            "install a package exposing this fannagent.backends entry point"
        )
    try:
        instance = point.load()
        if not isinstance(instance, BackendExtension):
            raise IncompatibleExtension("entry point must expose an API v1 extension descriptor")
        manifest = instance.manifest()
        if not isinstance(manifest, ExtensionManifest):
            raise IncompatibleExtension("malformed extension descriptor manifest")
        manifest.validate()
        if manifest.name != name:
            raise IncompatibleExtension("entry point and manifest names differ")
        return instance
    except (IncompatibleExtension, UnsupportedTarget):
        raise
    except Exception as exc:
        raise IncompatibleExtension(f"cannot load extension {name!r}: {exc}") from exc


def create(config, store):
    from ..extension_host import context

    selected = extension(config.backend.name)
    options = selected.normalize_options(config.backend.options, config.configuration_origin)
    backend = selected.create(options, context(config, store))
    if not isinstance(backend, Backend):
        raise IncompatibleExtension("extension does not implement the base backend contract")
    try:
        validate_capabilities(backend, selected.manifest())
        from ..api.conformance import check_descriptor

        check_descriptor(selected.manifest(), backend)
    except Exception:
        backend.close()
        raise
    return backend
