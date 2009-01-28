"""

A module to hold all the java opcodes. Data taken from publicly
available sources (see following for more information)

http://java.sun.com/docs/books/jvms/second_edition/html/VMSpecTOC.doc.html

author: Christopher O'Brien  <siege@preoccupied.net>

"""



_optable = {}
    



def _op(name,val,format=None,const=False,consume=0,produce=0):
    name = name.lower()

    operand = (name,val,format,consume,produce,const)

    assert(not _optable.has_key(name))
    assert(not _optable.has_key(val))

    _optable[name] = operand
    _optable[val] = operand
    globals()["OP_"+name] = val



def get_opcode_by_name(name):
    return _optable[name.lower()][1]



def get_opname_by_code(code):
    return _optable[code][0]



def get_arg_format(code):
    return _optable[code][2]



def has_const_arg(code):
    return _optable[code][5]



def _unpack(frmt, bc, offset=0):
    from javaclass import _compile

    sfmt = _compile(frmt)

    buff = buffer(bc, offset, sfmt.size)
    
    if len(bc) < sfmt.size:
        raise Exception("not enough data in buffer for format")

    val = sfmt.unpack(buff)
    return val, offset+sfmt.size



def _unpack_lookupswitch(bc, offset):
    jump = (offset % 4)
    if jump:
        offset += (4 - jump)

    (default, npairs), offset = _unpack(">ii", bc, offset)

    switches = []
    for i in xrange(0, npairs):
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
    for i in xrange(0, (high - low) + 1):
        j, offset = _unpack(">i", bc, offset)
        joffs.append(j)
    joffs = tuple(joffs)

    return (default, low, high, joffs), offset



def _unpack_wide(bc, offset):
    code = ord(bc[offset])

    if code == OP_iinc:
        # 0x84

        # iinc
        return _unpack(">BHh", bc, offset)

    elif code in (OP_iload, OP_fload, OP_aload, OP_lload, OP_dload,
                  OP_istore, OP_fstore, OP_astore, OP_lstore,
                  OP_dstore, OP_ret):

        # ( 0x15, 0x17, 0x19, 0x16, 0x18, 0x36, 0x38, 0x3a, 0x37,
        #   0x39, 0xa9 )

        return _unpack(">BH", bc, offset)

    else:

        # nothing else is valid
        assert(False)



def disassemble(bytecode):
    
    """ disassembles Java bytecode into a sequence of
    (offset,code,args) tuples """

    offset = 0
    end = len(bytecode)

    dis = []

    while offset < end:
        orig_offset = offset

        code = ord(bytecode[offset])
        offset += 1

        format = get_arg_format(code)

        if callable(format):
            args,offset = format(bytecode, offset)
        elif format:
            args,offset = _unpack(format, bytecode, offset)
        else:
            args = ()

        dis.append( (orig_offset, code, args) )

    return tuple(dis)



# And now for all the operator definitions

_op("aaload", 0x32)
_op("aastore", 0x53)
_op("aconst_null", 0x01)
_op("aload", 0x19, format=">B")
_op("aload_0", 0x2a)
_op("aload_1", 0x2b)
_op("aload_2", 0x2c)
_op("aload_3", 0x2d)
_op("anewarray", 0xbd, format=">H", const=True)
_op("areturn", 0xb0)
_op("arraylength", 0xbe)
_op("astore", 0x3a, format=">B")
_op("astore_0", 0x4b)
_op("astore_1", 0x4c)
_op("astore_2", 0x4d)
_op("astore_3", 0x4e)
_op("athrow", 0xbf)

_op("baload", 0x33)
_op("bastore", 0x54)
_op("bipush", 0x10, format=">B")

_op("caload", 0x34)
_op("castore", 0x55)
_op("checkcast", 0xc0, format=">H", const=True)

_op("d2f", 0x90)
_op("d2i", 0x8e)
_op("d2l", 0x8f)
_op("dadd", 0x63)
_op("daload", 0x31)
_op("dastore", 0x52)
_op("dcmpg", 0x98)
_op("dcmpl", 0x97)
_op("dconst_0", 0x0e)
_op("dconst_1", 0x0f)
_op("ddiv", 0x6f)
_op("dload", 0x18, format=">B")
_op("dload_0", 0x26)
_op("dload_1", 0x27)
_op("dload_2", 0x28)
_op("dload_3", 0x29)
_op("dmul", 0x6b)
_op("dneg", 0x77)
_op("drem", 0x73)
_op("dreturn", 0xaf)
_op("dstore", 0x39, format=">B")
_op("dstore_0", 0x47)
_op("dstore_1", 0x48)
_op("dstore_2", 0x49)
_op("dstore_3", 0x4a)
_op("dsub", 0x67)
_op("dup", 0x59)
_op("dup_x1", 0x5a)
_op("dup_x2", 0x5b)
_op("dup2", 0x5c)
_op("dup2_x1", 0x5d)
_op("dup2_x2", 0x5e)

_op("f2d", 0x8d)
_op("f2i", 0x8b)
_op("f2l", 0x8c)
_op("fadd", 0x62)
_op("faload", 0x30)
_op("fastore", 0x51)
_op("fcmpg", 0x96)
_op("fcmpl", 0x95)
_op("fconst_0", 0x0b)
_op("fconst_1", 0x0c)
_op("fconst_2", 0x0d)
_op("fdiv", 0x6e)
_op("fload", 0x17, format=">B")
_op("fload_0", 0x22)
_op("fload_1", 0x23)
_op("fload_2", 0x24)
_op("fload_3", 0x25)
_op("fmul", 0x6a)
_op("fneg", 0x76)
_op("frem", 0x72)
_op("freturn", 0x174)
_op("fstore", 0x38, format=">B")
_op("fstore_0", 0x43)
_op("fstore_1", 0x44)
_op("fstore_2", 0x45)
_op("fstore_3", 0x46)
_op("fsub", 0x66)

