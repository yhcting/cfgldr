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
        raise VerificationError(None, None, 'Verifier function exception: %s' % str(e))


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
