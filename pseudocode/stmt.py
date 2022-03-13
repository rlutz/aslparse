from . import token, expr, stmt, dtype, decl, tstream
from . import ParseError

class Assignment:
    def __init__(self, lhs, expression):
        self.lhs = lhs
        self.expression = expression

    def __print__(self, indent):
        print(indent + '%s = %s;' % (str(self.lhs), str(self.expression)))

class ConstantAssignment:
    def __init__(self, datatype, lhs, expression):
        self.datatype = datatype
        self.lhs = lhs
        self.expression = expression

    def __print__(self, indent):
        print(indent + 'constant %s %s = %s;' % (
            str(self.datatype), str(self.lhs), str(self.expression)))

class Declaration:
    def __init__(self, datatype, variables):
        self.datatype = datatype
        self.variables = variables

    def __print__(self, indent):
        variables = ', '.join('%s = %s' % (str(lhs), str(expression))
                              if expression is not None else str(lhs)
                              for lhs, expression in self.variables)
        print(indent + '%s %s;' % (str(self.datatype), variables))

class FunctionCall:
    def __init__(self, func, args):
        self.func = func
        self.args = args

    def __print__(self, indent):
        print(indent + str(self.func) + '(' +
            ', '.join(str(arg) for arg in self.args) + ');')

class See:
    def __init__(self, target):
        self.target = target

    def __print__(self, indent):
        print(indent + 'SEE "%s";' % self.target)

class Undefined:
    def __print__(self, indent):
        print(indent + 'UNDEFINED;')

class Unpredictable:
    def __print__(self, indent):
        print(indent + 'UNPREDICTABLE;')

class ImplementationDefined:
    def __init__(self, aspect):
        self.aspect = aspect

    def __print__(self, indent):
        print(indent + 'IMPLEMENTATION_DEFINED "%s"' % self.aspect)

class If:
    def __init__(self, expression, then_body, else_body):
        self.expression = expression
        self.then_body = then_body
        self.else_body = else_body

    def __print__(self, indent):
        statement = self
        print(indent + 'if %s then' % str(statement.expression))

        while True:
            if not statement.then_body:
                print(indent + '    // empty body')
            for s in statement.then_body:
                s.__print__(indent + '    ')

            if not statement.else_body:
                break

            if len(statement.else_body) != 1 or \
               not isinstance(statement.else_body[0], stmt.If):
                print(indent + 'else')
                if not statement.else_body:
                    print(indent + '    // empty body')
                for s in statement.else_body:
                    s.__print__(indent + '    ')
                break

            statement = statement.else_body[0]
            print(indent + 'elsif %s then' % str(statement.expression))

class For:
    def __init__(self, var, start, down, stop, body):
        self.var = var
        self.start = start
        self.down = down
        self.stop = stop
        self.body = body

    def __print__(self, indent):
        print(indent + 'for %s = %s %s %s' % (
            str(self.var), str(self.start), 'downto' if self.down else 'to',
            str(self.stop)))
        if not self.body:
            print(indent + '    // empty body')
        for statement in self.body:
            statement.__print__(indent + '    ')

class While:
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def __print__(self, indent):
        print(indent + 'while %s do' % str(self.condition))
        if not self.body:
            print(indent + '    // empty body')
        for statement in self.body:
            statement.__print__(indent + '    ')

class Repeat:
    def __init__(self, body, condition):
        self.body = body
        self.condition = condition

    def __print__(self, indent):
        print(indent + 'repeat')
        if not self.body:
            print(indent + '    // empty body')
        for statement in self.body:
            statement.__print__(indent + '    ')
        print(indent + 'until %s;' % str(self.condition))

class Case:
    def __init__(self, expression, clauses):
        self.expression = expression
        self.clauses = clauses

    def __print__(self, indent):
        print(indent + 'case ' + str(self.expression) + ' of')
        if not self.clauses:
            print(indent + '    // no clauses')
        for clause in self.clauses:
            clause.__print__(indent + '    ')

class CaseClause:
    def __init__(self, patterns, body):
        self.patterns = patterns
        self.body = body

    def __print__(self, indent):
        if self.patterns is not None:
            print(indent + 'when ' + ', '.join(str(p) for p in self.patterns))
        else:
            print(indent + 'otherwise')
        if not self.body:
            print(indent + '    // empty body')
        for statement in self.body:
            statement.__print__(indent + '    ')

