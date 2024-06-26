# Copyright (C) 2024 Jose Mendoza. All rights reserved. Use of this
# source code is governed by an MIT license that can be found in the
# LICENSE file.

import os
from bsc import sym, utils
from bsc.lua_ast import *

BSC_OUT_DIR = "bsc-out"

class LuaRender:
    def __init__(self, ctx, modules):
        self.ctx = ctx

        self.modules = modules
        self.cur_module = None

        self.indent = 0
        self.empty_line = True
        self.lua_file = utils.Builder()

    def render_modules(self):
        if not os.path.exists(BSC_OUT_DIR):
            os.mkdir(BSC_OUT_DIR)
        for module in self.modules:
            self.cur_module = module
            self.render_module(module)

    def render_module(self, module):
        self.writeln(
            f"-- Autogenerated by the BlueScript compiler - {utils.full_version()}"
        )
        self.writeln(
            "-- WARNING: DO NOT MODIFY MANUALLY! YOUR CHANGES WILL BE OVERWRITTEN --\n"
        )

        self.writeln(f"local {module.name} = {{}} -- package\n")
        self.render_decls(module.decls)
        self.writeln(f"return {module.name}\n")

        with open(f"{BSC_OUT_DIR}/{module.name}.lua", "w") as f:
            f.write(str(self.lua_file))
        self.lua_file.clear()

    def render_decls(self, decls):
        for decl in decls:
            self.render_decl(decl)

    def render_decl(self, decl):
        if isinstance(decl, LuaModule):
            self.render_mod(decl)
        elif isinstance(decl, LuaTable):
            self.render_table(decl)
        elif isinstance(decl, LuaAssignment):
            self.render_assign_decl(decl)
        elif isinstance(decl, LuaFunction):
            self.render_fn_decl(decl)

    def render_mod(self, decl):
        if decl.is_inline:
            self.writeln(f"{decl.name} = {{}} -- inline module\n")
            self.render_decls(decl.decls)
            self.writeln(f"-- end module `{decl.name}`\n")
        else:
            self.writeln(
                f"{decl.name} = require(\"{BSC_OUT_DIR}.{decl.lua_filename}\") -- load module file\n"
            )

    def render_table(self, decl):
        self.writeln(f"{decl.name} = {{")
        self.indent += 1
        for i, field in enumerate(decl.fields):
            self.write(f"{field.name} = {field.value}")
            if i < len(decl.fields) - 1:
                self.writeln(",")
            else:
                self.writeln()
        self.indent -= 1
        self.writeln("}\n")

    def render_fn_decl(self, decl):
        self.write(f"function {decl.name}(")
        for i, arg in enumerate(decl.args):
            self.write(arg.name)
            if i < len(decl.args) - 1:
                self.write(", ")
        self.writeln(")")
        self.indent += 1
        self.render_stmts(decl.block.stmts)
        self.indent -= 1
        self.writeln("end\n")

    def render_assign_decl(self, decl):
        if decl.is_local:
            self.write("local ")
        for i, left in enumerate(decl.lefts):
            self.render_ident(left)
            if i < len(decl.lefts) - 1:
                self.write(", ")
        self.write(" = ")
        for i, right in enumerate(decl.rights):
            self.render_expr(right)
            if i < len(decl.rights) - 1:
                self.write(", ")
        self.writeln()

    def render_stmts(self, stmts):
        for stmt in stmts:
            self.render_stmt(stmt)

    def render_stmt(self, stmt):
        if isinstance(stmt, LuaWhile):
            self.write("while ")
            self.render_expr(stmt.cond)
            self.writeln(" do")
            self.indent += 1
            self.render_stmts(stmt.stmts)
            self.indent -= 1
            self.writeln("end")
        elif isinstance(stmt, LuaRepeat):
            self.writeln("repeat")
            self.indent += 1
            self.render_stmts(stmt.stmts)
            self.indent -= 1
            self.write("until ")
            self.render_expr(stmt.cond)
            self.writeln()
        elif isinstance(stmt, LuaIf):
            for i, branch in enumerate(stmt.branches):
                if branch.is_else:
                    self.writeln("else")
                else:
                    self.write("if " if i == 0 else "elseif ")
                    self.render_expr(branch.cond)
                self.indent += 1
                self.render_stmts(branch.stmts)
                self.indent -= 1
            self.writeln("end")
        elif isinstance(stmt, LuaBlock):
            self.writeln("do")
            self.indent += 1
            self.render_stmts(stmt.stmts)
            self.indent -= 1
            self.writeln("end")
        elif isinstance(stmt, LuaAssignment):
            self.render_assign_decl(stmt)
        elif isinstance(stmt, LuaReturn):
            self.write("return")
            if stmt.expr != None:
                self.write(" ")
                self.render_expr(stmt.expr)
            self.writeln()

    def render_expr(self, expr):
        if isinstance(expr, LuaParenExpr):
            self.write("(")
            self.render_expr(expr.expr)
            self.write(")")
        elif isinstance(expr, LuaBinaryExpr):
            self.write("(")
            self.render_expr(expr.left)
            self.write(f" {expr.op} ")
            self.render_expr(expr.right)
            self.write(")")
        elif isinstance(expr, LuaUnaryExpr):
            self.write("(")
            self.write(expr.op)
            self.render_expr(expr.right)
            self.write(")")
        elif isinstance(expr, LuaCallExpr):
            self.render_expr(expr.left)
            self.write("(")
            for i, arg in enumerate(expr.args):
                self.render_expr(arg)
                if i < len(expr.args) - 1:
                    self.write(", ")
            self.write(")")
        elif isinstance(expr, LuaSelector):
            self.render_expr(expr.left)
            self.write(f".{expr.name}")
        elif isinstance(expr, LuaIdent):
            self.write(expr.name)
        elif isinstance(expr, LuaNumberLit):
            if "." in expr.value: self.write(expr.value)
            else: self.write(hex(int(expr.value, 0)))
        elif isinstance(expr, LuaBooleanLit):
            self.write(str(expr.value).lower())
        elif isinstance(expr, LuaNil):
            self.write("nil")

    def render_ident(self, ident):
        self.write(ident.name)

    ## Utils

    def write(self, s):
        if self.indent > 0 and self.empty_line:
            self.lua_file.write("\t" * self.indent)
        self.lua_file.write(s)
        self.empty_line = False

    def writeln(self, s = ""):
        if self.indent > 0 and self.empty_line:
            self.lua_file.write("\t" * self.indent)
        self.lua_file.writeln(s)
        self.empty_line = True
