class AgentError(RuntimeError):
    """An actionable operation failure."""


class BudgetExceeded(AgentError):
    pass


class ProtectedEvidence(AgentError):
    pass


class UnsupportedTarget(AgentError):
    pass


class IncompatibleExtension(AgentError):
    pass


class UnsupportedCapability(UnsupportedTarget):
    pass


class LegacyRun(AgentError):
    pass
