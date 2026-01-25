# Parses a limited subset of Verilog / SystemVerilog

from ..util.nodes import (
    AlwaysBlockNode,
    AssignmentStatementNode,
    BinaryExpressionNode,
    CaseItemNode,
    CaseStatementNode,
    ConcatenationNode,
    ConditionalExpressionNode,
    ConditionalStatementNode,
    ContinuousAssignmentNode,
    DeclarationNode,
    EventExpressionNode,
    ForeverStatementNode,
    ForStatementNode,
    GateInstantiationNode,
    HierarchicalIdentifierNode,
    IdentifierNode,
    IndexExpressionNode,
    ModuleInstantiationNode,
    ModuleNode,
    NullStatementNode,
    NumericNode,
    PortConnectionNode,
    PortNode,
    RangeNode,
    RepeatStatementNode,
    ReplicationNode,
    RootNode,
    SequentialBlockNode,
    UnaryExpressionNode,
    WhileStatementNode,
)
from ..util.structures import PushbackIter
from ..util.tokens import (
    DirectiveToken,
    EndToken,
    IdentifierToken,
    KeywordToken,
    MacroToken,
    NumericToken,
    OperatorToken,
    SemicolonToken,
    Token,
)
from ..util.verilog import (
    BINARY_OPERATORS,
    DIRECTIVES,
    KEYWORDS,
    OPERATOR_PRECEDENCE,
    OPERATORS,
    UNARY_OPERATORS,
)

# === Lexer / Tokenizer ===


def read_ident(it):
    """reads an identifier from the pushback iterator `it`"""

    ident = next(it)
    assert ident.isalpha() or ident in "_\\"
    for c in it:
        if ident[0] == "\\":
            # escaped identifier ends at whitespace
            if c in " \t\n":
                return ident
            else:
                ident += c
        else:
            if c.isalpha() or c.isdigit() or c in "_$":
                ident += c
            else:
                it.pushback(c)
                return ident
    return ident


def read_number(it):
    """reads a numeric literal from the pushback iterator `it`"""

    radix = 10
    apostrophe = False
    sized = False
    size = 0
    signed = True
    negative = False
    empty = True
    value_empty = True
    value = 0

    for c in it:
        # segmentation, e.g. 1_000_000
        if c == "_":
            pass
        # +, - sign
        elif empty and c in "+-":
            empty = False
            negative = c == "-"
        # size and radix, e.g. 8"hff
        elif c == "'":
            assert not apostrophe
            assert not negative
            apostrophe = True
            sized = not empty
            size = value
            value = 0
            empty = False
            value_empty = True
            negative = False
            c = next(it)
            signed = False
            if c.lower() == "s":
                signed = True
                c = next(it)
            radix_map = {"b": 2, "o": 8, "d": 10, "h": 16}
            radix = radix_map[c.lower()]
        # actual digits
        elif c.lower() in "0123456789abcdef":
            empty = False
            value_empty = False
            digit = int(c.lower(), radix)
            value = value * radix + digit
        elif c.lower() in "xz":
            raise NotImplementedError("4-value xz logic unimplemented")
        elif c == ".":
            raise NotImplementedError("Floating-point support unimplemented")
        else:
            it.pushback(c)
            break

    assert not value_empty
    if negative:
        value = -value
    if not sized:
        size = None
    return NumericToken(value=value, signed=signed, size=size)


