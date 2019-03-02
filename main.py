#!/usr/bin/env python
import os, sys, xml.parsers.expat
from pseudocode import *
from pseudocode import LexError, ParseError

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

    def end(self, is_shared_pseudocode):
        try:
            self.tokenizer.process(''.join(self.buf) + '\n')
            self.tokenizer.process_end()
        except LexError as e:
            e.report()
            sys.exit(1)
        del self.buf[:]

        #print '{'
        #for token in self.tokens:
        #    print '\t' + str(token)
        #print '}'

        tokens = self.tokenizer.tokens

        try:
          if not tokens:
            print
            print '// empty'
            print
          elif (tokens[-1] == token.NEWLINE and
                tokens[-2] == token.SEMICOLON) \
                  or isinstance(tokens[-1], list) \
                  or tokens[0] == token.rw['type']:
            if is_shared_pseudocode:
                body = stmt.parse_block(tokens, decl.parse)
            else:
                body = stmt.parse_block(tokens, stmt.parse_statement)
            print
            for statement in body:
                statement.__print__('')
            print
          else:
            assert tokens[-1] == token.NEWLINE
            expression = tstream.parse(tokens, 0, len(tokens) - 1,
                                       expr.parse_ternary)
            print
            print str(expression)
            print
        except ParseError as e:
            e.report()
            sys.exit(1)


container = None
fragment = None

def parse_file(path, is_shared_pseudocode):
    p = xml.parsers.expat.ParserCreate(namespace_separator = '!')

    def XmlDeclHandler(version, encoding, standalone):
        #print 'XmlDecl', repr(version), repr(encoding), repr(standalone)
        pass

    def StartDoctypeDeclHandler(doctypeName, systemId, publicId, has_internal_subset):
        #print 'StartDoctypeDecl', repr(doctypeName), repr(systemId), repr(publicId), repr(has_internal_subset)
        pass

    def EndDoctypeDeclHandler():
        #print 'EndDoctypeDecl'
        pass

    def ElementDeclHandler(name, model):
        print 'ElementDecl', repr(name), repr(model)

    def AttlistDeclHandler(elname, attname, type, default, required):
        print 'AttlistDecl', repr(elname), repr(attname), repr(type), repr(default), repr(required)

    def StartElementHandler(name, attributes):
        global container, fragment
        #print 'StartElement', repr(name), repr(attributes)
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
        #print 'EndElement', repr(name)
        if name == 'ps':
            if container is None:
                log.error('closing ps tag without opening tag')
            container = None
        elif name == 'pstext':
            if fragment is None:
                log.error('closing pstext tag without opening tag')
            fragment.end(is_shared_pseudocode)
            fragment = None
        elif fragment is not None:
            fragment.end_element(name)

    def ProcessingInstructionHandler(target, data):
        #print 'ProcessingInstruction', repr(target), repr(data)
        pass

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
        #print 'CharacterData', repr(data)

    def UnparsedEntityDeclHandler(entityName, base, systemId, publicId, notationName):
        print 'UnparsedEntityDecl', repr(entityName), repr(base), repr(systemId), repr(publicId), repr(notationName)

    def EntityDeclHandler(entityName, is_parameter_entity, value, base, systemId, publicId, notationName):
        print 'EntityDecl', repr(entityName), repr(is_parameter_entity), repr(value), repr(base), repr(systemId), repr(publicId), repr(notationName)

    def NotationDeclHandler(notationName, base, systemId, publicId):
        print 'NotationDecl', repr(notationName), repr(base), repr(systemId), repr(publicId)

    def StartNamespaceDeclHandler(prefix, uri):
        print 'StartNamespaceDecl', repr(prefix), repr(uri)

    def EndNamespaceDeclHandler(prefix):
        print 'EndNamespaceDecl', repr(prefix)

    def CommentHandler(data):
        #print 'Comment', repr(data)
        pass

    def StartCdataSectionHandler():
        print 'StartCdataSection'

    def EndCdataSectionHandler():
        print 'EndCdataSection'

    def DefaultHandler(data):
        if data.strip('\n'):
            log.error('Unexpected toplevel data: %s' % repr(data))

    def NotStandaloneHandler():
        #print 'NotStandalone'
        return 1

    def ExternalEntityRefHandler(context, base, systemId, publicId):
        print 'ExternalEntityRef', repr(context), repr(base), repr(systemId), repr(publicId)
        return 0

    p.XmlDeclHandler = XmlDeclHandler
    p.StartDoctypeDeclHandler = StartDoctypeDeclHandler
    p.EndDoctypeDeclHandler = EndDoctypeDeclHandler
    p.ElementDeclHandler = ElementDeclHandler
    p.AttlistDeclHandler = AttlistDeclHandler
    p.StartElementHandler = StartElementHandler
    p.EndElementHandler = EndElementHandler
    p.ProcessingInstructionHandler = ProcessingInstructionHandler
    p.CharacterDataHandler = CharacterDataHandler
    p.UnparsedEntityDeclHandler = UnparsedEntityDeclHandler
    p.EntityDeclHandler = EntityDeclHandler
    p.NotationDeclHandler = NotationDeclHandler
    p.StartNamespaceDeclHandler = StartNamespaceDeclHandler
    p.EndNamespaceDeclHandler = EndNamespaceDeclHandler
    p.CommentHandler = CommentHandler
    p.StartCdataSectionHandler = StartCdataSectionHandler
    p.EndCdataSectionHandler = EndCdataSectionHandler
    p.DefaultHandler = DefaultHandler
    p.NotStandaloneHandler = NotStandaloneHandler
    p.ExternalEntityRefHandler = ExternalEntityRefHandler

    f = open(path)

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
        print
        print '###', path
        parse_file(path, fn == 'shared_pseudocode.xml')

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
