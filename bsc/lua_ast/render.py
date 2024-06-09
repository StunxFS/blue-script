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
            self.render_inline_mod(decl)
        elif isinstance(decl, LuaTable):
            self.render_table(decl)
        elif isinstance(decl, LuaFunction):
            self.render_fn_decl(decl)

    def render_table(self, decl):
        self.writeln(f"{decl.name} = {{ -- enum")
        self.indent += 1
        for i, field in enumerate(decl.fields):
            self.write(f"{field.name} = {field.value}")
            if i < len(decl.fields) - 1:
                self.writeln(",")
            else:
                self.writeln()
        self.indent -= 1
        self.writeln("}\n")

    def render_inline_mod(self, decl):
        self.writeln(f"{decl.name} = {{}} -- inline module\n")
        self.render_decls(decl.decls)

    def render_fn_decl(self, decl):
        self.write(f"function {decl.name}(")
        for i, arg in enumerate(decl.args):
            self.write(arg.name)
            if i < len(decl.args) - 1:
                self.write(", ")
        self.writeln(")")
        #self.indent += 1
        #self.indent -= 1
        self.writeln("end\n")

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