def tokenize(source):
    """lexes the verilog source code in `source` into tokens"""

    it = PushbackIter(source)
    tokens = []
    for c in it:
        # whitespace
        if c in " \t\n":
            pass
        elif c == "/":
            c = next(it)
            # single line comment
            if c == "/":
                while c != "\n":
                    c = next(it)
            # multi-line comment
            elif c == "*":
                digraph = next(it) + next(it)
                while digraph != "*/":
                    digraph = digraph[-1] + next(it)
            else:
                it.pushback(c)
                tokens.append(OperatorToken(operator="/"))
        # semicolon
        elif c == ";":
            tokens.append(SemicolonToken())
        # directive or macro
        elif c == "`":
            ident = read_ident(it)
            if ident in DIRECTIVES:
                line = ""
                last = ""
                c = next(it)
                while c != "\n" or last == "\\":
                    if c == "\n":
                        # remove the backslash
                        line = line[:-1]
                    line += c
                    last = c
                    c = next(it)
                tokens.append(DirectiveToken(directive=ident, line=line.strip()))
            else:
                tokens.append(MacroToken(name=ident))
        # keyword or identifier
        elif c.isalpha() or c in "_\\":
            it.pushback(c)
            ident = read_ident(it)
            if ident in KEYWORDS:
                tokens.append(KeywordToken(keyword=ident))
            else:
                tokens.append(IdentifierToken(name=ident))
        # numeric literal
        elif c.isdigit() or c == "'":
            it.pushback(c)
            tokens.append(read_number(it))
        # +, -, +:, -: operator or sign of numeric literal
        elif c in "+-":
            n = next(it)
            if n == ":":
                c += n
                tokens.append(OperatorToken(operator=c))
            else:
                it.pushback(n)
                expect_unary_op = True
                if len(tokens) > 0:
                    last_token = tokens[-1]
                    if (
                        isinstance(last_token, IdentifierToken)
                        or isinstance(last_token, MacroToken)
                        or isinstance(last_token, NumericToken)
                        or isinstance(last_token, OperatorToken)
                        and last_token.operator in ")]}"
                    ):
                        expect_unary_op = False
                if n.isdigit() and expect_unary_op:
                    it.pushback(c)
                    tokens.append(read_number(it))
                else:
                    tokens.append(OperatorToken(operator=c))
        # unary, binary and special operators
        # (we make use of the fact that every prefix of an operator is also an operator)
        elif c in OPERATORS:
            while c in OPERATORS:
                c += next(it)
            it.pushback(c[-1])
            c = c[:-1]
            tokens.append(OperatorToken(operator=c))
        else:
            line = ""
            while c != "\n":
                line += c
                c = next(it)
            raise SyntaxError(f"Unexpected Verilog syntax: {line}")

    tokens.append(EndToken())
    return tokens


# === Preprocessor ===


def preproc_macro_line(line):
    """parse arguments to a `define or similar directive"""
    it = PushbackIter(line)
    name = read_ident(it)
    try:
        c = next(it)
        if c == "(":
            raise NotImplementedError(
                "Macros with arguments are not supported at this time"
            )
        else:
            it.pushback(c)
    except StopIteration:
        pass
    contents = tokenize(it)
    last = contents.pop(-1)
    assert isinstance(last, EndToken)
    return name, contents


def preprocess(tokens):
    """preprocess ` directives in tokenized verilog source code"""

    definitions = {}
    preproc_tokens = []
    ifdef_level = 0
    ifdef_false_level = 0

    for t in tokens:
        assert isinstance(t, Token)
        if isinstance(t, DirectiveToken):
            # `ifdef
            if t.directive == "ifdef":
                name, contents = preproc_macro_line(t.line)
                assert not contents
                if ifdef_false_level > 0 or name not in definitions:
                    ifdef_false_level += 1
                else:
                    ifdef_level += 1

            # `ifndef
            elif t.directive == "ifndef":
                name, contents = preproc_macro_line(t.line)
                assert not contents
                if ifdef_false_level > 0 or name in definitions:
                    ifdef_false_level += 1
                else:
                    ifdef_level += 1

            # `else
            elif t.directive == "else":
                assert not t.line
                assert ifdef_level > 0 or ifdef_false_level > 0
                if ifdef_false_level == 1:
                    ifdef_false_level = 0
                    ifdef_level += 1
                elif ifdef_false_level == 0:
                    ifdef_false_level = 1
                    ifdef_level -= 1

            # `endif
            elif t.directive == "endif":
                assert not t.line
                assert ifdef_level > 0 or ifdef_false_level > 0
                if ifdef_false_level > 0:
                    ifdef_false_level -= 1
                else:
                    ifdef_level -= 1

            elif ifdef_false_level > 0:
                continue

            # `define
            elif t.directive == "define":
                if ifdef_false_level > 0:
                    continue
                name, contents = preproc_macro_line(t.line)
                definitions[name] = contents

            # `undef
            elif t.directive == "undef":
                if ifdef_false_level > 0:
                    continue
                name, contents = preproc_macro_line(t.line)
                assert not contents
                definitions.pop(name, None)

            # `include
            elif t.directive == "include":
                raise NotImplementedError(
                    "Include directives are not supported at this time"
                )

            # `default_nettype
            elif t.directive == "default_nettype":
                if t.line.strip() != "none":
                    raise NotImplementedError(
                        "Only `default_nettype none is supported, and it's assumed by default"
                    )

            else:
                raise NotImplementedError(f"Unsupported directive: `{t.directive}")

        elif ifdef_false_level > 0:
            continue

        elif isinstance(t, MacroToken):
            preproc_tokens.append(definitions[t.name])

        else:
            preproc_tokens.append(t)

    return preproc_tokens


