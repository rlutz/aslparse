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

from . import token, expr, stmt, dtype, decl
from . import ParseError

FUNCTION, SETTER, GETTER = range(3)

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

    def dump(self):
        name = '.'.join(str(part) for part in self.name)
        if self.parameters is None:
            params = None
        else:
            params = ', '.join('%s %s%s' % (
                                 str(pt), '&' if by_reference else '', str(pi))
                               for pt, pi, by_reference in self.parameters)

        lines = []

        if self.functype == SETTER:
            lines.append('%s%s = %s %s%s' % (
                name,
                '[%s]' % params if params is not None else '',
                str(self.result_type),
                str(self.result_name),
                ';' if self.body is None else ''))
        elif self.functype == GETTER:
            lines.append('%s %s%s%s' % (
                str(self.result_type),
                name,
                '[%s]' % params if params is not None else '',
                ';' if self.body is None else ''))
        else:
            lines.append('%s %s(%s)%s' % (
                str(self.result_type),
                name,
                params,
                ';' if self.body is None else ''))

        if self.body is not None:
            for statement in self.body:
                for l in statement.dump():
                    lines.append('    ' + l)

        return lines

class Variable:
    def __init__(self, is_constant, datatype, variables):
        self.is_constant = is_constant
        self.datatype = datatype
        self.variables = variables

    def dump(self):
        return ['%s%s %s;' % (
            'constant ' if self.is_constant else '',
            str(self.datatype),
            ', '.join(
                '%s%s' % (
                    '.'.join(str(part) for part in name),
                    ' = ' + str(expression) if expression is not None else '')
                for name, expression in self.variables))]

class Array:
    def __init__(self, datatype, name):
        self.datatype = datatype
        self.name = name

    def dump(self):
        return ['array %s %s[%s..%s];' % (
            str(self.datatype.base),
            '.'.join(str(part) for part in self.name),
            str(self.datatype.start),
            str(self.datatype.stop))]

class Enumeration:
    def __init__(self, name, values):
        self.name = name
        self.values = values

    def dump(self):
        lines = []
        lines.append('enumeration %s {' % self.name)
        for i, value in enumerate(self.values):
            lines.append('    %s%s' % (
                str(value),
                ',' if i != len(self.values) - 1 else ''))
        lines.append('};')
        return lines

class Type:
    def __init__(self, name, fields):
        self.name = name
        self.fields = fields

    def dump(self):
        if self.fields is None:
            return ['type %s;' % (
                '.'.join(str(part) for part in self.name))]
        lines = []
        lines.append('type %s is (' % (
            '.'.join(str(part) for part in self.name)))
        for i, field in enumerate(self.fields):
            field_type, field_identifier = field
            lines.append('    %s %s%s' % (
                str(field_type),
                str(field_identifier),
                ',' if i != len(self.fields) - 1 else ''))
        lines.append(')')
        return lines

class TypeEquals:
    def __init__(self, name, datatype):
        self.name = name
        self.datatype = datatype

    def dump(self):
        return ['type %s = %s;' % (
            '.'.join(str(part) for part in self.name),
            str(self.datatype))]

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
        if not ts.consume_if(token.Nonalpha('.')):
            overload = True
            break
    return name, overload

