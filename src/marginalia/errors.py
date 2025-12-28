# marginalia/errors.py

# meta: modules=errors callers=*
class MarginaliaError(Exception):
    pass

# meta: modules=errors callers=*
class UsageError(MarginaliaError):
    pass

# meta: modules=errors callers=*
class MetaParseError(MarginaliaError):
    pass

# meta: modules=errors callers=*
class StrictFailure(MarginaliaError):
    pass

# meta: modules=errors callers=*
class IoFailure(MarginaliaError):
    pass
