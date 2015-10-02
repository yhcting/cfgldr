import logging


logging.basicConfig()


class P(object):
    # log levels
    VERBOSE = 5
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARN = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

    def __init__(self, name):
        self.lgr = logging.getLogger(name)

    def disable(self):
        self.lgr.setLevel(logging.CRITICAL)

    def set_level(self, lvl):
        self.lgr.setLevel(lvl)

    def d(self, msg):
        self.lgr.debug(msg)

    def i(self, msg):
        self.lgr.info(msg)

    def w(self, msg):
        self.lgr.warning(msg)

    def e(self, msg):
        self.lgr.error(msg)

    def c(self, msg):
        self.lgr.critical(msg)
        assert False


logging.addLevelName(P.VERBOSE, 5)
