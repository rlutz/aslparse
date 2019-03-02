__all__ = ['token', 'expr', 'stmt', 'dtype', 'decl', 'tstream', 'ns']

class LexError(Exception):
    def __init__(self, data, pos):
        self.data = data
        self.pos = pos

    def report(self):
        import sys, os, traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()

        cwd = os.getcwd()
        if not cwd.endswith('/'):
            cwd = cwd + '/'

        for fn, lineno, func, text in traceback.extract_tb(exc_traceback):
            if fn.startswith(cwd):
                fn = fn[len(cwd):]
            print '%-26s%-18s%s' % ('%s:%s' % (fn, lineno), func, text[:36])
        del exc_traceback  # avoid circular reference

        start = 0
        while True:
            try:
                p = self.data.index('\n', start) + 1
            except ValueError:
                break
            if p >= self.pos:
                break
            start = p
        try:
            stop = self.data.index('\n', start)
        except ValueError:
            stop = len(self.data)

        print
        print self.data[start:stop]
        print ' ' * (self.pos - start) + '^'

class ParseError(Exception):
    def __init__(self, ts):
        self.ts = ts

    def report(self):
        import sys, os, traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()

        #print 'Traceback (most recent call last):'
        #traceback.print_tb(exc_traceback)

        cwd = os.getcwd()
        if not cwd.endswith('/'):
            cwd = cwd + '/'

        for fn, lineno, func, text in traceback.extract_tb(exc_traceback):
            if fn.startswith(cwd):
                fn = fn[len(cwd):]
            print '%-26s%-18s%s' % ('%s:%s' % (fn, lineno), func, text[:36])
        del exc_traceback  # avoid circular reference

        print
        for i, t in enumerate(self.ts.tokens):
            if i == self.ts.pos:
                print '###',
            else:
                print '   ',
            if isinstance(t, list):
                print ' '.join('[...]' if isinstance(t1, list) else str(t1)
                               for t1 in t[:10]) \
                          + (' ...' if len(t) > 10 else '')
            else:
                print str(t)
