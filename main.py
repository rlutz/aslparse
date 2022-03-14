#!/usr/bin/python3
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

import os
import sys
import xml.parsers.expat

from pseudocode import *

class Progress:
    def __init__(self, msg):
        self.msg = msg

    def __enter__(self):
        sys.stderr.write(self.msg + ' ...')
        sys.stderr.flush()

    def __exit__(self, *exc_info):
        sys.stderr.write('\x1b[u\x1b[K')

class Fragment:
    def __init__(self, file_processor,
                 mayhavelinks, section = None, rep_section = None):
        self.file_processor = file_processor

        if file_processor.container is None:
            self.name = None
            assert section is None
            assert rep_section is None
        else:
            self.name = file_processor.container.name
            assert self.name is not None
            assert (file_processor.container.secttype,
                    section, rep_section) in {
                ('noheading', 'Decode', 'decode'),
                ('Operation', 'Execute', 'execute'),
                ('Library', 'Functions', 'functions'),
                ('Shared Decode', 'Postdecode', 'postdecode')
            }
        assert mayhavelinks == '1'
        self.section = section

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
            elif is_shared_pseudocode:
                self.body = stmt.parse_block(tokens, decl.parse)
                for declaration in self.body:
                    ns.process(declaration)
            elif self.name is not None:
                self.body = stmt.parse_block(tokens, stmt.parse_statement)
            else:
                assert tokens[-1] == token.NEWLINE
                self.expression = tstream.parse(tokens, 0, len(tokens) - 1,
                                                expr.parse_ternary)
        except ParseError as e:
            e.report()
            sys.exit(1)

class Container:
    def __init__(self, name, mylink, enclabels, sections, secttype):
        self.name = name
        if secttype in {'Operation', 'Shared Decode'}:
            assert mylink == 'commonps'
        else:
            assert mylink == name.replace('/', '.')
        assert enclabels == ''
        assert sections == '1'
        assert secttype in {'noheading', 'Library',
                            'Operation', 'Shared Decode'}
        self.secttype = secttype

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

        with Progress('processing %s' % fn):
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

def escape_html(s):
    return s.replace('&', '&amp;').replace('"', '&quot;') \
            .replace('<', '&lt;').replace('>', '&gt;')

def main(base_dir):
    sys.stderr.write('\x1b[s')

    file_processors = [FileProcessor(base_dir, fn)
                       for fn in sorted(os.listdir(base_dir))
                       if fn[0] != '.' and fn.endswith('.xml')
                                       and fn != 'onebigfile.xml']

    #for l in ns.global_ns.dump():
    #    print('| ' + l)

    with Progress('resolving library'):
        scope.process_namespace(ns.global_ns)

    with Progress('writing output'):
        with open('output.html', 'w') as f:
            f.write('''\
<!DOCTYPE html>
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
    <title>ASL snippets</title>
    <link href="style.css" rel="stylesheet" type="text/css">
  </head>
  <body>
''')
            for file_processor in file_processors:
                f.write('<h3>%s</h3>\n' % file_processor.fn)
                for fragment in file_processor.fragments:
                    if fragment.name is not None:
                        f.write('%s<br>\n' % escape_html(fragment.name))
                    f.write('<pre class="sect_%s">'
                              % str(fragment.section).lower())
                    if fragment.body is not None:
                        for statement in fragment.body:
                            for l in statement.dump():
                                f.write(escape_html(l) + '\n')
                    elif fragment.expression is not None:
                        s = str(fragment.expression)
                        f.write(escape_html(s) + '\n')
                    else:
                        f.write('// empty\n')
                    f.write('</pre>\n')

            f.write('</body></html>\n')

if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1].startswith('-'):
        sys.stderr.write(
            "Usage: %s path/to/ISA_v85A_AArch32_xml_00bet9/\n" % sys.argv[0])
        sys.stderr.write(
            "       %s path/to/ISA_v85A_A64_xml_00bet9/\n" % sys.argv[0])
        sys.exit(1)
    main(sys.argv[1])