_op("getfield", 0xb4, format=">H", const=True)
_op("getstatic", 0xb2, format=">H", const=True)
_op("goto", 0xa7, format=">h")
_op("goto_w", 0xc8, format=">i")

_op("i2b", 0x91)
_op("i2c", 0x92)
_op("i2d", 0x87)
_op("i2f", 0x86)
_op("i2l", 0x85)
_op("i2s", 0x93)
_op("iadd", 0x60)
_op("iaload", 0x2e)
_op("iand", 0x7e)
_op("iastore", 0x4f)
_op("iconst_m1", 0x02)
_op("iconst_0", 0x03)
_op("iconst_1", 0x04)
_op("iconst_2", 0x05)
_op("iconst_3", 0x06)
_op("iconst_4", 0x07)
_op("iconst_5", 0x08)
_op("idiv", 0x6c)
_op("if_acmpeq", 0xa5, format=">h")
_op("if_acmpne", 0xa6, format=">h")
_op("if_icmpeq", 0x9f, format=">h")
_op("if_icmpne", 0xa0, format=">h")
_op("if_icmplt", 0xa1, format=">h")
_op("if_icmpge", 0xa2, format=">h")
_op("if_icmpgt", 0xa3, format=">h")
_op("if_icmple", 0xa4, format=">h")
_op("ifeq", 0x99, format=">h")
_op("ifne", 0x9a, format=">h")
_op("iflt", 0x9b, format=">h")
_op("ifge", 0x9c, format=">h")
_op("ifgt", 0x9d, format=">h")
_op("ifle", 0x9e, format=">h")
_op("ifnonnull", 0xc7, format=">h")
_op("ifnull", 0xc6, format=">h")
_op("iinc", 0x84, format=">Bb")
_op("iload", 0x15, format=">B")
_op("iload_0", 0x1a)
_op("iload_1", 0x1b)
_op("iload_2", 0x1c)
_op("iload_3", 0x1d)
_op("imul", 0x68)
_op("ineg", 0x74)
_op("instanceof", 0xc1, format=">H", const=True)
_op("invokeinterface", 0xb9, format=">HBB", const=True)
_op("invokespecial", 0xb7, format=">H", const=True)
_op("invokestatic", 0xb8, format=">H", const=True)
_op("invokevirtual", 0xb6, format=">H", const=True)
_op("ior", 0x80)
_op("irem", 0x70)
_op("ireturn", 0xac)
_op("ishl", 0x78)
_op("ishr", 0x7a)
_op("istore", 0x36, format=">B")
_op("istore_0", 0x3b)
_op("istore_1", 0x3c)
_op("istore_2", 0x3d)
_op("istore_3", 0x3e)
_op("isub", 0x64)
_op("iushr", 0x7c)
_op("ixor", 0x82)

_op("jsr", 0xa8, format=">h")
_op("jsr_w", 0xc9, format=">i")

_op("l2d", 0x8a)
_op("l2f", 0x89)
_op("l2i", 0x88)
_op("ladd", 0x61)
_op("laload", 0x2f)
_op("land", 0x7f)
_op("lastore", 0x50)
_op("lcmp", 0x94)
_op("lconst_0", 0x09)
_op("lconst_1", 0x0a)
_op("ldc", 0x12, format=">B", const=True)
_op("ldc_w", 0x13, format=">H", const=True)
_op("ldc2_w", 0x14, format=">H", const=True)
_op("ldiv", 0x6d)
_op("lload", 0x16, format=">B")
_op("lload_0", 0x1e)
_op("lload_1", 0x1f)
_op("lload_2", 0x20)
_op("lload_3", 0x21)
_op("lmul", 0x69)
_op("lneg", 0x75)
_op("lookupswitch", 0xab, format=_unpack_lookupswitch)
_op("lor", 0x81)
_op("lrem", 0x71)
_op("lreturn", 0xad)
_op("lshl", 0x79)
_op("lshr", 0x7b)
_op("lstore", 0x37, format=">B")
_op("lstore_0", 0x3f)
_op("lstore_1", 0x40)
_op("lstore_2", 0x41)
_op("lstore_3", 0x42)
_op("lsub", 0x65)
_op("lushr", 0x7d)
_op("lxor", 0x83)

_op("monitorentry", 0xc2)
_op("monitorexit", 0xc3)
_op("multianewarray", 0xc5)

_op("new", 0xbb, format=">H", const=True)
_op("newarray", 0xbc, format=">B")
_op("nop", 0x00)

_op("pop", 0x57)
_op("pop2", 0x58)
_op("putfield", 0xb5, format=">H", const=True)
_op("putstatic", 0xb3, format=">H", const=True)

_op("ret", 0xa9, format=">B")
_op("return", 0xb1)

_op("saload", 0x35)
_op("sastore", 0x56)
_op("sipush", 0x11, format=">h")
_op("swap", 0x5f)

_op("tableswitch", 0xaa, format=_unpack_tableswitch)

_op("wide", 0xc4, format=_unpack_wide)



#
# The end.
