import token

# '\t', '\n', '\r', ' ': whitespace
EXCLAMATION_MARK = intern('!')
#QUOTATION_MARK = intern('"')
#HASH = intern('#')
#DOLLAR = intern('$')
#PERCENT = intern('%')
#AMPERSAND = intern('&')
DOUBLE_AMPERSAND = intern('&&')
# '\'': bit vector # APOSTROPHE
OPAREN = intern('(')
CPAREN = intern(')')
ASTERISK = intern('*')
PLUS = intern('+')
COMMA = intern(',')
HYPHEN = intern('-')
PERIOD = intern('.')
SLASH = intern('/')
COLON = intern(':')
SEMICOLON = intern(';')
LESS = intern('<')
EQUALS = intern('=')
DOUBLE_EQUALS = intern('==')
EXCLAMATION_EQUALS = intern('!=')
GREATER = intern('>')
#QUESTION_MARK = intern('?')
#AT = intern('@')
OBRACKET = intern('[')
#DOUBLE_BACKSLASH = intern('\\')
CBRACKET = intern(']')
#CARET = intern('^')
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
        return 'rw:' + self.name

class Identifier:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'id:' + self.name

class LinkedIdentifier:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'a:' + self.name

class Number:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'num:' + self.name

class Bitvector:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'bv:' + self.name


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

for s in ['EOR',
          'IN',
          'UNDEFINED',
          'UNPREDICTABLE',
          'else',
          'elsif',
          'for',
          'if',
          'then',
          'to']:
    s = intern(s)
    rw[s] = token.intern_token(s, token.ReservedWord)


class Tokenizer:
    def __init__(self):
        self.tokens = []
        self.stack = []

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
                indent = 0
                while data.startswith('    ', pos + 1 + indent * 4):
                    indent += 1
                pos += 1 + indent * 4
                if data.startswith(' ', pos):
                    raise ParseError
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
                raise ParseError
            elif ch == '#':
                raise ParseError
            elif ch == '$':
                raise ParseError
            elif ch == '%':
                raise ParseError
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
                    raise ParseError
                name = data[pos + 1:pos + 1 + n]
                self.tokens.append(token.intern_token(name, token.Bitvector))
                pos += n + 2
            elif ch == '(':
                self.tokens.append(token.OPAREN)
                pos += 1
            elif ch == ')':
                self.tokens.append(token.CPAREN)
                pos += 1
            elif ch == '*':
                self.tokens.append(token.ASTERISK)
                pos += 1
            elif ch == '+':
                self.tokens.append(token.PLUS)
                pos += 1
            elif ch == ',':
                self.tokens.append(token.COMMA)
                pos += 1
            elif ch == '-':
                self.tokens.append(token.HYPHEN)
                pos += 1
            elif ch == '.':
                self.tokens.append(token.PERIOD)
                pos += 1
            elif ch == '/':
                if pos + 1 < len(data) and data[pos + 1] == '/':
                    try:
                        pos = data.index('\n', pos)
                    except ValueError:
                        raise ParseError
                else:
                    self.tokens.append(token.SLASH)
                    pos += 1
            elif ch >= '0' and ch <= '9':
                n = 1
                while pos + n < len(data):
                    ch = data[pos + n]
                    if not (ch >= '0' and ch <= '9'):
                        break
                    n += 1
                name = data[pos:pos + n]
                self.tokens.append(token.intern_token(name, token.Number))
                pos += n
            elif ch == ':':
                self.tokens.append(token.COLON)
                pos += 1
            elif ch == ';':
                self.tokens.append(token.SEMICOLON)
                pos += 1
            elif ch == '<':
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
                self.tokens.append(token.GREATER)
                pos += 1
            elif ch == '?':
                raise ParseError
            elif ch == '@':
                raise ParseError
            elif ch == '[':
                self.tokens.append(token.OBRACKET)
                pos += 1
            elif ch == '\\':
                raise ParseError
            elif ch == ']':
                self.tokens.append(token.CBRACKET)
                pos += 1
            elif ch == '^':
                raise ParseError
            elif ch == '`':
                raise ParseError
            elif ch == '{':
                self.tokens.append(token.OBRACE)
                pos += 1
            elif ch == '|':
                if pos + 1 < len(data) and data[pos + 1] == '|':
                    self.tokens.append(token.DOUBLE_VBAR)
                    pos += 2
                else:
                    self.tokens.append(token.VBAR)
                    pos += 1
            elif ch == '}':
                self.tokens.append(token.CBRACE)
                pos += 1
            elif ch == '~':
                raise ParseError
            else:
                raise ParseError


        #print 'Character data: ', repr(data)

    def process_a(self, data):
        if not data:
            raise ParseError
        for i, ch in enumerate(data):
            if not (ch >= 'A' and ch <= 'Z' or ch >= 'a' and ch <= 'z'
                      or ch == '_' or i > 0 and ch >= '0' and ch <= '9'):
                raise ParseError
        self.tokens.append(token.intern_token(data, token.LinkedIdentifier))

    def process_end(self):
        while self.stack:
            self.tokens = self.stack.pop()
