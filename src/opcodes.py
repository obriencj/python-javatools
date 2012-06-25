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
A module to hold all the java opcodes. Data taken from publicly
available sources (see following for more information)

http://java.sun.com/docs/books/jvms/second_edition/html/VMSpecTOC.doc.html

author: Christopher O'Brien  <obriencj@gmail.com>
license: LGPL
"""



_optable = {}



def _op(name, val, fmt=None, const=False, consume=0, produce=0):

    """ provides sensible defaults for a code, and registers it with
    the _optable for lookup. """

    name = name.lower()
    
    operand = (name, val, fmt, consume, produce, const)

    assert(not _optable.has_key(name))
    assert(not _optable.has_key(val))

    _optable[name] = operand
    _optable[val] = operand

    return val



def get_opcode_by_name(name):

    """ get the integer opcode by its name """

    return _optable[name.lower()][1]



def get_opname_by_code(code):

    """ get the name of an opcode """

    return _optable[code][0]



def get_arg_format(code):

    """ get the format of arguments to this opcode """

    return _optable[code][2]



def has_const_arg(code):

    """ which arg is a const for this opcode """
    
    return _optable[code][5]



def _unpack(frmt, bc, offset=0):

    """ returns the unpacked data tuple, and the next offset past the
    unpacked data"""

    from javatools import compile_struct

    sfmt = compile_struct(frmt)
    data = buffer(bc, offset, sfmt.size)

    return (sfmt.unpack(data), offset+sfmt.size)



def _unpack_lookupswitch(bc, offset):
    jump = (offset % 4)
    if jump:
        offset += (4 - jump)

    (default, npairs), offset = _unpack(">ii", bc, offset)

    switches = []
    for _ in xrange(0, npairs):
        pair, offset = _unpack(">ii", bc, offset)
        switches.append(pair)
    switches = tuple(switches)

    return (default, switches), offset



def _unpack_tableswitch(bc, offset):
    jump = (offset % 4)
    if jump:
        offset += (4 - jump)

    (default, low, high), offset = _unpack(">iii", bc, offset)

    joffs = []
    for _ in xrange(0, (high - low) + 1):
        j, offset = _unpack(">i", bc, offset)
        joffs.append(j)
    joffs = tuple(joffs)

    return (default, low, high, joffs), offset



def _unpack_wide(bc, offset):
    code = ord(bc[offset])

    if code == OP_iinc:
        return _unpack(">BHh", bc, offset)

    elif code in (OP_iload, OP_fload, OP_aload, OP_lload, OP_dload,
                  OP_istore, OP_fstore, OP_astore, OP_lstore,
                  OP_dstore, OP_ret):

        return _unpack(">BH", bc, offset)

    else:

        # nothing else is valid, so it shouldn't have been passed here.
        assert(False)



def disassemble_gen(bytecode):
    
    """ disassembles Java bytecode into a sequence of
    (offset,code,args) tuples """

    offset = 0
    end = len(bytecode)

    while offset < end:
        orig_offset = offset

        code = ord(bytecode[offset])
        offset += 1

        fmt = get_arg_format(code)

        if callable(fmt):
            args,offset = fmt(bytecode, offset)
        elif fmt:
            args,offset = _unpack(fmt, bytecode, offset)
        else:
            args = ()

        yield (orig_offset, code, args)
    


def disassemble(bytecode):
    return tuple(disassemble_gen(bytecode))



# And now, the OP codes themselves

# The individual OP_* constants just have the numerical value. The
# rest is just information to get stored in the _optable

#pylint: disable=C0103

OP_aaload = _op('aaload', 0x32)
OP_aastore = _op('aastore', 0x53)
OP_aconst_null = _op('aconst_null', 0x1)
OP_aload = _op('aload', 0x19, fmt='>B')
OP_aload_0 = _op('aload_0', 0x2a)
OP_aload_1 = _op('aload_1', 0x2b)
OP_aload_2 = _op('aload_2', 0x2c)
OP_aload_3 = _op('aload_3', 0x2d)
OP_anewarray = _op('anewarray', 0xbd, fmt='>H', const=True)
OP_areturn = _op('areturn', 0xb0)
OP_arraylength = _op('arraylength', 0xbe)
OP_astore = _op('astore', 0x3a, fmt='>B')
OP_astore_0 = _op('astore_0', 0x4b)
OP_astore_1 = _op('astore_1', 0x4c)
OP_astore_2 = _op('astore_2', 0x4d)
OP_astore_3 = _op('astore_3', 0x4e)
OP_athrow = _op('athrow', 0xbf)

OP_baload = _op('baload', 0x33)
OP_bastore = _op('bastore', 0x54)
OP_bipush = _op('bipush', 0x10, fmt='>B')

OP_caload = _op('caload', 0x34)
OP_castore = _op('castore', 0x55)
OP_checkcast = _op('checkcast', 0xc0, fmt='>H', const=True)

OP_d2f = _op('d2f', 0x90)
OP_d2i = _op('d2i', 0x8e)
OP_d2l = _op('d2l', 0x8f)
OP_dadd = _op('dadd', 0x63)
OP_daload = _op('daload', 0x31)
OP_dastore = _op('dastore', 0x52)
OP_dcmpg = _op('dcmpg', 0x98)
OP_dcmpl = _op('dcmpl', 0x97)
OP_dconst_0 = _op('dconst_0', 0xe)
OP_dconst_1 = _op('dconst_1', 0xf)
OP_ddiv = _op('ddiv', 0x6f)
OP_dload = _op('dload', 0x18, fmt='>B')
OP_dload_0 = _op('dload_0', 0x26)
OP_dload_1 = _op('dload_1', 0x27)
OP_dload_2 = _op('dload_2', 0x28)
OP_dload_3 = _op('dload_3', 0x29)
OP_dmul = _op('dmul', 0x6b)
OP_dneg = _op('dneg', 0x77)
OP_drem = _op('drem', 0x73)
OP_dreturn = _op('dreturn', 0xaf)
OP_dstore = _op('dstore', 0x39, fmt='>B')
OP_dstore_0 = _op('dstore_0', 0x47)
OP_dstore_1 = _op('dstore_1', 0x48)
OP_dstore_2 = _op('dstore_2', 0x49)
OP_dstore_3 = _op('dstore_3', 0x4a)
OP_dsub = _op('dsub', 0x67)
OP_dup = _op('dup', 0x59)
OP_dup_x1 = _op('dup_x1', 0x5a)
OP_dup_x2 = _op('dup_x2', 0x5b)
OP_dup2 = _op('dup2', 0x5c)
OP_dup2_x1 = _op('dup2_x1', 0x5d)
OP_dup2_x2 = _op('dup2_x2', 0x5e)

OP_f2d = _op('f2d', 0x8d)
OP_f2i = _op('f2i', 0x8b)
OP_f2l = _op('f2l', 0x8c)
OP_fadd = _op('fadd', 0x62)
OP_faload = _op('faload', 0x30)
OP_fastore = _op('fastore', 0x51)
OP_fcmpg = _op('fcmpg', 0x96)
OP_fcmpl = _op('fcmpl', 0x95)
OP_fconst_0 = _op('fconst_0', 0xb)
OP_fconst_1 = _op('fconst_1', 0xc)
OP_fconst_2 = _op('fconst_2', 0xd)
OP_fdiv = _op('fdiv', 0x6e)
OP_fload = _op('fload', 0x17, fmt='>B')
OP_fload_0 = _op('fload_0', 0x22)
OP_fload_1 = _op('fload_1', 0x23)
OP_fload_2 = _op('fload_2', 0x24)
OP_fload_3 = _op('fload_3', 0x25)
OP_fmul = _op('fmul', 0x6a)
OP_fneg = _op('fneg', 0x76)
OP_frem = _op('frem', 0x72)
OP_freturn = _op('freturn', 0xae)
OP_fstore = _op('fstore', 0x38, fmt='>B')
OP_fstore_0 = _op('fstore_0', 0x43)
OP_fstore_1 = _op('fstore_1', 0x44)
OP_fstore_2 = _op('fstore_2', 0x45)
OP_fstore_3 = _op('fstore_3', 0x46)
OP_fsub = _op('fsub', 0x66)

OP_getfield = _op('getfield', 0xb4, fmt='>H', const=True)
OP_getstatic = _op('getstatic', 0xb2, fmt='>H', const=True)
OP_goto = _op('goto', 0xa7, fmt='>h')
OP_goto_w = _op('goto_w', 0xc8, fmt='>i')

OP_i2b = _op('i2b', 0x91)
OP_i2c = _op('i2c', 0x92)
OP_i2d = _op('i2d', 0x87)
OP_i2f = _op('i2f', 0x86)
OP_i2l = _op('i2l', 0x85)
OP_i2s = _op('i2s', 0x93)
OP_iadd = _op('iadd', 0x60)
OP_iaload = _op('iaload', 0x2e)
OP_iand = _op('iand', 0x7e)
OP_iastore = _op('iastore', 0x4f)
OP_iconst_m1 = _op('iconst_m1', 0x2)
OP_iconst_0 = _op('iconst_0', 0x3)
OP_iconst_1 = _op('iconst_1', 0x4)
OP_iconst_2 = _op('iconst_2', 0x5)
OP_iconst_3 = _op('iconst_3', 0x6)
OP_iconst_4 = _op('iconst_4', 0x7)
OP_iconst_5 = _op('iconst_5', 0x8)
OP_idiv = _op('idiv', 0x6c)
OP_if_acmpeq = _op('if_acmpeq', 0xa5, fmt='>h')
OP_if_acmpne = _op('if_acmpne', 0xa6, fmt='>h')
OP_if_icmpeq = _op('if_icmpeq', 0x9f, fmt='>h')
OP_if_icmpne = _op('if_icmpne', 0xa0, fmt='>h')
OP_if_icmplt = _op('if_icmplt', 0xa1, fmt='>h')
OP_if_icmpge = _op('if_icmpge', 0xa2, fmt='>h')
OP_if_icmpgt = _op('if_icmpgt', 0xa3, fmt='>h')
OP_if_icmple = _op('if_icmple', 0xa4, fmt='>h')
OP_ifeq = _op('ifeq', 0x99, fmt='>h')
OP_ifne = _op('ifne', 0x9a, fmt='>h')
OP_iflt = _op('iflt', 0x9b, fmt='>h')
OP_ifge = _op('ifge', 0x9c, fmt='>h')
OP_ifgt = _op('ifgt', 0x9d, fmt='>h')
OP_ifle = _op('ifle', 0x9e, fmt='>h')
OP_ifnonnull = _op('ifnonnull', 0xc7, fmt='>h')
OP_ifnull = _op('ifnull', 0xc6, fmt='>h')
OP_iinc = _op('iinc', 0x84, fmt='>Bb')
OP_iload = _op('iload', 0x15, fmt='>B')
OP_iload_0 = _op('iload_0', 0x1a)
OP_iload_1 = _op('iload_1', 0x1b)
OP_iload_2 = _op('iload_2', 0x1c)
OP_iload_3 = _op('iload_3', 0x1d)
OP_imul = _op('imul', 0x68)
OP_ineg = _op('ineg', 0x74)
OP_instanceof = _op('instanceof', 0xc1, fmt='>H', const=True)
OP_invokeinterface = _op('invokeinterface', 0xb9, fmt='>HBB', const=True)
OP_invokespecial = _op('invokespecial', 0xb7, fmt='>H', const=True)
OP_invokestatic = _op('invokestatic', 0xb8, fmt='>H', const=True)
OP_invokevirtual = _op('invokevirtual', 0xb6, fmt='>H', const=True)
OP_ior = _op('ior', 0x80)
OP_irem = _op('irem', 0x70)
OP_ireturn = _op('ireturn', 0xac)
OP_ishl = _op('ishl', 0x78)
OP_ishr = _op('ishr', 0x7a)
OP_istore = _op('istore', 0x36, fmt='>B')
OP_istore_0 = _op('istore_0', 0x3b)
OP_istore_1 = _op('istore_1', 0x3c)
OP_istore_2 = _op('istore_2', 0x3d)
OP_istore_3 = _op('istore_3', 0x3e)
OP_isub = _op('isub', 0x64)
OP_iushr = _op('iushr', 0x7c)
OP_ixor = _op('ixor', 0x82)

OP_jsr = _op('jsr', 0xa8, fmt='>h')
OP_jsr_w = _op('jsr_w', 0xc9, fmt='>i')

OP_l2d = _op('l2d', 0x8a)
OP_l2f = _op('l2f', 0x89)
OP_l2i = _op('l2i', 0x88)
OP_ladd = _op('ladd', 0x61)
OP_laload = _op('laload', 0x2f)
OP_land = _op('land', 0x7f)
OP_lastore = _op('lastore', 0x50)
OP_lcmp = _op('lcmp', 0x94)
OP_lconst_0 = _op('lconst_0', 0x9)
OP_lconst_1 = _op('lconst_1', 0xa)
OP_ldc = _op('ldc', 0x12, fmt='>B', const=True)
OP_ldc_w = _op('ldc_w', 0x13, fmt='>H', const=True)
OP_ldc2_w = _op('ldc2_w', 0x14, fmt='>H', const=True)
OP_ldiv = _op('ldiv', 0x6d)
OP_lload = _op('lload', 0x16, fmt='>B')
OP_lload_0 = _op('lload_0', 0x1e)
OP_lload_1 = _op('lload_1', 0x1f)
OP_lload_2 = _op('lload_2', 0x20)
OP_lload_3 = _op('lload_3', 0x21)
OP_lmul = _op('lmul', 0x69)
OP_lneg = _op('lneg', 0x75)
OP_lookupswitch = _op('lookupswitch', 0xab, fmt=_unpack_lookupswitch)
OP_lor = _op('lor', 0x81)
OP_lrem = _op('lrem', 0x71)
OP_lreturn = _op('lreturn', 0xad)
OP_lshl = _op('lshl', 0x79)
OP_lshr = _op('lshr', 0x7b)
OP_lstore = _op('lstore', 0x37, fmt='>B')
OP_lstore_0 = _op('lstore_0', 0x3f)
OP_lstore_1 = _op('lstore_1', 0x40)
OP_lstore_2 = _op('lstore_2', 0x41)
OP_lstore_3 = _op('lstore_3', 0x42)
OP_lsub = _op('lsub', 0x65)
OP_lushr = _op('lushr', 0x7d)
OP_lxor = _op('lxor', 0x83)

OP_monitorentry = _op('monitorentry', 0xc2)
OP_monitorexit = _op('monitorexit', 0xc3)
OP_multianewarray = _op('multianewarray', 0xc5)

OP_new = _op('new', 0xbb, fmt='>H', const=True)
OP_newarray = _op('newarray', 0xbc, fmt='>B')
OP_nop = _op('nop', 0x0)

OP_pop = _op('pop', 0x57)
OP_pop2 = _op('pop2', 0x58)
OP_putfield = _op('putfield', 0xb5, fmt='>H', const=True)
OP_putstatic = _op('putstatic', 0xb3, fmt='>H', const=True)

OP_ret = _op('ret', 0xa9, fmt='>B')
OP_return = _op('return', 0xb1)

OP_saload = _op('saload', 0x35)
OP_sastore = _op('sastore', 0x56)
OP_sipush = _op('sipush', 0x11, fmt='>h')
OP_swap = _op('swap', 0x5f)

OP_tableswitch = _op('tableswitch', 0xaa, fmt=_unpack_tableswitch)

OP_wide = _op('wide', 0xc4, fmt=_unpack_wide)



#
# The end.
