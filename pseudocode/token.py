import sys
from . import token
from . import LexError

NEWLINE = sys.intern('\\n')
# '\t', '\r', ' ': whitespace
EXCLAMATION_MARK = sys.intern('!')
#QUOTATION_MARK = sys.intern('"')
#HASH = sys.intern('#')
#DOLLAR = sys.intern('$')
#PERCENT = sys.intern('%')
AMPERSAND = sys.intern('&')
DOUBLE_AMPERSAND = sys.intern('&&')
# '\'': bit vector # APOSTROPHE
OPAREN = sys.intern('(')
CPAREN = sys.intern(')')
ASTERISK = sys.intern('*')
PLUS = sys.intern('+')
PLUS_COLON = sys.intern('+:')
COMMA = sys.intern(',')
HYPHEN = sys.intern('-')
PERIOD = sys.intern('.')
DOUBLE_PERIOD = sys.intern('..')
SLASH = sys.intern('/')
COLON = sys.intern(':')
SEMICOLON = sys.intern(';')
LESS = sys.intern('<')
DOUBLE_LESS = sys.intern('<<')
LESS_EQUALS = sys.intern('<=')
EQUALS = sys.intern('=')
DOUBLE_EQUALS = sys.intern('==')
EXCLAMATION_EQUALS = sys.intern('!=')
GREATER = sys.intern('>')
DOUBLE_GREATER = sys.intern('>>')
GREATER_EQUALS = sys.intern('>=')
#QUESTION_MARK = sys.intern('?')
#AT = sys.intern('@')
OBRACKET = sys.intern('[')
#DOUBLE_BACKSLASH = sys.intern('\\')
CBRACKET = sys.intern(']')
CARET = sys.intern('^')
#UNDERSCORE = sys.intern('_')
#BACKTICK = sys.intern('`')
OBRACE = sys.intern('{')
VBAR = sys.intern('|')
DOUBLE_VBAR = sys.intern('||')
CBRACE = sys.intern('}')
#TILDE = sys.intern('~')


class ReservedWord:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name # 'rw:' + self.name

class Identifier:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name # 'id:' + self.name

class LinkedIdentifier:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name # 'a:' + self.name

class DeclarationIdentifier:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name # 'decl:' + self.name

class Number:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name # 'num:' + self.name

class HexadecimalNumber:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return '0x' + self.name # 'num:' + self.name

class Bitvector:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return "'%s'" % self.name # 'bv:' + self.name

class String:
    def __init__(self, data):
        self.data = data

    def __str__(self):
        return '"' + self.data + '"' # 'str:"' + self.data + '"'


def intern_token(name, t):
    try:
        tokens = t.tokens
    except AttributeError:
        tokens = t.tokens = {}
    try:
        t_ = t.tokens[name]
    except KeyError:
        t_ = t.tokens[name] = t(name)
    return t_


rw = {}

for s in ['AND',
          'DIV',
          'EOR',
          'FALSE',
          'HIGH',
          'IMPLEMENTATION_DEFINED',
          'IN',
          'LOW',
          'MOD',
          'NOT',
          'OR',
          'REM',
          'SEE',
          'TRUE',
          'UNDEFINED',
          'UNKNOWN',
          'UNPREDICTABLE',
          'array',
          'assert',
          'bit',
          'bits',
          'boolean',
          'case',
          'constant',
          'do',
          'downto',
          'else',
          'elsif',
          'enumeration',
          'for',
          'if',
          'integer',
          'is',
          'of',
          'otherwise',
          'repeat',
          'return',
          'then',
          'to',
          'until',
          'when',
          'while']:
    s = sys.intern(s)
    rw[s] = token.intern_token(s, token.ReservedWord)

