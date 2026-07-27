"""Public exceptions raised by the contract library."""


class ContractValidationError(ValueError):
    """A payload does not conform to its canonical contract."""


class UnsupportedContractVersionError(ContractValidationError):
    """A payload names a contract version this installation cannot validate."""


class ContractSchemaLoadError(RuntimeError):
    """A canonical schema or version file could not be loaded."""
