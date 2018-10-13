# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, see
# <http://www.gnu.org/licenses/>.


"""
A module to hold all the Java opcodes. Data taken from publicly
available sources (see following for more information)

References
----------
* http://java.sun.com/docs/books/jvms/second_edition/html/VMSpecTOC.doc.html

:author: Christopher O'Brien  <obriencj@gmail.com>
:license: LGPL v.3
"""


from functools import partial
from six.moves import range

from .pack import compile_struct


__all__ = (
    "get_opcode_by_name", "get_opname_by_code",
    "get_arg_format", "has_const_arg",
    "disassemble",
    "OP_aaload", "OP_aastore", "OP_aconst_null", "OP_aload", "OP_aload_0",
    "OP_aload_1", "OP_aload_2", "OP_aload_3", "OP_anewarray", "OP_areturn",
    "OP_arraylength", "OP_astore", "OP_astore_0", "OP_astore_1",
    "OP_astore_2", "OP_astore_3", "OP_athrow", "OP_baload", "OP_bastore",
    "OP_bipush", "OP_caload", "OP_castore", "OP_checkcast", "OP_d2f",
    "OP_d2i", "OP_d2l", "OP_dadd", "OP_daload", "OP_dastore", "OP_dcmpg",
    "OP_dcmpl", "OP_dconst_0", "OP_dconst_1", "OP_ddiv", "OP_dload",
    "OP_dload_0", "OP_dload_1", "OP_dload_2", "OP_dload_3", "OP_dmul",
    "OP_dneg", "OP_drem", "OP_dreturn", "OP_dstore", "OP_dstore_0",
    "OP_dstore_1", "OP_dstore_2", "OP_dstore_3", "OP_dsub", "OP_dup",
    "OP_dup2", "OP_dup2_x1", "OP_dup2_x2", "OP_dup_x1", "OP_dup_x2",
    "OP_f2d", "OP_f2i", "OP_f2l", "OP_fadd", "OP_faload", "OP_fastore",
    "OP_fcmpg", "OP_fcmpl", "OP_fconst_0", "OP_fconst_1", "OP_fconst_2",
    "OP_fdiv", "OP_fload", "OP_fload_0", "OP_fload_1", "OP_fload_2",
    "OP_fload_3", "OP_fmul", "OP_fneg", "OP_frem", "OP_freturn",
    "OP_fstore", "OP_fstore_0", "OP_fstore_1", "OP_fstore_2",
    "OP_fstore_3", "OP_fsub", "OP_getfield", "OP_getstatic", "OP_goto",
    "OP_goto_w", "OP_i2b", "OP_i2c", "OP_i2d", "OP_i2f", "OP_i2l", "OP_i2s",
    "OP_iadd", "OP_iaload", "OP_iand", "OP_iastore", "OP_iconst_0",
    "OP_iconst_1", "OP_iconst_2", "OP_iconst_3", "OP_iconst_4",
    "OP_iconst_5", "OP_iconst_m1", "OP_idiv", "OP_if_acmpeq",
    "OP_if_acmpne", "OP_if_icmpeq", "OP_if_icmpge", "OP_if_icmpgt",
    "OP_if_icmple", "OP_if_icmplt", "OP_if_icmpne", "OP_ifeq", "OP_ifge",
    "OP_ifgt", "OP_ifle", "OP_iflt", "OP_ifne", "OP_ifnonnull",
    "OP_ifnull", "OP_iinc", "OP_iload", "OP_iload_0", "OP_iload_1",
    "OP_iload_2", "OP_iload_3", "OP_imul", "OP_ineg", "OP_instanceof",
    "OP_invokedynamic", "OP_invokeinterface", "OP_invokespecial",
    "OP_invokestatic", "OP_invokevirtual", "OP_ior", "OP_irem",
    "OP_ireturn", "OP_ishl", "OP_ishr", "OP_istore", "OP_istore_0",
    "OP_istore_1", "OP_istore_2", "OP_istore_3", "OP_isub", "OP_iushr",
    "OP_ixor", "OP_jsr", "OP_jsr_w", "OP_l2d", "OP_l2f", "OP_l2i",
    "OP_ladd", "OP_laload", "OP_land", "OP_lastore", "OP_lcmp",
    "OP_lconst_0", "OP_lconst_1", "OP_ldc", "OP_ldc2_w", "OP_ldc_w",
    "OP_ldiv", "OP_lload", "OP_lload_0", "OP_lload_1", "OP_lload_2",
    "OP_lload_3", "OP_lmul", "OP_lneg", "OP_lookupswitch", "OP_lor",
    "OP_lrem", "OP_lreturn", "OP_lshl", "OP_lshr", "OP_lstore",
    "OP_lstore_0", "OP_lstore_1", "OP_lstore_2", "OP_lstore_3", "OP_lsub",
    "OP_lushr", "OP_lxor", "OP_monitorentry", "OP_monitorexit",
    "OP_multianewarray", "OP_new", "OP_newarray", "OP_nop", "OP_pop",
    "OP_pop2", "OP_putfield", "OP_putstatic", "OP_ret", "OP_return",
    "OP_saload", "OP_sastore", "OP_sipush", "OP_swap", "OP_tableswitch",
    "OP_wide",
)


