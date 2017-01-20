from __future__ import print_function
import logger

from datastruct import OrderedDict

P = logger.P(__name__)
#P.set_level(P.VERBOSE)
P.set_level(P.ERROR)


# Key info attribute
_KIWR = 'wr'  # writable
_KIPI = 'pi'  # context stack info

# Public ki
KIFIN = 'fin'  # final
KITMP = 'tmp'  # temp key
KIMAN = 'man'  # mandatory


class Sect(OrderedDict):
    def __init__(self, name):
        OrderedDict.__init__(self)
        self.name = name
        # key infomation
        self._ki = {}

    def __setitem__(self, k, v):
        if self.is_readonly(k):
            P.d('Sect(%s): keyprop: %s' % (self.name, str(self._ki)))
            raise KeyError('Key(%s) is NOT writable' % k)
        OrderedDict.__setitem__(self, k, v)
        self._init_ki(k)
        self._setro(k)

    def force_setitem(self, k, v):
        """\
        Replace key value without modifying key-info-attributes
        This is very dangerous function(may break internal data-relation).
        So, if you are not sure, DO NOT USE this.
        """
        dict.__setitem__(self, k, v)

    def __delitem__(self, k):
        self._ki.pop(k, None)
        OrderedDict.__delitem__(self, k)

    def _init_ki(self, k):
        self._ki[k] = {
            _KIWR: False,
            _KIPI: None,
            KIMAN: False,
            KIFIN: False,
            KITMP: False,
        }

    def _setro(self, k):
        P.d('%s:%s set to RO' % (self.name, k))
        self._ki[k][_KIWR] = False

    def _setrw(self, k):
        P.d('%s:%s set to RW' % (self.name, k))
        self._ki[k][_KIWR] = True

    def set_writable(self, key=None, recursive=True):
        """
        Make key be writable.
        This works recursively if key is section name.
        Once key is overwriting, key property is changed to read-only again.
        :param key: key that are writable.
                    'None' for 'all-keys are writable'
        :param recursive:
        """
        ks = [key] if key else self.ks
        for k in ks:
            if (recursive
                    and isinstance(self[k], Sect)):
                self[k].set_writable(None)
            self._setrw(k)

    def set_readonly(self, key=None, recursive=True):
        """
        Make key be read-only.
        This works recursively if key is section name.
        :param key: key that are readonly.
                    'None' for 'all-keys are read-only'
        :param recursive:
        """
        ks = [key] if key else self.ks
        for k in ks:
            if recursive and isinstance(self[k], Sect):
                self[k].set_readonly(None)
            self._setro(k)

    def is_readonly(self, k):
        if k not in self:
            return False
        # order is important (means priority of attribute).
        if self._ki[k][KIFIN]:
            return True
        if self._ki[k][KITMP]:
            return False
        return not self._ki[k][_KIWR]

    def set_ki(self, k, attr, boolv):
        self._ki[k][attr] = boolv

    def is_ki_set(self, k, attr):
        return (k in self
                and self._ki[k][attr])

    def clear_temp_keys(self, recursive=False):
        ks = self.keys()[:]
        for k in ks:
            if (recursive
                    and isinstance(self[k], Sect)):
                self[k].clear_temp_keys(True)
            if self.is_ki_set(k, KITMP):
                del self[k]

    def is_section(self, k):
        return (k in self
                and isinstance(self[k], Sect))

    def set_key_parseinfo(self, k, pi):
        """
        :param k:
        :param pi: (KeyParseInfo) key parse info
        :return:
        """
        assert k in self
        self._ki[k][_KIPI] = pi

    def get_key_parseinfo(self, k):
        assert k in self
        return self._ki[k][_KIPI]

    def scopy(self):
        news = Sect(self.name)
        news.supdate(self)
        return news

    def supdate(self, s):
        for k in s:
            # if 'source' and 'target' are 'Sect'.
            #     Recursive merging.
            # else
            #     Just replace key value.
            #
            # Type of key value should be same.
            if k in self:
                if (isinstance(self[k], Sect)
                        and isinstance(s[k], Sect)):
                    # if this is section key, merge subsection
                    if self.is_readonly(k):
                        raise KeyError('Section(%s) is not writable.'
                                       % k)
                    else:
                        P.d('Sect(%s) is merged' % self[k].name)
                        self[k].supdate(s[k])
                else:
                    self[k] = s[k]
            else:
                if isinstance(s[k], Sect):
                    P.d('Sect(%s) is copied' % s[k].name)
                    self[k] = s[k].scopy()
                else:
                    self[k] = s[k]
        # noinspection PyProtectedMember
        self._ki.update(s._ki)

    def to_dict(self):
        d = dict()
        for k in self:
            if isinstance(self[k], Sect):
                d[k] = self[k].to_dict()
            else:
                d[k] = self[k]
        return d


# ============================================================================
#
#
#
# ============================================================================
def test():
    #s = Sect('root')

    s0 = Sect('sec0')
    s0['1'] = 1
    s0['2'] = 2
    s0['3'] = 3

    assert 3 == s0.pop('3', None)
    assert '3' not in s0
    assert None is s0.pop('3', None)
    s0['3'] = 3
    s0.set_ki('3', KITMP, True)
    s0.set_ki('2', KITMP, True)
    s0.clear_temp_keys()
    assert '2' not in s0
    assert '3' not in s0
    s0['2'] = 2
    s0['3'] = 3

    s00 = Sect('sec00')
    s00['1'] = 1
    s00['2'] = 2

    s000 = Sect('sec000')
    s000['1'] = 1
    s000['2'] = 2

    s00[s000.name] = s000
    s0[s00.name] = s00

    s1 = Sect('sec1')
    s1['1'] = 1
    s1['2'] = 2
    s1['a'] = 'A'

    s00_ = s00.scopy()
    s00_['a'] = 'A'

    s10 = Sect('sec10')
    s10['1'] = 1
    s10['a'] = 'A'

    s1[s00_.name] = s00_
    s1[s10.name] = s10

    s2 = s0.scopy()
    s2.set_writable()
    s2.supdate(s1)

    print(s0)

    d = s0.to_dict()
    print(d)

if '__main__' == __name__:
    test()
