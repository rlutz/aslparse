# Parser and resolver for ARM ASL pseudocode
# Copyright (C) 2019, 2021-2022 Roland Lutz
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from . import ParseError

class TokenStream:
    def __init__(self, tokens, start, stop):
        self.tokens = tokens
        self.pos = start
        self.stop = stop
        assert stop >= start
        self.forks = set()

    def consume(self):
        if self.pos == self.stop:
            raise ParseError(self)
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

    def consume_assert(self, expected):
        if self.pos == self.stop:
            raise ParseError(self)
        if self.tokens[self.pos] != expected:
            raise ParseError(self)
        self.pos += 1

    def peek(self):
        if self.pos == self.stop:
            raise ParseError(self)
        return self.tokens[self.pos]

    def maybe_peek(self):
        if self.pos == self.stop:
            return None
        return self.tokens[self.pos]

    def fork(self):
        sub_ts = TokenStream(self.tokens, self.pos, self.stop)
        self.forks.add(sub_ts)
        return sub_ts

    def abandon(self, sub_ts):
        self.forks.remove(sub_ts)

    def become(self, sub_ts):
        self.pos = sub_ts.pos
        self.forks.remove(sub_ts)

def parse(tokens, start, stop, parse_func):
    ts = TokenStream(tokens, start, stop)
    result = parse_func(ts)
    if ts.pos != stop:
        raise ParseError(ts)
    if ts.forks:
        raise ParseError(ts)
    return result
