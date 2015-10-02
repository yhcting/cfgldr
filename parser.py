from __future__ import print_function
import sys
import os.path

import logger
import verifier
import pyparsing as pp
from section import Sect
from errors import BaseError, ParseBaseError, ParseError, FileIOError

P = logger.P(__name__)
#P.set_level(P.VERBOSE)
P.set_level(P.ERROR)


_SHOW_TEST_NOK_MSG = False
#_SHOW_TEST_NOK_MSG = True


class Context(object):
    """Context used to parse a config file."""
    def __init__(self, fconf):
        self.ss = [Sect(None)]
        self.fconf = os.path.abspath(fconf)
        self.ps = None  # parse string of current context
        self.loc = 0  # current parse location (interesting location)

    def __getattr__(self, aname):
        """Dummy function for future use."""
        raise AttributeError(aname)

    @property
    def file(self):
        return self.fconf

    @property
    def cwd(self):
        return os.path.dirname(self.fconf)

    @property
    def sroot(self):
        """Get root section of this context"""
        assert len(self.ss) > 0
        return self.ss[0]

    @property
    def sdepth(self):
        """Current section depth. 0 means root section"""
        return len(self.ss) - 1

    @property
    def cws(self):
        """Current working section"""
        return self.ss[-1]

    def spop(self):
        return self.ss.pop()

    def spush(self, s):
        self.ss.append(s)

    def setinfo(self, ps, loc):
        self.ps = ps
        self.loc = loc


class ContextManager(object):
    """Context manager"""
    def __init__(self):
        self.cstk = []

    @property
    def context(self):
        """Get current working context"""
        assert len(self.cstk) > 0
        return self.cstk[-1]

    def get_conf_context(self, fconf):
        """
        Get context matching given fconf(config file)
        :param fconf: abs-path for config file.
        :return: (Context) context for given config file.
                 None if there is no matching context.
        """
        for c in self.cstk:
            if c.file == fconf:
                return c
        return None

    def get_context_stack_info(self):
        """
        :return: [(file, ps, loc) ...] array of tuples
        """
        r = []
        for s in self.cstk:
            # should be reverse of stack order
            r.append((s.file, s.ps, s.loc))
        assert len(r) > 0
        return r

    def parse_start(self, ps, loc, fconf):
        """
        Enter to new parsing context to parse specified config file.
        ps : current parse string. 'None' means 'parse directly via API'
        loc : current location
        fconf : new config file
        """
        P.d('parse_start: %s' % fconf)
        if len(self.cstk) > 0:
            c = self.context
            c.setinfo(ps, loc)
        self.cstk.append(Context(fconf))

    def parse_end(self):
        """
        End current parsing context.
        Current working context is changed to previous one.
        And parsed context is returned.
        """
        P.d('parse_end')
        self.cstk.pop()


# context manager
_cm = ContextManager()


# ============================================================================
#
# Utility functions
#
# ============================================================================
def _is_abspath(v):
    return v[0] == os.path.sep


# ============================================================================
#
# Action functions
#
# ============================================================================
def _include_conf(ps, loc, v):
    c = _cm.context
    fconf = v if _is_abspath(v) else os.path.join(c.cwd, v)
    try:
        c = _parse_conf(ps, loc, fconf)
    except ParseBaseError as e:
        e.append_ei(_cm.context.file, ps, loc)
        raise
    return c


def _merge_section(dst, src, ps, loc):
    try:
        dst.supdate(src)
    except KeyError as e:
        raise ParseError(_cm.context.file, ps, loc, e.message)


# return None if success, otherwise error message.
def _cmdhandle_inherit(ps, loc, v):
    subs = _include_conf(ps, loc, v).sroot
    subs.set_writable()
    _merge_section(_cm.context.cws, subs, ps, loc)


# return None if success, otherwise error message.
def _cmdhandle_include(ps, loc, v):
    s = _cm.context.cws
    subs = _include_conf(ps, loc, v).sroot
    subs.set_readonly()
    _merge_section(s, subs, ps, loc)


_cmdhandler_map = {
    # 'inherit' and 'include' are basically same - including external config.
    # Difference is that caller can override section key created by 'inherit'.
    # But, in case of 'include' this case raise 'DuplicatedKey' error.
    'inherit': _cmdhandle_inherit,
    'include': _cmdhandle_include
}


def _cmd_parse_action(ps, loc, toks):
    assert(2 == len(toks))
    cc = _cm.context
    cmd = toks[0].strip()
    value = toks[1].strip()
    if not cmd in _cmdhandler_map:
        raise ParseError(cc.file, ps, loc,
                         'Unknown command : ' + cmd)
    # noinspection PyCallingNonCallable
    errmsg = _cmdhandler_map[cmd](ps, loc, value)
    if errmsg:
        raise ParseError(cc.file, ps, loc,
                         '[%s] %s' % (cmd, errmsg))