class Assert:
    def __init__(self, expression):
        self.expression = expression

    def __print__(self, indent):
        print(indent + 'assert ' + str(self.expression) + ';')

class Return:
    def __init__(self, value):
        self.value = value

    def __print__(self, indent):
        if self.value is not None:
            print(indent + 'return ' + str(self.value) + ';')
        else:
            print(indent + 'return;')

class LocalDeclaration:
    def __init__(self, decl):
        self.decl = decl

    def __print__(self, indent):
        self.decl.__print__(indent)


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
    ts.consume_assert(token.ReservedWord('then'))

    then_body = stmt.parse_body(ts)

    consumed_nl = ts.consume_if(token.NEWLINE)

    if ts.consume_if(token.ReservedWord('elsif')):
        else_body = [parse_if_segment(ts)]
    elif ts.consume_if(token.ReservedWord('else')):
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
    if ts.consume_if(token.ReservedWord('when')):
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
    elif ts.consume_if(token.ReservedWord('otherwise')):
        patterns = None
    else:
        raise ParseError(ts)

    if ts.maybe_peek() == None:
        body = []
    elif isinstance(ts.peek(), list):
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


# variable-def :== identifier-chain
#                | identifier-chain '=' expression3
# variable-def-list :== variable-def | variable-def-list ',' variable-def

# statement :== 'if' if-segment
#             | 'for' identifier '=' expression2 'to' expression2 body
#             | 'for' identifier '=' expression2 'downto' expression2 body
#             | 'while' expression2 'do' body
#             | 'repeat' body 'until' expression2 ';'
#             | 'case' expression2 'of' BEGIN case-clause-list END
#             | 'SEE' string ';'
#             | 'UNDEFINED' ';'
#             | 'UNPREDICTABLE' ';'
#             | 'IMPLEMENTATION_DEFINED' string ';'
#             | 'assert' expression3 ';'
#             | 'return' ';'
#             | 'return' expression3 ';'
#             | datatype variable-def-list ';'
#             | 'constant' datatype variable-def ';'
#             | assignable '=' expression3 ';'
#             | identifier-chain '(' maybe-expression-list ')' ';'

