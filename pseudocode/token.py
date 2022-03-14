# Parser and resolver for ARM ASL pseudocode
# Copyright (C) 2019, 2021-2022 Roland Lutz

import functools
import sys
import weakref

from . import token
from . import LexError

RESERVED_WORDS = {
    'AND', 'DIV', 'EOR', 'FALSE', 'HIGH', 'IMPLEMENTATION_DEFINED', 'IN',
    'LOW', 'MOD', 'NOT', 'OR', 'REM', 'SEE', 'TRUE', 'UNDEFINED', 'UNKNOWN',
    'UNPREDICTABLE',
    'array', 'assert', 'bit', 'bits', 'boolean', 'case', 'constant', 'do',
    'downto', 'else', 'elsif', 'enumeration', 'for', 'if', 'integer', 'is',
    'of', 'otherwise', 'repeat', 'return', 'then', 'to', 'until', 'when',
    'while'
}

# 'type' is a reserved word but can also be used as an identifier
MAYBE_RESERVED_WORDS = {
    'type'
}

NONALPHA = {
    '\\n', '!', '&', '&&', '(', ')', '*', '+', '+:', ',', '-', '.', '..', '/',
    ':', ';', '<', '<<', '<=', '=', '==', '!=', '>', '>>', '>=', '[', ']', '^',
    '{', '|', '||', '}'
}

# Using singletons here has an enormous performance impact (execution
# time is about 2.5x higher as with interned strings), but I think the
# improved readability is worth it.

def singleton(x):
    actual_new = x.__new__

    @functools.wraps(actual_new)
    def new(cls, *args):
        try:
            d = cls._instances
        except AttributeError:
            d = cls._instances = weakref.WeakValueDictionary()
        try:
            inst = d[args]
        except KeyError:
            inst = d[args] = actual_new(cls)
            inst.args = args
            try:
                inst.__init_singleton__(*args)
            except:
                del d[args]
                raise
        return inst

    x.__new__ = new
    return x

@singleton
class Token:
    def __repr__(self):
        try:
            data = repr(self.data)
        except AttributeError:
            data = ''
        return '%s.%s(%s)' % (self.__class__.__module__,
                              self.__class__.__qualname__, data)

class ReservedWord(Token):
    def __init_singleton__(self, data):
        if data not in RESERVED_WORDS and \
           data not in MAYBE_RESERVED_WORDS:
            raise ValueError
        self.data = data

    def __str__(self):
        return self.data # 'rw:' + self.data

class Identifier(Token):
    def __init_singleton__(self, data):
        if data in RESERVED_WORDS:
            raise ValueError
        self.data = data

    def __str__(self):
        return self.data # 'id:' + self.data

class LinkedIdentifier(Token):
    def __init_singleton__(self, data):
        if data in RESERVED_WORDS:
            raise ValueError
        self.data = data

    def __str__(self):
        return self.data # 'a:' + self.data

class DeclarationIdentifier(Token):
    def __init_singleton__(self, data):
        if data in RESERVED_WORDS:
            raise ValueError
        self.data = data

    def __str__(self):
        return self.data # 'decl:' + self.data

class Number(Token):
    def __init_singleton__(self, data):
        self.data = data

    def __str__(self):
        return self.data # 'num:' + self.data

class HexadecimalNumber(Token):
    def __init_singleton__(self, data):
        self.data = data

    def __str__(self):
        return '0x' + self.data # 'num:' + self.data

class Bitvector(Token):
    def __init_singleton__(self, data):
        self.data = data

    def __str__(self):
        return "'%s'" % self.data # 'bv:' + self.data

class String(Token):
    def __init_singleton__(self, data):
        self.data = data

    def __str__(self):
        return '"' + self.data + '"' # 'str:"' + self.data + '"'

class Nonalpha(Token):
    def __init_singleton__(self, data):
        if data not in NONALPHA:
            raise ValueError
        self.data = data

    def __str__(self):
        return self.data

