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

from . import token, expr, dtype
from . import ParseError

class Bit:
    def __str__(self):
        return 'bit'

class Bits:
    def __init__(self, expression):
        self.expression = expression

    def __str__(self):
        return 'bits(%s)' % str(self.expression)

class Boolean:
    def __str__(self):
        return 'boolean'

class Integer:
    def __str__(self):
        return 'integer'

class Compound:
    def __init__(self, partial_types):
        self.partial_types = partial_types

    def __str__(self):
        return '(' + ', '.join(str(t) for t in self.partial_types) + ')'

class Custom:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return '.'.join(str(part) for part in self.name)

class Void:
    def __str__(self):
        return 'void'

class Array:
    def __init__(self, base, start, stop):
        self.base = base
        self.start = start
        self.stop = stop

    def __str__(self):
        return 'array [%s..%s] of %s' % (str(self.start), str(self.stop),
                                         str(self.base))

dt_bit = dtype.Bit()
dt_boolean = dtype.Boolean()
dt_integer = dtype.Integer()
dt_void = dtype.Void()

# datatype :== 'bit'
#            | 'bits' '(' expression3 ')'
#            | 'boolean'
#            | 'integer'
#            | '(' datatype-list ')'

# datatype-list :== datatype | datatype-list ',' datatype

def parse(ts):
    if ts.consume_if(token.ReservedWord('array')):
        ts.consume_assert(token.Nonalpha('['))
        start = expr.parse_binary(ts)
        ts.consume_assert(token.Nonalpha('..'))
        stop = expr.parse_binary(ts)
        ts.consume_assert(token.Nonalpha(']'))
        ts.consume_assert(token.ReservedWord('of'))
        base_type = dtype.parse(ts)
        return dtype.Array(base_type, start, stop)

    if ts.consume_if(token.ReservedWord('bit')):
        return dtype.dt_bit

    if ts.consume_if(token.ReservedWord('bits')):
        ts.consume_assert(token.Nonalpha('('))
        expression = expr.parse_ternary(ts)
        ts.consume_assert(token.Nonalpha(')'))
        return dtype.Bits(expression)

    if ts.consume_if(token.ReservedWord('boolean')):
        return dtype.dt_boolean

    if ts.consume_if(token.ReservedWord('integer')):
        return dtype.dt_integer

    if ts.consume_if(token.Nonalpha('(')):
        partial_types = []
        while True:
            partial_types.append(dtype.parse(ts))
            if not ts.consume_if(token.Nonalpha(',')):
                break
        ts.consume_assert(token.Nonalpha(')'))
        return dtype.Compound(partial_types)

    name = []
    while True:
        name.append(ts.consume())
        if not isinstance(name[-1], token.Identifier) and \
           not isinstance(name[-1], token.LinkedIdentifier):
            raise ParseError(ts)
        if isinstance(name[-1], token.LinkedIdentifier) or \
           not ts.consume_if(token.Nonalpha('.')):
            break
    return dtype.Custom(name)
