# Parser and resolver for ARM ASL pseudocode
# Copyright (C) 2019, 2021-2022 Roland Lutz
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from . import token, expr, dtype
from . import ParseError

class Identifier:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return str(self.name)

class QualifiedIdentifier:
    def __init__(self, expression, name):
        self.expression = expression
        self.name = name

    def __str__(self):
        return str(self.expression) + '.' + str(self.name)

class Arguments:
    def __init__(self, func, method, args):
        self.func = func
        self.method = method
        self.args = args

    def _fmt_arg(self, arg):
        if isinstance(arg, tuple):
            return '%s%s%s' % tuple(str(a) for a in arg)
        else:
            return str(arg)

    def __str__(self):
        if isinstance(self.func, expr.Ternary) or \
           isinstance(self.func, expr.Operator) or \
           isinstance(self.func, expr.Unary):
            func = '(%s)' % str(self.func)
        else:
            func = str(self.func)
        return func + self.method[0] + \
            ', '.join(self._fmt_arg(arg) for arg in self.args) + self.method[1]

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
        op = str(self.operator)
        if isinstance(self.operator, token.ReservedWord):
            op = op + ' '
        arg = str(self.arg)
        if isinstance(self.arg, expr.Ternary) or \
           isinstance(self.arg, expr.Operator):
            arg = '(%s)' % arg
        return op + arg

class Operator:
    def __init__(self, arg0, arg1, operator, precedence):
        self.arg0 = arg0
        self.arg1 = arg1
        self.operator = operator
        self.precedence = precedence

    def __str__(self):
        if isinstance(self.arg0, expr.Ternary) or \
           isinstance(self.arg0, expr.Operator) and \
              self.arg0.precedence < self.precedence:
            arg0 = '(' + str(self.arg0) + ')'
        else:
            arg0 = str(self.arg0)

        if isinstance(self.arg1, expr.Ternary) or \
           isinstance(self.arg1, expr.Operator) and \
              self.arg1.precedence < self.precedence:
            arg1 = '(' + str(self.arg1) + ')'
        else:
            arg1 = str(self.arg1)

        return '%s %s %s' % (arg0, str(self.operator), arg1)

class Ternary:
    def __init__(self, condition, arg0, arg1):
        self.condition = condition
        self.arg0 = arg0
        self.arg1 = arg1

    def __str__(self):
        return 'if %s then %s else %s' % (str(self.condition),
                                          str(self.arg0), str(self.arg1))

class Bits:
    def __init__(self, elements):
        self.elements = elements

    def __str__(self):
        is_qualified, = set(isinstance(element, expr.QualifiedIdentifier)
                            for element in self.elements)
        if is_qualified:
            prefix, = set(str(element.expression) for element in self.elements)
            return prefix + '.<' + \
                ','.join(str(element.name) for element in self.elements) + '>'
        else:
            return '<' + \
                ','.join(str(element) for element in self.elements) + '>'

class Values:
    def __init__(self, members):
        self.members = members

    def __str__(self):
        return '(' + ', '.join(str(member) for member in self.members) + ')'

class Omitted:
    def __str__(self):
        return '-'

class Unknown:
    def __init__(self, datatype):
        self.datatype = datatype

    def __str__(self):
        return str(self.datatype) + ' UNKNOWN'

class ImplementationDefined:
    def __init__(self, datatype, aspect):
        self.datatype = datatype
        self.aspect = aspect

    def __str__(self):
        if self.aspect is None:
            return str(self.datatype) + ' IMPLEMENTATION_DEFINED'
        else:
            return str(self.datatype) + \
                ' IMPLEMENTATION_DEFINED "%s"' % self.aspect

class Primitive:
    def __init__(self, token):
        self.token = token

    def __str__(self):
        return str(self.token)


def parse_identifier_chain(ts):
    expression = None
    while True:
        t = ts.consume()
        if not isinstance(t, token.Identifier) and \
           not isinstance(t, token.LinkedIdentifier):
            raise ParseError(ts)
        if expression is None:
            expression = expr.Identifier(t)
        else:
            expression = expr.QualifiedIdentifier(expression, t)
        if not ts.consume_if(token.Nonalpha('.')):
            break
    return expression


# bitspec :== expression2                   (+, -, *, / only)
#           | expression2 ':' expression2   (+, -, *, / only)
#           | expression2 '+:' expression2  (+, -, *, / only)
# bitspec-list :== bitspec | bitspec-list ',' bitspec
# bitspec-clause :== '<' bitspec-list '>'

def parse_bitspec_clause(ts):
    sub_ts = ts.fork()
    args = []
    try:
        sub_ts.consume_assert(token.Nonalpha('<'))
        while True:
            arg = expr.parse_binary(sub_ts, len(operators) - 3)
            if sub_ts.consume_if(token.Nonalpha(':')):
                arg1 = expr.parse_binary(sub_ts, len(operators) - 3)
                args.append((arg, token.Nonalpha(':'), arg1))
            elif sub_ts.consume_if(token.Nonalpha('+:')):
                arg1 = expr.parse_binary(sub_ts, len(operators) - 3)
                args.append((arg, token.Nonalpha('+:'), arg1))
            else:
                args.append(arg)
            if not sub_ts.consume_if(token.Nonalpha(',')):
                break
        sub_ts.consume_assert(token.Nonalpha('>'))
    except ParseError as e:
        ts.abandon(sub_ts)
        return None
    else:
        ts.become(sub_ts)
        return args


