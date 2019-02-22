import token, expr

class Identifier:
    def __init__(self, chain):
        self.chain = chain

    def __str__(self):
        return '.'.join(str(t) for t in self.chain)

class Arguments:
    def __init__(self, func, method, args):
        self.func = func
        self.method = method
        self.args = args

    def __str__(self):
        return str(self.func) + self.method[0] + \
            ', '.join(str(arg) for arg in self.args) + self.method[1]

class Set:
    def __init__(self, members):
        self.members = members

    def __str__(self):
        return '{%s}' % ', '.join(str(member) for member in self.members)

class Numeric:
    def __init__(self, number_or_bitvector):
        self.number_or_bitvector = number_or_bitvector

    def __str__(self):
        return str(self.number_or_bitvector)

class Unary:
    def __init__(self, arg, operator):
        self.arg = arg
        self.operator = operator

    def __str__(self):
        return '%s %s' % (str(self.arg), str(self.operator))

class Operator:
    def __init__(self, arg0, arg1, operator):
        self.arg0 = arg0
        self.arg1 = arg1
        self.operator = operator

    def __str__(self):
        return '%s %s %s' % (str(self.arg0), str(self.operator), str(self.arg1))

class Ternary:
    def __init__(self, condition, arg0, arg1):
        self.condition = condition
        self.arg0 = arg0
        self.arg1 = arg1

    def __str__(self):
        return '%s ? %s : %s' % (str(self.condition), str(self.arg0), str(self.arg1))


# identifier :== unlinked-identifier | linked-identifier
# identifier-chain :== identifier | identifier-chain '.' identifier

# maybe-expression-list :== <empty> | expression-list

# expression0 :== identifier-chain
#               | identifier-chain '(' maybe-expression-list ')'
#               | identifier-chain '[' maybe-expression-list ']'
#               | identifier-chain '<' expression-list '>'
#               | number
#               | bitvector
#               | '(' expression3 ')'
#               | '{' maybe-expression-list '}'

def parse0(ts):
    t = ts.peek()

    if isinstance(t, token.ReservedWord):
        raise ParseError
    elif isinstance(t, token.Identifier) or \
         isinstance(t, token.LinkedIdentifier):
        chain = [ts.consume()]
        while ts.consume_if(token.PERIOD):
            t = ts.consume()
            if not isinstance(t, token.Identifier) and \
               not isinstance(t, token.LinkedIdentifier):
                raise ParseError
            chain.append(t)
        expression = expr.Identifier(chain)
        if ts.consume_if(token.OPAREN):
            if ts.peek() != token.CPAREN:
                args = expr.parse_list(ts)
            else:
                args = []
            if ts.consume() != token.CPAREN:
                raise ParseError
            expression = expr.Arguments(expression, '()', args)
        elif ts.consume_if(token.OBRACKET):
            if ts.peek() != token.CBRACKET:
                args = expr.parse_list(ts)
            else:
                args = []
            if ts.consume() != token.CBRACKET:
                raise ParseError
            expression = expr.Arguments(expression, '[]', args)
    elif isinstance(t, token.Number):
        expression = expr.Numeric(t)
        ts.consume()
    elif isinstance(t, token.Bitvector):
        expression = expr.Numeric(t)
        ts.consume()
    elif ts.consume_if(token.OPAREN):
        expression = expr.parse3(ts)
        if ts.consume() != token.CPAREN:
            raise ParseError
    elif ts.consume_if(token.OBRACE):
        if ts.peek() != token.CBRACE:
            members = expr.parse_list(ts)
        else:
            members = []
        if ts.consume() != token.CBRACE:
            raise ParseError
        expression = expr.Set(members)
    else:
        raise ParseError

    return expression


# expression1 :== expression0
#               | '!' expression1

def parse1(ts):
    if ts.consume_if(token.EXCLAMATION_MARK):
        expression = expr.parse1(ts)
        return expr.Unary(expression, token.EXCLAMATION_MARK)

    return expr.parse0(ts)


# operator :== '+' | '-' | '*' | '/' | '==' | '!=' | '<' | '>'
#            | '&&' | '||' | 'EOR' | ':' | 'IN'

# expression2 :== expression1
#               | expression1 operator expression1

operators = [
    token.ASTERISK,
    token.PLUS,
    token.HYPHEN,
    token.SLASH,
    token.LESS,
    token.DOUBLE_EQUALS,
    token.EXCLAMATION_EQUALS,
    token.GREATER,
    token.DOUBLE_AMPERSAND,
    token.DOUBLE_VBAR,
    token.COLON,
    token.rw['IN'],
    token.rw['EOR']
]

def parse2(ts):
    expression = expr.parse1(ts)

    while True:
        if not ts.maybe_peek() in operators:
            break
        operator = ts.consume()

        next_expr = expr.parse1(ts)

        if operator == token.LESS and (ts.maybe_peek() == token.GREATER or
                                     ts.maybe_peek() == token.COMMA):
            if ts.consume() == token.GREATER:
                args = []
            else:
                args = expr.parse_list(ts)
                if ts.consume() != token.GREATER:
                    raise ParseError
            expression = expr.Arguments(expression, '<>', [next_expr] + args)
        else:
            expression = expr.Operator(expression, next_expr, operator)

    return expression


# expression3 :== expression2
#               | 'if' expression2 'then' expression2 'else' expression2

def parse3(ts):
    if ts.consume_if(token.rw['if']):
        condition = expr.parse2(ts)
        if ts.consume() != token.rw['then']:
            raise ParseError
        arg0 = expr.parse2(ts)
        if ts.consume() != token.rw['else']:
            raise ParseError
        arg1 = expr.parse2(ts)
        return expr.Ternary(condition, arg0, arg1)

    return expr.parse2(ts)


# expression-list :== expression3
#                   | expression3 ',' expression-list

def parse_list(ts):
    expressions = []
    while True:
        expression = expr.parse3(ts)
        expressions.append(expression)
        if not ts.consume_if(token.COMMA):
            break
    return expressions