# 'type' is a reserved word but can also be used as an identifier
s = sys.intern('type')
rw[s] = token.intern_token(s, token.Identifier)


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
                try:
                    t = token.rw[name]
                except KeyError:
                    t = token.intern_token(name, token.Identifier)
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
                    if t == token.rw['if'] or \
                       t == token.rw['elsif'] or \
                       t == token.rw['then']:
                        break
                if t == token.rw['if'] or t == token.rw['elsif']:
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
                    self.tokens.append(token.EXCLAMATION_EQUALS)
                    pos += 2
                else:
                    self.tokens.append(token.EXCLAMATION_MARK)
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
                self.tokens.append(token.intern_token(
                    data[pos + 1:pos + 1 + n], token.String))
                pos += n + 2
            elif ch == '#':
                raise LexError(data, pos)
            elif ch == '$':
                raise LexError(data, pos)
            elif ch == '%':
                raise LexError(data, pos)
            elif ch == '&':
                if pos + 1 < len(data) and data[pos + 1] == '&':
                    self.tokens.append(token.DOUBLE_AMPERSAND)
                    pos += 2
                else:
                    self.tokens.append(token.AMPERSAND)
                    pos += 1
            elif ch == '\'':
                try:
                    n = data.index('\'', pos + 1) - pos - 1
                except ValueError:
                    raise LexError(data, pos)
                name = data[pos + 1:pos + 1 + n]
                self.tokens.append(token.intern_token(name, token.Bitvector))
                pos += n + 2
            elif ch == '(':
                self.tokens.append(token.OPAREN)
                self.parentheses.append('()')
                pos += 1
            elif ch == ')':
                if not self.parentheses or self.parentheses.pop() != '()':
                    raise LexError(data, pos)
                self.tokens.append(token.CPAREN)
                pos += 1
            elif ch == '*':
                self.tokens.append(token.ASTERISK)
                pos += 1
            elif ch == '+':
                if pos + 1 < len(data) and data[pos + 1] == ':':
                    self.tokens.append(token.PLUS_COLON)
                    pos += 2
                else:
                    self.tokens.append(token.PLUS)
                    pos += 1
            elif ch == ',':
                self.tokens.append(token.COMMA)
                pos += 1
            elif ch == '-':
                self.tokens.append(token.HYPHEN)
                pos += 1
            elif ch == '.' and (pos + 1 == len(data) or not (
                    data[pos + 1] >= '0' and data[pos + 1] <= '9')):
                if pos + 1 < len(data) and data[pos + 1] == '.':
                    self.tokens.append(token.DOUBLE_PERIOD)
                    pos += 2
                else:
                    self.tokens.append(token.PERIOD)
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
                    self.tokens.append(token.SLASH)
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
                    self.tokens.append(token.intern_token(
                        data[pos:pos + n], token.HexadecimalNumber))
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
                    self.tokens.append(token.intern_token(
                        data[pos:pos + n], token.Number))
                pos += n
                if pos < len(data) and (ch >= '0' and ch <= '9' or
                                        ch >= 'A' and ch <= 'Z' or
                           ch == '_' or ch >= 'a' and ch <= 'z'):
                    raise LexError(data, pos)
            elif ch == ':':
                self.tokens.append(token.COLON)
                pos += 1
            elif ch == ';':
                self.tokens.append(token.SEMICOLON)
                pos += 1
            elif ch == '<':
                if pos + 1 < len(data) and data[pos + 1] == '<':
                    self.tokens.append(token.DOUBLE_LESS)
                    pos += 2
                elif pos + 1 < len(data) and data[pos + 1] == '=':
                    self.tokens.append(token.LESS_EQUALS)
                    pos += 2
                else:
                    self.tokens.append(token.LESS)
                    pos += 1
            elif ch == '=':
                if pos + 1 < len(data) and data[pos + 1] == '=':
                    self.tokens.append(token.DOUBLE_EQUALS)
                    pos += 2
                else:
                    self.tokens.append(token.EQUALS)
                    pos += 1
            elif ch == '>':
                if pos + 1 < len(data) and data[pos + 1] == '>':
                    self.tokens.append(token.DOUBLE_GREATER)
                    pos += 2
                elif pos + 1 < len(data) and data[pos + 1] == '=':
                    self.tokens.append(token.GREATER_EQUALS)
                    pos += 2
                else:
                    self.tokens.append(token.GREATER)
                    pos += 1
            elif ch == '?':
                raise LexError(data, pos)
            elif ch == '@':
                raise LexError(data, pos)
            elif ch == '[':
                self.tokens.append(token.OBRACKET)
                self.parentheses.append('[]')
                pos += 1
            elif ch == '\\':
                raise LexError(data, pos)
            elif ch == ']':
                if not self.parentheses or self.parentheses.pop() != '[]':
                    raise LexError(data, pos)
                self.tokens.append(token.CBRACKET)
                pos += 1
            elif ch == '^':
                self.tokens.append(token.CARET)
                pos += 1
            elif ch == '`':
                raise LexError(data, pos)
            elif ch == '{':
                self.tokens.append(token.OBRACE)
                self.parentheses.append('{}')
                pos += 1
            elif ch == '|':
                if pos + 1 < len(data) and data[pos + 1] == '|':
                    self.tokens.append(token.DOUBLE_VBAR)
                    pos += 2
                else:
                    self.tokens.append(token.VBAR)
                    pos += 1
            elif ch == '}':
                if not self.parentheses or self.parentheses.pop() != '{}':
                    raise LexError(data, pos)
                self.tokens.append(token.CBRACE)
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

        parts = data.split('.')
        for part in parts:
            if not part:
                raise LexError(part, 0)
            for i, ch in enumerate(part):
                if not (ch >= 'A' and ch <= 'Z' or ch >= 'a' and ch <= 'z'
                          or ch == '_' or i > 0 and ch >= '0' and ch <= '9'):
                    raise LexError(part, i)

        for part in parts[:-1]:
            self.tokens.append(token.intern_token(part, token.Identifier))
            self.tokens.append(token.PERIOD)
        self.tokens.append(token.intern_token(parts[-1],
                                              token.LinkedIdentifier))

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
            self.tokens.append(token.intern_token(part, token.Identifier))
            self.tokens.append(token.PERIOD)
        self.tokens.append(token.intern_token(parts[-1],
                                              token.DeclarationIdentifier))

    def process_end(self):
        if self.inside_string is not None:
            raise LexError(self.inside_string, 0)

        if self.tokens \
              and self.tokens[-1] != token.NEWLINE \
              and not isinstance(self.tokens[-1], list):
            self.tokens.append(token.NEWLINE)

        while self.stack:
            self.tokens = self.stack.pop()