# the op table itself
__OPTABLE = {}

# mnemonics for the op tuples
_OPINDEX_NAME = 0
_OPINDEX_VAL = 1
_OPINDEX_FMT = 2
_OPINDEX_CONSUME = 3
_OPINDEX_PRODUCE = 4
_OPINDEX_CONST = 5


# commonly re-occurring struct formats
# pylint: disable=C0103
_struct_i = compile_struct(">i")
_struct_ii = compile_struct(">ii")
_struct_iii = compile_struct(">iii")
_struct_BH = compile_struct(">BH")
_struct_BHh = compile_struct(">BHh")


def __op(name, val, fmt=None, const=False, consume=0, produce=0):
    """
    provides sensible defaults for a code, and registers it with the
    __OPTABLE for lookup.
    """

    name = name.lower()

    # fmt can either be a str representing the struct to unpack, or a
    # callable to do more complex unpacking. If it's a str, create a
    # callable for it.
    if isinstance(fmt, str):
        fmt = partial(_unpack, compile_struct(fmt))

    operand = (name, val, fmt, consume, produce, const)

    assert(name not in __OPTABLE)
    assert(val not in __OPTABLE)

    __OPTABLE[name] = operand
    __OPTABLE[val] = operand

    return val


def get_opcode_by_name(name):
    """
    get the integer opcode by its name
    """

    return __OPTABLE[name.lower()][_OPINDEX_VAL]


def get_opname_by_code(code):
    """
    get the name of an opcode
    """

    return __OPTABLE[code][_OPINDEX_NAME]


def get_arg_format(code):
    """
    get the format of arguments to this opcode
    """

    return __OPTABLE[code][_OPINDEX_FMT]


def has_const_arg(code):
    """
    which arg is a const for this opcode
    """

    return __OPTABLE[code][_OPINDEX_CONST]


def _unpack(struct, bc, offset=0):
    """
    returns the unpacked data tuple, and the next offset past the
    unpacked data
    """

    return struct.unpack_from(bc, offset), offset + struct.size


def _unpack_lookupswitch(bc, offset):
    """
    function for unpacking the lookupswitch op arguments
    """

    jump = (offset % 4)
    if jump:
        offset += (4 - jump)

    (default, npairs), offset = _unpack(_struct_ii, bc, offset)

    switches = list()
    for _index in range(npairs):
        pair, offset = _unpack(_struct_ii, bc, offset)
        switches.append(pair)

    return (default, switches), offset


def _unpack_tableswitch(bc, offset):
    """
    function for unpacking the tableswitch op arguments
    """

    jump = (offset % 4)
    if jump:
        offset += (4 - jump)

    (default, low, high), offset = _unpack(_struct_iii, bc, offset)

    joffs = list()
    for _index in range((high - low) + 1):
        j, offset = _unpack(_struct_i, bc, offset)
        joffs.append(j)

    return (default, low, high, joffs), offset


def _unpack_wide(bc, offset):
    """
    unpacker for wide ops
    """

    code = ord(bc[offset])

    if code == OP_iinc:
        return _unpack(_struct_BHh, bc, offset)

    elif code in (OP_iload, OP_fload, OP_aload, OP_lload, OP_dload,
                  OP_istore, OP_fstore, OP_astore, OP_lstore,
                  OP_dstore, OP_ret):

        return _unpack(_struct_BH, bc, offset)

    else:
        # no other opcodes are valid, so shouldn't have fallen through
        # to here.
        assert False


