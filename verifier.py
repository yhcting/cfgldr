import re

import logger
import section
from section import Sect
from errors import VerificationError


P = logger.P(__name__)


def _match_keyrule(k, rule):
    return None is not re.match('^' + rule + '$', k)


def _match_valrule(v, rule):
    if len(rule) > 0:
        if rule[0] == '^':
            # NotImplementedError
            return False
    return None is not re.match('^' + rule + '$', v, re.M | re.S)


def _verify_sect(csct, cscsi, vsct, vscsi):
    # check mandatory key
    mank = {}  # mandatory keys.
    for vk in vsct:
        if vsct.is_ki_set(vk, section.KIMAN):
            mank[vk] = False

    for ck in csct:
        mfound = False
        ccsi = csct.get_key_parseinfo(ck)
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

            vcsi = vsct.get_key_parseinfo(vk)
            if isinstance(cv, Sect):
                _verify_sect(cv, ccsi, vv, vcsi)
            elif not _match_valrule(cv, vv):
                raise VerificationError(ccsi, vcsi,
                                        'Rule-verification fails')
            P.d('Matched: key(%s, %s), value(%s, %s)' %
                (ck, vk, cv, vv))
            # Rule matches. Move to next config key
            mfound = True
            break

        if not mfound:
            raise VerificationError(ccsi, vscsi,
                                    'No-rule found')
    for vk in mank:
        if not mank[vk]:
            vcsi = vsct.get_key_parseinfo(vk)
            # Some mandatory key is NOT defined.
            raise VerificationError(cscsi, vcsi,
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
