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


import pyparsing as pp


class ConfPos(object):
    """
    Position at config file
    """
    def __init__(self, fconf, ps, loc=0, tag=''):
        assert None is not fconf
        self.file = fconf
        self.ps = ps  # parse string of current parsed file
        self.loc = loc  # current parsed location (interesting location)
        self.tag = tag  # tag message for this position

    @property
    def lineno(self):
        return pp.lineno(self.loc, self.ps)

    @property
    def column(self):
        return pp.col(self.loc, self.ps)

    @property
    def line(self):
        return pp.line(self.loc, self.ps)

    def clone(self):
        return ConfPos(self.file, self.ps, self.loc, self.tag)

    def __str__(self):
        if self.ps:
            return '%s\n\t%s (#line: %d, col: %d)\n\tline: %s' % \
                   (self.tag, self.file, self.lineno, self.column, self.line)
        else:
            return '%s\n\t%s' % (self.tag, self.file)


class ParsePos(object):
    """
    Parse position
    """
    def __init__(self, cfpolist=None):
        self._cfpol = [] if None is cfpolist else cfpolist

    def __str__(self):
        """Get backtrace message"""
        lst = self._cfpol[:]
        lst.reverse()
        msg = ''
        n = len(self._cfpol) - 1
        for e in lst:
            msg += '#%2d: %s\n' % (n, str(e))
            n -= 1
        msg += '#End'
        return msg

    def push(self, cfpo):
        self._cfpol.append(cfpo)

    def pop(self):
        self._cfpol.pop()

    def peek(self):
        return self._cfpol[-1]

    def size(self):
        return len(self._cfpol)

    def get(self, i):
        """Get i-th ConfPos. index 0 is root(base) config"""
        return self._cfpol[i]


class SectPath(object):
    """
    Section path
    """
    def __init__(self, path=None):
        self.path = [] if None is path else path

    def __str__(self):
        return '> ' + ' > '.join(self.path)


class ParseInfo(object):
    """
    Parse information of key.
    """
    def __init__(self, prpo, sectpath):
        """
        :param prpo: (ParsePos)
        """
        assert isinstance(prpo, ParsePos) and isinstance(sectpath, SectPath)
        self.prpo = prpo
        self.sectpath = sectpath

    def __str__(self):
        return '''\
* Section trace: %s
* Include back trace:
%s''' % (str(self.sectpath), str(self.prpo))

    def set_current_pos(self, ps, loc):
        if (None is self.prpo
                or 0 == self.prpo.size()):
            return
        cfpo = self.prpo.peek()
        cfpo.ps = ps
        cfpo.loc = loc

    def set_current_tag(self, tag):
        if (None is self.prpo
                or 0 == self.prpo.size()):
            return
        cfpo = self.prpo.peek()
        cfpo.tag = tag
