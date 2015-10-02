import parser


def load_config(fconf, fverifier):
    """
    Load config file and returns corresponding 'dict' structure.
    :param fconf: config file path
    :param fverifier: verifier file path. None is allowed.
    :return: (dict)
    """
    return parser.parse_conf(fconf, fverifier).to_dict()