# === Parser ===


def parse(tokens, config):
    """parses the tokenized verilog source code into a syntax tree"""

    it = PushbackIter(preprocess(tokens))
    modules = []

    for t in it:
        assert isinstance(t, Token)
        if isinstance(t, KeywordToken) and t.keyword == "module":
            it.pushback(t)
            module = parse_module(it)
            modules.append(module)

        elif isinstance(t, EndToken):
            break

        else:
            raise SyntaxError(f"Expected module or EOF, found {t}")

    return RootNode(modules=modules, config=config)


def parse_module(it):
    """parses a verilog module"""

    t = next(it)
    assert isinstance(t, KeywordToken) and t.keyword == "module"

    t = next(it)
    assert isinstance(t, IdentifierToken)
    name = t.name

    t = next(it)
    if isinstance(t, OperatorToken) and t.operator == "#":
        raise NotImplementedError("Parametric modules are not supported at this time")
    assert isinstance(t, OperatorToken) and t.operator == "("

    # parse the argument list

    ports = parse_declarations(it, module_port_list=True)
    t = next(it)
    assert isinstance(t, SemicolonToken)

    # parse the module body

    body = []
    while True:
        t = next(it)

        if isinstance(t, KeywordToken):
            if t.keyword == "endmodule":
                break

            elif t.keyword in ("always", "always_comb", "always_ff", "always_latch"):
                it.pushback(t)
                body.append(parse_always_block(it))

            elif t.keyword == "assign":
                it.pushback(t)
                body.extend(parse_continuous_assignments(it))

            elif t.keyword in ("wire", "reg", "logic"):
                it.pushback(t)
                body.extend(parse_declarations(it))

            elif t.keyword in ("buf", "not", "and", "nand", "or", "nor", "xor", "xnor"):
                it.pushback(t)
                body.append(parse_gate_instantiation(it))

            elif t.keyword == "initial":
                raise NotImplementedError("Initial blocks are not supported")

            elif t.keyword in ("generate", "genvar"):
                raise NotImplementedError(
                    "Generate blocks are not supported at this time"
                )

            elif t.keyword in ("input", "output", "inout"):
                raise NotImplementedError(
                    "Only Verilog-2001 style port declarations are supported at this time"
                )

            elif t.keyword in ("parameter", "localparam"):
                raise NotImplementedError("Parameters are not supported at this time")

            else:
                raise SyntaxError(f"Unexpected token {t} in module body")

        elif isinstance(t, IdentifierToken):
            it.pushback(t)
            body.append(parse_module_instantiation(it))

        elif isinstance(t, SemicolonToken):
            pass

        else:
            raise SyntaxError(f"Unexpected token {t} in module body")

    return ModuleNode(name=name, ports=ports, body=body)


