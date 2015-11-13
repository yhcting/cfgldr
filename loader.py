import parser


def load_config(fconf, fverifier,
                confdict=None, verifierdict=None):
    """
    Load config file and returns corresponding 'dict' structure.
    :param fconf: (str) config file path
    :param fverifier: (str) verifier file path. None is allowed.
    :param confdict: (dict) That can be used as named-replacement-dict for conf
    :param verifierdict: (dict) That can be used as named-replacement-dict for
                         verifier
    :return: (dict)
    """
    return parser.parse_conf(fconf, fverifier,
                             confdict, verifierdict).to_dict()
