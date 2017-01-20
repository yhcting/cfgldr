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
