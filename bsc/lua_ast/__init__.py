# Copyright (C) 2024 Jose Mendoza. All rights reserved. Use of this
# source code is governed by an MIT license that can be found in the
# LICENSE file.

class LuaModule:
    def __init__(self, name, decls = []):
        self.name = name
        self.decls = decls

class LuaTableField:
    def __init__(self, name, value):
        self.name = name
        self.value = value

class LuaTable:
    def __init__(self, name, fields):
        self.name = name
        self.fields = fields

class LuaFunction:
    def __init__(self, name, args):
        self.name = name
        self.args = args
        self.stmts = []

class LuaBlock:
    def __init__(self):
        self.chunk = []

class LuaAssignment:
    def __init__(self, lefts, op, rights):
        self.lefts = lefts
        self.op = op
        self.rights = rights

class LuaIdent:
    def __init__(self, name):
        self.name = name

class LuaNil:
    pass