def parse(ts):
    if ts.consume_if(token.ReservedWord('constant')):
        datatype = dtype.parse(ts)
        variables = []
        while True:
            name, overload = parse_name(ts)
            ts.consume_assert(token.Nonalpha('='))
            expression = expr.parse_ternary(ts)
            variables.append((name, expression))
            if not ts.consume_if(token.Nonalpha(',')):
                break
        ts.consume_assert(token.Nonalpha(';'))
        return decl.Variable(True, datatype, variables)

    if ts.consume_if(token.ReservedWord('enumeration')):
        name = ts.consume()
        if not isinstance(name, token.Identifier) and \
           not isinstance(name, token.DeclarationIdentifier):
            raise ParseError(ts)
        ts.consume_assert(token.Nonalpha('{'))
        values = []
        while True:
            value = ts.consume()
            if not isinstance(value, token.Identifier) and \
               not isinstance(value, token.DeclarationIdentifier):
                raise ParseError(ts)
            values.append(value)
            if not ts.consume_if(token.Nonalpha(',')):
                break
        ts.consume_assert(token.Nonalpha('}'))
        ts.consume_assert(token.Nonalpha(';'))
        return decl.Enumeration(name, values)

    if ts.consume_if(token.Identifier('type')):
        name, overload = parse_name(ts)
        if ts.consume_if(token.Nonalpha(';')):
            return decl.Type(name, None)
        if ts.consume_if(token.Nonalpha('=')):
            datatype = dtype.parse(ts)
            ts.consume_assert(token.Nonalpha(';'))
            return decl.TypeEquals(name, datatype)
        elif ts.consume_if(token.ReservedWord('is')):
            ts.consume_assert(token.Nonalpha('('))
            fields = []
            while True:
                field_type = dtype.parse(ts)
                t = ts.consume()
                if not isinstance(t, token.Identifier) and \
                   not isinstance(t, token.LinkedIdentifier):
                    raise ParseError(ts)
                fields.append((field_type, t))
                if not ts.consume_if(token.Nonalpha(',')):
                    break
            ts.consume_assert(token.Nonalpha(')'))
            return decl.Type(name, fields)
        else:
            raise ParseError(ts)

    if ts.consume_if(token.ReservedWord('array')):
        base_type = dtype.parse(ts)
        name = []
        while True:
            name.append(ts.consume())
            if not isinstance(name[-1], token.Identifier):
                raise ParseError(ts)
            if not ts.consume_if(token.Nonalpha('.')):
                break
        ts.consume_assert(token.Nonalpha('['))
        start = expr.parse_binary(ts)
        ts.consume_assert(token.Nonalpha('..'))
        stop = expr.parse_binary(ts)
        ts.consume_assert(token.Nonalpha(']'))
        ts.consume_assert(token.Nonalpha(';'))
        return decl.Array(dtype.Array(base_type, start, stop), name)


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
        if ts.peek() == token.Nonalpha('=') or \
           ts.peek() == token.Nonalpha(',') or \
           ts.peek() == token.Nonalpha(';'):
            variables = []
            while True:
                if variables:
                    name, overload = parse_name(ts)
                if not overload:
                    raise ParseError(ts)
                if ts.consume_if(token.Nonalpha('=')):
                    expression = expr.parse_ternary(ts)
                else:
                    expression = None
                variables.append((name, expression))
                if not ts.consume_if(token.Nonalpha(',')):
                    break
            ts.consume_assert(token.Nonalpha(';'))
            return decl.Variable(False, result_type, variables)

    if ts.consume_if(token.Nonalpha('(')):
        expected_closing = token.Nonalpha(')')
        functype = FUNCTION
    else:
        if ts.consume_if(token.Nonalpha('[')):
            expected_closing = token.Nonalpha(']')
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
                by_reference = ts.consume_if(token.Nonalpha('&'))
                t = ts.consume()
                if not isinstance(t, token.Identifier) and \
                   not isinstance(t, token.LinkedIdentifier):
                    raise ParseError(ts)
                parameters.append((param_type, t, by_reference))
                if not ts.consume_if(token.Nonalpha(',')):
                    break
        ts.consume_assert(expected_closing)
    else:
        parameters = None
    if functype == SETTER:
        ts.consume_assert(token.Nonalpha('='))
        result_type = dtype.parse(ts)
        result_name = ts.consume()
        if not isinstance(result_name, token.Identifier) and \
           not isinstance(result_name, token.LinkedIdentifier):
            raise ParseError(ts)
    else:
        result_name = None
    if ts.consume_if(token.Nonalpha(';')):
        body = None
    elif isinstance(ts.peek(), list):
        body = stmt.parse_block(ts.consume(), stmt.parse_statement)
    else:
        raise ParseError(ts)
    return decl.Function(functype, result_type, result_name,
                         name, overload, parameters, body)
