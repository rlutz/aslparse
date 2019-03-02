import token, expr, dtype
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
        return 'array[%s..%s] %s' % (str(self.start), str(self.stop),
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
    if ts.consume_if(token.rw['bit']):
        return dtype.dt_bit

    if ts.consume_if(token.rw['bits']):
        ts.consume_assert(token.OPAREN)
        expression = expr.parse_ternary(ts)
        ts.consume_assert(token.CPAREN)
        return dtype.Bits(expression)

    if ts.consume_if(token.rw['boolean']):
        return dtype.dt_boolean

    if ts.consume_if(token.rw['integer']):
        return dtype.dt_integer

    if ts.consume_if(token.OPAREN):
        partial_types = []
        while True:
            partial_types.append(dtype.parse(ts))
            if not ts.consume_if(token.COMMA):
                break
        ts.consume_assert(token.CPAREN)
        return dtype.Compound(partial_types)

    name = []
    while True:
        name.append(ts.consume())
        if not isinstance(name[-1], token.Identifier) and \
           not isinstance(name[-1], token.LinkedIdentifier):
            raise ParseError(ts)
        if isinstance(name[-1], token.LinkedIdentifier) or \
           not ts.consume_if(token.PERIOD):
            break
    return dtype.Custom(name)
