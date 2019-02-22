#!/usr/bin/env python
import sys, xml.parsers.expat
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
        self.inside_a = False

    def character_data(self, data):
        self.buf.append(data)

    def start_element_a(self, link, file, hover):
        if self.buf:
            try:
                self.tokenizer.process(''.join(self.buf))
            except LexError as e:
                e.report()
                sys.exit(1)
            del self.buf[:]

        if self.inside_a:
            log.error('a tag inside another a tag in pstext tag')
            return
        self.inside_a = True
        #print link, file, hover

    def end_element_a(self):
        assert self.inside_a
        self.inside_a = False

        try:
            self.tokenizer.process_a(''.join(self.buf))
        except LexError as e:
            e.report()
            sys.exit(1)
        del self.buf[:]

    def end(self):
        if self.buf:
            try:
                self.tokenizer.process(''.join(self.buf))
            except LexError as e:
                e.report()
                sys.exit(1)
            del self.buf[:]
        self.tokenizer.process_end()

        #print '{'
        #for token in self.tokens:
        #    print '\t' + str(token)
        #print '}'

        tokens = self.tokenizer.tokens

        try:
          if tokens[-1] == token.SEMICOLON or isinstance(tokens[-1], list):
            body = stmt.parse_block(tokens)
            print
            for statement in body:
                statement.__print__('')
            print
          else:
            expression = tstream.parse(tokens, 0, len(tokens), expr.parse3)
            print
            print str(expression)
            print
        except ParseError as e:
            e.report()
            sys.exit(1)


container = None
fragment = None

def main():
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
            if name != 'a':
                raise ParseError
            fragment.start_element_a(**attributes)

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
            fragment.end()
            fragment = None
        elif fragment is not None:
            if name != 'a':
                raise ParseError
            fragment.end_element_a()

    def ProcessingInstructionHandler(target, data):
        #print 'ProcessingInstruction', repr(target), repr(data)
        pass

    def CharacterDataHandler(data):
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

    f = open(sys.argv[1])

    log.p = p
    try:
        p.ParseFile(f)
    except xml.parsers.expat.ExpatError as e:
        log.lineno = e.lineno - 1
        log.error("%s" % e)

    f.close()

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