def parse_identifier(it):
    """parse an identifier, including indexed & hierarchical identifiers"""

    t = next(it)
    assert isinstance(t, IdentifierToken)
    ident = IdentifierNode(name=t.name)
    t = next(it)
    while isinstance(t, OperatorToken) and t.operator in "[.":
        has_variable_index = False
        has_range_index = False

        # indexed
        while isinstance(t, OperatorToken) and t.operator == "[":
            if has_range_index:
                raise SyntaxError("Only the last index can be a range")
            index, is_constant = parse_index(it, return_constant=True)
            if not is_constant:
                has_variable_index = True
            if issubclass(index, RangeNode):
                has_range_index = True
            ident = IndexExpressionNode(identifier=ident, index=index)
            t = next(it)

        # hierarchical
        if isinstance(t, OperatorToken) and t.operator == ".":
            if has_range_index:
                raise SyntaxError(
                    "Hierarchical identifiers cannot use range indices in the parent"
                )
            if has_variable_index:
                raise SyntaxError(
                    "Hierarchical identifiers can only use constant indices in the parent"
                )
            t = next(it)
            assert isinstance(t, IdentifierToken)
            ident = HierarchicalIdentifierNode(parent=ident, name=t.name)
            t = next(it)

    it.pushback(t)
    return ident


def parse_lvalue(it):
    """parse an expression used as a left-value of an assignment"""

    t = next(it)

    if isinstance(t, IdentifierToken):
        it.pushback(t)
        lvalue = parse_identifier(it)

    elif isinstance(t, OperatorToken) and t.operator == "{":
        expressions = []
        while True:
            expressions.append(parse_lvalue(it))
            t = next(it)
            if isinstance(t, OperatorToken) and t.operator == "}":
                break
            elif isinstance(t, OperatorToken) and t.operator == ",":
                continue
            else:
                raise SyntaxError(f"Unexpected token in lvalue concatenation: {t}")
        lvalue = ConcatenationNode(expressions=expressions)

    else:
        raise SyntaxError(f"Unexpected token in lvalue: {t}")

    return lvalue


def parse_primary(it, require_constant=False, return_constant=False):
    """parse a verilog expression without unary, binary or conditional operators"""

    t = next(it)
    # numeric literal
    if isinstance(t, NumericToken):
        is_constant = True
        primary = NumericNode(value=t.value, signed=t.signed, size=t.size)

    # identifier, including indexed & hierarchical identifiers
    elif isinstance(t, IdentifierToken):
        if require_constant:
            raise SyntaxError(f"Constant expression expected, found {t}")
        is_constant = False
        it.pushback(t)
        primary = parse_identifier(it)

    # parenthesised subexpression
    elif isinstance(t, OperatorToken) and t.operator == "(":
        primary, is_constant = parse_expr(
            it, require_constant=require_constant, return_constant=True
        )
        t = next(it)
        assert isinstance(t, OperatorToken) and t.operator == ")"

    # concatenation or replication
    elif isinstance(t, OperatorToken) and t.operator == "{":
        replicate = False
        expr, is_constant = parse_expr(
            it, require_constant=require_constant, return_constant=True
        )
        t = next(it)

        # replication
        if isinstance(t, OperatorToken) and t.operator == "{":
            replicate = True
            if not is_constant:
                raise SyntaxError("Repeat count for replication needs to be constant")
            repeat = expr
            expr, expr_is_constant = parse_expr(
                it, require_constant=require_constant, return_constant=True
            )
            if not expr_is_constant:
                is_constant = False
            t = next(it)

        # concatenation (also as part of replication)
        expressions = [expr]
        while isinstance(t, OperatorToken) and t.operator == ",":
            expr, expr_is_constant = parse_expr(
                it, require_constant=require_constant, return_constant=True
            )
            if not expr_is_constant:
                is_constant = False
            t = next(it)
            expressions.append(expr)

        assert isinstance(t, OperatorToken) and t.operator == "}"

        if replicate:
            t = next(it)
            assert isinstance(t, OperatorToken) and t.operator == "}"
            primary = ReplicationNode(repeat=repeat, expressions=expressions)
        else:
            primary = ConcatenationNode(expressions=expressions)

    else:
        raise SyntaxError(f"Unexpected token in primary expression: {t}")

    if return_constant:
        return primary, is_constant
    else:
        return primary


