import expr, stmt, dtype, decl, ns, scope

class SemanticError(Exception):
    pass

class Scope:
    def __init__(self, declaration):
        assert isinstance(declaration, decl.Function)
        self.local_dict = {}
        if declaration.result_type is not None:
            self.process_signature_type(declaration.result_type)
        if declaration.result_name is not None:
            self.add_local_variable(declaration.result_type,
                                    declaration.result_name)
        for param_type, param_name, by_reference in declaration.parameters:
            self.process_signature_type(param_type)
            self.add_local_variable(param_type, param_name)
        if declaration.body is not None:
            self.crawl_body(declaration.body)

    # type is mentioned in function signature -> extract templating parameters
    def process_signature_type(self, datatype):
        if isinstance(datatype, dtype.Bit):
            pass
        elif isinstance(datatype, dtype.Bits):
            self.process_signature_expr(datatype.expression)
        elif isinstance(datatype, dtype.Boolean):
            pass
        elif isinstance(datatype, dtype.Integer):
            pass
        elif isinstance(datatype, dtype.Compound):
            for partial_type in datatype.partial_types:
                self.process_signature_type(partial_type)
        elif isinstance(datatype, dtype.Custom):
            pass
        elif isinstance(datatype, dtype.Void):
            pass
        elif isinstance(datatype, dtype.Array):
            self.process_signature_type(datatype.base)
            self.process_signature_expr(datatype.start)
            self.process_signature_expr(datatype.stop)
        else:
            assert None

    # expression is mentioned in function signature -> templating parameter
    def process_signature_expr(self, expression):
        if isinstance(expression, expr.Identifier):
            self.local_dict[expression.name.name] = None
        elif isinstance(expression, expr.Operator):
            self.process_signature_expr(expression.arg0)
            self.process_signature_expr(expression.arg1)
        else:
            assert isinstance(expression, expr.Numeric)

    def add_local_variable(self, datatype, name):
        self.local_dict[name.name] = None

    def resolve(self, single_name):
        try:
            return self.local_dict[single_name.name]
        except KeyError:
            pass
        return ns.lookup([single_name])

    # find local variables/constants and add them to the scope
    def crawl_body(self, body):
        for statement in body:
            self.crawl_statement(statement)

    def crawl_statement(self, statement):
        if isinstance(statement, stmt.Assignment):
            self.crawl_lhs(statement.lhs)
        elif isinstance(statement, stmt.ConstantAssignment):
            self.plain_lhs(statement.lhs)
        elif isinstance(statement, stmt.Declaration):
            for lhs, expression in statement.variables:
                self.plain_lhs(lhs)
        elif isinstance(statement, stmt.If):
            self.crawl_body(statement.then_body)
            if True: # statement.else_body is not None:
                self.crawl_body(statement.else_body)
        elif isinstance(statement, stmt.For):
            self.plain_lhs(statement.var)
            self.crawl_body(statement.body)
        elif isinstance(statement, stmt.While):
            self.crawl_body(statement.body)
        elif isinstance(statement, stmt.Repeat):
            self.crawl_body(statement.body)
        elif isinstance(statement, stmt.Case):
            for clause in statement.clauses:
                if True: # clause.body is not None:
                    self.crawl_body(clause.body)
        elif isinstance(statement, stmt.LocalDeclaration):
            assert isinstance(statement.declaration, decl.Enumeration)
            for value in statement.declaration.values:
                assert value.name not in self.local_dict
                self.local_dict[value.name] = None

    def crawl_lhs(self, lhs):
        if isinstance(lhs, expr.Identifier):
            if lhs.name.name not in self.local_dict:
                try:
                    ns.lookup([lhs.name])
                except ns.LookupError:
                    self.local_dict[lhs.name.name] = None
        elif isinstance(lhs, expr.Values):
            for member in lhs.members:
                self.crawl_lhs(member)

    # a "plain" LHS (constant/variable declaration or for statement)
    # must be a plain identifier and always defines a local variable
    def plain_lhs(self, lhs):
        assert isinstance(lhs, expr.Identifier)
        #TODO: handle nested scopes
        #assert lhs.name.name not in self.local_dict
        try:
            ns.lookup([lhs.name])
        except ns.LookupError:
            pass
        else:
            pass # print 'OVERRIDING "%s"' % str(lhs.name)
        self.local_dict[lhs.name.name] = None


def process_namespace(namespace):
    for name, value in sorted(namespace.members.iteritems()):
        #print
        #print '###', name
        process_declaration(value)

def process_declaration(declaration):
    if not isinstance(declaration, ns.Function):
        return
    for signature, declaration in declaration.signatures:
        #print name
        #print signature
        #print declaration.__class__.__name__
        if declaration.body is None:
            continue
        scope = Scope(declaration)
        process_body(declaration.body, scope)

def process_body(body, scope):
    for statement in body:
        process_statement(statement, scope)