def disassemble(bytecode):
    """
    Generator. Disassembles Java bytecode into a sequence of (offset,
    code, args) tuples
    :type bytecode: bytes
    """

    offset = 0
    end = len(bytecode)

    while offset < end:
        orig_offset = offset

        code = bytecode[offset]
        if not isinstance(code, int):   # Py3
            code = ord(code)

        offset += 1

        args = tuple()
        fmt = get_arg_format(code)
        if fmt:
            args, offset = fmt(bytecode, offset)

        yield (orig_offset, code, args)


# And now, the OP codes themselves

# The individual OP_* constants just have the numerical value. The
# rest is just information to get stored in the __OPTABLE

# pylint: disable=C0103

OP_aaload = __op('aaload', 0x32)
OP_aastore = __op('aastore', 0x53)
OP_aconst_null = __op('aconst_null', 0x1)
OP_aload = __op('aload', 0x19, fmt='>B')
OP_aload_0 = __op('aload_0', 0x2a)
OP_aload_1 = __op('aload_1', 0x2b)
OP_aload_2 = __op('aload_2', 0x2c)
OP_aload_3 = __op('aload_3', 0x2d)
OP_anewarray = __op('anewarray', 0xbd, fmt='>H', const=True)
OP_areturn = __op('areturn', 0xb0)
OP_arraylength = __op('arraylength', 0xbe)
OP_astore = __op('astore', 0x3a, fmt='>B')
OP_astore_0 = __op('astore_0', 0x4b)
OP_astore_1 = __op('astore_1', 0x4c)
OP_astore_2 = __op('astore_2', 0x4d)
OP_astore_3 = __op('astore_3', 0x4e)
OP_athrow = __op('athrow', 0xbf)

OP_baload = __op('baload', 0x33)
OP_bastore = __op('bastore', 0x54)
OP_bipush = __op('bipush', 0x10, fmt='>B')

OP_caload = __op('caload', 0x34)
OP_castore = __op('castore', 0x55)
OP_checkcast = __op('checkcast', 0xc0, fmt='>H', const=True)

OP_d2f = __op('d2f', 0x90)
OP_d2i = __op('d2i', 0x8e)
OP_d2l = __op('d2l', 0x8f)
OP_dadd = __op('dadd', 0x63)
OP_daload = __op('daload', 0x31)
OP_dastore = __op('dastore', 0x52)
OP_dcmpg = __op('dcmpg', 0x98)
OP_dcmpl = __op('dcmpl', 0x97)
OP_dconst_0 = __op('dconst_0', 0xe)
OP_dconst_1 = __op('dconst_1', 0xf)
OP_ddiv = __op('ddiv', 0x6f)
OP_dload = __op('dload', 0x18, fmt='>B')
OP_dload_0 = __op('dload_0', 0x26)
OP_dload_1 = __op('dload_1', 0x27)
OP_dload_2 = __op('dload_2', 0x28)
OP_dload_3 = __op('dload_3', 0x29)
OP_dmul = __op('dmul', 0x6b)
OP_dneg = __op('dneg', 0x77)
OP_drem = __op('drem', 0x73)
OP_dreturn = __op('dreturn', 0xaf)
OP_dstore = __op('dstore', 0x39, fmt='>B')
OP_dstore_0 = __op('dstore_0', 0x47)
OP_dstore_1 = __op('dstore_1', 0x48)
OP_dstore_2 = __op('dstore_2', 0x49)
OP_dstore_3 = __op('dstore_3', 0x4a)
OP_dsub = __op('dsub', 0x67)
OP_dup = __op('dup', 0x59)
OP_dup_x1 = __op('dup_x1', 0x5a)
OP_dup_x2 = __op('dup_x2', 0x5b)
OP_dup2 = __op('dup2', 0x5c)
OP_dup2_x1 = __op('dup2_x1', 0x5d)
OP_dup2_x2 = __op('dup2_x2', 0x5e)

