"""

Module for reading and writing MANIFEST.MF files.

http://java.sun.com/j2se/1.5.0/docs/guide/jar/jar.html#JAR%20Manifest

"""


import sys



class ManifestSection(dict):
    
    primary_key = "Name"


    def __init__(self, name=None):
        dict.__init__(self)
        self[self.primary_key] = name


    def __setitem__(self, k, v):
        # our keys should always be strings, as should our values

        k = str(k)
        if len(k) > 69:
            raise Exception("key too long for Manifest")
        else:
            dict.__setitem__(self, k, str(v))


    def primary(self):
        return self.get(self.primary_key)

    
    def load(self, items):
        for k,vals in items:
            self[k] = "".join(vals)


    def store(self, stream):
        # when written to a stream, the primary key must be the first
        # written

        prim = self.primary_key

        keys = sorted(self.keys())
        keys.remove(prim)

        store_item(prim, self[prim], stream)
        
        for k in keys:
            store_item(k, self[k], stream)

        stream.write("\n")



class Manifest(ManifestSection):

    primary_key = "Manifest-Version"

    def __init__(self, version="1.0"):
        ManifestSection.__init__(self, version)
        self.sub_sections = {}


    def create_section(self, name):

        """ create and return a new sub-section of this manifest, with
        the given Name attribute """

        sect = ManifestSection(name)
        self.sub_sections[name] = sect
        return sect


    def parse(self, data):
        
        """ populate instance with values and sub-sections from data
        in a stream or a string"""

        sections = parse_sections(stream)
        self.load(sections.next())

        for section in sections:
            ms = ManifestSection(None)
            ms.load(section)
            self.sub_sections[ms.primary()] = ms


    def store(self, stream):

        """ write Manifest to a stream """

        ManifestSection.store(self, stream)
        for k,sect in sorted(self.sub_sections.items()):
            sect.store(stream)



def store_item(k, v, stream):

    """ The MANIFEST specification limits the width of individual
    lines to 72 bytes (including the terminating newlines). Any key
    and value pair that would be longer must be split up over multiple
    continuing lines"""

    # technically, there's an issue here. The spec doesn't allow for
    # the key string to be broken up with a line continuation: that is
    # to say that the key and the separator colon and space must all
    # be on a single line, and only the value may be broken up. It
    # would be most appropriate to fix this by putting some wrapping
    # methods on the Manifest class so that the sections aren't just
    # plain dictionaries (and thus so we can raise an exception when a
    # too-large key is given)

    from StringIO import StringIO

    v = v or ""
    if len(k) + len(v) > 69:
        s = StringIO()
        s.write(k)
        s.write(": ")
        s.write(v)
        k = s.getvalue()
        s.close()

        s = StringIO(k)

        # first grab 71 (which is 72 after the trailing newline)
        stream.write(s.read(71))

        # now only 70 at a time, because we need a leading space and a
        # trailing \n
        k = s.read(70)
        while k:
            stream.write("\n ")
            stream.write(k)
            k = s.read(70)
        s.close()

    else:
        stream.write(k)
        stream.write(": ")
        stream.write(v)

    stream.write("\n")



def parse_sections(data):

    from StringIO import StringIO
    
    if not data:
        return
    
    if isinstance(data, str):
        data = StringIO(data)

    curr = None

    for line in data:

        # TODO: need to look into whether this is wrong. White space
        # might need to be preserved.
        sl = line.strip()
        
        if not sl:
            if curr:
                yield curr
                curr = None

        elif line[0] == ' ':
            # continuation
            if curr is None:
                raise Exception("malformed Manifest, bad continuation")

            else:
                curr[-1][1].append(sl)

        else:
            if curr is None:
                curr = []
        
            k,v = sl.split(':', 1)
            curr.append( (k, [v[1:]]) )
    
    if curr:
        yield curr



_hashes_new = ()

try:
    import hashlib
    _hashes_new = (hashlib.md5, hashlib.sha1)
except ImportError, err:
    from Crypto.Hash import MD5, SHA
    _hashes_new = (MD5.new, SHA.new)
    


