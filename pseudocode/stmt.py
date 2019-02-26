import token, expr, stmt, dtype, tstream
from . import ParseError

class Assignment:
    def __init__(self, lhs, expression):
        self.lhs = lhs
        self.expression = expression

    def __print__(self, indent):
        print indent + '%s = %s;' % (str(self.lhs), str(self.expression))

class ConstantAssignment:
    def __init__(self, datatype, lhs, expression):
        self.datatype = datatype
        self.lhs = lhs
        self.expression = expression

    def __print__(self, indent):
        print indent + 'constant %s %s = %s;' % (
            str(self.datatype), str(self.lhs), str(self.expression))

class Declaration:
    def __init__(self, datatype, lhs, expression):
        self.datatype = datatype
        self.lhs = lhs
        self.expression = expression

    def __print__(self, indent):
        if self.expression is None:
            print indent + '%s %s;' % (str(self.datatype), str(self.lhs))
        else:
            print indent + '%s %s = %s;' % (
                str(self.datatype), str(self.lhs), str(self.expression))

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

class While:
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def __print__(self, indent):
        print indent + 'while %s do' % str(self.condition)
        for statement in self.body:
            statement.__print__(indent + '    ')

class Repeat:
    def __init__(self, body, condition):
        self.body = body
        self.condition = condition

    def __print__(self, indent):
        print indent + 'repeat'
        for statement in self.body:
            statement.__print__(indent + '    ')
        print indent + 'until %s;' % str(self.condition)

class Case:
    def __init__(self, expression, clauses):
        self.expression = expression
        self.clauses = clauses

    def __print__(self, indent):
        print indent + 'case ' + str(self.expression) + ' of'
        for clause in self.clauses:
            clause.__print__(indent + '    ')

class CaseClause:
    def __init__(self, patterns, body):
        self.patterns = patterns
        self.body = body

    def __print__(self, indent):
        if self.patterns is not None:
            print indent + 'when ' + ', '.join(str(p) for p in self.patterns)
        else:
            print indent + 'otherwise'
        for statement in self.body:
            statement.__print__(indent + '    ')

class Assert:
    def __init__(self, expression):
        self.expression = expression

    def __print__(self, indent):
        print indent + 'assert ' + str(self.expression) + ';'

class Return:
    def __init__(self, value):
        self.value = value

    def __print__(self, indent):
        if self.value is not None:
            print indent + 'return ' + str(self.value) + ';'
        else:
            print indent + 'return;'


# body :== statement | indented-block

def parse_body(ts):
    if isinstance(ts.peek(), list):
        return stmt.parse_block(ts.consume(), stmt.parse_statement)

    return [stmt.parse_statement(ts)]


# if-segment :== expression2 'then' body
#              | expression2 'then' body 'elsif' if-segment
#              | expression2 'then' body 'else' body

def parse_if_segment(ts):
    expression = expr.parse_binary(ts)
    if ts.consume() != token.rw['then']:
        raise ParseError(ts)

    then_body = stmt.parse_body(ts)

    consumed_nl = ts.consume_if(token.NEWLINE)

    if ts.consume_if(token.rw['elsif']):
        else_body = [parse_if_segment(ts)]
    elif ts.consume_if(token.rw['else']):
        else_body = stmt.parse_body(ts)
    elif consumed_nl:
        raise ParseError(ts)
    else:
        else_body = []

    return stmt.If(expression, then_body, else_body)


# case-pattern :== identifier | number | bitvector
# case-pattern-list :== case-pattern | case-pattern ',' case-pattern-list

# case-clause :== 'when' case-pattern body
# case-clause-list :== case-clause
#                    | case-clause case-clause-list
#                    | 'otherwise' body

def parse_case_clause(ts):
    if ts.consume_if(token.rw['when']):
        patterns = []
        while True:
            pattern = ts.consume()
            if not isinstance(pattern, token.Identifier) and \
               not isinstance(pattern, token.LinkedIdentifier) and \
               not isinstance(pattern, token.Number) and \
               not isinstance(pattern, token.HexadecimalNumber) and \
               not isinstance(pattern, token.Bitvector):
                raise ParseError(ts)
            patterns.append(pattern)
            if not ts.consume_if(token.COMMA):
                break
    elif ts.consume_if(token.rw['otherwise']):
        patterns = None
    else:
        raise ParseError(ts)

    if isinstance(ts.peek(), list):
        body = stmt.parse_block(ts.consume(), stmt.parse_statement)
    else:
        body = []
        while True:
            body.append(stmt.parse_statement(ts))
            if ts.maybe_peek() is None:
                break

    if patterns is None and not (
            ts.stop == len(ts.tokens) or
            ts.stop == len(ts.tokens) - 1 and ts.tokens[-1] == token.NEWLINE):
        raise ParseError(ts)
    return stmt.CaseClause(patterns, body)


