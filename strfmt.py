#
# Formatting syntax (!\w)
# To escape '(!', use '((!'
#
from __future__ import print_function

import pyparsing as pp
import threading

import parseinfo as pi


_tlo = threading.local()  # thread local object


class Context(object):
    def __init__(self, dic, filepath, pierr):
        self.outs = ''
        self.pos = 0
        self.dic = dic
        self.fp = filepath
        self.pierr = pierr


def _start_strfmt(dic, filepath, pierr):
    cxt = getattr(_tlo, 'cxt', None)
    assert None is cxt
    _tlo.cxt = Context(dic, filepath, pierr)


def _finish_strfmt():
    assert not None is _tlo.cxt
    _tlo.cxt = None


def _context():
    return _tlo.cxt


def _fmts_parse_action(ps, loc, toks):
    c = _context()
    tok = toks[0]
    ts = tok[2:-1]  # FORMAT-DEPENDENT
    try:
        s = c.dic[ts]
    except KeyError as e:
        if c.pierr:
            raise KeyError(str(pi.ConfPos(c.fp, ps, loc, 'Error: ' + str(e))))
        else:
            raise
    c.outs += ps[c.pos:loc] + s
    c.pos = loc + len(tok)


def _build_parser():
    fmts = pp.Regex(r'(?<!\()\(\![^\)]+\)')  # FORMAT-DEPENDENT
    anychar = pp.Regex(r'.')
    e = fmts ^ anychar
    fmts.setParseAction(_fmts_parse_action)
    grammer = pp.StringStart() + pp.ZeroOrMore(e) + pp.StringEnd()
    grammer.parseWithTabs()
    return grammer

def strfmt2(filepath, dic, pierr=False):
    with open(filepath, 'rb') as f:
        s = f.read()
    return strfmt(s, dic, filepath, pierr)


def strfmt(s, dic, filepath='', pierr=False):
    """
    :param s: (str) Source string
    :param dic: (obj) Object that has '__getitem__' function.
    :param filename: (str) Optional, filename contains this string.
    :param pierr: (bool) True to include parse info in error.
    :return: (str)
    """
    _start_strfmt(dic, filepath, pierr)
    try:
        _PSR.parseString(s)
        c = _context()
        r = c.outs
        r += s[c.pos:]
        r = r.replace('((!', '(!')  # FORMAT-DEPENDENT
    finally:
        _finish_strfmt()
    return r


_PSR = _build_parser()


# ============================================================================
#
#
#
# ============================================================================
def test():
    dic = {'a': '@a',
           'b': '@b',
           'aa': '@aa',
           'aa bb': '@aa bb',
           '**\n**': '@**\n**'}

    # ============================
    # Success cases
    # ============================
    ss = [
        # Simple strings
        ('', ''),
        ('     ', '     '),
        ('\n', '\n'),
        ('\n    \n', '\n    \n'),
        ('434nsdn', '434nsdn'),
        (' 1234 562kdkd,\ne333\n44kk', ' 1234 562kdkd,\ne333\n44kk'),
        # Simple formats : one replacement
        ('(!a)', '@a'),
        ('aaa(!a)bbb', 'aaa@abbb'),
        ('aa\ta(!a)sbbb', 'aa\ta@asbbb'),
        ('22320sdk,n ae nld 89awe   en\t (!a)sje \r\n;lskd\r m',
         '22320sdk,n ae nld 89awe   en\t @asje \r\n;lskd\r m'),
        # Multiple replacements
        ('(!a)(!aa)', '@a@aa'),
        ('1(!a)22(!aa)333(!b)555', '1@a22@aa333@b555'),
        ('1(!a)\n22(!aa)333\n(!b)555\n',
         '1@a\n22@aa333\n@b555\n'),
        # Wierd format
        ('(!aa bb)(!**\n**)', '@aa bb@**\n**'),
        # Escape formats
        ('((!aa)', '(!aa)'),
        ('((!aa)((!bb)((!b)', '(!aa)(!bb)(!b)'),
        ('aa(!aa)bb', 'aa@aabb')
    ]
    for ts in ss:
        s = ts[0]
        expected = ts[1]
        fs = strfmt(s, dic, pierr=True)
        if fs != expected:
            print('Base string:\n' + s + '\n')
            print('Formatted:\n' + fs + '\n')
            print('Expected:\n' + expected + '\n')
            assert False

    # ============================
    # Failure cases
    # ============================
    ss = [
        '(!unknown)'
    ]
    for s in ss:
        try:
            strfmt(s, dic, 'testfile', pierr=True)
        except KeyError as e:
            print(e.message)
            pass  # expected error.


if '__main__' == __name__:
    test()