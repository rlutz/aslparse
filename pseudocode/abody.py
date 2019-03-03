import expr, stmt, decl, ns, abody

class SemanticError(Exception):
    pass

def lookup(name, local_dict):
    if len(name) == 1:
        try:
            return local_dict[name[0].name]
        except KeyError:
            pass
    return ns.lookup(name)

def process_namespace(namespace):
    for name, value in sorted(namespace.members.iteritems()):
        print
        print '###', name
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
        local_dict = {}
        if declaration.result_name is not None:
            #print 'Result name:', declaration.result_name.name
            local_dict[declaration.result_name.name] = None
        for param_type, param_name, by_reference in declaration.parameters:
            #print 'Parameter:', param_name.name
            local_dict[param_name.name] = None
        process_body(declaration.body, local_dict)

def process_body(body, local_dict):
    local_dict = local_dict.copy()
    for statement in body:
        # also, process value LHS!
        if isinstance(statement, stmt.Assignment) and \
           isinstance(statement.lhs, expr.Identifier) and \
           statement.lhs.name.name not in local_dict: # or global, TODO
            #print 'implicit variable:', statement.lhs.name.name
            local_dict[statement.lhs.name.name] = None
        elif isinstance(statement, stmt.ConstantAssignment):
            assert isinstance(statement.lhs, expr.Identifier)
            #print 'constant variable:', statement.lhs.name.name
            local_dict[statement.lhs.name.name] = None
        elif isinstance(statement, stmt.Declaration):
            for lhs, expression in statement.variables:
                assert isinstance(lhs, expr.Identifier)
                #print 'variable:', lhs.name.name
                local_dict[lhs.name.name] = None

    for statement in body:
        process_statement(statement, local_dict)

def process_statement(statement, local_dict):
    if isinstance(statement, stmt.Assignment):
        process_lhs(statement.lhs, local_dict)
        process_expression(statement.expression, local_dict)
    elif isinstance(statement, stmt.ConstantAssignment):
        process_lhs(statement.lhs, local_dict)
        process_expression(statement.expression, local_dict)
    elif isinstance(statement, stmt.Declaration):
        for lhs, expression in statement.variables:
            process_lhs(lhs, local_dict)
            if expression is not None:
                process_expression(expression, local_dict)
    elif isinstance(statement, stmt.FunctionCall):
        process_expression(statement.func, local_dict)
        for arg in statement.args:
            process_expression(arg, local_dict)
    elif isinstance(statement, stmt.See):
        pass
    elif isinstance(statement, stmt.Undefined):
        pass
    elif isinstance(statement, stmt.Unpredictable):
        pass
    elif isinstance(statement, stmt.ImplementationDefined):
        pass
    elif isinstance(statement, stmt.If):
        process_expression(statement.expression, local_dict)
        process_body(statement.then_body, local_dict)
        #if statement.else_body is not None:
        process_body(statement.else_body, local_dict)
    elif isinstance(statement, stmt.For):
        process_expression(statement.start, local_dict)
        process_expression(statement.stop, local_dict)
        process_body(statement.body, local_dict)
    elif isinstance(statement, stmt.While):
        process_expression(statement.condition, local_dict)
        process_body(statement.body, local_dict)
    elif isinstance(statement, stmt.Repeat):
        process_body(statement.body, local_dict)
        process_expression(statement.condition, local_dict)
    elif isinstance(statement, stmt.Case):
        process_expression(statement.expression, local_dict)
        for clause in statement.clauses:
            #if clause.body is not None:
            process_body(clause.body, local_dict)
    elif isinstance(statement, stmt.Assert):
        process_expression(statement.expression, local_dict)
    elif isinstance(statement, stmt.Return):
        if statement.value is not None:
            process_expression(statement.value, local_dict)
    elif isinstance(statement, stmt.LocalDeclaration):
        assert isinstance(statement.declaration, decl.Enumeration)
    else:
        assert False

def process_lhs(expression, local_dict):
    if isinstance(expression, expr.Identifier):
        try:
            abody.lookup([expression.name], local_dict)
        except ns.LookupError:
            print "can't lookup", str(expression.name)
        else:
            pass#print "OK", str(expression.name)
    elif isinstance(expression, expr.QualifiedIdentifier):
        pass
    elif isinstance(expression, expr.Arguments):
        if expression.method != '[]' and expression.method != '<>':
            raise SemanticError(expression.method + ' call is not a valid LHS')
        process_expression(expression.func, local_dict)
        for arg in expression.args:
            if isinstance(arg, tuple):
                process_expression(arg[0], local_dict)
                process_expression(arg[2], local_dict)
            else:
                process_expression(arg, local_dict)
    elif isinstance(expression, expr.Bits):
        for element in expression.elements:
            process_lhs(element, local_dict)
    elif isinstance(expression, expr.Values):
        for member in expression.members:
            process_lhs(member, local_dict)
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

def process_expression(expression, local_dict):
    if isinstance(expression, expr.Identifier):
        try:
            abody.lookup([expression.name], local_dict)
        except ns.LookupError:
            print "can't lookup", str(expression.name)
        else:
            pass#print "OK", str(expression.name)
    elif isinstance(expression, expr.QualifiedIdentifier):
        pass
    elif isinstance(expression, expr.Arguments):
        process_expression(expression.func, local_dict)
        for arg in expression.args:
            if isinstance(arg, tuple):
                process_expression(arg[0], local_dict)
                process_expression(arg[2], local_dict)
            else:
                process_expression(arg, local_dict)
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
            process_expression(element, local_dict)
    elif isinstance(expression, expr.Values):
        for member in expression.members:
            process_expression(member, local_dict)
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
