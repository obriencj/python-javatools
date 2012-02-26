"""

Module and utility for fetching information out of a JAR file, and
printing it out.

author: Christopher O'Brien  <obriencj@gmail.com>

"""



import sys



def get_manifest_info(zipfile):
    
    """ fetch the sections from the MANIFEST.MF file. Returns a list
    of dicts representing all of the key:val sections in the
    manifest. """

    from manifest import parse_sections

    data = zipfile.read("META-INF/MANIFEST.MF")
    return parse_sections(data)



def cli_manifest_info(options, zipfile):
    mf = get_manifest_info(zipfile)

    if not mf:
        print "META-INFO/MANIFEST.MF not found"
        return -1


    print "Manifest main section:"
    for k,v in sorted(mf[0].items()):
        print "  %s: %s" % (k,v)

    for sect in mf[1:]:
        print
        print "Manifest sub-section:"
        for k,v in sorted(sect.items()):
            print "  %s: %s" % (k,v)

    print



def zip_entry_rollup(zipfile):
    
    """ returns a tuple of (files, dirs, size_uncompressed,
    size_compressed). files+dirs will equal len(zipfile.infolist) """
    
    files, dirs = 0, 0
    total_c, total_u = 0, 0
    
    for i in zipfile.infolist():
        if i.filename[-1] == '/':
            # I wonder if there's a better detection method than this
            dirs += 1
        else:
            files += 1
            total_c += i.compress_size
            total_u += i.file_size
    
    return files, dirs, total_c, total_u



def cli_zip_info(options, zipfile):
    
    files, dirs, comp, uncomp = zip_entry_rollup(zipfile)
    prcnt = (float(comp)  / float(uncomp)) * 100

    print "Contains %i files, %i directories" % (files, dirs)
    print "Uncompressed size is %i" % uncomp
    print "Compressed size is %i (%0.1f%%)" % (comp, prcnt)
    print
    
    return 0



def get_jar_class_info_map(zipfile):
    from javaclass import is_class, unpack_class

    """ A map of entry names to ClassInfo instances representing the
    classes available in the given JAR. zip should be a ZipFile
    instance."""

    ret = {}

    for i in zipfile.infolist():
        if i.filename.endswith('.class'):
            buff = zipfile.read(i.filename)
            if is_class(buff):
                ret[i.filename] = unpack_class(buff)
            del buff

    return ret



def get_class_infos_provides(class_infos):

    return [info.pretty_this() for info in class_infos]



def get_class_infos_requires(class_infos):

    from classinfo import get_class_info_requires

    deps = []

    for info in class_infos:
        deps.extend(get_class_info_requires(info))
    
    return set(deps)



def cli_get_class_info_map(options, zipfile):

    """ Collect the classinfo for the class files contained in the
    zip, and store them for later use on options. This is a bit of a hack
    to use options to save state """

    ci = getattr(options, "_classes_", None)
    if not ci:
        ci = get_jar_class_info_map(zipfile)
        options._classes_ = ci
    return ci
    


def cli_get_class_infos(options, zipfile):
    return cli_get_class_info_map(options, zipfile).values()



def cli_classes(options, zipfile):
    from classinfo import cli_print_classinfo

    for k,ci in cli_get_class_info_map(options, zipfile).items():
        print "Entry: ", k
        cli_print_classinfo(options, ci)
        print


def cli_provides(options, zipfile):

    for i in get_class_infos_provides(cli_get_class_infos(options, zipfile)):
        print i

    return 0



def cli_requires(options, zipfile):

    for i in get_class_infos_requires(cli_get_class_infos(options, zipfile)):
        print i

    return 0



def cli_zipfile(options, zipfile):
    ret = 0

    # zip information (compression, etc)
    if options.zip:
        ret = ret or cli_zip_info(options, zipfile)

    # manifest information
    if options.manifest:
        ret = ret or cli_manifest_info(options, zipfile)

    # signature information

    # contained classes
    if options.classes:
        ret = ret or cli_classes(options, zipfile)

    # contained non-classes
        

    # classes provided
    if options.provides:
        ret = ret or cli_provides(options, zipfile)

    # classes required
    if options.requires:
        ret = ret or cli_requires(options, zipfile)

    return ret



def cli(options, rest):
    from zipdelta import ZipFile

    # TODO: temporary yucky handling of magic options brought in from
    # the classinfo module's create_optparse.

    if options.verbose:
        options.lines = True
        options.locals = True
        options.disassemble = True
        options.sigs = True
        options.constpool = True

    options.indent = not(options.lines or
                         options.disassemble or
                         options.sigs)

    ret = 0

    for fn in rest[1:]:
        nret = cli_zipfile(options, ZipFile(fn))
        ret = ret or nret

    return ret



def create_optparser():
    import classinfo

    p = classinfo.create_optparser()
    
    p.add_option("--zip", action="store_true", default=False,
                 help="print zip information")

    p.add_option("--manifest", action="store_true", default=False,
                 help="print manifest information")

    p.add_option("--provides", action="store_true", default=False,
                 help="print provided class names")

    p.add_option("--requires", action="store_true", default=False,
                 help="print requirements for classes")

    p.add_option("--classes", action="store_true", default=False,
                 help="print information about contained classes")

    return p



def main(args):
    parser = create_optparser()
    return cli(*parser.parse_args(args))



if __name__ == "__main__":
    sys.exit(main(sys.argv))



#
# The end.
