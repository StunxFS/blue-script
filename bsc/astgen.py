# Copyright (C) 2024 Jose Mendoza. All rights reserved. Use of this
# source code is governed by an MIT license that can be found in the
# LICENSE file.

import os

from lark import Lark, v_args, Transformer, Token, Tree

from AST import *

bs_parser = Lark.open(
    "grammar.lark", rel_to = __file__, parser = 'earley', start = "module"
)

@v_args(inline = True)
class AstGen(Transformer):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.file = ""
        self.source_file = None

    def parse_file(self, file):
        self.file = file
        self.source_file = SourceFile(self.file)
        return self.transform(bs_parser.parse(open(file).read()))

    def mkpos(self, token):
        return Pos.from_token(self.file, token)

    # Declarations
    def fn_decl(self, *nodes):
        name = nodes[1]
        args = nodes[3]
        if isinstance(args, Token):
            is_method = False
            args = []
        else:
            is_method = args[0]
            args = list(args[1])
        ret_type = nodes[5]
        if isinstance(ret_type, Token) or not ret_type:
            ret_type = VoidType()
        stmts = []
        if not isinstance(nodes[-1], Token):
            print(nodes[-1])
        return FnDecl(
            name, args, ret_type, stmts, name == "main"
            and self.file == self.ctx.prefs.input
        )

    def fn_args(self, *nodes):
        is_method = str(nodes[0]) == "self"
        return (is_method, nodes[2:] if is_method else nodes)

    def fn_arg(self, *nodes):
        return FnArg(nodes[1], nodes[3], nodes[-1])

    def fn_body(self, *nodes):
        stmts = []
        if len(nodes) != 2:
            stmts = nodes[1:-1]
        return BlockStmt(stmts, self.mkpos(nodes[0]))

    # Statements
    def assignment(self, *nodes):
        lefts = []
        op_assign = ""
        for node in nodes:
            if str(node) == ",":
                continue
            if isinstance(node, OpAssign):
                break
            lefts.append(node)
        right = nodes[-1]
        return AssignStmt(lefts, op_assign, right, lefts[0].pos + nodes[-1].pos)

    def op_assign(self, *nodes):
        op_assign = str(nodes[0])
        match op_assign:
            case ":=":
                op_assign = OpAssign.Decl
            case "=":
                op_assign = OpAssign.Assign
            case "+=":
                op_assign = OpAssign.PlusAssign
            case "-=":
                op_assign = OpAssign.MinusAssign
            case "/=":
                op_assign = OpAssign.DivAssign
            case "*=":
                op_assign = OpAssign.MulAssign
            case "%=":
                op_assign = OpAssign.ModAssign
            case "&=":
                op_assign = OpAssign.AndAssign
            case "|=":
                op_assign = OpAssign.OrAssign
            case "^=":
                op_assign = OpAssign.XorAssign
        return op_assign

    def block(self, *nodes):
        stmts = list(nodes[1:-1])
        return BlockStmt(stmts, self.mkpos(nodes[0]) + self.mkpos(nodes[-1]))

    def while_stmt(self, *nodes):
        return WhileStmt(
            nodes[1], nodes[3],
            self.mkpos(nodes[0]) + self.mkpos(nodes[-1])
        )

    # Expressions
    def par_expr(self, *nodes):
        return ParExpr(nodes[1], self.mkpos(nodes[0]) + self.mkpos(nodes[2]))

    def builtin_var(self, *nodes):
        return BuiltinVar(nodes[1].name, self.mkpos(nodes[0]) + nodes[1].pos)

    def KW_NIL(self, lit):
        return NilLiteral(self.mkpos(lit))

    def bool_lit(self, lit):
        return BoolLiteral(lit.value == "true", self.mkpos(lit))

    def number_lit(self, lit):
        return NumberLiteral(lit.value, self.mkpos(lit))

    def STRING(self, lit):
        return StringLiteral(lit.value, self.mkpos(lit))

    def KW_SELF(self, lit):
        return SelfLiteral(self.mkpos(lit))

    def NAME(self, lit):
        return Ident(lit.value, self.mkpos(lit))

    def selector_expr(self, *nodes):
        return SelectorExpr(
            nodes[0], nodes[2].name, nodes[0].pos + nodes[2].pos
        )

    def array_literal(self, *nodes):
        elems = []
        for node in nodes[1:]:
            if str(node) == ",":
                continue
            if str(node) == "]":
                break
            elems.append(node)
        is_fixed = str(nodes[-1]) == "!"
        return ArrayLiteral(
            elems, is_fixed,
            self.mkpos(nodes[0]) + self.mkpos(nodes[-1])
        )

    def tuple_literal(self, *nodes):
        elems = []
        for node in nodes[1:]:
            if str(node) == ",":
                continue
            if str(node) == ")":
                break
            elems.append(node)
        return TupleLiteral(elems, self.mkpos(nodes[0]) + self.mkpos(nodes[-1]))

    def call_expr(self, *nodes):
        left = nodes[0]
        args = list(nodes[2:-2])
        return CallExpr(left, args, left.pos + self.mkpos(nodes[-1]))

    def if_expr(self, *nodes):
        branches = list(nodes)
        return IfExpr(list(nodes), nodes[0].pos + nodes[-1].pos)

    def if_header(self, *nodes):
        cond = nodes[2]
        stmt = nodes[4]
        return IfBranch(cond, False, stmt, self.mkpos(nodes[0]) + nodes[-1].pos)

    def else_if_expr(self, *nodes):
        cond = nodes[3]
        stmt = nodes[4]
        return IfBranch(cond, False, stmt, self.mkpos(nodes[0]) + nodes[-1].pos)

    def else_stmt(self, *nodes):
        return IfBranch(
            None, True, nodes[1],
            self.mkpos(nodes[0]) + nodes[-1].pos
        )

    # Modifiers
    def access_modifier(self, modifier):
        match modifier.value:
            case "pub":
                return AccessModifier.public
            case "prot":
                return AccessModifier.protected
        return AccessModifier.private

    # Types
    def primitive_type(self, *nodes):
        return BasicType(nodes[0].value, self.mkpos(nodes[0]))

    def user_type(self, *names):
        left = names[0]
        for name in names[1:]:
            if not isinstance(name, Ident):
                continue
            left = SelectorExpr(left, name, left.pos + name.pos)
        return BasicType(left, left.pos)

    def option_type(self, *nodes):
        return OptionType(nodes[1], self.mkpos(nodes[0]) + nodes[1].pos)

    def array_type(self, *nodes):
        has_size = not isinstance(nodes[1], Token)
        size = nodes[1] if has_size else None
        return ArrayType(
            size, nodes[3 if has_size else 2],
            self.mkpos(nodes[0]) + nodes[-1].pos
        )

    def map_type(self, *nodes):
        return MapType(
            nodes[1], nodes[3],
            self.mkpos(nodes[0]) + self.mkpos(nodes[-1])
        )

    def sum_type(self, *nodes):
        types = list(filter(lambda node: not isinstance(node, Token), nodes))
        return SumType(types, nodes[0].pos + nodes[-1].pos)
