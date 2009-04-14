"""

Module and utility for fetching information out of a JAR file, and
printing it out.

author: Christopher O'Brien  <obriencj@gmail.com>

"""



import sys



def parse_sections(data):

    """ Parse a string or a stream into a sequence of key:value
    sections as specified in the JAR specification. Returns a list of
    dicts """

    from StringIO import StringIO
    
    if not data:
        return tuple()
    
    if isinstance(data, str):
        data = StringIO(data)
        
    sects = []
    curr = None
    cont_key = None

    for line in data:
        if not line:
            curr = None

        elif line[0] == ' ':
            prev = curr[cont_key]
            curr[cont_key] = prev + line.strip()

        else:
            if not curr:
                curr = {}
                sects.append(curr)
        
            k,v = line.split(':', 1)
            curr[k] = v.strip()
    
    return sects



def get_manifest_info(zip):
    
    """ fetch the sections from the MANIFEST.MF file. Returns a list
    of dicts representing all of the key:val sections in the
    manifest. """

    data = zip.read("META-INF/MANIFEST.MF")
    return parse_sections(data)



def cli_manifest_info(options, zip):
    mf = get_manifest_info(zip)

    if not mf:
        print "META-INFO/MANIFEST.MF not found"
        return -1

    print "Manifest data follows:"

    print " Main section:"
    for k,v in mf[0].items():
        print "  %s: %s" % (k,v)

    for sect in mf[1:]:
        print " Sub-section:"
        for k,v in sect.items():
            print "  %s: %s" % (k,v)


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

    return 0



def cli_zipfile(options, zip):
    ret = 0

    # zip information (compression, etc)
    ret = ret or cli_zip_info(options, zip)

    # manifest information
    ret = ret or cli_manifest_info(options, zip)

    # signature information
    # contained classes
    # contained non-classes

    return ret



def cli(options, rest):
    from zipfile import ZipFile, BadZipfile

    ret = 0

    for fn in rest[0:]:
        try:
            zip = ZipFile(fn, "r")
            nret = cli_zipfile(zip)

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
