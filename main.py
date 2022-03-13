#!/usr/bin/python3
import os
import sys
import xml.parsers.expat

from pseudocode import *

class Log:
    def __init__(self):
        self.p = None
        self.lineno = None

    def error(self, msg):
        if self.lineno is not None:
            lineno = self.lineno
        else:
            lineno = self.p.CurrentLineNumber - 1
        sys.stderr.write('%s: error: %s\n' % (lineno + 1, msg))

log = Log()




class Container:
    def __init__(self, name, mylink, enclabels, sections, secttype):
        self.name = name            # 'aarch32/instrs/#/#.txt'
        self.mylink = mylink        # 'aarch32.instrs.#.#.txt' / 'commonps'
        self.enclabels = enclabels  # ''
        self.sections = sections    # '1'
        self.secttype = secttype    # 'noheading' / 'Operation'
        self.fragment = None


class Fragment:
    def __init__(self, mayhavelinks, section = None, rep_section = None):
        self.mayhavelinks = mayhavelinks  # '1'
        self.section = section            # 'Decode' / 'Execute'
        self.rep_section = rep_section    # 'decode' / 'execute'

        self.tokenizer = token.Tokenizer()
        self.buf = []
        self.inside_element = None

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
            log.error('%s tag inside %s tag in pstext tag'
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

    def end(self, is_shared_pseudocode, do_print):
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
                #print()
                #print('// empty')
                #print()
            elif (tokens[-1] == token.NEWLINE and
                  tokens[-2] == token.Nonalpha(';')) \
                    or isinstance(tokens[-1], list) \
                    or tokens[0] == token.Identifier('type'):
                if is_shared_pseudocode:
                    body = stmt.parse_block(tokens, decl.parse)
                else:
                    body = stmt.parse_block(tokens, stmt.parse_statement)
                if do_print:
                    print()
                    for statement in body:
                        statement.__print__('')
                    print()
                if is_shared_pseudocode:
                    for declaration in body:
                        ns.process(declaration)
            else:
                assert tokens[-1] == token.NEWLINE
                expression = tstream.parse(tokens, 0, len(tokens) - 1,
                                           expr.parse_ternary)
                if do_print:
                    print()
                    print(str(expression))
                    print()
        except ParseError as e:
            e.report()
            sys.exit(1)


container = None
fragment = None

def parse_file(path, is_shared_pseudocode, do_print):
    def StartElementHandler(name, attributes):
        global container, fragment
        if name == 'ps':
            if fragment is not None:
                log.error('ps tag inside pstext tag')
                return
            if container is not None:
                log.error('ps tag inside another ps tag')
            container = Container(**attributes)
        elif name == 'pstext':
            if fragment is not None:
                log.error('pstext tag inside another pstext tag')
            fragment = Fragment(**attributes)
            if container is not None:
                if container.fragment is not None:
                    log.error('multiple pstext tags inside ps tag')
                container.fragment = fragment
        elif fragment is not None:
            if name != 'a' and name != 'anchor':
                raise ParseError
            fragment.start_element(name, **attributes)

    def EndElementHandler(name):
        global container, fragment
        if name == 'ps':
            if container is None:
                log.error('closing ps tag without opening tag')
            container = None
        elif name == 'pstext':
            if fragment is None:
                log.error('closing pstext tag without opening tag')
            fragment.end(is_shared_pseudocode, do_print)
            fragment = None
        elif fragment is not None:
            fragment.end_element(name)

    def CharacterDataHandler(data):
        # some files contain indentation errors
        if path.endswith('/mrs_br.xml'):
            data = data.replace('       UNPREDICTABLE;',
                                '        UNPREDICTABLE;')
        if path.endswith('/vcmla.xml'):
            data = data.replace('               element',
                                '                element')
        if path.endswith('/vcvt_xs.xml'):
            data = data.replace('     when ',
                                '    when ')
        if fragment is not None:
            fragment.character_data(data)

    p = xml.parsers.expat.ParserCreate(namespace_separator = '!')
    p.StartElementHandler = StartElementHandler
    p.EndElementHandler = EndElementHandler
    p.CharacterDataHandler = CharacterDataHandler

    f = open(path, 'rb')

    log.p = p
    try:
        p.ParseFile(f)
    except xml.parsers.expat.ExpatError as e:
        log.lineno = e.lineno - 1
        log.error("%s" % e)

    f.close()

def main():
    base_dir = sys.argv[1]
    for fn in sorted(os.listdir(base_dir)):
        if not fn.endswith('.xml') or fn == 'onebigfile.xml':
            continue
        path = os.path.join(base_dir, fn)
        #print()
        #print('###', path)
        parse_file(path, fn == 'shared_pseudocode.xml', fn == 'ldm_u.xml')

    #ns.global_ns.__print__('| ')

    scope.process_namespace(ns.global_ns)

if __name__ == '__main__':
    main()




# Magic word: if then elsif else for to IN UNDEFINED UNPREDICTABLE
#
# Identifier, linked:
#         ConditionPassed
#         EL2
#         M32_User
#         M32_System
#         BitCount
#         R
#         Rmode
#         MemA
#         UInt
#         BitCount
#
# Identifier, not linked:
#         EncodingSpecificOperations
#         PSTATE.EL
#         PSTATE.M
#         registers<...>
#         (... values from instruction ...)
#         (... self-defined variables ...)
#
# Special characters: ( ) ; == . { , } = * [ ] - < > ||
#
# Numbers: [0-9]+
#
# ?: '1'
#
# Comments: //...
