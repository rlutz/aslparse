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
    def __init__(self, identifier):
        self.identifier = identifier

    def __str__(self):
        return str(self.identifier)

class Void:
    def __str__(self):
        return 'void'

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
        if ts.consume() != token.OPAREN:
            raise ParseError(ts)
        expression = expr.parse_ternary(ts)
        if ts.consume() != token.CPAREN:
            raise ParseError(ts)
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
        if ts.consume() != token.CPAREN:
            raise ParseError(ts)
        return dtype.Compound(partial_types)

    if isinstance(ts.peek(), token.Identifier) or \
       isinstance(ts.peek(), token.LinkedIdentifier):
        return dtype.Custom(ts.consume())

    raise ParseError(ts)
