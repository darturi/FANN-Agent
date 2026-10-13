class ValidationError(ValueError):
    """A shared data, policy, or evidence contract is invalid."""

    def __init__(self, *args: object, path: str = ""):
        super().__init__(*args)
        self.path = path
