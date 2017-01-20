from __future__ import print_function
import sys
import os.path

import logger
import verifier
import pyparsing as pp
import section
import kvfmt
from section import Sect
from parseinfo import ConfPos, ParsePos, SectPath, ParseInfo
from errors import BaseError, ParseError, FileIOError

P = logger.P(__name__)
#P.set_level(P.VERBOSE)
P.set_level(P.ERROR)


#_SHOW_TEST_NOK_MSG = False
_SHOW_TEST_NOK_MSG = True


class Context(object):
    """Context used to parse a config file."""
    def __init__(self, fconf):
        self.ss = [Sect(None)]
        self.cfpo = ConfPos(os.path.abspath(fconf), None, 0)

    def __getattr__(self, aname):
        """Dummy function for future use."""
        raise AttributeError(aname)

    @property
    def file(self):
        return self.cfpo.file

    @property
    def cwd(self):
        return os.path.dirname(self.cfpo.file)

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

    def setloc(self, ps, loc):
        self.cfpo.ps = ps
        self.cfpo.loc = loc


class ContextManager(object):
    """Context manager"""
    def __init__(self):
        self.cstk = []
        self.repldict = None  # dictionary for named replacement

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
            if c.cfpo.file == fconf:
                return c
        return None

    def get_current_sect_path(self):
        sectpath = []
        for c in self.cstk:
            for s in c.ss:
                if None is s.name:
                    continue
                sectpath.append(s.name)
        return sectpath

    def create_parseinfo(self, ps=None, loc=None, tag=None):
        po = ParsePos([c.cfpo.clone() for c in self.cstk])
        sectpath = []
        for c in self.cstk:
            for s in c.ss:
                if None is s.name:
                    continue
                sectpath.append(s.name)
        sp = SectPath(self.get_current_sect_path())
        pi = ParseInfo(po, sp)
        if (None is not ps
                and None is not loc):
            pi.set_current_pos(ps, loc)
        if None is not tag:
            pi.set_current_tag(tag)
        return pi

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
            c.setloc(ps, loc)
        self.cstk.append(Context(fconf))

    def parse_end(self):
        """
        End current parsing context.
        Current working context is changed to previous one.
        And parsed context is returned.
        """
        P.d('parse_end')
        c = self.cstk.pop()
        kvfmt.kveval_all(c.sroot)
        c.sroot.clear_temp_keys(True)


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
# Parser constants
#
# ============================================================================
_KIMAN_CH = '^'  # Mandatory key prefix
_KIFIN_CH = '!'  # Final key prefix
_KITMP_CH = '~'  # Temporal key prefix
_KICMD_CH = '@'  # Command prefix


# ============================================================================
#
# Action functions
#
# ============================================================================
def _include_conf(ps, loc, v):
    c = _cm.context
    fconf = v if _is_abspath(v) else os.path.join(c.cwd, v)
    return _parse_conf(ps, loc, fconf)


def _merge_section(dst, src, ps, loc):
    try:
        dst.supdate(src)
    except KeyError as e:
        raise ParseError(_cm.create_parseinfo(ps, loc, str(e)))


# return None if success, otherwise error message.
def _cmdhandle_inherit(ps, loc, v):
    """
    Inherit from external config file. Overwriting included keys are allowed.
    """
    subs = _include_conf(ps, loc, v).sroot
    subs.set_writable()
    _merge_section(_cm.context.cws, subs, ps, loc)


# return None if success, otherwise error message.
def _cmdhandle_include(ps, loc, v):
    """
    Include external config file. Overwriting included keys are NOT allowed.
    """
    s = _cm.context.cws
    subs = _include_conf(ps, loc, v).sroot
    subs.set_readonly()
    _merge_section(s, subs, ps, loc)


def _cmdhandle_rmkeys(ps, loc, v):
    """
    Remove keys from current working section.
    """
    cc = _cm.context
    s = cc.cws
    for key in v.split():
        if key in s:
            del s[key]
        else:
            raise ParseError(_cm.create_parseinfo(
                ps, loc, 'Unknown key : ' + key))


