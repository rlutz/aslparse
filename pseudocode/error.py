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
import traceback

class LexError(Exception):
    def __init__(self, data, pos):
        self.data = data
        self.pos = pos

    def report(self):
        exc_type, exc_value, exc_traceback = sys.exc_info()

        cwd = os.getcwd()
        if not cwd.endswith('/'):
            cwd = cwd + '/'

        sys.stderr.write('\n')
        for fn, lineno, func, text in traceback.extract_tb(exc_traceback):
            if fn.startswith(cwd):
                fn = fn[len(cwd):]
            sys.stderr.write('%-26s%-18s%s\n' % (
                '%s:%s' % (fn, lineno), func, text[:36]))
        del exc_traceback  # avoid circular reference

        start = 0
        while True:
            try:
                p = self.data.index('\n', start) + 1
            except ValueError:
                break
            if p >= self.pos:
                break
            start = p
        try:
            stop = self.data.index('\n', start)
        except ValueError:
            stop = len(self.data)

        sys.stderr.write('\n')
        sys.stderr.write(self.data[start:stop] + '\n')
        sys.stderr.write(' ' * (self.pos - start) + '^\n')

class ParseError(Exception):
    def __init__(self, ts):
        self.ts = ts

    def report(self):
        exc_type, exc_value, exc_traceback = sys.exc_info()

        #sys.stderr.write('Traceback (most recent call last):\n')
        #traceback.print_tb(exc_traceback)

        cwd = os.getcwd()
        if not cwd.endswith('/'):
            cwd = cwd + '/'

        sys.stderr.write('\n')
        for fn, lineno, func, text in traceback.extract_tb(exc_traceback):
            if fn.startswith(cwd):
                fn = fn[len(cwd):]
            sys.stderr.write('%-26s%-18s%s\n' % (
                '%s:%s' % (fn, lineno), func, text[:36]))
        del exc_traceback  # avoid circular reference

        sys.stderr.write('\n')
        for i, t in enumerate(self.ts.tokens):
            if i == self.ts.pos:
                sys.stderr.write('### ')
            else:
                sys.stderr.write('    ')
            if isinstance(t, list):
                sys.stderr.write('%s%s\n' % (
                    ' '.join('[...]' if isinstance(t1, list) else str(t1)
                             for t1 in t[:10]),
                    ' ...' if len(t) > 10 else ''))
            else:
                sys.stderr.write(str(t) + '\n')