def _sect_parse_action(ps, loc, toks):
    assert(3 == len(toks))
    (sect_s, name, sect_e) = toks

    cc = _cm.context
    # check error cases.
    thisdepth = len(sect_s)
    if thisdepth != len(sect_e):
        raise ParseError(cc.file, ps, loc,
                         'Incorrect section depth')
    if thisdepth > cc.sdepth + 1:
        raise ParseError(cc.file, ps, loc,
                         'Section too nested')
    # move to parent section of this depth
    while cc.sdepth >= thisdepth:
        cc.spop()

    csi = _cm.get_context_stack_info()
    # replace current context info with this parsing value
    csi.pop()
    csi.append((cc.file, ps, loc))
    parentsect = cc.cws
    if parentsect.is_readonly(name):
        raise ParseError(cc.file, ps, loc,
                         'Section name(%s) already in use.' % name)
    elif not parentsect.is_section(name):
        parentsect[name] = Sect(name)
        parentsect.set_key_parseinfo(name, csi)
    else:
        # 'name' is existing-subsection.
        # And now it is shown at config file
        # So, it should be set as readonly
        parentsect.set_readonly(name, False)
        # Use latest(defined lastly) information
        parentsect.set_key_parseinfo(name, csi)
    P.d('Sect "%s" is added to Sect "%s"\n' % (name, parentsect.name))
    cc.spush(parentsect[name])


_MANDATORY_KEY_PREFIX = '^'
_FINAL_KEY_PREFIX = '!'


def _keyvalue_parse_action(ps, loc, toks):
    assert(1 == len(toks)
           or 2 == len(toks))
    cc = _cm.context
    k = toks[0]
    assert len(k) > 0
    mankey = False
    finkey = False
    if k[0] == _MANDATORY_KEY_PREFIX:
        k = k[1:]
        mankey = True
    elif k[0] == _FINAL_KEY_PREFIX:
        k = k[1:]
        finkey = True
    if 1 == len(toks):
        v = ''  # empty string by default
    else:
        v = toks[1]
    s = cc.cws
    P.d('Key "%s" is added to Sect "%s"\n' % (k, s.name))
    csi = _cm.get_context_stack_info()
    # replace current context info with this parsing value
    csi.pop()
    csi.append((cc.file, ps, loc))
    try:
        s[k] = v
        s.set_key_parseinfo(k, csi)
        s.set_mandatory(k, mankey)
        s.set_final(k, finkey)
    except KeyError as e:
        raise ParseError(cc.file, ps, loc, e.message)


# ===============================
# Constructs config file BNF form
# ===============================
def _build_recursive_descent_parser(vrfconf):
    ##########################################################################
    #
    # Implements BNF with pyparsing
    #
    ##########################################################################
    # parsing config item is based on line-by-line parsing by default.
    pp.ParserElement.setDefaultWhitespaceChars('\f\v\r')

    lnend = pp.Literal('\n').suppress()
    allchars = pp.CharsNotIn('\n')
    spacestr = r'[ \t]'
    spaces = pp.Regex(spacestr + '+').suppress()

    #
    # base token for name.
    #

    if vrfconf:
        wordrestr = r'[^\s]+'
    else:
        wordrestr = r'[a-zA-Z0-9_\-\.]+'
    word = pp.Regex(wordrestr)

    #
    # command
    #
    cmdprefix = pp.Literal('@')
    cmdword = cmdprefix.suppress() + word
    command = cmdword + spaces + \
        pp.QuotedString('(', endQuoteChar=')', multiline=True)

    #
    # section
    #
    sect_s = pp.Regex(r'\[+')
    sect_e = pp.Regex(r'\]+')
    sect = sect_s + spaces + word + spaces + sect_e

    #
    # comment
    #
    comment = pp.Literal('#') + pp.Optional(allchars)
    # comment is ignored
    comment = comment.suppress()

    #
    # key / value
    #
    if vrfconf:
        key = word
    else:
        keyattr_prefix = '[\\' + _FINAL_KEY_PREFIX + r'!]'
        key = pp.Regex(keyattr_prefix + '?' + wordrestr)

    squoted = pp.QuotedString("'")
    dquoted = pp.QuotedString('"')
    tsquoted = pp.QuotedString("'''", multiline=True)
    tdquoted = pp.QuotedString('"""', multiline=True)
    # unquoted value SHOULD NOT include 'spacestr' leading comments
    unquoted = pp.Regex(r'([^\n \t]|' + spacestr + r'(?!#))*')
    value = tdquoted ^ tsquoted ^ dquoted ^ squoted ^ unquoted
    keyvalue = key + spaces \
        + pp.Literal('=').suppress() + pp.Optional(spaces + value)

    #
    # define high-level token. Order is very important.
    #
    # non-comment spaces
    ncmtsps = pp.Regex(r'(?:' + spacestr + r'(?!#))+')
    item = sect ^ command ^ keyvalue
    entry = comment\
        ^ (pp.Optional(ncmtsps) + pp.Optional(item)
            + pp.Optional(ncmtsps) + pp.Optional(pp.Regex(spacestr) + comment))
    entries = entry + pp.ZeroOrMore(lnend + entry)
    pp.StringStart() + pp.Optional(entries) + pp.StringEnd()

    fullcfg = entries

    ##########################################################################
    #
    # Define action functions
    #
    ##########################################################################
    command.setParseAction(_cmd_parse_action)
    sect.setParseAction(_sect_parse_action)
    keyvalue.setParseAction(_keyvalue_parse_action)

    return fullcfg


