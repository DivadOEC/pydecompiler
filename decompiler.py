from __future__ import print_function
import opcode
import ast


class DecompilerError(Exception):
    pass


class UnsupportedOperation(DecompilerError):

    def __init__(self, what):
        message = 'Unsupported operation: %s' % what
        super(UnsupportedOperation, self).__init__(message)


class WellDone(Exception):
    pass


class Stack(list):

    def push(self, item):
        self.append(item)

    def pop(self, count=1):
        items = self[-count:]
        self[-count:] = []
        return items


class Decompiler(object):

    def __init__(self, co):
        self._co = co
        self._pos = 0
        self._end = len(co.co_code)

        self.ast = None
        self.stack = Stack()
        self.targets = []
        self.names = set()
        self.astnames = set()

    def peak(self):
        return ord(self._co.co_code[self._pos])

    def next(self):
        self._pos += 1
        return self.peak()

    def has_next(self):
        return self._pos < self._end

    def parse(self):
        while self.has_next():
            op = self.peak()
            self.dispatch(op)
            self.next()

    def parse_argument(self):
        lsb = self.next()
        msb = self.next()
        return 256 * msb + lsb

    def resolve_argument(self, op, argument):
        if op in opcode.hasconst:
            return [self._co.co_code]
        if op in opcode.hasname:
            return [self._co.co_names[argument]]
        if op in opcode.hasjrel:
            return [self._pos + argument]
        if op in opcode.hasjabs:
            raise NotImplemented  # XXX: Could this even happen?
        if op in opcode.haslocal:
            return self._co.co_varnames[argument]
        if op in opcode.hascompare:
            return
        if op in opcode.hasfree:
            if argument in self._co.co_freevars:
                return self._co.co_freevars[argument]
            return self._co.co_cellvars[argument]

    def dispatch(self, op):
        if op >= opcode.HAVE_ARGUMENT:
            argument = self.parse_argument()
            if op == opcode.EXTENDED_ARG:
                op = self.next()
                print(op)
                extended = self.parse_argument()
                argument += 65536 * extended
            argument = self.resolve_argument(op, argument)
        else:
            argument = []
        mnemonic = opcode.opname[op].replace('+', '_')
        method = getattr(self, mnemonic, self.unsupported)
        value = method(*argument)
        if value is not None:
            self.stack.push(value)

    def unsupported(self):
        mnemonic = opcode.opname[self.peak()]
        raise UnsupportedOperation(mnemonic)

    def binary_operation(self, ast_op, container):
        left = self.stack.pop()
        right = self.stack.pop()
        return ast.BinOp(left, ast_op, right)

    # Rebuild AST based on opcodes
    # For opcode reference see http://docs.python.org/2/library/dis.html

    def BINARY_POWER(self):
        return self.binary_operation(ast.Pow)

    def BINARY_MULTIPLY(self):
        return self.binary_operation(ast.Mult)

    def BINARY_DIVIDE(self):
        return self.binary_operation(ast.Div)

    def BINARY_FLOOR_DIVIDE(self):
        return self.binary_operation(ast.FloorDiv)

    def BINARY_TRUE_DIVIDE(self):
        return self.binary_operation(ast.Div)

    def BINARY_MODULE(self):
        return self.binary_operation(ast.Mod)

    def BINARY_ADD(self):
        return self.binary_operation(ast.Add)

    def BINARY_SUBSTRACT(self):
        return self.binary_operation(ast.Sub)

    def BINARY_SUBSCR(self):
        raise DecompilerError('Have no idea how implement BINARY_SUBSCR')

    def BINARY_LSHIFT(self):
        return self.binary_operation(ast.LShift)

    def BINARY_RSHIFT(self):
        return self.binary_operation(ast.RShift)

    def BINARY_AND(self):
        return self.binary_operation(ast.BitAnd)

    def BINARY_XOR(self):
        return self.binary_operation(ast.BitXor)

    def BINARY_OR(self):
        return self.binary_operation(ast.Or)

    def SLICE_0(self):
        expr = self.stack.pop()
        return ast.Subscript(expr)

    def SLICE_1(self):
        tos = self.stack.pop()
        tos1 = self.stack.pop()
        return ast.Subscript(tos1, ast.Slice(tos))

    def SLICE_2(self):
        tos = self.stack.pop()
        tos1 = self.stack.pop()
        return ast.Subscript(tos1, ast.Slice(None, tos))

    def SLICE_3(self):
        tos = self.stack.pop()
        tos1 = self.stack.pop()
        tos2 = self.stack.pop()
        return ast.Subscript(tos2, ast.Slice(tos1, tos))

    def LOAD_CONST(self, number):
        return ast.Num(number)

    def LOAD_NAME(self, identifier):
        return ast.Name(identifier, ast.Load)

    def LOAD_ATTR(self, identifier):
        expr = self.stack.pop()
        return ast.Attribute(expr, identifier, ast.Load)

    def LOAD_GLOBAL(self, identifier):
        pass

    def LOAD_FAST(self, identifier):
        pass

    def LOAD_CLOSURE(self, identifier):
        pass

    def LOAD_DEREF(self, identifier):
        pass

    def BUILD_TUPLE(self, count):
        if count:
            elts = self.stack.pop(count)
        else:
            elts = []
        return ast.Tuple(elts, ast.Load)

    def BUILD_LIST(self, count):
        if count:
            elts = self.stack.pop(count)
        else:
            elts = []
        return ast.List(elts, ast.Load)

    def BUILD_SET(self, count):
        if count:
            elts = self.stack.pop(count)
        else:
            elts = []
        return ast.Set(elts)

    def BUILD_MAP(self, count):
        return ast.Dict()

    def STORE_MAP(self):
        pass

    def RETURN_VALUE(self):
        if self.has_next():
            raise DecompilerError('Unexpected return statement')
        expr = self.stack.pop()
        return ast.Return(expr)

    def CALL_FUNCTION_VAR(self, argc):
        pass

    def CALL_FUNCTION_KW(self, argc):
        pass

    def CALL_FUNCTION_VAR_KW(self, argc):
        pass
