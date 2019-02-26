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
        if self.parameters is None:
            params = None
        else:
            params = ', '.join(str(pt) + ' ' + str(pi)
                               for pt, pi in self.parameters)

        if self.functype == SETTER:
            if params is not None:
                params = '[%s]' % params
            else:
                params = ''
            print indent + '%s%s = %s %s%s' % (
                name, params, str(self.result_type), str(self.result_name),
                ';' if self.body is None else '')
        elif self.functype == GETTER:
            if params is not None:
                params = '[%s]' % params
            else:
                params = ''
            print indent + '%s %s%s%s' % (
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

class Array:
    def __init__(self, datatype, name):
        self.datatype = datatype
        self.name = name

    def __print__(self, indent):
        print indent + '%s %s;' % (
            str(self.datatype), '.'.join(str(part) for part in self.name))

class Enumeration:
    def __init__(self, name, values):
        self.name = name
        self.values = values

    def __print__(self, indent):
        print indent + 'enumeration %s {%s\n};' % (
            self.name, ','.join('\n' + indent + '    ' + str(value)
                                for value in self.values))

class Type:
    def __init__(self, name, fields):
        self.name = name
        self.fields = fields

    def __print__(self, indent):
        if self.fields is None:
            print indent + 'type %s;' % '.'.join(str(part)
                                                 for part in self.name)
            return
        print indent + 'type ' + '.'.join(str(part) for part in self.name) \
            + ' is ('
        for i, field in enumerate(self.fields):
            field_type, field_identifier = field
            print indent + '    %s %s%s' % (
                str(field_type),
                str(field_identifier),
                ',' if i != len(self.fields) - 1 else '')
        print indent + ')'

# parameter :== datatype identifier
# parameter-list :== parameter | parameter-list ',' parameter
# maybe-parameter-list :== <empty> | parameter-list

# value-list :== identifier | value-list ',' identifier

# declaration :== datatype decl-identifier '(' maybe-parameter-list ')' ';'
#               | datatype decl-identifier '(' maybe-parameter-list ')' body
#               | datatype decl-identifier ';'
#               | datatype decl-identifier body
#               | datatype decl-identifier '[' maybe-parameter-list ']' ';'
#               | datatype decl-identifier '[' maybe-parameter-list ']' body
#               | decl-identifier '=' datatype identifier ';'
#               | decl-identifier '=' datatype identifier body
#               | decl-identifier '[' maybe-parameter-list ']'
#                     '=' datatype identifier ';'
#               | decl-identifier '[' maybe-parameter-list ']'
#                     '=' datatype identifier body
#               | 'constant' datatype identifier-chain '=' expression3 ';'
#               | 'enumeration' identifier-chain '{' value-list '}' ';'
#               | 'type' identifier-chain ';'
#               | 'type' identifier-chain 'is' '(' parameter-list ')'
#               | 'array' datatype identifier-chain
#                     '[' expression2 '..' expression2 ']' ';'

def parse_name(ts):
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
        if not ts.consume_if(token.PERIOD):
            overload = True
            break
    return name, overload

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

    if ts.consume_if(token.rw['type']):
        name, overload = parse_name(ts)
        if overload:
            raise ParseError(ts)
        if ts.consume_if(token.SEMICOLON):
            return decl.Type(name, None)
        if ts.consume() != token.rw['is']:
            raise ParseError(ts)
        if ts.consume() != token.OPAREN:
            raise ParseError(ts)
        fields = []
        while True:
            field_type = dtype.parse(ts)
            t = ts.consume()
            if not isinstance(t, token.Identifier):
                raise ParseError(ts)
            fields.append((field_type, t))
            if not ts.consume_if(token.COMMA):
                break
        if ts.consume() != token.CPAREN:
            raise ParseError(ts)
        return decl.Type(name, fields)

    if ts.consume_if(token.rw['array']):
        base_type = dtype.parse(ts)
        name = []
        while True:
            name.append(ts.consume())
            if not isinstance(name[-1], token.Identifier):
                raise ParseError(ts)
            if not ts.consume_if(token.PERIOD):
                break
        if ts.consume() != token.OBRACKET:
            raise ParseError(ts)
        start = expr.parse_binary(ts)
        if ts.consume() != token.DOUBLE_PERIOD:
            raise ParseError(ts)
        stop = expr.parse_binary(ts)
        if ts.consume() != token.CBRACKET:
            raise ParseError(ts)
        if ts.consume() != token.SEMICOLON:
            raise ParseError(ts)
        return decl.Array(dtype.Array(base_type, start, stop), name)


    if isinstance(ts.peek(), token.DeclarationIdentifier) and \
       ts.peek().name == 'ElemP':
        ts.pos = ts.stop
        class Dummy:
            def __print__(self, indent):
                print indent + '// skipping ElemP setter'
        return Dummy()


    sub_ts = ts.fork()
    try:
        result_type = dtype.parse(sub_ts)
        name, overload = parse_name(sub_ts)
    except ParseError:
        ts.abandon(sub_ts)
        result_type = dtype.dt_void
        name, overload = parse_name(ts)
    else:
        ts.become(sub_ts)

    if ts.consume_if(token.OPAREN):
        expected_closing = token.CPAREN
        functype = FUNCTION
    else:
        if ts.consume_if(token.OBRACKET):
            expected_closing = token.CBRACKET
        else:
            expected_closing = None
        if result_type == dtype.dt_void:
            functype = SETTER
        else:
            functype = GETTER
    if expected_closing is not None:
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
    else:
        parameters = None
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
