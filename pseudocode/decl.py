import token, stmt, dtype, decl
from . import ParseError

class Function:
    def __init__(self, datatype, name, parameters, body):
        self.datatype = datatype
        self.name = name
        self.parameters = parameters
        self.body = body

    def __print__(self, indent):
        print indent + '%s %s(%s)' % (
            str(self.datatype), '.'.join(str(part) for part in self.name),
            ', '.join(str(pt) + ' ' + str(pi) for pt, pi in self.parameters))
        for statement in self.body:
            statement.__print__(indent + '    ')

# parameter :== datatype identifier
# parameter-list :== parameter | parameter-list ',' parameter
# maybe-parameter-list :== <empty> | parameter-list

# declaration :== datatype decl-identifier '(' maybe-parameter-list ')' body

def parse(ts):
    if isinstance(ts.peek(), token.Identifier) and \
          ts.pos + 1 < ts.stop and ts.tokens[ts.pos + 1] == token.PERIOD:
        datatype = dtype.dt_void
    else:
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
    body = stmt.parse_body(ts)
    return decl.Function(datatype, name, parameters, body)