def parse_expr(it, require_constant=False, return_constant=False, min_precedence=0):
    """parse a verilog expression using the precedence climbing method"""

    t = next(it)

    # unary operator
    if isinstance(t, OperatorToken) and t.operator in UNARY_OPERATORS:
        arg, is_constant = parse_primary(
            it, require_constant=require_constant, return_constant=True
        )
        expr = UnaryExpressionNode(operator=t.operator, argument=arg)

    else:
        it.pushback(t)
        expr, is_constant = parse_primary(
            it, require_constant=require_constant, return_constant=True
        )

    t = next(it)

    while isinstance(t, OperatorToken) and (
        t.operator in BINARY_OPERATORS or t.operator == "?"
    ):
        # conditional (ternary) operator
        if t.operator == "?":
            if min_precedence == 0:
                arg1 = expr
                arg2, arg2_is_constant = parse_expr(
                    it,
                    require_constant=require_constant,
                    return_constant=True,
                    min_precedence=0,
                )
                if not arg2_is_constant:
                    is_constant = False
                t = next(it)
                assert isinstance(t, OperatorToken) and t.operator == ":"
                arg3, arg3_is_constant = parse_expr(
                    it,
                    require_constant=require_constant,
                    return_constant=True,
                    min_precedence=0,
                )
                if not arg3_is_constant:
                    is_constant = False
                expr = ConditionalExpressionNode(
                    condition=arg1, branch1=arg2, branch0=arg3
                )
                t = next(it)
            else:
                break

        # binary operator
        else:
            op = t.operator
            prec = OPERATOR_PRECEDENCE[op]
            if prec >= min_precedence:
                lhs = expr
                rhs, rhs_is_constant = parse_expr(
                    it,
                    require_constant=require_constant,
                    return_constant=True,
                    min_precedence=prec + 1,
                )
                if not rhs_is_constant:
                    is_constant = False
                expr = BinaryExpressionNode(operator=op, arguments=(lhs, rhs))
                t = next(it)
            else:
                break

    it.pushback(t)
    if return_constant:
        return expr, is_constant
    else:
        return expr


def parse_index(it, require_constant=False, return_constant=False):
    """parse a bit-select or part-select where the "[" was already consumed"""

    index, is_constant = parse_expr(
        it, require_constant=require_constant, return_constant=True
    )

    t = next(it)

    # bit-select
    if isinstance(t, OperatorToken) and t.operator == "]":
        if return_constant:
            return index, is_constant
        else:
            return index

    # part-select
    elif isinstance(t, OperatorToken) and t.operator in (":", "+:", "-:"):
        index1 = index
        index2, index2_is_constant = parse_expr(
            it, require_constant=require_constant, return_constant=True
        )
        if not index2_is_constant:
            is_constant = False
        index_range = RangeNode(operator=t.operator, indices=(index1, index2))
        t = next(it)
        assert isinstance(t, OperatorToken) and t.operator == "]"
        if return_constant:
            return index_range, is_constant
        else:
            return index_range


