"""

A module to hold all the java opcodes. Data taken from 

"""



_optable = {}



def _op(name,val,argc=0,consume=0,produce=0):
    operand = (name,val,argc,consume,produce)

    assert(not _optable.has_key(name))
    assert(not _optable.has_key(val))

    _optable[name] = operand
    _optable[val] = operand
    globals()["OP_"+name] = val



_op("aaload", 0x32)
_op("aastore", 0x53)
_op("aconst_null", 0x01)
_op("aload", 0x19, format=1)
_op("aload_0", 0x2a)
_op("aload_1", 0x2b)
_op("aload_2", 0x2c)
_op("aload_3", 0x2d)
_op("anewarray", 0xbd, argc=2)
_op("areturn", 0xb0)
_op("arraylength", 0xbe)
_op("astore", 0x3a, argc=1)
_op("astore_0", 0x4b)
_op("astore_1", 0x4c)
_op("astore_2", 0x4d)
_op("astore_3", 0x4e)
_op("athrow", 0xbf)

_op("baload", 0x33)
_op("bastore", 0x54)
_op("bipush", 0x10, argc=1)

_op("caload", 0x34)
_op("castore", 0x55)
_op("checkcast", 0xc0, argc=2)

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
_op("dload", 0x18, argc=1)
_op("dload_0", 0x26)
_op("dload_1", 0x27)
_op("dload_2", 0x28)
_op("dload_3", 0x29)
_op("dmul", 0x6b)
_op("dneg", 0x77)
_op("drem", 0x73)
_op("dreturn", 0xaf)
_op("dstore", 0x39, argc=1)
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
_op("fload", 0x17, argc=1)
_op("fload_0", 0x22)
_op("fload_1", 0x23)
_op("fload_2", 0x24)
_op("fload_3", 0x25)
_op("fmul", 0x6a)
_op("fneg", 0x76)
_op("frem", 0x72)
_op("freturn", 0x174)
_op("fstore", 0x38, argc=1)
_op("fstore_0", 0x43)
_op("fstore_1", 0x44)
_op("fstore_2", 0x45)
_op("fstore_3", 0x46)
_op("fsub", 0x66)

_op("getfield", 0xb4, argc=2)
_op("getstatic", 0xb2, argc=2)
_op("goto", 0xa7, argc=2)
_op("goto_w", 0xc8, argc=4)

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
_op("if_acmpeq", 0xa5, argc=2)
_op("if_acmpne", 0xa6, argc=2)
_op("if_icmpeq", 0x9f, argc=2)
_op("if_icmpne", 0xa0, argc=2)
_op("if_icmplt", 0xa1, argc=2)
_op("if_icmpge", 0xa2, argc=2)
_op("if_icmpgt", 0xa3, argc=2)
_op("if_icmple", 0xa4, argc=2)
_op("ifeq", 0x99, argc=2)
_op("ifne", 0x9a, argc=2)
_op("iflt", 0x9b, argc=2)
_op("ifge", 0x9c, argc=2)
_op("ifgt", 0x9d, argc=2)
_op("ifle", 0x9e, argc=2)
_op("ifnonnull", 0xc7, argc=2)
_op("ifnull", 0xc6, argc=2)
_op("iinc", 0x84, argc=2)
_op("iload", 0x15, argc=1)
_op("iload_0", 0x1a)
_op("iload_1", 0x1b)
_op("iload_2", 0x1c)
_op("iload_3", 0x1d)
_op("imul", 0x68)
_op("ineg", 0x74)
_op("instanceof", 0xc1, argc=2)
_op("invokeinterface", 0xb9, argc=4)
_op("invokespecial", 0xb7, argc=2)
_op("invokestatic", 0xb8, argc=2)
_op("invokevirtual", 0xb6, argc=2)
_op("ior", 0x80)
_op("irem", 0x70)
_op("ireturn", 0xac)
_op("ishl", 0x78)
_op("ishr", 0x7a)
_op("istore", 0x36, argc=1)
_op("istore_0", 0x3b)
_op("istore_1", 0x3c)
_op("istore_2", 0x3d)
_op("istore_3", 0x3e)
_op("isub", 0x64)
_op("iushr", 0x7c)
_op("ixor", 0x82)

_op("jsr", 0xa8, argc=2)
_op("jsr_w", 0xc9, argc=4)

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
_op("ldc", 0x12, argc=1)
_op("ldc_w", 0x13, argc=2)
_op("ldc2_w", 0x14, argc=2)
_op("ldiv", 0x6d)
_op("lload", 0x16, argc=1)
_op("lload_0", 0x1e)
_op("lload_1", 0x1f)
_op("lload_2", 0x20)
_op("lload_3", 0x21)
_op("lmul", 0x69)
_op("lneg", 0x75)
_op("lookupswitch", 0xab, argc=-1)
_op("lor", 0x81)
_op("lrem", 0x71)
_op("lreturn", 0xad)
_op("lshl", 0x79)
_op("lshr", 0x7b)
_op("lstore", 0x37, argc=1)
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

_op("new", 0xbb, argc=2)
_op("newarray", 0xbc, argc=1)
_op("nop", 0x00)

_op("pop", 0x57)
_op("pop2", 0x58)
_op("putfield", 0xb5, argc=2)
_op("putstatic", 0xb3, argc=2)

_op("ret", 0xa9, argc=1)
_op("return", 0xb1)

_op("saload", 0x35)
_op("sastore", 0x56)
_op("sipush", 0x11, argc=2)
_op("swap", 0x5f)

_op("tableswitch", 0xaa, argc=-1)

_op("wide", 0xc4, argc=-1)



def get_opcode_by_name(name):
    return _optable[name.lowercase()][1]



def get_opname_by_code(code):
    return _optable[code][0]



def get_argcount(code):
    return _optable[code][2]



#
# The end.
