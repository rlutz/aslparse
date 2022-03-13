#!/usr/bin/python3
import os
import sys
import xml.parsers.expat

from pseudocode import *

class Fragment:
    def __init__(self, file_processor,
                 mayhavelinks, section = None, rep_section = None):
        self.file_processor = file_processor

        self.mayhavelinks = mayhavelinks  # '1'
        self.section = section            # 'Decode' / 'Execute'
        self.rep_section = rep_section    # 'decode' / 'execute'

        self.tokenizer = token.Tokenizer()
        self.buf = []
        self.inside_element = None

        self.body = None
        self.expression = None

    def character_data(self, data):
        self.buf.append(data)

    def start_element(self, name, link, hover, file = None):
        if self.buf:
            try:
                self.tokenizer.process(''.join(self.buf))
            except LexError as e:
                e.report()
                sys.exit(1)
            del self.buf[:]

        if name != 'a' and name != 'anchor':
            raise ParseError
        if self.inside_element is not None:
            self.file_processor.error('%s tag inside %s tag in pstext tag'
                                        % (name, self.inside_element))
        self.inside_element = name

    def end_element(self, name):
        assert self.inside_element == name
        self.inside_element = None

        try:
            if name == 'a':
                self.tokenizer.process_a(''.join(self.buf))
            elif name == 'anchor':
                self.tokenizer.process_anchor(''.join(self.buf))
        except LexError as e:
            e.report()
            sys.exit(1)
        del self.buf[:]

    def end(self, is_shared_pseudocode):
        try:
            self.tokenizer.process(''.join(self.buf) + '\n')
            self.tokenizer.process_end()
        except LexError as e:
            e.report()
            sys.exit(1)
        del self.buf[:]

        #print('{')
        #for token in self.tokens:
        #    print('\t' + str(token))
        #print('}')

        tokens = self.tokenizer.tokens

        try:
            if not tokens:
                pass
            elif (tokens[-1] == token.NEWLINE and
                  tokens[-2] == token.Nonalpha(';')) \
                    or isinstance(tokens[-1], list) \
                    or tokens[0] == token.Identifier('type'):
                if is_shared_pseudocode:
                    self.body = stmt.parse_block(tokens, decl.parse)
                else:
                    self.body = stmt.parse_block(tokens, stmt.parse_statement)
                if is_shared_pseudocode:
                    for declaration in self.body:
                        ns.process(declaration)
            else:
                assert tokens[-1] == token.NEWLINE
                self.expression = tstream.parse(tokens, 0, len(tokens) - 1,
                                                expr.parse_ternary)
        except ParseError as e:
            e.report()
            sys.exit(1)

class Container:
    def __init__(self, name, mylink, enclabels, sections, secttype):
        self.name = name            # 'aarch32/instrs/#/#.txt'
        self.mylink = mylink        # 'aarch32.instrs.#.#.txt' / 'commonps'
        self.enclabels = enclabels  # ''
        self.sections = sections    # '1'
        self.secttype = secttype    # 'noheading' / 'Operation'
        self.fragment = None

class FileProcessor:
    def __init__(self, base_dir, fn):
        self.base_dir = base_dir
        self.fn = fn
        self.path = os.path.join(base_dir, fn)
        self.is_shared_pseudocode = fn == 'shared_pseudocode.xml'

        self.lineno = None
        self.container = None
        self.fragment = None
        self.fragments = []

        self.p = xml.parsers.expat.ParserCreate(namespace_separator = '!')
        self.p.StartElementHandler = self.StartElementHandler
        self.p.EndElementHandler = self.EndElementHandler
        self.p.CharacterDataHandler = self.CharacterDataHandler

        with open(self.path, 'rb') as f:
            try:
                self.p.ParseFile(f)
            except xml.parsers.expat.ExpatError as e:
                self.error(str(e), lineno = e.lineno - 1)

    def StartElementHandler(self, name, attributes):
        if name == 'ps':
            if self.fragment is not None:
                self.error('ps tag inside pstext tag')
                return
            if self.container is not None:
                self.error('ps tag inside another ps tag')
            self.container = Container(**attributes)
        elif name == 'pstext':
            if self.fragment is not None:
                self.error('pstext tag inside another pstext tag')
            self.fragment = Fragment(self, **attributes)
            self.fragments.append(self.fragment)
            if self.container is not None:
                if self.container.fragment is not None:
                    self.error('multiple pstext tags inside ps tag')
                self.container.fragment = self.fragment
        elif self.fragment is not None:
            if name != 'a' and name != 'anchor':
                raise ParseError
            self.fragment.start_element(name, **attributes)

    def EndElementHandler(self, name):
        if name == 'ps':
            if self.container is None:
                self.error('closing ps tag without opening tag')
            if self.container.fragment is None:
                self.error('ps tag does not contain pstext tag')
            self.container = None
        elif name == 'pstext':
            if self.fragment is None:
                self.error('closing pstext tag without opening tag')
            self.fragment.end(self.is_shared_pseudocode)
            self.fragment = None
        elif self.fragment is not None:
            self.fragment.end_element(name)

    def CharacterDataHandler(self, data):
        # some files contain indentation errors
        if self.path.endswith('/mrs_br.xml'):
            data = data.replace('       UNPREDICTABLE;',
                                '        UNPREDICTABLE;')
        if self.path.endswith('/vcmla.xml'):
            data = data.replace('               element',
                                '                element')
        if self.path.endswith('/vcvt_xs.xml'):
            data = data.replace('     when ',
                                '    when ')
        if self.fragment is not None:
            self.fragment.character_data(data)

    def error(self, msg, lineno = None):
        if lineno is None:
            lineno = self.p.CurrentLineNumber - 1
        sys.stderr.write('%s: error: %s\n' % (lineno + 1, msg))

def main(base_dir):
    file_processors = [FileProcessor(base_dir, fn)
                       for fn in sorted(os.listdir(base_dir))
                       if fn[0] != '.' and fn.endswith('.xml')
                                       and fn != 'onebigfile.xml']
    for file_processor in file_processors:
        if file_processor.fn == 'ldm_u.xml':
            for fragment in file_processor.fragments:
                if fragment.body is not None:
                    print()
                    for statement in fragment.body:
                        for l in statement.dump():
                            print(l)
                    print()
                elif fragment.expression is not None:
                    print()
                    print(str(fragment.expression))
                    print()
                else:
                    print()
                    print('// empty')
                    print()

    #for l in ns.global_ns.dump():
    #    print('| ' + l)

    scope.process_namespace(ns.global_ns)

if __name__ == '__main__':
    main(sys.argv[1])