# identifier :== unlinked-identifier | linked-identifier
# qualified-identifier :== identifier
#                        | qualified-identifier '.' identifier
#                        | qualified-identifier '[' maybe-expression-list ']'
#                                               '.' identifier
# identifier-list :== identifier | identifier-list ',' identifier

# maybe-expression-list :== <empty> | expression-list

# assignable :== identifier-chain
#              | identifier-chain '[' maybe-expression-list ']'
#              | identifier-chain bitspec-clause
#              | identifier-chain '[' maybe-expression-list ']' bitspec-clause
#              | '<' identifier-list '>'
#              | identifier-chain '.' '<' identifier-list '>'
#              | '(' assignable-list ')'
#              | '-'
# assignable-list :== assignable | assignable-list ',' assignable

def parse_assignable(ts):
    t = ts.peek()

    if isinstance(t, token.Identifier) or \
       isinstance(t, token.LinkedIdentifier):
        expression = expr.Identifier(ts.consume())
        while True:
            if ts.consume_if(token.Nonalpha('[')):
                if ts.peek() != token.Nonalpha(']'):
                    args = expr.parse_list(ts)
                else:
                    args = []
                ts.consume_assert(token.Nonalpha(']'))
                expression = expr.Arguments(expression, '[]', args)
            if not ts.consume_if(token.Nonalpha('.')):
                break
            t = ts.consume()
            if t == token.Nonalpha('<'):
                elements = []
                while True:
                    t = ts.consume()
                    if not isinstance(t, token.Identifier) and \
                       not isinstance(t, token.LinkedIdentifier):
                        raise ParseError(ts)
                    elements.append(expr.QualifiedIdentifier(expression, t))
                    if not ts.consume_if(token.Nonalpha(',')):
                        break
                ts.consume_assert(token.Nonalpha('>'))
                return Bits(elements)
            if not isinstance(t, token.Identifier) and \
               not isinstance(t, token.LinkedIdentifier):
                raise ParseError(ts)
            expression = expr.QualifiedIdentifier(expression, t)
        if ts.maybe_peek() == token.Nonalpha('<'):
            args = expr.parse_bitspec_clause(ts)
            if args is not None:
                expression = expr.Arguments(expression, '<>', args)
        return expression

    if ts.consume_if(token.Nonalpha('<')):
        elements = []
        while True:
            t = ts.consume()
            if not isinstance(t, token.Identifier) and \
               not isinstance(t, token.LinkedIdentifier):
                raise ParseError(ts)
            elements.append(expr.Identifier(t))
            if not ts.consume_if(token.Nonalpha(',')):
                break
        ts.consume_assert(token.Nonalpha('>'))
        return Bits(elements)

    if ts.consume_if(token.Nonalpha('(')):
        members = []
        while True:
            members.append(expr.parse_assignable(ts))
            if not ts.consume_if(token.Nonalpha(',')):
                break
        ts.consume_assert(token.Nonalpha(')'))
        return Values(members)

    if ts.consume_if(token.Nonalpha('-')):
        return Omitted()

    raise ParseError(ts)


# expression0 :== assignable
#               | identifier-chain '(' maybe-expression-list ')'
#               | identifier-chain '(' maybe-expression-list ')' bitspec-clause
#               | number
#               | number bitspec-clause
#               | bitvector
#               | '(' expression-list ')'
#               | '(' expression-list ')' bitspec-clause
#               | '{' maybe-expression-list '}'
#               | datatype 'UNKNOWN'
#               | datatype 'IMPLEMENTATION_DEFINED'
#               | datatype 'IMPLEMENTATION_DEFINED' string
#               | 'FALSE' | 'TRUE' | 'LOW' | 'HIGH'

