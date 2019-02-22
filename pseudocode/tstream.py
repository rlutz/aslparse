class TokenStream:
    def __init__(self, tokens, start, stop):
        self.tokens = tokens
        self.pos = start
        self.stop = stop
        assert stop >= start

    def consume(self):
        if self.pos == self.stop:
            raise ParseError
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def consume_if(self, expected):
        if self.pos == self.stop:
            return False
        if self.tokens[self.pos] != expected:
            return False
        self.pos += 1
        return True

    def peek(self):
        if self.pos == self.stop:
            raise ParseError
        return self.tokens[self.pos]

    def maybe_peek(self):
        if self.pos == self.stop:
            return None
        return self.tokens[self.pos]

def parse(tokens, start, stop, parse_func):
    ts = TokenStream(tokens, start, stop)
    result = parse_func(ts)
    if ts.pos != stop:
        raise ParseError
    return result
