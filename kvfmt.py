# Key-value format handler
#
# Formatting syntax (!\w)
# To escape '(!', use '((!'
#
from __future__ import print_function

import pyparsing as pp
import threading

from section import Sect
from errors import EvalError


_tlo = threading.local()  # thread local object


_KP_DELIMITER = ':'  # Key Path Delimiter
_UNLIMIT_RECUR_DEPTH = 999999999


class _KRef(object):
    def __init__(self, tok):
        pl = tok.split(_KP_DELIMITER)
        if 0 == len(pl):
            raise KeyError
        self.is_abs = (0 == len(pl[0]))
        if self.is_abs:
            self.pl = pl[1:]
        else:
            self.pl = pl
        for s in self.pl:
            if 0 == len(s):
                raise KeyError


class _KValue(object):
    def __init__(self, l=None):
        self.l = [] if None is l else l


class _Context(object):
    def __init__(self):
        self.outs = []  # list of parsed tokens
        self.pos = 0


# ============================================================================
#
# Parsing
#
# ============================================================================
def _start_parse():
    cxt = getattr(_tlo, 'cxt', None)
    assert None is cxt
    _tlo.cxt = _Context()


def _finish_parse():
    assert not None is _tlo.cxt
    _tlo.cxt = None


def _context():
    return _tlo.cxt


def _fmts_parse_action(ps, loc, toks):
    c = _context()
    tok = toks[0]
    ts = tok[2:-1]  # FORMAT-DEPENDENT
    c.outs.append(ps[c.pos:loc])
    c.outs.append(_KRef(ts))
    c.pos = loc + len(tok)


def _build_parser():
    fmts = pp.Regex(r'(?<!\()\(\![^\)]+\)')  # FORMAT-DEPENDENT
    anychar = pp.Regex(r'.')
    e = fmts ^ anychar
    fmts.setParseAction(_fmts_parse_action)
    grammer = pp.StringStart() + pp.ZeroOrMore(e) + pp.StringEnd()
    grammer.parseWithTabs()
    return grammer


def kvparse2(filepath):
    with open(filepath, 'rb') as f:
        s = f.read()
    return kvparse(s)


def kvparse(s):
    """
    :param s: (str) Source string
    :return: (list) parsed result.
    """
    _start_parse()
    try:
        _PSR.parseString(s)
        c = _context()
        c.outs.append(s[c.pos:])
        r = _KValue()
        all_string = True
        for e in c.outs:
            if isinstance(e, str):
                e = e.replace('((!', '(!')  # FORMAT-DEPENDENT
            else:
                all_string = False
            r.l.append(e)
        if all_string:
            return ''.join(r.l)
        else:
            return r
    finally:
        _finish_parse()


_PSR = _build_parser()


# ============================================================================
#
# Evaluation
#
# ============================================================================
def _get_keyvalue(rootsect, kpath):
    cs = rootsect
    for s in kpath:
        if (not isinstance(cs, Sect)
                or not s in cs):
            raise KeyError('Invalid key path')
        cs = cs[s]
    return cs


def _parse_kpath(rootsect, kpath):
    sec = _get_keyvalue(rootsect, kpath[:-1])  # get parent section of this key
    if not isinstance(sec, Sect):
        raise KeyError('Invalid key path')
    key = kpath[-1]
    return sec, key


def _eval_kref(rootsect, kpath, e, evhis, evkref):
    kpathstr = _KP_DELIMITER.join(kpath)
    if evkref and kpathstr in evhis:
        raise KeyError('Recursive reference')
    refpath = e.pl
    if not e.is_abs:
        # relative to abs path
        refpath = kpath[:-1] + e.pl
    evhis.append(kpathstr)
    try:
        if evkref:
            ev = _eval_kvalue(rootsect,
                              refpath,
                              _get_keyvalue(rootsect, refpath),
                              evhis,
                              True)
        else:
            ev = _get_keyvalue(rootsect, refpath)
        evhis.pop()
        if isinstance(ev, Sect):
            raise KeyError('Section reference')
        return ev
    except KeyError as ke:
        sec, key = _parse_kpath(rootsect, kpath)
        if key in sec:
            pi = sec.get_key_parseinfo(key)
            if not None is pi:
                pi.set_current_tag(ke.message)
            raise EvalError(pi, evhis[:], _KP_DELIMITER.join(refpath))
        else:
            raise ke


def _eval_kvalue(rootsect, kpath, kve, evhis, evkref):
    if isinstance(kve, _KValue):
        l = []
        evdone = True
        for e in kve.l:
            if isinstance(e, _KRef):
                ev = _eval_kref(rootsect, kpath, e, evhis, evkref)
            elif isinstance(e, _KValue):
                ev = _eval_kvalue(rootsect, kpath, e, evhis, evkref)
            else:
                assert isinstance(e, str)
                ev = e
            if not isinstance(ev, str):
                evdone = False
            l.append(ev)
        if evdone:
            return ''.join(l)
        else:
            return _KValue(l)
    else:
        return kve


def _eval_sect(rootsect, cs, kpath):
    for k in cs:
        v = cs[k]
        if isinstance(v, Sect):
            _eval_sect(rootsect, v, kpath + [k])
        elif isinstance(v, _KValue):
            nv = _eval_kvalue(rootsect, kpath + [k], v, [], True)
            assert isinstance(nv, str)
            cs.force_setitem(k, nv)
        else:
            assert isinstance(v, str)
            # nothing to do.


def kveval_all(rootsect):
    """
    Evaluates all key value under the section.
    This function should be called before using Sections.
    :param rootsect: (Sect) Root section to be evaluated.
    """
    _eval_sect(rootsect, rootsect, [])


def kveval_parsed_non_recursive(rootsect, kpath, kve):
    return _eval_kvalue(rootsect,
                        kpath,
                        kve,
                        [],
                        False)


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
#        # Simple strings
#        ('', ''),
#        ('     ', '     '),
#        ('\n', '\n'),
#        ('\n    \n', '\n    \n'),
#        ('434nsdn', '434nsdn'),
#        (' 1234 562kdkd,\ne333\n44kk', ' 1234 562kdkd,\ne333\n44kk'),
#        # Simple formats : one replacement
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

    tsect = Sect('___')
    for k in dic:
        tsect[k] = dic[k]

    for ts in ss:
        s = ts[0]
        expected = ts[1]
        tsect['_'] = kvparse(s)
        print("++ %s / %s" % (s, expected))
        kveval_all(tsect)
        fs = tsect['_']
        if fs != expected:
            print('Base string:\n' + s + '\n')
            print('Formatted:\n' + fs + '\n')
            print('Expected:\n' + expected + '\n')
            assert False
        del tsect['_']
    # ============================
    # Failure cases
    # ============================
    ss = [
        '(!unknown)'
    ]
    for s in ss:
        tsect['_'] = kvparse(s)
        try:
            kveval_all(tsect)
        except EvalError as e:
            print(str(e))
        del tsect['_']


if '__main__' == __name__:
    test()