def parse_statement(ts):
    if ts.consume_if(token.ReservedWord('if')):
        return parse_if_segment(ts)

    if ts.consume_if(token.ReservedWord('for')):
        var = ts.consume()
        if not isinstance(var, token.Identifier) and \
           not isinstance(var, token.LinkedIdentifier):
            raise ParseError(ts)
        ts.consume_assert(token.EQUALS)
        start = expr.parse_binary(ts)
        if ts.consume_if(token.ReservedWord('to')):
            down = False
        elif ts.consume_if(token.ReservedWord('downto')):
            down = True
        else:
            raise ParseError(ts)
        stop = expr.parse_binary(ts)
        body = stmt.parse_body(ts)
        return stmt.For(expr.Identifier(var), start, down, stop, body)

    if ts.consume_if(token.ReservedWord('while')):
        condition = expr.parse_binary(ts)
        ts.consume_assert(token.ReservedWord('do'))
        body = stmt.parse_body(ts)
        return stmt.While(condition, body)

    if ts.consume_if(token.ReservedWord('repeat')):
        if not isinstance(ts.peek(), list):
            raise ParseError(ts)
        body = stmt.parse_block(ts.consume(), stmt.parse_statement)
        ts.consume_assert(token.ReservedWord('until'))
        condition = expr.parse_binary(ts)
        ts.consume_assert(token.SEMICOLON)
        return stmt.Repeat(body, condition)

    if ts.consume_if(token.ReservedWord('case')):
        expression = expr.parse_binary(ts)
        ts.consume_assert(token.ReservedWord('of'))
        if not isinstance(ts.peek(), list):
            raise ParseError(ts)
        clauses = stmt.parse_block(ts.consume(), parse_case_clause)
        return stmt.Case(expression, clauses)

    if ts.consume_if(token.ReservedWord('SEE')):
        s = ts.consume()
        if not isinstance(s, token.String):
            raise ParseError(ts)
        ts.consume_assert(token.SEMICOLON)
        return stmt.See(s.data)

    if ts.consume_if(token.ReservedWord('UNDEFINED')):
        ts.consume_assert(token.SEMICOLON)
        return stmt.Undefined()

    if ts.consume_if(token.ReservedWord('UNPREDICTABLE')):
        ts.consume_assert(token.SEMICOLON)
        return stmt.Unpredictable()

    if ts.consume_if(token.ReservedWord('IMPLEMENTATION_DEFINED')):
        if not isinstance(ts.peek(), token.String):
            raise ParseError(ts)
        aspect = ts.consume().data
        ts.consume_assert(token.SEMICOLON)
        return stmt.ImplementationDefined(aspect)

    if ts.consume_if(token.ReservedWord('assert')):
        expression = expr.parse_ternary(ts)
        ts.consume_assert(token.SEMICOLON)
        return stmt.Assert(expression)

    if ts.consume_if(token.ReservedWord('return')):
        if ts.peek() == token.SEMICOLON:
            value = None
        else:
            value = expr.parse_ternary(ts)
        ts.consume_assert(token.SEMICOLON)
        return stmt.Return(value)

    if ts.consume_if(token.ReservedWord('constant')):
        datatype = dtype.parse(ts)
        lhs = expr.parse_identifier_chain(ts)
        ts.consume_assert(token.EQUALS)
        expression = expr.parse_ternary(ts)
        ts.consume_assert(token.SEMICOLON)
        return stmt.ConstantAssignment(datatype, lhs, expression)

    if ts.peek() == token.ReservedWord('enumeration'):
        return stmt.LocalDeclaration(decl.parse(ts))

    sub_ts = ts.fork()
    try:
        datatype = dtype.parse(sub_ts)
        variables = []
        while True:
            lhs = expr.parse_identifier_chain(sub_ts)
            if sub_ts.consume_if(token.EQUALS):
                variables.append((lhs, expr.parse_ternary(sub_ts)))
            else:
                variables.append((lhs, None))
            if not sub_ts.consume_if(token.COMMA):
                break
        sub_ts.consume_assert(token.SEMICOLON)
    except ParseError:
        ts.abandon(sub_ts)
    else:
        ts.become(sub_ts)
        return stmt.Declaration(datatype, variables)


    lhs = expr.parse_assignable(ts)

    if ts.consume_if(token.OPAREN):
        if ts.peek() != token.CPAREN:
            args = expr.parse_list(ts)
        else:
            args = []
        ts.consume_assert(token.CPAREN)
        ts.consume_assert(token.SEMICOLON)
        return stmt.FunctionCall(lhs, args)

    ts.consume_assert(token.EQUALS)
    expression = expr.parse_ternary(ts)
    ts.consume_assert(token.SEMICOLON)
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
                if pos < len(tokens) and (
                        tokens[pos] == token.ReservedWord('elsif') or
                        tokens[pos] == token.ReservedWord('else') or
                        tokens[pos] == token.ReservedWord('until')):
                    continue
                break

            if pos == len(tokens) or t == token.NEWLINE:
                if tokens[0] == token.Identifier('type'):
                    break
                if tokens[0] == token.ReservedWord('when'):
                    # empty case clause
                    break
                raise ParseError(tstream.TokenStream(tokens, pos, pos))

            if t == token.SEMICOLON:
                if tokens[start] == token.ReservedWord('when') or \
                   tokens[start] == token.ReservedWord('otherwise'):
                    if pos < len(tokens) and tokens[pos] == token.NEWLINE:
                        pos += 1
                        break
                    continue

                if pos < len(tokens) and tokens[pos] == token.NEWLINE:
                    pos += 1

                if pos < len(tokens) and (
                        tokens[pos] == token.ReservedWord('elsif') or
                        tokens[pos] == token.ReservedWord('else') or
                        tokens[pos] == token.ReservedWord('until')):
                    continue
                break

        if tokens[pos - 1] == token.NEWLINE:
            statements.append(tstream.parse(tokens, start, pos - 1, parse_func))
        else:
            statements.append(tstream.parse(tokens, start, pos, parse_func))
        start = pos

    return statements