OP_f2d = __op('f2d', 0x8d)
OP_f2i = __op('f2i', 0x8b)
OP_f2l = __op('f2l', 0x8c)
OP_fadd = __op('fadd', 0x62)
OP_faload = __op('faload', 0x30)
OP_fastore = __op('fastore', 0x51)
OP_fcmpg = __op('fcmpg', 0x96)
OP_fcmpl = __op('fcmpl', 0x95)
OP_fconst_0 = __op('fconst_0', 0xb)
OP_fconst_1 = __op('fconst_1', 0xc)
OP_fconst_2 = __op('fconst_2', 0xd)
OP_fdiv = __op('fdiv', 0x6e)
OP_fload = __op('fload', 0x17, fmt='>B')
OP_fload_0 = __op('fload_0', 0x22)
OP_fload_1 = __op('fload_1', 0x23)
OP_fload_2 = __op('fload_2', 0x24)
OP_fload_3 = __op('fload_3', 0x25)
OP_fmul = __op('fmul', 0x6a)
OP_fneg = __op('fneg', 0x76)
OP_frem = __op('frem', 0x72)
OP_freturn = __op('freturn', 0xae)
OP_fstore = __op('fstore', 0x38, fmt='>B')
OP_fstore_0 = __op('fstore_0', 0x43)
OP_fstore_1 = __op('fstore_1', 0x44)
OP_fstore_2 = __op('fstore_2', 0x45)
OP_fstore_3 = __op('fstore_3', 0x46)
OP_fsub = __op('fsub', 0x66)

OP_getfield = __op('getfield', 0xb4, fmt='>H', const=True)
OP_getstatic = __op('getstatic', 0xb2, fmt='>H', const=True)
OP_goto = __op('goto', 0xa7, fmt='>h')
OP_goto_w = __op('goto_w', 0xc8, fmt='>i')

OP_i2b = __op('i2b', 0x91)
OP_i2c = __op('i2c', 0x92)
OP_i2d = __op('i2d', 0x87)
OP_i2f = __op('i2f', 0x86)
OP_i2l = __op('i2l', 0x85)
OP_i2s = __op('i2s', 0x93)
OP_iadd = __op('iadd', 0x60)
OP_iaload = __op('iaload', 0x2e)
OP_iand = __op('iand', 0x7e)
OP_iastore = __op('iastore', 0x4f)
OP_iconst_m1 = __op('iconst_m1', 0x2)
OP_iconst_0 = __op('iconst_0', 0x3)
OP_iconst_1 = __op('iconst_1', 0x4)
OP_iconst_2 = __op('iconst_2', 0x5)
OP_iconst_3 = __op('iconst_3', 0x6)
OP_iconst_4 = __op('iconst_4', 0x7)
OP_iconst_5 = __op('iconst_5', 0x8)
OP_idiv = __op('idiv', 0x6c)
OP_if_acmpeq = __op('if_acmpeq', 0xa5, fmt='>h')
OP_if_acmpne = __op('if_acmpne', 0xa6, fmt='>h')
OP_if_icmpeq = __op('if_icmpeq', 0x9f, fmt='>h')
OP_if_icmpne = __op('if_icmpne', 0xa0, fmt='>h')
OP_if_icmplt = __op('if_icmplt', 0xa1, fmt='>h')
OP_if_icmpge = __op('if_icmpge', 0xa2, fmt='>h')
OP_if_icmpgt = __op('if_icmpgt', 0xa3, fmt='>h')
OP_if_icmple = __op('if_icmple', 0xa4, fmt='>h')
OP_ifeq = __op('ifeq', 0x99, fmt='>h')
OP_ifne = __op('ifne', 0x9a, fmt='>h')
OP_iflt = __op('iflt', 0x9b, fmt='>h')
OP_ifge = __op('ifge', 0x9c, fmt='>h')
OP_ifgt = __op('ifgt', 0x9d, fmt='>h')
OP_ifle = __op('ifle', 0x9e, fmt='>h')
OP_ifnonnull = __op('ifnonnull', 0xc7, fmt='>h')
OP_ifnull = __op('ifnull', 0xc6, fmt='>h')
OP_iinc = __op('iinc', 0x84, fmt='>Bb')
OP_iload = __op('iload', 0x15, fmt='>B')
OP_iload_0 = __op('iload_0', 0x1a)
OP_iload_1 = __op('iload_1', 0x1b)
OP_iload_2 = __op('iload_2', 0x1c)
OP_iload_3 = __op('iload_3', 0x1d)
OP_imul = __op('imul', 0x68)
OP_ineg = __op('ineg', 0x74)
OP_instanceof = __op('instanceof', 0xc1, fmt='>H', const=True)
OP_invokedynamic = __op('invokedynamic', 0xba, fmt='>HBB', const=True)
OP_invokeinterface = __op('invokeinterface', 0xb9, fmt='>HBB', const=True)
OP_invokespecial = __op('invokespecial', 0xb7, fmt='>H', const=True)
OP_invokestatic = __op('invokestatic', 0xb8, fmt='>H', const=True)
OP_invokevirtual = __op('invokevirtual', 0xb6, fmt='>H', const=True)
OP_ior = __op('ior', 0x80)
OP_irem = __op('irem', 0x70)
OP_ireturn = __op('ireturn', 0xac)
OP_ishl = __op('ishl', 0x78)
OP_ishr = __op('ishr', 0x7a)
OP_istore = __op('istore', 0x36, fmt='>B')
OP_istore_0 = __op('istore_0', 0x3b)
OP_istore_1 = __op('istore_1', 0x3c)
OP_istore_2 = __op('istore_2', 0x3d)
OP_istore_3 = __op('istore_3', 0x3e)
OP_isub = __op('isub', 0x64)
OP_iushr = __op('iushr', 0x7c)
OP_ixor = __op('ixor', 0x82)

