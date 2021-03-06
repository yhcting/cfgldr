################################################################################
# Copyright (C) 2016, 2017
# Younghyung Cho. <yhcting77@gmail.com>
# All rights reserved.
#
# This file is part of cfgldr in ypylib
#
# This program is licensed under the FreeBSD license
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation
# are those of the authors and should not be interpreted as representing
# official policies, either expressed or implied, of the FreeBSD Project.
################################################################################


from __future__ import print_function
import logger

from datastruct import OrderedDict
from parseinfo import ParseInfoHistory

P = logger.P(__name__)
# P.set_level(P.VERBOSE)
P.set_level(P.ERROR)


# Key info attribute
_KIWR = 'wr'  # writable
_KIPIH = 'pih'  # key parsing info history

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
        if k not in self._ki:
            self._ki[k] = Sect._create_ki()
        else:
            Sect._init_ki_vals(self._ki[k])
        OrderedDict.__setitem__(self, k, v)
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

    @staticmethod
    def _init_ki_vals(ki):
        ki.update({
            _KIWR: False,
            KIMAN: False,
            KIFIN: False,
            KITMP: False,
        })

    @staticmethod
    def _create_ki():
        ki = dict()
        Sect._init_ki_vals(ki)
        ki[_KIPIH] = ParseInfoHistory()
        return ki

    def _overlay_ki(self, k, other_ki):
        pih = self._ki[k][_KIPIH]
        self._ki[k].update(other_ki)
        pih.add_overlay_history(other_ki[_KIPIH])
        self._ki[k][_KIPIH] = pih

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

    def overlay_key_parseinfo(self, k, pi):
        """
        :param k:
        :param pi: (KeyParseInfo) key parse info
        :return:
        """
        assert k in self
        # last element of list is final information couplied with key value.
        self._ki[k][_KIPIH].add_overlay_pi(pi)

    def get_key_parseinfo_history(self, k):
        """
        :param k: key
        :return: list[(ParseInfoHistory)]
        """
        assert k in self
        return self._ki[k][_KIPIH]

    def scopy(self):
        news = Sect(self.name)
        news.supdate(self)
        return news

    def kupdate(self, k, other):
        if isinstance(other[k], Sect):
            P.d('Sect(%s) is copied' % other[k].name)
            self[k] = other[k].scopy()
        else:
            self[k] = other[k]
        # noinspection PyProtectedMember
        self._overlay_ki(k, other._ki[k])

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
                    self.kupdate(k, s)
            else:
                self.kupdate(k, s)
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
    # s = Sect('root')

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
