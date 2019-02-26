import token
from . import LexError

NEWLINE = intern('\\n')
# '\t', '\r', ' ': whitespace
EXCLAMATION_MARK = intern('!')
#QUOTATION_MARK = intern('"')
#HASH = intern('#')
#DOLLAR = intern('$')
#PERCENT = intern('%')
AMPERSAND = intern('&')
DOUBLE_AMPERSAND = intern('&&')
# '\'': bit vector # APOSTROPHE
OPAREN = intern('(')
CPAREN = intern(')')
ASTERISK = intern('*')
PLUS = intern('+')
PLUS_COLON = intern('+:')
COMMA = intern(',')
HYPHEN = intern('-')
PERIOD = intern('.')
DOUBLE_PERIOD = intern('..')
SLASH = intern('/')
COLON = intern(':')
SEMICOLON = intern(';')
LESS = intern('<')
LESS_EQUALS = intern('<=')
EQUALS = intern('=')
DOUBLE_EQUALS = intern('==')
EXCLAMATION_EQUALS = intern('!=')
GREATER = intern('>')
GREATER_EQUALS = intern('>=')
#QUESTION_MARK = intern('?')
#AT = intern('@')
OBRACKET = intern('[')
#DOUBLE_BACKSLASH = intern('\\')
CBRACKET = intern(']')
CARET = intern('^')
#UNDERSCORE = intern('_')
#BACKTICK = intern('`')
OBRACE = intern('{')
VBAR = intern('|')
DOUBLE_VBAR = intern('||')
CBRACE = intern('}')
#TILDE = intern('~')


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
          'IMPLEMENTATION_DEFINED',
          'IN',
          'MOD',
          'OR',
          'SEE',
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
          'when']:
    s = intern(s)
    rw[s] = token.intern_token(s, token.ReservedWord)

# 'type' is a reserved word but can also be used as an identifier
s = intern('type')
rw[s] = token.intern_token(s, token.Identifier)


class Tokenizer:
    def __init__(self):
        self.tokens = []
        self.stack = []
        self.parentheses = []

    def process(self, data):
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
                    if pos < len(data) and data[pos] == '\n':
                        pos += 1
                        continue
                    try:
                        p = data.index('//', pos)
                    except ValueError:
                        break
                    if data[pos:p] != ' ' * (p - pos):
                        break
                    pos = data.index('\n', pos)
                indent = 0
                while data.startswith('    ', pos + indent * 4):
                    indent += 1
                pos += indent * 4
                # ignore irregular line break inside 'if' condition
                t = None
                for t in reversed(self.tokens):
                    if t == token.rw['if'] or t == token.rw['then']:
                        break
                if t == token.rw['if']:
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
                    raise LexError(data, pos)
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
                if pos + 1 < len(data) and data[pos + 1] == '/':
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
                if pos + 1 < len(data) and data[pos + 1] == '=':
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
                if pos + 1 < len(data) and data[pos + 1] == '=':
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


        #print 'Character data: ', repr(data)

    def process_a(self, data):
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
        if self.tokens \
              and self.tokens[-1] != token.NEWLINE \
              and not isinstance(self.tokens[-1], list):
            self.tokens.append(token.NEWLINE)

        while self.stack:
            self.tokens = self.stack.pop()