_cmdhandler_map = {
    # 'inherit' and 'include' are basically same - including external config.
    # Difference is that caller can override section key created by 'inherit'.
    # But, in case of 'include' this case raise 'DuplicatedKey' error.
    'inherit': _cmdhandle_inherit,
    'include': _cmdhandle_include,
    # Supporing 'rmkeys' commands may break 'key overwriting protection'.
    # Therefore, 'rmkeys' command is disabled.
    #'rmkeys': _cmdhandle_rmkeys
}


def _cmd_parse_action(ps, loc, toks):
    assert(2 == len(toks))
    cmd = toks[0].strip()
    value = toks[1].strip()
    if cmd not in _cmdhandler_map:
        raise ParseError(_cm.create_parseinfo(
            ps, loc, 'Unknown command : ' + cmd))
    # noinspection PyCallingNonCallable
    errmsg = _cmdhandler_map[cmd](ps, loc, value)
    if errmsg:
        raise ParseError(_cm.create_parseinfo(
            ps, loc, '[%s] %s' % (cmd, errmsg)))


def _sect_parse_action(ps, loc, toks):
    assert(3 == len(toks))
    (sect_s, name, sect_e) = toks

    cc = _cm.context
    pi = _cm.create_parseinfo(ps, loc)
    # check error cases.
    thisdepth = len(sect_s)
    if thisdepth != len(sect_e):
        pi.set_current_tag('Incorrect section depth')
        raise ParseError(pi)
    if thisdepth > cc.sdepth + 1:
        pi.set_current_tag('Section too nested')
        raise ParseError(pi)
    # move to parent section of this depth
    while cc.sdepth >= thisdepth:
        cc.spop()
    # NOTE
    # Section path is updated. So, re-create parseinfo here.
    pi = _cm.create_parseinfo(ps, loc)
    parentsect = cc.cws
    if parentsect.is_readonly(name):
        pi.set_current_tag('Section name(%s) already in use.' % name)
        raise ParseError(pi)
    elif not parentsect.is_section(name):
        parentsect[name] = Sect(name)
        parentsect.set_key_parseinfo(name, pi)
    else:
        # 'name' is existing-subsection.
        # And now it is shown at config file
        # So, it should be set as readonly
        parentsect.set_readonly(name, False)
        # Use latest(defined lastly) information
        parentsect.set_key_parseinfo(name, pi)
    P.d('Sect "%s" is added to Sect "%s"\n' % (name, parentsect.name))
    cc.spush(parentsect[name])


_KIMAP = {_KIMAN_CH: section.KIMAN,
          _KIFIN_CH: section.KIFIN,
          _KITMP_CH: section.KITMP}