def parse_always_block(it):
    """parse an always block"""

    t = next(it)
    assert isinstance(t, KeywordToken)
    block_type = t.keyword
    assert block_type in ("always", "always_comb", "always_ff", "always_latch")

    if block_type in ("always", "always_ff"):
        t = next(it)
        assert isinstance(t, OperatorToken) and t.operator == "@"
        t = next(it)
        if (
            block_type == "always"
            and isinstance(t, OperatorToken)
            and t.operator == "*"
        ):
            raise NotImplementedError("always @* unsupported, use always_comb instead")
        else:
            assert isinstance(t, OperatorToken) and t.operator == "("
            sensitivity_list = []
            while True:
                t = next(it)
                if isinstance(t, OperatorToken) and t.operator == "*":
                    raise NotImplementedError(
                        "always @(*) unsupported, use always_comb instead"
                    )
                elif isinstance(t, KeywordToken) and t.keyword in (
                    "posedge",
                    "negedge",
                ):
                    event = EventExpressionNode(
                        edge=t.keyword, expression=parse_expr(it)
                    )
                    sensitivity_list.append(event)
                    t = next(it)
                    if isinstance(t, OperatorToken) and t.operator == ",":
                        continue
                    elif isinstance(t, KeywordToken) and t.keyword == "or":
                        continue
                    elif isinstance(t, OperatorToken) and t.operator == ")":
                        break
                    else:
                        raise SyntaxError(
                            f"Unexpected token in always block sensitivity list: {t}"
                        )
    else:
        sensitivity_list = None

    return AlwaysBlockNode(
        block_type=block_type,
        sensitivity_list=sensitivity_list,
        statement=parse_statement(it),
    )


def parse_statement(it, allow_null=False):
    """parse a statement within an always block"""

    t = next(it)

    if isinstance(t, KeywordToken):
        # if
        if t.keyword == "if":
            t = next(it)
            assert isinstance(t, OperatorToken) and t.operator == "("
            condition = parse_expr(it)
            t = next(it)
            assert isinstance(t, OperatorToken) and t.operator == ")"
            branch1 = parse_statement(it, allow_null=True)
            t = next(it)
            if isinstance(t, KeywordToken) and t.keyword == "else":
                branch0 = parse_statement(it, allow_null=True)
            else:
                it.pushback(t)
                branch0 = NullStatementNode()
            return ConditionalStatementNode(
                condition=condition,
                branch0=branch0,
                branch1=branch1,
            )

        # case
        elif t.keyword == "case":
            t = next(it)
            assert isinstance(t, OperatorToken) and t.operator == "("
            expression = parse_expr(it)
            t = next(it)
            assert isinstance(t, OperatorToken) and t.operator == ")"
            cases = []
            while True:
                t = next(it)
                if isinstance(t, KeywordToken) and t.keyword == "endcase":
                    break
                if isinstance(t, KeywordToken) and t.keyword == "default":
                    matches = "default"
                    t = next(it)
                    if not (isinstance(t, OperatorToken) and t.operator == ":"):
                        it.pushback(t)
                else:
                    it.pushback(t)
                    matches = []
                    while True:
                        expr = parse_expr(it)
                        matches.append(expr)
                        t = next(it)
                        if isinstance(t, OperatorToken) and t.operator == ",":
                            continue
                        elif isinstance(t, OperatorToken) and t.operator == ":":
                            break
                        else:
                            raise SyntaxError(
                                f"Unexpected token in case statement: {t}"
                            )
                branch = parse_statement(it, allow_null=True)
                cases.append(CaseItemNode(matches=matches, branch=branch))
            return CaseStatementNode(expression=expression, cases=cases)

        # forever
        elif t.keyword == "forever":
            body = parse_statement(it, allow_null=True)
            return ForeverStatementNode(body=body)

        # repeat
        elif t.keyword == "repeat":
            t = next(it)
            assert isinstance(t, OperatorToken) and t.operator == "("
            count = parse_expr(it)
            t = next(it)
            assert isinstance(t, OperatorToken) and t.operator == ")"
            body = parse_statement(it, allow_null=True)
            return RepeatStatementNode(count=count, body=body)

        # while
        elif t.keyword == "while":
            t = next(it)
            assert isinstance(t, OperatorToken) and t.operator == "("
            condition = parse_expr(it)
            t = next(it)
            assert isinstance(t, OperatorToken) and t.operator == ")"
            body = parse_statement(it, allow_null=True)
            return WhileStatementNode(condition=condition, body=body)

        # for
        elif t.keyword == "for":
            t = next(it)
            assert isinstance(t, OperatorToken) and t.operator == "("
            init_lhs = parse_lvalue(it)
            t = next(it)
            assert isinstance(t, OperatorToken) and t.operator == "="
            init_rhs = parse_expr(it)
            init = AssignmentStatementNode(blocking=True, lhs=init_lhs, rhs=init_rhs)
            t = next(it)
            assert isinstance(t, SemicolonToken)
            condition = parse_expr(it)
            t = next(it)
            assert isinstance(t, SemicolonToken)
            step_lhs = parse_lvalue(it)
            t = next(it)
            assert isinstance(t, OperatorToken) and t.operator == "="
            step_rhs = parse_expr(it)
            step = AssignmentStatementNode(blocking=True, lhs=step_lhs, rhs=step_rhs)
            t = next(it)
            assert isinstance(t, OperatorToken) and t.operator == ")"
            body = parse_statement(it, allow_null=True)
            return ForStatementNode(
                init=init, condition=condition, step=step, body=body
            )

        # begin
        elif t.keyword == "begin":
            statements = []
            t = next(it)
            while not (isinstance(t, KeywordToken) and t.keyword == "end"):
                it.pushback(t)
                statements.append(parse_statement(it, allow_null=True))
                t = next(it)
            return SequentialBlockNode(statements=statements)

        else:
            raise SyntaxError(f"Unexpected token in always block: {t}")

    elif isinstance(t, SemicolonToken):
        if not allow_null:
            raise SyntaxError("Null statement not allowed here")
        return NullStatementNode()

    else:
        it.pushback(t)
        lhs = parse_lvalue(it)
        t = next(it)

        if isinstance(t, OperatorToken) and t.operator == "=":
            blocking = True

        elif isinstance(t, OperatorToken) and t.operator == "<=":
            blocking = False

        else:
            raise SyntaxError(
                f"Unexpected token in always block, expected assignment operator, found: {t}"
            )

        rhs = parse_expr(it)
        t = next(it)
        assert isinstance(t, SemicolonToken)
        return AssignmentStatementNode(blocking=blocking, lhs=lhs, rhs=rhs)


