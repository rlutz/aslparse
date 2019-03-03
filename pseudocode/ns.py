import decl, ns

class Namespace:
    def __init__(self):
        self.members = {}

    def __print__(self, indent):
        print 'namespace'
        for name, value in sorted(self.members.iteritems()):
            print indent + name + ':',
            value.__print__(indent + '    ')

class Function:
    def __init__(self):
        self.signatures = []

    def __print__(self, indent):
        print 'function'
        for signature, decl in self.signatures:
            print indent + signature

class Accessor:
    def __init__(self):
        self.setter = None
        self.getter = None

    def __print__(self, indent):
        print 'accessor'

class Variable:
    def __print__(self, indent):
        print 'variable'

class Array:
    def __print__(self, indent):
        print 'array'

class Enumeration:
    def __print__(self, indent):
        print 'enumeration'

class Struct:
    def __print__(self, indent):
        print 'struct'

class Type:
    def __print__(self, indent):
        print 'type'

global_ns = ns.Namespace()

class LookupError(Exception):
    def __init__(self, name):
        self.name = name

def lookup(name):
    x = global_ns
    for part in name:
        assert isinstance(x, ns.Namespace)
        if not isinstance(part, str):
            part = part.name
        try:
            x = x.members[part]
        except KeyError:
            raise LookupError(name)
    assert not isinstance(x, ns.Namespace)
    return x

def define(name, value):
    x = global_ns
    for i, part in enumerate(name):
        assert isinstance(x, ns.Namespace)
        if not isinstance(part, str):
            part = part.name
        if i == len(name) - 1:
            assert part not in x.members
            x.members[part] = value
            return
        try:
            x = x.members[part]
        except KeyError:
            x.members[part] = ns.Namespace()
            x = x.members[part]

def process(declaration):
    if isinstance(declaration, decl.Function):
        if declaration.functype == decl.FUNCTION:
            try:
                function = ns.lookup(declaration.name)
            except LookupError:
                function = ns.Function()
                ns.define(declaration.name, function)
            assert isinstance(function, ns.Function)
            params = ', '.join('%s %s%s' % (
                                 str(pt), '&' if by_reference else '', str(pi))
                               for pt, pi, by_reference
                                   in declaration.parameters)
            function.signatures.append(
                ('%s (%s)' % (str(declaration.result_type), params),
                 declaration))
        else:
            try:
                accessor = ns.lookup(declaration.name)
            except LookupError:
                accessor = ns.Accessor()
                ns.define(declaration.name, accessor)
            assert isinstance(accessor, ns.Accessor)

            if declaration.functype == decl.GETTER:
                #print '.'.join(str(part) for part in declaration.name)
                #assert accessor.getter is None
                accessor.getter = 1
            elif declaration.functype == decl.SETTER:
                #assert accessor.setter is None
                accessor.setter = 1
            else:
                assert False
    elif isinstance(declaration, decl.Variable):
        for name, expression in declaration.variables:
            ns.define(name, ns.Variable())
            # + (' = ' + str(expression) if expression is not None else '')
    elif isinstance(declaration, decl.Array):
        ns.define(declaration.name, ns.Array())
    elif isinstance(declaration, decl.Enumeration):
        ns.define([declaration.name], ns.Enumeration())
    elif isinstance(declaration, decl.Type):
        ns.define(declaration.name, ns.Struct())
    elif isinstance(declaration, decl.TypeEquals):
        ns.define(declaration.name, ns.Type())
    else:
        assert False