def _keyvalue_parse_action(ps, loc, toks):
    assert(2 == len(toks)
           or 3 == len(toks))
    cc = _cm.context
    k = toks[0]
    assert len(k) > 0
    kis = {
        section.KIMAN: False,
        section.KIFIN: False,
        section.KITMP: False
    }
    for prefix in _KIMAP.keys():
        if k[0] == prefix:
            k = k[1:]
            kis[_KIMAP[prefix]] = True
    op = toks[1]
    if 2 == len(toks):
        v = ''  # empty string by default
    else:
        v = toks[2]
    s = cc.cws
    P.d('Key "%s" is added to Sect "%s"\n' % (k, s.name))
    pi = _cm.create_parseinfo(ps, loc)
    # execute named replacement with current working section
    try:
        v = kvfmt.kvparse(v)
        if op == ':=':
            # Immediate non-recursive evaluation.
            v = kvfmt.kveval_parsed_non_recursive(
                cc.sroot, _cm.get_current_sect_path() + [k], v)
            # update with evaluated value.
        s[k] = v
        s.set_key_parseinfo(k, pi)
        for ki in kis:
            s.set_ki(k, ki, kis[ki])
    except KeyError as e:
        pi.set_current_tag(str(e))
        raise ParseError(pi)


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
    cmdprefix = pp.Literal(_KICMD_CH)
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
        keyattr_prefix = '[\\' + _KIFIN_CH + '\\' + _KITMP_CH + ']'
        key = pp.Regex(keyattr_prefix + '?' + wordrestr)

    squoted = pp.QuotedString("'", escChar='\\')
    dquoted = pp.QuotedString('"', escChar='\\')
    tsquoted = pp.QuotedString("'''",  escChar='\\', multiline=True)
    tdquoted = pp.QuotedString('"""',  escChar='\\', multiline=True)
    # unquoted value SHOULD NOT include 'spacestr' leading comments
    unquoted = pp.Regex(r'([^\n \t]|' + spacestr + r'+(?!\s*#))*')
    value = tdquoted ^ tsquoted ^ dquoted ^ squoted ^ unquoted
    keyvalue = key + spaces \
        + (pp.Literal('=') ^ pp.Literal(':=')) + pp.Optional(spaces + value)

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
    :param fconf: (str) abs-path for config file.
    :return: (Context) context contains parse result.
    """
    assert _is_abspath(fconf)

    # check recursive(cyclic) parsing
    # This may be happened by including recursively
    if None is not _cm.get_conf_context(fconf):
        # cyclic parsing is detected.
        raise ParseError(_cm.create_parseinfo(
            ps, loc, 'Cyclic(Recursive) parsing is detected'))

    _cm.parse_start(ps, loc, fconf)
    try:
        with open(fconf, 'rb') as f:
            content = f.read()

        # change new line style : DOS -> UNIX
        content = content.decode('utf-8')
        content.replace('\r\n', '\n')
        repldict = _cm.repldict
        if repldict is not None:
            try:
                content = content % repldict
            except KeyError as e:
                msg = 'Unknown symbol at named-replacement: %%(%s)s' % str(e)
                raise ParseError(_cm.create_parseinfo(None, 0, msg))
        _get_parser().parseString(content, True)
        return _cm.context
    except IOError:
        raise FileIOError(_cm.create_parseinfo(
            None, -1, 'Fail to access config file'))
    except pp.ParseBaseException as e:
        # Ugly hack.
        # But, this is better response.
        if e.msg == 'Expected end of text':
            e.msg = 'Syntax error'
        raise ParseError(_cm.create_parseinfo(e.pstr, e.loc, e.msg))
    finally:
        _cm.parse_end()


def parse_conf(fconf, fverifier, confdict, vrfdict):
    """
    Parse config file and gives root section as result.
    :param fconf: config file path
    :param fverifier: verifier file path. None is allowed.
    :param confdict: configuration dictionary
    :param vrfdict: verifier dictionary
    :return: (section.Sect) root section.
    """
    fconf = os.path.abspath(fconf)
    _cm.repldict = confdict
    _set_parser(_cpsr)
    ctxt = _parse_conf(None, -1, fconf)
    csct = ctxt.sroot  # config section
    cfconf = ctxt.file
    vsct = None  # verifier section
    vfconf = None
    if None is not fverifier:
        _cm.repldict = vrfdict
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
            fdata = fh.read().decode('utf-8')
        if fdata != datastr:
            P.e('%s: Success. But section data is different from expected\n%s'
                % (datafile, datastr))
            assert False

    def test_file_(fconf, fverifier, expectok):
        #cfg.setDebug()
        #print('Testing : %s\n' % fconf)
        try:
            confdict = {
                '__filename__': os.path.basename(fconf)
            }
            if fverifier is None:
                vrfdict = None
            else:
                vrfdict = {
                    '__filename__': os.path.basename(fverifier)
                }
            sroot = parse_conf(fconf, fverifier, confdict, vrfdict)
            if not expectok:
                P.e('Failure is expected. But success! : %s\n' % fconf)
                assert False
            return sroot
        except BaseError as e:
            emsg = 'Fail parse\n%s\n' % str(e)
            if _SHOW_TEST_NOK_MSG:
                P.e(emsg)
            else:
                P.d(emsg)
            if expectok:
                P.e('Fail parse\n%s\n' % fconf)
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

    if len(sys.argv) > 1:
        #print('######## TEST WITH EXTERNAL SAMPLES ########\n')
        for f in sys.argv[1:]:
            if os.path.isdir(f):
                test_dir(f)
            elif os.path.isfile(f):
                test_file(f)
            else:
                print('Invalid file path(Skipped) : %s\n' % f)
    else:
        test_dir('tests')


# ============================================================================
#
#
#
# ============================================================================

if '__main__' == __name__:
    test()
    print('* Congraturations! Test PASSED *')
