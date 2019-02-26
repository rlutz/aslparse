import token, expr, stmt, dtype, decl
from . import ParseError

FUNCTION, SETTER, GETTER = xrange(3)

class Function:
    def __init__(self, functype, result_type, result_name,
                       name, overload, parameters, body):
        self.functype = functype
        self.result_type = result_type
        self.result_name = result_name
        self.name = name
        self.overload = overload
        self.parameters = parameters
        self.body = body

    def __print__(self, indent):
        name = '.'.join(str(part) for part in self.name)
        params = ', '.join(str(pt) + ' ' + str(pi)
                           for pt, pi in self.parameters)

        if self.functype == SETTER:
            print indent + '%s[%s] = %s %s%s' % (
                name, params, str(self.result_type), str(self.result_name),
                ';' if self.body is None else '')
        elif self.functype == GETTER:
            print indent + '%s %s[%s]%s' % (
                str(self.result_type), name, params,
                ';' if self.body is None else '')
        else:
            print indent + '%s %s(%s)%s' % (
                str(self.result_type), name, params,
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

class Enumeration:
    def __init__(self, name, values):
        self.name = name
        self.values = values

    def __print__(self, indent):
        print indent + 'enumeration %s {%s};' % (
            self.name, ', '.join(str(value) for value in self.values))

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

    if ts.consume_if(token.rw['enumeration']):
        name = ts.consume()
        if not isinstance(name, token.DeclarationIdentifier):
            raise ParseError(ts)
        if ts.consume() != token.OBRACE:
            raise ParseError(ts)
        values = []
        while True:
            value = ts.consume()
            if not isinstance(value, token.DeclarationIdentifier):
                raise ParseError(ts)
            values.append(value)
            if not ts.consume_if(token.COMMA):
                break
        if ts.consume() != token.CBRACE:
            raise ParseError(ts)
        if ts.consume() != token.SEMICOLON:
            raise ParseError(ts)
        return decl.Enumeration(name, values)


    if (isinstance(ts.peek(), token.Identifier) or
        isinstance(ts.peek(), token.DeclarationIdentifier)) and \
          ts.pos + 1 < ts.stop and (ts.tokens[ts.pos + 1] == token.PERIOD or
                                    ts.tokens[ts.pos + 1] == token.OPAREN or
                                    ts.tokens[ts.pos + 1] == token.OBRACKET):
        result_type = dtype.dt_void
    else:
        result_type = dtype.parse(ts)
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
    if ts.consume_if(token.OPAREN):
        expected_closing = token.CPAREN
        functype = FUNCTION
    elif ts.consume_if(token.OBRACKET):
        expected_closing = token.CBRACKET
        if result_type == dtype.dt_void:
            functype = SETTER
        else:
            functype = GETTER
    else:
        raise ParseError(ts)
    parameters = []
    if ts.peek() != expected_closing:
        while True:
            param_type = dtype.parse(ts)
            t = ts.consume()
            if not isinstance(t, token.Identifier) and \
               not isinstance(t, token.LinkedIdentifier):
                raise ParseError(ts)
            parameters.append((param_type, t))
            if not ts.consume_if(token.COMMA):
                break
    if ts.consume() != expected_closing:
        raise ParseError(ts)
    if functype == SETTER:
        if ts.consume() != token.EQUALS:
            raise ParseError(ts)
        result_type = dtype.parse(ts)
        result_name = ts.consume()
        if not isinstance(result_name, token.Identifier) and \
           not isinstance(result_name, token.LinkedIdentifier):
            raise ParseError(ts)
    else:
        result_name = None
    if ts.consume_if(token.SEMICOLON):
        body = None
    elif isinstance(ts.peek(), list):
        body = stmt.parse_block(ts.consume(), stmt.parse_statement)
    else:
        raise ParseError(ts)
    return decl.Function(functype, result_type, result_name,
                         name, overload, parameters, body)