def digests(chunks):

    """ returns a base64 rep of the MD5 and SHA1 digests from the
    chunks of data """

    from base64 import b64encode as b64

    hashes = [h() for h in _hashes_new]
    
    for chunk in chunks:
        for h in hashes:
            h.update(chunk)

    return [b64(h.digest()) for h in hashes]



def file_chunk(filename, x=1024):

    """ returns a generator function which when called will emit
    x-sized chunks of filename's contents""" 

    def chunks():
        fd = open(filename, "rb")
        buf = fd.read(x)
        while buf:
            yield buf
            buf = fd.read(x)
        fd.close()
    return chunks



def zipentry_chunk(zipfile, name, x=1024):

    """ returns a generator function which when called will emit
    x-sized chunks of the named entry in the zipfile object"""

    def chunks():
        fd = zipfile.open(name)
        buf = fd.read(x)
        while buf:
            yield buf
            buf = fd.read(x)
        fd.close()
    return chunks



def directory_generator(dirname, trim=0):
    from os.path import isdir, join, sep, walk

    def gather(collect, dirname, fnames):
        for fname in fnames:
            f = join(dirname, fname)
            if not isdir(f):
                collect.append(f)

    collect = []
    walk(dirname, gather, collect)
    for f in collect:
        yield f[trim:], file_chunk(f)



def multi_path_generator(pathnames):

    """ emits name,chunkgen pairs for all of the files found under the
    list of pathnames given. This is recursive, so directories will
    have their contents emitted. chunkgen is a generator that can be
    iterated over to obtain the contents of the file in multiple parts
    """

    from os.path import isdir
    for pathname in pathnames:
        if isdir(pathname):
            for entry in directory_generator(pathname):
                yield entry
        else:
            yield pathname, file_chunk(pathname)



def single_path_generator(pathname):

    """ emits name,chunkgen pairs for the given file at pathname. If
    pathname is a directory, will act recursively and will emit for
    each file in the directory tree chunkgen is a generator that can
    be iterated over to obtain the contents of the file in multiple
    parts """

    from os.path import isdir, sep
    from zipfile import ZipFile

    if isdir(pathname):
        trim = len(pathname)
        if pathname[-1] != sep:
            trim += 1
        for entry in directory_generator(pathname, trim):
            yield entry

    else:
        zf = ZipFile(pathname)
        for f in zf.namelist():
            yield f, zipentry_chunk(zf, f)
        zf.close()



def cli_create(options, rest):
    from os.path import exists, split
    from os import makedirs

    if options.recursive:
        entries = multi_path_generator(rest[1:])
    else:
        entries = single_path_generator(rest[1])

    mf = Manifest()
    
    for name,chunks in entries:
        sec = mf.create_section(name)

        d = digests(chunks())
        if d:
            md5,sha1 = digests(chunks())
            sec["SHA1-Digest"] = sha1
            sec["MD5-Digest"] = md5

    output = sys.stdout

    if options.manifest:
        # we'll output to the manifest file if specified, and we'll
        # even create parent directories for it, if necessary

        mfdir = split(options.manifest)[0]
        if not exists(mfdir):
            makedirs(mfdir)
        output = open(options.manifest, "wt")

    mf.store(output)

    if options.manifest:
        output.close()



def cli_verify(options, rest):
    # TODO: read in the manifest, and then verify the digests for every
    # file listed.

    pass



def cli(options, rest):
    if options.verify:
        pass
        #return cli_verify(options, rest)
    elif options.create:
        return cli_create(options, rest)
    else:
        print "specify one of --verify or --create"
        return 0



def create_optparser():
    from optparse import OptionParser
    
    parse = OptionParser(usage="Create or verify a MANIFEST for a JAR/ZIP"
                         " or directory")
    
    parse.add_option("-v", "--verify", action="store_true")
    parse.add_option("-c", "--create", action="store_true")
    parse.add_option("-r", "--recursive", action="store_true")
    parse.add_option("-m", "--manifest", action="store", default=None,
                     help="manifest file, default is stdout for create"
                     " or the argument-relative META-INF/MANIFEST.MF"
                     " for verify.")

    return parse



def main(args):
    parser = create_optparser()
    return cli(*parser.parse_args(args))



if __name__ == "__main__":
    sys.exit(main(sys.argv))



#
# The end.
