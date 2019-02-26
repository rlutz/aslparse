import token, expr, stmt, dtype, decl
from . import ParseError

class Function:
    def __init__(self, datatype, name, overload, parameters, body):
        self.datatype = datatype
        self.name = name
        self.overload = overload
        self.parameters = parameters
        self.body = body

    def __print__(self, indent):
        print indent + '%s %s(%s)%s' % (
            str(self.datatype), '.'.join(str(part) for part in self.name),
            ', '.join(str(pt) + ' ' + str(pi) for pt, pi in self.parameters),
            ';' if self.body is None else '')
        if self.body is not None:
            for statement in self.body:
                statement.__print__(indent + '    ')

class Constant:
    def __init__(self, datatype, name, expression):
        self.datatype = datatype
        self.name = name
        self.expression = expression

    def __print__(self, indent):
        print indent + 'constant %s %s = %s;' % (
            str(self.datatype), '.'.join(str(part) for part in self.name),
            str(self.expression))

# parameter :== datatype identifier
# parameter-list :== parameter | parameter-list ',' parameter
# maybe-parameter-list :== <empty> | parameter-list

# declaration :== datatype decl-identifier '(' maybe-parameter-list ')' body

def parse(ts):
    if ts.consume_if(token.rw['constant']):
        datatype = dtype.parse(ts)
        name = []
        while True:
            name.append(ts.consume())
            if isinstance(name[-1], token.DeclarationIdentifier):
                break
            if not isinstance(name[-1], token.Identifier):
                raise ParseError(ts)
            if ts.consume() != token.PERIOD:
                raise ParseError(ts)
        if ts.consume() != token.EQUALS:
            raise ParseError(ts)
        expression = expr.parse_ternary(ts)
        if ts.consume() != token.SEMICOLON:
            raise ParseError(ts)
        return decl.Constant(datatype, name, expression)


    if (isinstance(ts.peek(), token.Identifier) or
        isinstance(ts.peek(), token.DeclarationIdentifier)) and \
          ts.pos + 1 < ts.stop and (ts.tokens[ts.pos + 1] == token.PERIOD or
                                    ts.tokens[ts.pos + 1] == token.OPAREN):
        datatype = dtype.dt_void
    else:
        datatype = dtype.parse(ts)
    name = []
    while True:
        name.append(ts.consume())
        if isinstance(name[-1], token.DeclarationIdentifier):
            overload = False
            break
        if isinstance(name[-1], token.LinkedIdentifier):
            overload = True
            break
        if not isinstance(name[-1], token.Identifier):
            raise ParseError(ts)
        if ts.consume() != token.PERIOD:
            raise ParseError(ts)
    if ts.consume() != token.OPAREN:
        raise ParseError(ts)
    parameters = []
    if ts.peek() != token.CPAREN:
        while True:
            param_type = dtype.parse(ts)
            t = ts.consume()
            if not isinstance(t, token.Identifier) and \
               not isinstance(t, token.LinkedIdentifier):
                raise ParseError(ts)
            parameters.append((param_type, t))
            if not ts.consume_if(token.COMMA):
                break
    if ts.consume() != token.CPAREN:
        raise ParseError(ts)
    if ts.consume_if(token.SEMICOLON):
        body = None
    elif isinstance(ts.peek(), list):
        body = stmt.parse_block(ts.consume(), stmt.parse_statement)
    else:
        raise ParseError(ts)
    return decl.Function(datatype, name, overload, parameters, body)
