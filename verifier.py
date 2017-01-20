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


import logger
import section
import re
from section import Sect
from errors import VerificationError


P = logger.P(__name__)
_ev_VAL = None  # variable containing current working value being verified


# ============================================================================
#
# Key-rule evaluator functions
# value is stored at VAL in verifier globals, and at _ev_VAL at here.
#
# ============================================================================
def _ev_re(pattern):
    global _ev_VAL
    return re.match(pattern, _ev_VAL, re.S)


def _generate_verifier_dict():
    funcs = ['re']
    evdict = dict()
    for fname in funcs:
        evdict[fname] = globals().get('_ev_%s' % fname)
        assert None is not evdict[fname]
    # Put position holder for value to be verified.
    evdict['VAL'] = None
    return evdict


_rule_eval_dict = _generate_verifier_dict()


# ============================================================================
#
#
#
# ============================================================================
def _match_keyrule(k, rule):
    return None is not re.match('^' + rule + '$', k)


def _match_valrule(v, rule):
    assert None is not v
    global _ev_VAL
    _ev_VAL = v
    _rule_eval_dict['VAL'] = v
    try:
        return eval(rule, _rule_eval_dict)
    except BaseException as e:
        raise VerificationError(None, None,
                                'Verifier function exception: %s' % str(e))


def _verify_sect(csct, cspi, vsct, vspi):
    # Current configuration section can be referred by verifier.
    _rule_eval_dict['CNF'] = csct.to_dict()

    # check mandatory key
    mank = {}  # mandatory keys.
    for vk in vsct:
        if vsct.is_ki_set(vk, section.KIMAN):
            mank[vk] = False

    # TODO: Any better way improving performance?
    # This is O(n * m) naive and simple algorithm.
    for ck in csct:
        mfound = False
        cpi = csct.get_key_parseinfo(ck)
        for vk in vsct:
            if not _match_keyrule(ck, vk):
                continue
            cv = csct[ck]
            vv = vsct[vk]
            # rule and config are different-type.
            # than ignore this rule.
            if isinstance(cv, Sect) != isinstance(vv, Sect):
                continue

            # key rule matches
            if vk in mank:
                # Mandatory is found.
                mank[vk] = True

            vpi = vsct.get_key_parseinfo(vk)
            try:
                if isinstance(cv, Sect):
                    _verify_sect(cv, cpi, vv, vpi)
                elif not _match_valrule(cv, vv):
                    raise VerificationError(cpi, vpi,
                                            'Rule-verification fails')
            except VerificationError as e:
                e.cpi = cpi
                e.vpi = vpi
                raise e
            P.d('Matched: key(%s, %s), value(%s, %s)' %
                (ck, vk, cv, vv))
            # Rule matches. Move to next config key
            mfound = True
            break

        if not mfound:
            raise VerificationError(cpi, vspi,
                                    'No-rule found')
    for vk in mank:
        if not mank[vk]:
            vpi = vsct.get_key_parseinfo(vk)
            # Some mandatory key is NOT defined.
            raise VerificationError(cspi, vpi,
                                    'Missing mandatory key')


def verify_conf(csct, cfconf, vsct, vfconf):
    """
    :param csct: (Sect) root section of config
    :param cfconf: (str) config file path
    :param vsct: (Sect) root section of verifier
    :param vfconf: (str) verifier file path
    :return:
    """
    if None is vsct:
        assert None is vfconf
        return  # nothing to do. Accept all.
    _verify_sect(csct, [(cfconf, None, 0)],
                 vsct, [(vfconf, None, 0)])
