import expr, stmt, decl, ns, abody

class SemanticError(Exception):
    pass

def process_namespace(namespace):
    for name, value in sorted(namespace.members.iteritems()):
        if isinstance(value, ns.Function):
            for signature, declaration in value.signatures:
                #print name
                #print signature
                #print declaration.__class__.__name__
                if declaration.body is not None:
                    process_body(declaration.body)

def process_declaration(declaration):
    if isinstance(declaration, decl.Function):
        process_body(declaration.body)

def process_body(body):
    for statement in body:
        process_statement(statement)

def process_statement(statement):
    if isinstance(statement, stmt.Assignment):
        process_lhs(statement.lhs)
        process_expression(statement.expression)
    elif isinstance(statement, stmt.ConstantAssignment):
        process_lhs(statement.lhs)
        process_expression(statement.expression)
    elif isinstance(statement, stmt.Declaration):
        for lhs, expression in statement.variables:
            process_lhs(lhs)
            process_expression(expression)
    elif isinstance(statement, stmt.FunctionCall):
        process_expression(statement.func)
        for arg in statement.args:
            process_expression(arg)
    elif isinstance(statement, stmt.See):
        pass
    elif isinstance(statement, stmt.Undefined):
        pass
    elif isinstance(statement, stmt.Unpredictable):
        pass
    elif isinstance(statement, stmt.ImplementationDefined):
        pass
    elif isinstance(statement, stmt.If):
        process_expression(statement.expression)
        process_body(statement.then_body)
        #if statement.else_body is not None:
        process_body(statement.else_body)
    elif isinstance(statement, stmt.For):
        process_expression(statement.start)
        process_expression(statement.stop)
        process_body(statement.body)
    elif isinstance(statement, stmt.While):
        process_expression(statement.condition)
        process_body(statement.body)
    elif isinstance(statement, stmt.Repeat):
        process_body(statement.body)
        process_expression(statement.condition)
    elif isinstance(statement, stmt.Case):
        process_expression(statement.expression)
        for clause in statement.clauses:
            #if clause.body is not None:
            process_body(clause.body)
    elif isinstance(statement, stmt.Assert):
        process_expression(statement.expression)
    elif isinstance(statement, stmt.Return):
        process_expression(statement.value)
    elif isinstance(statement, stmt.LocalDeclaration):
        assert isinstance(statement.declaration, decl.Enumeration)
    else:
        assert False

def process_lhs(expression):
    if isinstance(expression, expr.Identifier):
        try:
            ns.lookup([expression.name])
        except ns.LookupError:
            print "can't lookup", str(expression.name)
        else:
            print "OK", str(expression.name)
    elif isinstance(expression, expr.QualifiedIdentifier):
        pass
    elif isinstance(expression, expr.Arguments):
        if expression.method != '[]' and expression.method != '<>':
            raise SemanticError(expression.method + ' call is not a valid LHS')
        process_expression(expression.func)
        for arg in expression.args:
            process_expression(arg)
    elif isinstance(expression, expr.Bits):
        for element in expression.elements:
            process_lhs(element)
    elif isinstance(expression, expr.Values):
        for member in expression.members:
            process_lhs(member)
    elif isinstance(expression, expr.Omitted):
        pass
    elif isinstance(expression, expr.Set) or \
         isinstance(expression, expr.Numeric) or \
         isinstance(expression, expr.Unary) or \
         isinstance(expression, expr.Operator) or \
         isinstance(expression, expr.Ternary) or \
         isinstance(expression, expr.Unknown) or \
         isinstance(expression, expr.ImplementationDefined):
        raise SemanticError(
            expr.__class__.__name__ + ' expression is not a valid LHS')
    else:
        assert False

def process_expression(expression):
    if isinstance(expression, expr.Identifier):
        try:
            ns.lookup([expression.name])
        except ns.LookupError:
            print "can't lookup", str(expression.name)
        else:
            print "OK", str(expression.name)
    elif isinstance(expression, expr.QualifiedIdentifier):
        pass
    elif isinstance(expression, expr.Arguments):
        process_expression(expression.func)
        for arg in expression.args:
            if isinstance(arg, tuple):
                process_expression(arg[0])
                process_expression(arg[2])
            else:
                process_expression(arg)
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
            process_expression(element)
    elif isinstance(expression, expr.Values):
        for member in expression.members:
            process_expression(member)
    elif isinstance(expression, expr.Omitted):
        raise SemanticError('"-" can only be used as LHS')
    elif isinstance(expression, expr.Unknown):
        pass
    elif isinstance(expression, expr.ImplementationDefined):
        pass
    else:
        print expression.__class__.__name__
        assert False
