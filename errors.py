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
    def __init__(self, ckey, cpih, vkey, vpih, msg=''):
        """
        :param ckey: (str) Conf. key name
        :param cpih: (ParseInfoHistory) conf. parse info
        :param vkey: (str) Verifier key name
        :param vpih: (ParseInfoHistory) verifier parse info
        :param msg: (str) title message
        """
        self.ckey = ckey
        self.cpih = cpih
        self.vkey = vkey
        self.vpih = vpih
        self.msg = msg

    def __str__(self):
        return '''\
%s
< Config >
Issued key: %s
%s
*********************************************************************
< Verifier >
Issued keyrule: %s
%s''' % (self.msg, self.ckey, str(self.cpih), self.vkey, str(self.vpih))


class EvalError(BaseError):
    """Key value evaluation error."""
    def __init__(self, pih, evh, ref):
        """
        :param pih: list(ParseInfoHistory) Parse info history
        :param evh: list(str) evaluation history
        :param ref: (str) reference path
        """
        self.pih = pih
        self.evh = evh
        self.ref = ref

    def __str__(self):
        return '''\
%s
Reference path: %s
Reference key: %s''' % (str(self.pih), '->'.join(self.evh), self.ref)


class VerificationFailException(BaseError):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg
