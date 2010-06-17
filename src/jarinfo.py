"""

Module and utility for fetching information out of a JAR file, and
printing it out.

author: Christopher O'Brien  <obriencj@gmail.com>

"""



import sys



def get_manifest_info(zip):
    
    """ fetch the sections from the MANIFEST.MF file. Returns a list
    of dicts representing all of the key:val sections in the
    manifest. """

    from manifest import parse_sections

    data = zip.read("META-INF/MANIFEST.MF")
    return parse_sections(data)



def cli_manifest_info(options, zip):
    mf = get_manifest_info(zip)

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



def zip_entry_rollup(zip):
    
    """ returns a tuple of (files, dirs, size_uncompressed,
    size_compressed). files+dirs will equal len(zip.infolist) """
    
    files, dirs = 0, 0
    total_c, total_u = 0, 0
    
    for i in zip.infolist():
        if i.filename[-1] == '/':
            # I wonder if there's a better detection method than this
            dirs += 1
        else:
            files += 1
            total_c += i.compress_size
            total_u += i.file_size
    
    return files, dirs, total_c, total_u



def cli_zip_info(options, zip):
    
    files, dirs, comp, uncomp = zip_entry_rollup(zip)
    prcnt = (float(comp)  / float(uncomp)) * 100

    print "Contains %i files, %i directories" % (files, dirs)
    print "Uncompressed size is %i" % uncomp
    print "Compressed size is %i (%0.1f%%)" % (comp, prcnt)
    print
    
    return 0



def get_jar_class_info_gen(zip):
    from javaclass import is_class, unpack_class

    for i in zip.infolist():
        if i.filename[-6] == '.class':
            buff = i.read()
            if is_class(buff):
                yield unpack_class(buff)
            del buff



def get_jar_class_infos(zip):
    
    """ A sequence of ClassInfo instances representing the classes
    available in the given JAR. zip should be a ZipFile instance. """

    return tuple(get_jar_class_info_gen(zip))



def get_class_infos_provides(class_infos):

    return [info.pretty_this() for info in class_infos]



def get_class_infos_requires(class_infos):

    from classinfo import get_class_info_requires

    deps = []

    for info in class_infos:
        deps.extend(get_class_info_requires(info))
    
    return set(deps)



def cli_get_class_infos(options, zip):
    ci = getattr(options, "classes", None)
    if not ci:
        ci = get_jar_class_info(zip)
        options.classes = ci
    return ci



def cli_provides(options, zip):

    for i in get_jar_provides(cli_get_class_infos(options, zip)):
        print i

    return 0



def cli_requires(options, zip):

    for i in get_jar_requires(cli_get_class_infos(options, zip)):
        print i

    return 0



def cli_zipfile(options, zip):
    ret = 0

    # zip information (compression, etc)
    if options.zip:
        ret = ret or cli_zip_info(options, zip)

    # manifest information
    if options.manifest:
        ret = ret or cli_manifest_info(options, zip)

    # signature information
    # contained classes
    # contained non-classes

    # classes provided
    if options.provides:
        ret = ret or cli_provides(options, zip)

    # classes required
    if options.requires:
        ret = ret or cli_requires(options, zip)

    return ret



def cli(options, rest):
    from zipfile import ZipFile, BadZipfile

    ret = 0

    for fn in rest[1:]:
        try:
            zip = ZipFile(fn, "r")
            nret = cli_zipfile(options, zip)

        except BadZipfile, bad:
            print bad
            nret = -1

        ret = ret or nret

    return ret



def create_optparser():
    from optparse import OptionParser

    parse = OptionParser()
    # ...

    return parse



def main(args):
    parser = create_optparser()
    return cli(*parser.parse_args(args))



if __name__ == "__main__":
    sys.exit(main(sys.argv))



#
# The end.
