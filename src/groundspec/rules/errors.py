class RulePackError(ValueError):
    """Base class for all rule-pack loading/resolution failures."""


class PackNotFound(RulePackError):
    pass


class PackVersionMismatch(RulePackError):
    pass


class CyclicImport(RulePackError):
    pass


class ImportDepthExceeded(RulePackError):
    pass


class DuplicateRuleId(RulePackError):
    pass


class DuplicatePackId(RulePackError):
    pass