def process_statement(statement, scope):
    if isinstance(statement, stmt.Assignment):
        process_lhs(statement.lhs, scope)
        process_expression(statement.expression, scope)
    elif isinstance(statement, stmt.ConstantAssignment):
        process_lhs(statement.lhs, scope)
        process_expression(statement.expression, scope)
    elif isinstance(statement, stmt.Declaration):
        for lhs, expression in statement.variables:
            process_lhs(lhs, scope)
            if expression is not None:
                process_expression(expression, scope)
    elif isinstance(statement, stmt.FunctionCall):
        process_expression(statement.func, scope)
        for arg in statement.args:
            process_expression(arg, scope)
    elif isinstance(statement, stmt.See):
        pass
    elif isinstance(statement, stmt.Undefined):
        pass
    elif isinstance(statement, stmt.Unpredictable):
        pass
    elif isinstance(statement, stmt.ImplementationDefined):
        pass
    elif isinstance(statement, stmt.If):
        process_expression(statement.expression, scope)
        process_body(statement.then_body, scope)
        #if statement.else_body is not None:
        process_body(statement.else_body, scope)
    elif isinstance(statement, stmt.For):
        process_expression(statement.start, scope)
        process_expression(statement.stop, scope)
        process_body(statement.body, scope)
    elif isinstance(statement, stmt.While):
        process_expression(statement.condition, scope)
        process_body(statement.body, scope)
    elif isinstance(statement, stmt.Repeat):
        process_body(statement.body, scope)
        process_expression(statement.condition, scope)
    elif isinstance(statement, stmt.Case):
        process_expression(statement.expression, scope)
        for clause in statement.clauses:
            #if clause.body is not None:
            process_body(clause.body, scope)
    elif isinstance(statement, stmt.Assert):
        process_expression(statement.expression, scope)
    elif isinstance(statement, stmt.Return):
        if statement.value is not None:
            process_expression(statement.value, scope)
    elif isinstance(statement, stmt.LocalDeclaration):
        assert isinstance(statement.declaration, decl.Enumeration)
    else:
        assert False

def process_lhs(expression, scope):
    if isinstance(expression, expr.Identifier):
        try:
            scope.resolve(expression.name)
        except ns.LookupError:
            print "can't lookup", str(expression.name)
        else:
            pass#print "OK", str(expression.name)
    elif isinstance(expression, expr.QualifiedIdentifier):
        pass
    elif isinstance(expression, expr.Arguments):
        if expression.method != '[]' and expression.method != '<>':
            raise SemanticError(expression.method + ' call is not a valid LHS')
        process_expression(expression.func, scope)
        for arg in expression.args:
            if isinstance(arg, tuple):
                process_expression(arg[0], scope)
                process_expression(arg[2], scope)
            else:
                process_expression(arg, scope)
    elif isinstance(expression, expr.Bits):
        for element in expression.elements:
            process_lhs(element, scope)
    elif isinstance(expression, expr.Values):
        for member in expression.members:
            process_lhs(member, scope)
    elif isinstance(expression, expr.Omitted):
        pass
    elif isinstance(expression, expr.Set) or \
         isinstance(expression, expr.Numeric) or \
         isinstance(expression, expr.Unary) or \
         isinstance(expression, expr.Operator) or \
         isinstance(expression, expr.Ternary) or \
         isinstance(expression, expr.Unknown) or \
         isinstance(expression, expr.ImplementationDefined) or \
         isinstance(expression, expr.Primitive):
        raise SemanticError(
            expr.__class__.__name__ + ' expression is not a valid LHS')
    else:
        assert False

def process_expression(expression, scope):
    if isinstance(expression, expr.Identifier):
        try:
            scope.resolve(expression.name)
        except ns.LookupError:
            print "can't lookup", str(expression.name)
        else:
            pass#print "OK", str(expression.name)
    elif isinstance(expression, expr.QualifiedIdentifier):
        pass
    elif isinstance(expression, expr.Arguments):
        process_expression(expression.func, scope)
        for arg in expression.args:
            if isinstance(arg, tuple):
                process_expression(arg[0], scope)
                process_expression(arg[2], scope)
            else:
                process_expression(arg, scope)
    elif isinstance(expression, expr.Set):
        pass
    elif isinstance(expression, expr.Numeric):
        pass
    elif isinstance(expression, expr.Unary):
        pass
    elif isinstance(expression, expr.Operator):
        pass
    elif isinstance(expression, expr.Ternary):
        pass
    elif isinstance(expression, expr.Bits):
        for element in expression.elements:
            process_expression(element, scope)
    elif isinstance(expression, expr.Values):
        for member in expression.members:
            process_expression(member, scope)
    elif isinstance(expression, expr.Omitted):
        raise SemanticError('"-" can only be used as LHS')
    elif isinstance(expression, expr.Unknown):
        pass
    elif isinstance(expression, expr.ImplementationDefined):
        pass
    elif isinstance(expression, expr.Primitive):
        pass
    else:
        assert False
