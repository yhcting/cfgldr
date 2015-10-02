import pyparsing as pp


# ============================================================================
#
# Errors
#
# ============================================================================
class ErrorInfo(object):
    def __init__(self, fconf, ps, loc=0, msg=''):
        assert None is not fconf
        self.file = fconf
        self.ps = ps
        self.loc = loc
        self.msg = msg

    @property
    def lineno(self):
        return pp.lineno(self.loc, self.ps)

    @property
    def column(self):
        return pp.col(self.loc, self.ps)

    @property
    def line(self):
        return pp.line(self.loc, self.ps)

    def __str__(self):
        if self.ps:
            return '%s\n\t%s (#line: %d, col: %d)\n\tline: %s' % \
                   (self.msg, self.file, self.lineno, self.column, self.line)
        else:
            return '%s\n\t%s' % (self.msg, self.file)


class BaseError(Exception):
    """Top-most base error"""


class ParseBaseError(BaseError):
    def __init__(self, fconf, ps, loc, msg=''):
        ei = ErrorInfo(fconf, ps, loc, msg)
        self.eis = [ei]  # eis : Error Info Stack

    def __str__(self):
        s = '\n'
        i = 0
        for ei in self.eis:
            s += '# %d: %s\n' % (i, str(ei))
            i += 1
        return s

    def append_ei(self, fconf, ps, loc, msg=''):
        self.eis.append(ErrorInfo(fconf, ps, loc, msg))


class ParseError(ParseBaseError):
    """Incorrect syntax"""


class FileIOError(ParseBaseError):
    """Config file IO error."""


class VerificationError(BaseError):
    """Verification fails"""
    def __init__(self, ccsi, vcsi, msg=''):
        self.msg = msg
        eilst = []
        n = 0
        for csi in ccsi:
            # [0]:file, [1]:ps, [2]:loc
            eilst.insert(0, ErrorInfo(csi[0], csi[1], csi[2], '%s: ' % str(n)))
            n += 1
        self.cei = eilst

        eilst = []
        n = 0
        for csi in vcsi:
            # [0]:file, [1]:ps, [2]:loc
            eilst.insert(0, ErrorInfo(csi[0], csi[1], csi[2], '%s: ' % str(n)))
            n += 1
        self.vei = eilst

    def __str__(self):
        s = self.msg + '\n< Config >\n'
        for ei in self.cei:
            s += '%s\n' % str(ei)
        s += '\n< Verifier >\n'
        for ei in self.vei:
            s += '%s\n' % str(ei)
        return s
