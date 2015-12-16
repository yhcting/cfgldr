import parseinfo


# ============================================================================
#
# Errors
#
# ============================================================================
class BaseError(Exception):
    """Top-most base error"""


class ParseBaseError(BaseError):
    def __init__(self, pi):
        self.pi = pi

    def __str__(self):
        return str(self.pi)


class ParseError(ParseBaseError):
    """Incorrect syntax"""


class FileIOError(ParseBaseError):
    """Config file IO error."""


class VerificationError(BaseError):
    """Verification fails"""
    def __init__(self, cpi, vpi, msg=''):
        self.msg = msg
        self.cpi = cpi
        self.vpi = vpi

    def __str__(self):
        s = self.msg + '\n< Config >\n'
        s += str(self.cpi)
        s += '\n< Verifier >\n'
        s += str(self.vpi)
        return s


class EvalError(BaseError):
    """Key value evaluation error."""
    def __init__(self, pi, evhis, ref):
        self.pi = pi
        self.evhis = evhis
        self.ref = ref

    def __str__(self):
        return '''\
%s
Reference path: %s
Reference key: %s''' % (str(self.pi), '->'.join(self.evhis), self.ref)
