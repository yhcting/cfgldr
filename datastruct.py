_UNIQ_DUMMY_OBJ = object()


def __newobj__(cls, *args):
    # Hack for pickle
    return cls.__new__(cls, *args)


class OrderedDict(dict):
    def __setstate__(self, state):
        dict.update(self, state[0])
        self.__dict__.update(state[1])

    def __reduce__(self):
        state = (dict(self), self.__dict__)
        return __newobj__, (self.__class__,), state

    def __getitem__(self, k):
        return dict.__getitem__(self, k)

    def __setitem__(self, k, v):
        if k not in self:
            self.ks.append(k)
        dict.__setitem__(self, k, v)

    def __delitem__(self, k):
        dict.__delitem__(self, k)
        if k in self.ks:
            self.ks.remove(k)

    def __repr__(self):
        return '{%s}' % ', '.join([('%s: %s' % (repr(k), repr(self[k])))
                                   for k in self.ks])

    __str__ = __repr__
    __str__.__doc__ = "x.__str__() <==> str(x)"

    def __eq__(self, y):
        """Order of key should be same too."""
        return isinstance(y, self.__class__) \
            and self.ks == y.ks \
            and dict.__eq__(self, y)

    def __ne__(self, y):
        return not self.__eq__(y)

    def __init__(self):
        # noinspection PyTypeChecker
        dict.__init__(self)
        # sequence(order) of key values (including subsection name)
        self.ks = []  # key sequence

    def get(self, k, d=None):
        try:
            return self[k]
        except KeyError:
            return d

    def copy(self):
        news = OrderedDict()
        news.update(self)
        return news

    def update(self, e=None, **f):
        if e:
            if hasattr(e, 'keys'):
                for k in e:
                    self[k] = e[k]
            else:
                for (k, v) in e:
                    self[k] = v
        for k in f:
            self[k] = f[k]

    def pop(self, k, d=_UNIQ_DUMMY_OBJ):
        try:
            v = self[k]
        except KeyError:
            if d is _UNIQ_DUMMY_OBJ:
                raise
            v = d
        else:
            del self[k]
        return v

    def popitem(self):
        if not self.ks:
            raise KeyError(": 'popitem(): dictionary is empty'")
        k = self.ks[0]
        v = self[k]
        del self[k]
        return k, v

    def clear(self):
        dict.clear(self)
        self.ks = []

    def setdefault(self, k, d=None):
        try:
            return self[k]
        except KeyError:
            self[k] = d
            return self[k]

    def items(self):
        return zip(self.ks, self.values())

    def keys(self):
        return self.ks

    # noinspection PyMethodOverriding
    def values(self):
        return [self[k] for k in self.ks]

    def iteritems(self):
        return iter(self.items())

    def iterkeys(self):
        return iter(self.ks)

    __iter__ = iterkeys

    def itervalues(self):
        return iter(self.values())


# ============================================================================
#
#
#
# ============================================================================
def test():
    od = OrderedDict()
    od['a'] = 'A'
    assert None is od.pop('b', None)

if '__main__' == __name__:
    test()
