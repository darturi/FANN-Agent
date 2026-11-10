"""Existing durable binding/state rules with explicit admitted native namespace."""

from nh_binding import Campaign as Original
from nh_binding import validate_binding
from nh_common import private, save


class Campaign(Original):
    def __init__(self, root, binding, authority=None):
        if not root.name.startswith("native-"):
            super().__init__(root, binding)
            return
        if authority is None or getattr(authority, "native", False) is not True:
            raise RuntimeError("Admitted current native allocation required")
        self.root = private(root)
        self.binding = binding
        self.key = validate_binding(binding)
        authority.bind(self.key)
        save(self.root / "binding.json", {"binding": binding, "sha256": self.key})
        self.append("prepared")
