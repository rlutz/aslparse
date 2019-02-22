__all__ = ['token', 'expr', 'stmt', 'tstream']

class ParseError(Exception):
    def __init__(self, ts):
        self.ts = ts