def parse_continuous_assignments(it):
    """parse a statement describing one or more continuous assignments"""

    t = next(it)
    assert isinstance(t, KeywordToken) and t.keyword == "assign"

    assignments = []

    while True:
        lhs = parse_lvalue(it)
        t = next(it)
        assert isinstance(t, OperatorToken) and t.operator == "="
        rhs = parse_expr(it)
        assignments.append(ContinuousAssignmentNode(lhs=lhs, rhs=rhs))
        t = next(it)
        if isinstance(t, SemicolonToken):
            break
        assert isinstance(t, OperatorToken) and t.operator == ","

    return assignments


def parse_declarations(it, module_port_list=False):
    """parse a line describing one or more reg, wire or logic declarations
    (used both for module port lists and inside the module body)"""

    declarations = []
    while True:
        direction = None
        assignment = None
        data_type = "wire"
        signed = False
        index = None

        t = next(it)

        if (
            module_port_list
            and isinstance(t, KeywordToken)
            and t.keyword in ("input", "output", "inout")
        ):
            direction = t.keyword
            t = next(it)

        if isinstance(t, KeywordToken) and t.keyword in ("wire", "reg", "logic"):
            data_type = t.keyword
            t = next(it)

        if isinstance(t, KeywordToken) and t.keyword == "signed":
            signed = True
            t = next(it)

        if isinstance(t, OperatorToken) and t.operator == "[":
            index = parse_index(it, require_constant=True)
            t = next(it)

        if module_port_list and direction is None:
            assert data_type is None
            assert signed is None
            assert range is None
            assert len(declarations) > 0
            last_decl = declarations[-1]
            direction = last_decl.direction
            data_type = last_decl.data_type
            signed = last_decl.signed
            index = last_decl.index

        assert isinstance(t, IdentifierToken)
        name = t.name
        t = next(it)

        if not module_port_list:
            if isinstance(t, OperatorToken) and t.operator == "=":
                expr = parse_expr(it)
                assignment = expr
                t = next(it)

        if module_port_list:
            decl = PortNode(
                name=name,
                direction=direction,
                signed=signed,
                data_type=data_type,
                index=index,
            )
        else:
            decl = DeclarationNode(
                name=name,
                signed=signed,
                data_type=data_type,
                index=index,
                assignment=assignment,
            )

        declarations.append(decl)

        if module_port_list:
            if isinstance(t, OperatorToken) and t.operator == ")":
                break
        else:
            if isinstance(t, SemicolonToken):
                break
        assert isinstance(t, OperatorToken) and t.operator == ","

    return declarations