# statement :== 'if' if-segment
#             | 'for' identifier '=' expression2 'to' expression2 body
#             | 'case' expression2 'of' BEGIN case-clause-list END
#             | 'SEE' string ';'
#             | 'UNDEFINED' ';'
#             | 'UNPREDICTABLE' ';'
#             | 'assert' expression2 ';'
#             | 'return' ';'
#             | 'return' expression2 ';'
#             | datatype assignable ';'
#             | datatype assignable '=' expression3 ';'
#             | assignable '=' expression3 ';'
#             | 'constant' datatype assignable '=' expression3 ';'
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
        start = expr.parse_binary(ts)
        if ts.consume() != token.rw['to']:
            raise ParseError(ts)
        stop = expr.parse_binary(ts)
        body = stmt.parse_body(ts)
        return stmt.For(var, start, stop, body)

    if ts.consume_if(token.rw['while']):
        condition = expr.parse_binary(ts)
        if ts.consume() != token.rw['do']:
            raise ParseError(ts)
        body = stmt.parse_body(ts)
        return stmt.While(condition, body)

    if ts.consume_if(token.rw['repeat']):
        if not isinstance(ts.peek(), list):
            raise ParseError(ts)
        body = stmt.parse_block(ts.consume(), stmt.parse_statement)
        if ts.consume() != token.rw['until']:
            raise ParseError(ts)
        condition = expr.parse_binary(ts)
        if ts.consume() != token.SEMICOLON:
            raise ParseError(ts)
        return stmt.Repeat(body, condition)

    if ts.consume_if(token.rw['case']):
        expression = expr.parse_binary(ts)
        if ts.consume() != token.rw['of']:
            raise ParseError(ts)
        if not isinstance(ts.peek(), list):
            raise ParseError(ts)
        clauses = stmt.parse_block(ts.consume(), parse_case_clause)
        return stmt.Case(expression, clauses)

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

    if ts.consume_if(token.rw['assert']):
        expression = expr.parse_binary(ts)
        if ts.consume() != token.SEMICOLON:
            raise ParseError(ts)
        return stmt.Assert(expression)

    if ts.consume_if(token.rw['return']):
        if ts.peek() == token.SEMICOLON:
            value = None
        else:
            value = expr.parse_binary(ts)
        if ts.consume() != token.SEMICOLON:
            raise ParseError(ts)
        return stmt.Return(value)

    if ts.consume_if(token.rw['constant']):
        datatype = dtype.parse(ts)
        lhs = expr.parse_identifier_chain(ts)
        if ts.consume() != token.EQUALS:
            raise ParseError(ts)
        expression = expr.parse_ternary(ts)
        if ts.consume() != token.SEMICOLON:
            raise ParseError(ts)
        return stmt.ConstantAssignment(datatype, lhs, expression)

    sub_ts = ts.fork()
    try:
        datatype = dtype.parse(sub_ts)
        lhs = expr.parse_identifier_chain(sub_ts)
        if sub_ts.consume_if(token.EQUALS):
            expression = expr.parse_ternary(sub_ts)
        else:
            expression = None
        if sub_ts.consume() != token.SEMICOLON:
            raise ParseError(sub_ts)
    except ParseError:
        ts.abandon(sub_ts)
    else:
        ts.become(sub_ts)
        return stmt.Declaration(datatype, lhs, expression)


    lhs = expr.parse_assignable(ts)

    if ts.consume_if(token.OPAREN):
        if ts.peek() != token.CPAREN:
            args = expr.parse_list(ts)
        else:
            args = []
        if ts.consume() != token.CPAREN:
            raise ParseError(ts)
        if ts.consume() != token.SEMICOLON:
            raise ParseError(ts)
        return stmt.FunctionCall(lhs, args)

    if ts.consume() != token.EQUALS:
        raise ParseError(ts)
    expression = expr.parse_ternary(ts)
    if ts.consume() != token.SEMICOLON:
        raise ParseError(ts)
    return stmt.Assignment(lhs, expression)



# statements :== <empty> | statement statements
# indented-block :== BEGIN statements END

def parse_block(tokens, parse_func):
    assert isinstance(tokens, list)
    statements = []
    start = 0
    while start < len(tokens):
        pos = start
        while True:
            t = tokens[pos]
            pos += 1

            if isinstance(t, list):
                if pos < len(tokens) and (tokens[pos] == token.rw['elsif'] or
                                          tokens[pos] == token.rw['else'] or
                                          tokens[pos] == token.rw['until']):
                    continue
                break

            if pos == len(tokens):
                if tokens[0] == token.rw['type']:
                    break
                raise ParseError(tstream.TokenStream(tokens, pos, pos))

            if t == token.SEMICOLON:
                if tokens[start] == token.rw['when'] or \
                   tokens[start] == token.rw['otherwise']:
                    if tokens[pos] == token.NEWLINE:
                        pos += 1
                        break
                    continue

                if tokens[pos] == token.NEWLINE:
                    pos += 1

                if pos < len(tokens) and (tokens[pos] == token.rw['elsif'] or
                                          tokens[pos] == token.rw['else'] or
                                          tokens[pos] == token.rw['until']):
                    continue
                break

        if tokens[pos - 1] == token.NEWLINE:
            statements.append(tstream.parse(tokens, start, pos - 1, parse_func))
        else:
            statements.append(tstream.parse(tokens, start, pos, parse_func))
        start = pos

    return statements