OP_jsr = __op('jsr', 0xa8, fmt='>h')
OP_jsr_w = __op('jsr_w', 0xc9, fmt='>i')

OP_l2d = __op('l2d', 0x8a)
OP_l2f = __op('l2f', 0x89)
OP_l2i = __op('l2i', 0x88)
OP_ladd = __op('ladd', 0x61)
OP_laload = __op('laload', 0x2f)
OP_land = __op('land', 0x7f)
OP_lastore = __op('lastore', 0x50)
OP_lcmp = __op('lcmp', 0x94)
OP_lconst_0 = __op('lconst_0', 0x9)
OP_lconst_1 = __op('lconst_1', 0xa)
OP_ldc = __op('ldc', 0x12, fmt='>B', const=True)
OP_ldc_w = __op('ldc_w', 0x13, fmt='>H', const=True)
OP_ldc2_w = __op('ldc2_w', 0x14, fmt='>H', const=True)
OP_ldiv = __op('ldiv', 0x6d)
OP_lload = __op('lload', 0x16, fmt='>B')
OP_lload_0 = __op('lload_0', 0x1e)
OP_lload_1 = __op('lload_1', 0x1f)
OP_lload_2 = __op('lload_2', 0x20)
OP_lload_3 = __op('lload_3', 0x21)
OP_lmul = __op('lmul', 0x69)
OP_lneg = __op('lneg', 0x75)
OP_lookupswitch = __op('lookupswitch', 0xab, fmt=_unpack_lookupswitch)
OP_lor = __op('lor', 0x81)
OP_lrem = __op('lrem', 0x71)
OP_lreturn = __op('lreturn', 0xad)
OP_lshl = __op('lshl', 0x79)
OP_lshr = __op('lshr', 0x7b)
OP_lstore = __op('lstore', 0x37, fmt='>B')
OP_lstore_0 = __op('lstore_0', 0x3f)
OP_lstore_1 = __op('lstore_1', 0x40)
OP_lstore_2 = __op('lstore_2', 0x41)
OP_lstore_3 = __op('lstore_3', 0x42)
OP_lsub = __op('lsub', 0x65)
OP_lushr = __op('lushr', 0x7d)
OP_lxor = __op('lxor', 0x83)

OP_monitorentry = __op('monitorentry', 0xc2)
OP_monitorexit = __op('monitorexit', 0xc3)
OP_multianewarray = __op('multianewarray', 0xc5, fmt='>HB')

OP_new = __op('new', 0xbb, fmt='>H', const=True)
OP_newarray = __op('newarray', 0xbc, fmt='>B')
OP_nop = __op('nop', 0x0)

OP_pop = __op('pop', 0x57)
OP_pop2 = __op('pop2', 0x58)
OP_putfield = __op('putfield', 0xb5, fmt='>H', const=True)
OP_putstatic = __op('putstatic', 0xb3, fmt='>H', const=True)

OP_ret = __op('ret', 0xa9, fmt='>B')
OP_return = __op('return', 0xb1)

OP_saload = __op('saload', 0x35)
OP_sastore = __op('sastore', 0x56)
OP_sipush = __op('sipush', 0x11, fmt='>h')
OP_swap = __op('swap', 0x5f)

OP_tableswitch = __op('tableswitch', 0xaa, fmt=_unpack_tableswitch)

OP_wide = __op('wide', 0xc4, fmt=_unpack_wide)


#
# The end.
