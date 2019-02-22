import token, expr, stmt, tstream
from . import ParseError

class Assignment:
    def __init__(self, lhs, expression):
        self.lhs = lhs
        self.expression = expression

    def __print__(self, indent):
        print indent + '%s = %s;' % (str(self.lhs), str(self.expression))

class FunctionCall:
    def __init__(self, func, args):
        self.func = func
        self.args = args

    def __print__(self, indent):
        print indent + str(self.func) + '(' + \
            ', '.join(str(arg) for arg in self.args) + ');'

class See:
    def __init__(self, target):
        self.target = target

    def __print__(self, indent):
        print indent + 'SEE "%s";' % self.target

class Undefined:
    def __print__(self, indent):
        print indent + 'UNDEFINED;'

class Unpredictable:
    def __print__(self, indent):
        print indent + 'UNPREDICTABLE;'

class If:
    def __init__(self, expression, then_body, else_body):
        self.expression = expression
        self.then_body = then_body
        self.else_body = else_body

    def __print__(self, indent):
        statement = self
        print indent + 'if %s then' % str(statement.expression)

        while True:
            for s in statement.then_body:
                s.__print__(indent + '    ')

            if not statement.else_body:
                break

            if len(statement.else_body) != 1 or \
               not isinstance(statement.else_body[0], stmt.If):
                print indent + 'else'
                for s in statement.else_body:
                    s.__print__(indent + '    ')
                break

            statement = statement.else_body[0]
            print indent + 'elsif %s then' % str(statement.expression)

class For:
    def __init__(self, var, start, stop, body):
        self.var = var
        self.start = start
        self.stop = stop
        self.body = body

    def __print__(self, indent):
        print indent + 'for %s = %s to %s' % (
            str(self.var), str(self.start), str(self.stop))
        for statement in self.body:
            statement.__print__(indent + '    ')


# body :== statement | indented-block

def parse_body(ts):
    if isinstance(ts.peek(), list):
        return stmt.parse_block(ts.consume())

    return [stmt.parse_statement(ts)]


# if-segment :== expression2 'then' body
#              | expression2 'then' body 'elsif' if-segment
#              | expression2 'then' body 'else' body

def parse_if_segment(ts):
    expression = expr.parse2(ts)
    if ts.consume() != token.rw['then']:
        raise ParseError(ts)

    then_body = stmt.parse_body(ts)

    if ts.consume_if(token.rw['elsif']):
        else_body = [parse_if_segment(ts)]
    elif ts.consume_if(token.rw['else']):
        else_body = stmt.parse_body(ts)
    else:
        else_body = []

    return stmt.If(expression, then_body, else_body)


# statement :== 'if' if-segment
#             | 'for' identifier '=' expression2 'to' expression2 body
#             | 'UNDEFINED' ';'
#             | 'UNPREDICTABLE' ';'
#             | expression0 '=' expression3 ';'
#             | identifier-chain '(' maybe-expression-list ')' ';'

def parse_statement(ts):
    if ts.consume_if(token.rw['if']):
        return parse_if_segment(ts)

    if ts.consume_if(token.rw['for']):
        var = ts.consume()
        if not isinstance(var, token.Identifier) and \
           not isinstance(var, token.LinkedIdentifier):
            raise ParseError(ts)
        if ts.consume() != token.EQUALS:
            raise ParseError(ts)
        start = expr.parse2(ts)
        if ts.consume() != token.rw['to']:
            raise ParseError(ts)
        stop = expr.parse2(ts)
        body = stmt.parse_body(ts)
        return stmt.For(var, start, stop, body)

    if ts.consume_if(token.rw['SEE']):
        s = ts.consume()
        if not isinstance(s, token.String):
            raise ParseError(ts)
        if ts.consume() != token.SEMICOLON:
            raise ParseError(ts)
        return stmt.See(s.data)

    if ts.consume_if(token.rw['UNDEFINED']):
        if ts.consume() != token.SEMICOLON:
            raise ParseError(ts)
        return stmt.Undefined()

    if ts.consume_if(token.rw['UNPREDICTABLE']):
        if ts.consume() != token.SEMICOLON:
            raise ParseError(ts)
        return stmt.Unpredictable()


    t = ts.consume()
    if not isinstance(t, token.Identifier) and \
       not isinstance(t, token.LinkedIdentifier):
        raise ParseError(ts)
    chain = [t]

    while ts.consume_if(token.PERIOD):
        t = ts.consume()
        if not isinstance(t, token.Identifier) and \
           not isinstance(t, token.LinkedIdentifier):
            raise ParseError(ts)
        chain.append(t)

    expression = expr.Identifier(chain)

    if ts.consume_if(token.OPAREN):
        if ts.peek() != token.CPAREN:
            args = expr.parse_list(ts)
        else:
            args = []
        if ts.consume() != token.CPAREN:
            raise ParseError(ts)
        if ts.consume() != token.SEMICOLON:
            raise ParseError(ts)
        return stmt.FunctionCall(expression, args)

    # not a function call either? -> has to be an assignment

    if ts.consume_if(token.OBRACKET):
        if ts.peek() != token.CBRACKET:
            args = expr.parse_list(ts)
        else:
            args = []
        if ts.consume() != token.CBRACKET:
            raise ParseError(ts)
        expression = expr.Arguments(expression, '[]', args)

    if ts.consume() != token.EQUALS:
        raise ParseError(ts)

    lhs = expression
    expression = expr.parse3(ts)
    if ts.consume() != token.SEMICOLON:
        raise ParseError(ts)(ts)
    return stmt.Assignment(lhs, expression)



# statements :== <empty> | statement statements
# indented-block :== BEGIN statements END

def parse_block(tokens):
    statements = []
    start = 0
    while start < len(tokens):
        pos = start
        while True:
            t = tokens[pos]
            pos += 1
            if t == token.SEMICOLON or isinstance(t, list):
                if pos == len(tokens):
                    break
                t = tokens[pos]
                if t != token.rw['elsif'] and t != token.rw['else']:
                    break
            if pos == len(tokens):
                raise ParseError(None)

        statements.append(tstream.parse(
            tokens, start, pos, stmt.parse_statement))
        start = pos

    return statements