_cpsr = _build_recursive_descent_parser(False)
_vpsr = _build_recursive_descent_parser(True)
_current_parser = None  # default


def _set_parser(psr):
    global _current_parser
    _current_parser = psr


def _get_parser():
    return _current_parser


def _parse_conf(ps, loc, fconf):
    """
    :param ps: parse-string
    :param loc: interesting/issued location
    :param fconf: abs-path for config file.
    :return: (Context) context contains parse result.
    """
    assert _is_abspath(fconf)

    # check recursive(cyclic) parsing
    # This may be happened by including recursively
    if None != _cm.get_conf_context(fconf):
        # cyclic parsing is detected.
        raise ParseError(_cm.context.file, ps, loc,
                         'Cyclic(Recursive) parsing is detected')

    _cm.parse_start(ps, loc, fconf)
    try:
        with open(fconf, 'rb') as f:
            content = f.read()

        # change new line style : DOS -> UNIX
        content.replace('\r\n', '\n')
        _get_parser().parseString(content, True)
        return _cm.context
    except IOError:
        raise FileIOError(_cm.context.file, None, -1,
                          'Fail to access config file')
    except pp.ParseBaseException as e:
        # Ugly hack.
        # But, this is better response.
        if e.msg == 'Expected end of text':
            e.msg = 'Syntax error'
        raise ParseError(_cm.context.file, e.pstr, e.loc, e.msg)
    finally:
        _cm.parse_end()


def parse_conf(fconf, fverifier):
    """
    Parse config file and gives root section as result.
    :param fconf: config file path
    :param fverifier: verifier file path. None is allowed.
    :return: (section.Sect) root section.
    """
    fconf = os.path.abspath(fconf)
    _set_parser(_cpsr)
    ctxt = _parse_conf(None, -1, fconf)
    csct = ctxt.sroot  # config section
    cfconf = ctxt.file
    vsct = None  # verifier section
    vfconf = None
    if None is not fverifier:
        _set_parser(_vpsr)
        ctxt = _parse_conf(None, -1, fverifier)
        vsct = ctxt.sroot
        vfconf = ctxt.file
    verifier.verify_conf(csct, cfconf, vsct, vfconf)
    _set_parser(None)
    return csct
# ============================================================================
#
#
#
# ============================================================================


def test():
    import os

    def check_data(datastr, datafile):
        with open(datafile, 'rb') as fh:
            fdata = fh.read()
        if fdata != datastr:
            P.e('%s: Success. But section data is different from expected\n%s'
                % (datafile, datastr))
            assert False

    def test_file_(fconf, fverifier, expectok):
        #cfg.setDebug()
        #print('Testing : %s\n' % fconf)
        try:
            sroot = parse_conf(fconf, fverifier)
            if not expectok:
                P.e('Failure is expected. But success! : %s\n' % fconf)
                assert False
            return sroot
        except BaseError as e:
            emsg = 'Fail parse : %s\n' % str(e)
            if _SHOW_TEST_NOK_MSG:
                P.e(emsg)
            else:
                P.d(emsg)
            if expectok:
                P.e('Fail parse : %s\n' % fconf)
                raise e

    def test_file(fconf):
        fconf = os.path.abspath(fconf)
        okdata_file = fconf + '.ok'
        nokdata_file = fconf + '.nok'
        vrffile = fconf + '.vrf'
        if not os.path.exists(vrffile):
            vrffile = None
        expectok = not os.path.exists(nokdata_file)
        sroot = test_file_(fconf, vrffile, expectok)
        #print(str(sroot))
        if expectok and os.path.exists(okdata_file):
            check_data(str(sroot), okdata_file)

    # noinspection PyShadowingNames
    def test_dir(testdir):
        #
        # Test with given test samples
        #
        testdir = os.path.abspath(testdir)
        files = os.listdir(testdir)
        files.sort()
        for name in files:
            f = os.path.join(testdir, name)
            if os.path.isdir(f):
                test_dir(f)
            elif os.path.isfile(f) \
                    and (name.startswith('conf')
                         and not name.endswith('.ok')
                         and not name.endswith('.nok')
                         and not name.endswith('.vrf')):
                test_file(f)

    test_dir('tests')

    if len(sys.argv) > 1:
        #print('######## TEST WITH EXTERNAL SAMPLES ########\n')
        for f in sys.argv[1:]:
            if os.path.isdir(f):
                test_dir(f)
            elif os.path.isfile(f):
                test_file(f)
            else:
                print('Invalid file path(Skipped) : %s\n' % f)


# ============================================================================
#
#
#
# ============================================================================

if '__main__' == __name__:
    test()
    print('* Congraturations! Test PASSED *')