def parse_gate_instantiation(it):
    """parse a generic buf / not / and / nand / or / nor / xor / xnor gate instance"""

    t = next(it)
    assert isinstance(t, KeywordToken)
    gate = t.keyword
    assert gate in ("buf", "not", "and", "nand", "or", "nor", "xor", "xnor")

    t = next(it)
    assert isinstance(t, OperatorToken) and t.operator == "("
    output_terminal = parse_lvalue(it)
    t = next(it)
    assert isinstance(t, OperatorToken) and t.operator == ","
    if gate in ("buf", "not"):
        input_terminals = [parse_expr(it)]
    else:
        input_terminals = []
        input_terminals.append(parse_expr(it))
        t = next(it)
        assert isinstance(t, OperatorToken) and t.operator == ","
        input_terminals.append(parse_expr(it))
    t = next(it)
    assert isinstance(t, OperatorToken) and t.operator == ")"
    t = next(it)
    assert isinstance(t, SemicolonToken)
    return GateInstantiationNode(
        gate=gate, input_terminals=input_terminals, output_terminal=output_terminal
    )


def parse_module_instantiation(it):
    """parse a submodule instance"""

    t = next(it)
    assert isinstance(t, IdentifierToken)
    module_name = t.name
    t = next(it)
    if isinstance(t, OperatorToken) and t.operator == "#":
        raise NotImplementedError("Parameters are not supported at this time")
    assert isinstance(t, IdentifierToken)
    instance_name = t.name
    t = next(it)
    instance_index = None
    if isinstance(t, OperatorToken) and t.operator == "[":
        instance_index = parse_index(it, require_constant=True)
        t = next(it)
    assert isinstance(t, OperatorToken) and t.operator == "("
    t = next(it)
    port_connections = []
    while True:
        if not (isinstance(t, OperatorToken) and t.operator == "."):
            raise NotImplementedError(
                f"Module instances only support named port connection, unexpected {t}"
            )
        t = next(it)
        assert isinstance(t, IdentifierToken)
        port_name = t.name
        t = next(it)
        if isinstance(t, OperatorToken) and t.operator == "(":
            t = next(it)
            if isinstance(t, OperatorToken) and t.operator == ")":
                value = None
            else:
                it.pushback(t)
                value = parse_expr(it)
                t = next(it)
                assert isinstance(t, OperatorToken) and t.operator == ")"
        else:
            it.pushback(t)
            value = IdentifierNode(name=port_name)
        port_connections.append(PortConnectionNode(port_name=port_name, value=value))
        t = next(it)
        if isinstance(t, OperatorToken) and t.operator == ",":
            t = next(it)
            continue
        elif isinstance(t, OperatorToken) and t.operator == ")":
            break
        else:
            raise SyntaxError(f"Unexpected token in module instantiation: {t}")
    t = next(it)
    if isinstance(t, OperatorToken) and t.operator == ",":
        raise NotImplementedError(
            "Only one module can be instantiated at the same time"
        )
    assert isinstance(t, SemicolonToken)
    return ModuleInstantiationNode(
        module_name=module_name,
        instance_name=instance_name,
        instance_index=instance_index,
        port_connections=port_connections,
    )