NEWLINE = token.Nonalpha('\\n')
# '\t', '\r', ' ': whitespace


class Tokenizer:
    def __init__(self):
        self.tokens = []
        self.stack = []
        self.parentheses = []
        self.inside_string = None

    def process(self, data):
        if self.inside_string is not None:
            data = self.inside_string + data
            self.inside_string = None

        pos = 0
        while pos < len(data):
            ch = data[pos]

            if ch >= 'A' and ch <= 'Z' or ch >= 'a' and ch <= 'z' or ch == '_':
                n = 1
                while pos + n < len(data):
                    ch = data[pos + n]
                    if not (ch >= 'A' and ch <= 'Z' or ch >= 'a' and ch <= 'z'
                              or ch == '_' or ch >= '0' and ch <= '9'):
                        break
                    n += 1
                name = data[pos:pos + n]
                if name in RESERVED_WORDS:
                    t = token.ReservedWord(name)
                else:
                    t = token.Identifier(name)
                self.tokens.append(t)
                pos += n
            elif ch == '\n':
                pos += 1
                if self.parentheses:
                    continue
                # skip empty and comment-only lines
                while True:
                    try:
                        p = data.index('\n', pos)
                    except ValueError:
                        pass
                    else:
                        if data[pos:p] == ' ' * (p - pos):
                            pos = p + 1
                            continue
                    try:
                        p = data.index('//', pos)
                    except ValueError:
                        pass
                    else:
                        if data[pos:p] == ' ' * (p - pos):
                            pos = data.index('\n', pos) + 1
                            continue
                    break
                indent = 0
                while data.startswith('    ', pos + indent * 4):
                    indent += 1
                pos += indent * 4
                # ignore irregular line break inside 'if' condition
                t = None
                for t in reversed(self.tokens):
                    if t == token.ReservedWord('if') or \
                       t == token.ReservedWord('elsif') or \
                       t == token.ReservedWord('then'):
                        break
                if t == token.ReservedWord('if') or \
                   t == token.ReservedWord('elsif'):
                    continue
                if data.startswith(' ', pos):
                    raise LexError(data, pos)
                if len(self.stack) >= indent and self.tokens \
                      and self.tokens[-1] != token.NEWLINE \
                      and not isinstance(self.tokens[-1], list):
                    self.tokens.append(token.NEWLINE)
                while len(self.stack) < indent:
                    self.stack.append(self.tokens)
                    indented_tokens = []
                    self.tokens.append(indented_tokens)
                    self.tokens = indented_tokens
                while len(self.stack) > indent:
                    self.tokens = self.stack.pop()
            elif ch == ' ':
                pos += 1
            elif ch == '!':
                if pos + 1 < len(data) and data[pos + 1] == '=':
                    self.tokens.append(token.Nonalpha('!='))
                    pos += 2
                else:
                    self.tokens.append(token.Nonalpha('!'))
                    pos += 1
            elif ch == '"':
                try:
                    n = data.index('"', pos + 1) - pos - 1
                except ValueError:
                    self.inside_string = data[pos:]
                    return
                if data.find('\n', pos + 1, pos + 1 + n) != -1:
                    raise LexError(data, pos)
                if data.find('\\', pos + 1, pos + 1 + n) != -1:
                    raise LexError(data, pos)
                self.tokens.append(token.String(data[pos + 1:pos + 1 + n]))
                pos += n + 2
            elif ch == '#':
                raise LexError(data, pos)
            elif ch == '$':
                raise LexError(data, pos)
            elif ch == '%':
                raise LexError(data, pos)
            elif ch == '&':
                if pos + 1 < len(data) and data[pos + 1] == '&':
                    self.tokens.append(token.Nonalpha('&&'))
                    pos += 2
                else:
                    self.tokens.append(token.Nonalpha('&'))
                    pos += 1
            elif ch == '\'':
                try:
                    n = data.index('\'', pos + 1) - pos - 1
                except ValueError:
                    raise LexError(data, pos)
                name = data[pos + 1:pos + 1 + n]
                self.tokens.append(token.Bitvector(name))
                pos += n + 2
            elif ch == '(':
                self.tokens.append(token.Nonalpha('('))
                self.parentheses.append('()')
                pos += 1
            elif ch == ')':
                if not self.parentheses or self.parentheses.pop() != '()':
                    raise LexError(data, pos)
                self.tokens.append(token.Nonalpha(')'))
                pos += 1
            elif ch == '*':
                self.tokens.append(token.Nonalpha('*'))
                pos += 1
            elif ch == '+':
                if pos + 1 < len(data) and data[pos + 1] == ':':
                    self.tokens.append(token.Nonalpha('+:'))
                    pos += 2
                else:
                    self.tokens.append(token.Nonalpha('+'))
                    pos += 1
            elif ch == ',':
                self.tokens.append(token.Nonalpha(','))
                pos += 1
            elif ch == '-':
                self.tokens.append(token.Nonalpha('-'))
                pos += 1
            elif ch == '.' and (pos + 1 == len(data) or not (
                    data[pos + 1] >= '0' and data[pos + 1] <= '9')):
                if pos + 1 < len(data) and data[pos + 1] == '.':
                    self.tokens.append(token.Nonalpha('..'))
                    pos += 2
                else:
                    self.tokens.append(token.Nonalpha('.'))
                    pos += 1
            elif ch == '/':
                if pos + 1 < len(data) and data[pos + 1] == '*':
                    try:
                        pos = data.index('*/', pos) + 2
                    except ValueError:
                        raise LexError(data, pos)
                elif pos + 1 < len(data) and data[pos + 1] == '/':
                    try:
                        pos = data.index('\n', pos)
                    except ValueError:
                        raise LexError(data, pos)
                else:
                    self.tokens.append(token.Nonalpha('/'))
                    pos += 1
            elif ch >= '0' and ch <= '9' or ch == '.':
                if pos + 1 < len(data) and data[pos:pos + 2] == '0x':
                    pos += 2
                    n = 0
                    while pos + n < len(data):
                        ch = data[pos + n]
                        if not (ch >= '0' and ch <= '9' or
                                ch >= 'A' and ch <= 'F' or
                                ch >= 'a' and ch <= 'f'):
                            break
                        n += 1
                    if n == 0:
                        raise LexError(data, pos)
                    self.tokens.append(
                        token.HexadecimalNumber(data[pos:pos + n]))
                else:
                    n = 1
                    while pos + n < len(data):
                        ch = data[pos + n]
                        if not (ch >= '0' and ch <= '9' or ch == '.'):
                            break
                        if ch == '.' and pos + n + 1 < len(data) \
                                     and data[pos + n + 1] == '.':
                            break
                        n += 1
                    self.tokens.append(token.Number(data[pos:pos + n]))
                pos += n
                if pos < len(data) and (ch >= '0' and ch <= '9' or
                                        ch >= 'A' and ch <= 'Z' or
                           ch == '_' or ch >= 'a' and ch <= 'z'):
                    raise LexError(data, pos)
            elif ch == ':':
                self.tokens.append(token.Nonalpha(':'))
                pos += 1
            elif ch == ';':
                self.tokens.append(token.Nonalpha(';'))
                pos += 1
            elif ch == '<':
                if pos + 1 < len(data) and data[pos + 1] == '<':
                    self.tokens.append(token.Nonalpha('<<'))
                    pos += 2
                elif pos + 1 < len(data) and data[pos + 1] == '=':
                    self.tokens.append(token.Nonalpha('<='))
                    pos += 2
                else:
                    self.tokens.append(token.Nonalpha('<'))
                    pos += 1
            elif ch == '=':
                if pos + 1 < len(data) and data[pos + 1] == '=':
                    self.tokens.append(token.Nonalpha('=='))
                    pos += 2
                else:
                    self.tokens.append(token.Nonalpha('='))
                    pos += 1
            elif ch == '>':
                if pos + 1 < len(data) and data[pos + 1] == '>':
                    self.tokens.append(token.Nonalpha('>>'))
                    pos += 2
                elif pos + 1 < len(data) and data[pos + 1] == '=':
                    self.tokens.append(token.Nonalpha('>='))
                    pos += 2
                else:
                    self.tokens.append(token.Nonalpha('>'))
                    pos += 1
            elif ch == '?':
                raise LexError(data, pos)
            elif ch == '@':
                raise LexError(data, pos)
            elif ch == '[':
                self.tokens.append(token.Nonalpha('['))
                self.parentheses.append('[]')
                pos += 1
            elif ch == '\\':
                raise LexError(data, pos)
            elif ch == ']':
                if not self.parentheses or self.parentheses.pop() != '[]':
                    raise LexError(data, pos)
                self.tokens.append(token.Nonalpha(']'))
                pos += 1
            elif ch == '^':
                self.tokens.append(token.Nonalpha('^'))
                pos += 1
            elif ch == '`':
                raise LexError(data, pos)
            elif ch == '{':
                self.tokens.append(token.Nonalpha('{'))
                self.parentheses.append('{}')
                pos += 1
            elif ch == '|':
                if pos + 1 < len(data) and data[pos + 1] == '|':
                    self.tokens.append(token.Nonalpha('||'))
                    pos += 2
                else:
                    self.tokens.append(token.Nonalpha('|'))
                    pos += 1
            elif ch == '}':
                if not self.parentheses or self.parentheses.pop() != '{}':
                    raise LexError(data, pos)
                self.tokens.append(token.Nonalpha('}'))
                pos += 1
            elif ch == '~':
                raise LexError(data, pos)
            else:
                raise LexError(data, pos)


        #print('Character data: ', repr(data))

    def process_a(self, data):
        if self.inside_string is not None:
            self.inside_string += data
            return

        is_see = data[:4] == 'SEE(' and data[-1:] == ')'
        if is_see:
            data = data[4:-1]

        parts = data.split('.')
        for part in parts:
            if not part:
                raise LexError(part, 0)
            for i, ch in enumerate(part):
                if not (ch >= 'A' and ch <= 'Z' or ch >= 'a' and ch <= 'z'
                          or ch == '_' or i > 0 and ch >= '0' and ch <= '9'):
                    raise LexError(part, i)

        if is_see:
            self.tokens.append(token.ReservedWord('SEE'))
            self.tokens.append(token.Nonalpha('('))
        for part in parts[:-1]:
            self.tokens.append(token.Identifier(part))
            self.tokens.append(token.Nonalpha('.'))
        self.tokens.append(token.LinkedIdentifier(parts[-1]))
        if is_see:
            self.tokens.append(token.Nonalpha(')'))

    def process_anchor(self, data):
        if self.inside_string is not None:
            raise LexError(self.inside_string, 0)

        parts = data.split('.')
        for part in parts:
            if not part:
                raise LexError(part, 0)
            for i, ch in enumerate(part):
                if not (ch >= 'A' and ch <= 'Z' or ch >= 'a' and ch <= 'z'
                          or ch == '_' or i > 0 and ch >= '0' and ch <= '9'):
                    raise LexError(part, i)

        for part in parts[:-1]:
            self.tokens.append(token.Identifier(part))
            self.tokens.append(token.Nonalpha('.'))
        self.tokens.append(token.DeclarationIdentifier(parts[-1]))

    def process_end(self):
        if self.inside_string is not None:
            raise LexError(self.inside_string, 0)

        if self.tokens \
              and self.tokens[-1] != token.NEWLINE \
              and not isinstance(self.tokens[-1], list):
            self.tokens.append(token.NEWLINE)

        while self.stack:
            self.tokens = self.stack.pop()