def parse_operand(ts):
    t = ts.peek()

    if isinstance(t, token.Number) or \
       isinstance(t, token.HexadecimalNumber):
        ts.consume()
        expression = expr.Numeric(t)
        if ts.maybe_peek() == token.Nonalpha('<'):
            args = expr.parse_bitspec_clause(ts)
            expression = expr.Arguments(expression, '<>', args)
        return expression
    elif isinstance(t, token.Bitvector):
        ts.consume()
        return expr.Numeric(t)
    elif ts.consume_if(token.Nonalpha('(')):
        expressions = expr.parse_list(ts)
        ts.consume_assert(token.Nonalpha(')'))
        if len(expressions) > 1:
            return Values(expressions)
        expression = expressions[0]
        if ts.maybe_peek() == token.Nonalpha('<'):
            args = expr.parse_bitspec_clause(ts)
            if args is not None:
                expression = expr.Arguments(expression, '<>', args)
        return expression
    elif ts.consume_if(token.Nonalpha('{')):
        if ts.peek() != token.Nonalpha('}'):
            members = expr.parse_list(ts)
        else:
            members = []
        ts.consume_assert(token.Nonalpha('}'))
        return expr.Set(members)
    elif t in [token.ReservedWord('FALSE'), token.ReservedWord('TRUE'),
               token.ReservedWord('LOW'), token.ReservedWord('HIGH')]:
        return expr.Primitive(ts.consume())


    sub_ts = ts.fork()
    try:
        datatype = dtype.parse(sub_ts)
        if sub_ts.consume_if(token.ReservedWord('UNKNOWN')):
            expression = expr.Unknown(datatype)
        elif sub_ts.consume_if(token.ReservedWord('IMPLEMENTATION_DEFINED')):
            if isinstance(sub_ts.peek(), token.String):
                aspect = sub_ts.consume().data
            else:
                aspect = None
            expression = expr.ImplementationDefined(datatype, aspect)
        else:
            raise ParseError(sub_ts)
    except ParseError:
        ts.abandon(sub_ts)
    else:
        ts.become(sub_ts)
        return expression

    expression = parse_assignable(ts)
    if ts.consume_if(token.Nonalpha('(')):
        if ts.peek() != token.Nonalpha(')'):
            args = expr.parse_list(ts)
        else:
            args = []
        ts.consume_assert(token.Nonalpha(')'))
        expression = expr.Arguments(expression, '()', args)
    if ts.maybe_peek() == token.Nonalpha('<'):
        args = expr.parse_bitspec_clause(ts)
        if args is not None:
            expression = expr.Arguments(expression, '<>', args)
    return expression


# expression1 :== expression0
#               | '!' expression1

# Potentially: '~', '-', type casts

unary_operators = [token.Nonalpha('!'), token.Nonalpha('-'),
                   token.ReservedWord('NOT')]

def parse_unary(ts):
    if ts.peek() in unary_operators:
        operator = ts.consume()
        expression = expr.parse_unary(ts)
        return expr.Unary(expression, operator)

    return expr.parse_operand(ts)


# operator :== '||'
#            | '&&'
#            | 'IN'
#            | 'OR'
#            | 'EOR'
#            | 'AND'
#            | '==' | '!='
#            | '<' | '<=' | '>' | '>='
#            | '<<' | '>>' | ':'
#            | '+' | '-'
#            | '*' | '/' | 'DIV' | 'MOD' | 'REM'
#            | '^'

# expression2 :== expression1
#               | expression1 operator expression1

operators = [
    [token.Nonalpha('||')],
    [token.Nonalpha('&&')],
    [token.ReservedWord('IN')],
    [token.ReservedWord('OR')],
    [token.ReservedWord('EOR')],
    [token.ReservedWord('AND')],
    [token.Nonalpha('=='), token.Nonalpha('!=')],
    [token.Nonalpha('<'), token.Nonalpha('<='),
     token.Nonalpha('>'), token.Nonalpha('>=')],
    [token.Nonalpha('<<'), token.Nonalpha('>>'), token.Nonalpha(':')],
    [token.Nonalpha('+'), token.Nonalpha('-')],
    [token.Nonalpha('*'), token.Nonalpha('/'),
     token.ReservedWord('DIV'),
     token.ReservedWord('MOD'),
     token.ReservedWord('REM')],
    [token.Nonalpha('^')],
]

def parse_binary(ts, precedence_limit = 0):
    stack = []

    while True:
        while len(stack) < len(operators):
            stack.append(None)

        expression = expr.parse_unary(ts)

        while True:
            expr_op_prec = stack.pop()
            if expr_op_prec is not None:
                expression = expr.Operator(expr_op_prec[0], expression,
                                           expr_op_prec[1], expr_op_prec[2])

            if ts.maybe_peek() in operators[len(stack)]:
                break

            if len(stack) == precedence_limit:
                return expression

        stack.append((expression, ts.consume(), len(stack)))


# ternary-segment :== expression2 'then' expression2 'elsif' ternary-segment
#                   | expression2 'then' expression2 'else' expression3

# expression3 :== expression2
#               | 'if' ternary-segment

def parse_ternary_segment(ts):
    condition = expr.parse_binary(ts)
    ts.consume_assert(token.ReservedWord('then'))
    arg0 = expr.parse_binary(ts)
    if ts.consume_if(token.ReservedWord('elsif')):
        arg1 = expr.parse_ternary_segment(ts)
    elif ts.consume_if(token.ReservedWord('else')):
        arg1 = expr.parse_ternary(ts)
    else:
        raise ParseError(ts)
    return expr.Ternary(condition, arg0, arg1)

def parse_ternary(ts):
    if ts.consume_if(token.ReservedWord('if')):
        return parse_ternary_segment(ts)

    return expr.parse_binary(ts)


# expression-list :== expression3
#                   | expression3 ',' expression-list

def parse_list(ts):
    expressions = []
    while True:
        expression = expr.parse_ternary(ts)
        expressions.append(expression)
        if not ts.consume_if(token.Nonalpha(',')):
            break
    return expressions
