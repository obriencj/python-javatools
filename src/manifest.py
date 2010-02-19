"""

"""


import sys



class Manifest(object):

    def __init__(self):
        self.main_section = { "Manifest-Version": "1.0" }
        self.sub_sections = []

    def append_section(self):
        sect = {}
        self.sub_sections.append(sect)
        return sect

    def load(self, stream):
        sections = parse_sections(stream)
        self.main_section = sections[0]
        self.sub_sections = sections[1:]

    def store(self, stream):
        store_section(self.main_section, stream, "Manifest-Version")
        for sect in self.sub_sections:
            store_section(sect, stream, "Name")



def store_item(k, v, stream):

    """ The MANIFEST specification limits the width of individual
    lines to 72 bytes (including the terminating newlines). Any key
    and value pair that would be longer must be split up over multiple
    continuing lines"""

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
        stream.write(s.read(71))

        k = s.read(71)
        while k:
            stream.write("\n ")
            stream.write(k)
            k = s.read(71)
        s.close()

    else:
        stream.write(k)
        stream.write(": ")
        stream.write(v)

    stream.write("\n")



def store_section(sect, stream, head):
    store_item(head, sect[head], stream)

    for k,v in sect.items():
        if k != head:
            store_item(k, v, stream)

    stream.write("\n")



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
        sl = line.strip()
        
        if not sl:
            curr = None

        elif line[0] == ' ':
            prev = curr[cont_key]
            curr[cont_key] = prev + sl

        else:
            if not curr:
                curr = {}
                sects.append(curr)
        
            k,v = sl.split(':', 1)
            cont_key = k
            curr[k] = v[1:]
    
    return sects



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
    def chunks():
        fd = open(filename, "rb")
        buf = fd.read(x)
        while buf:
            yield buf
            buf = fd.read(x)
        fd.close()
    return chunks



def zipentry_chunk(zipfile, name, x=1024):
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



def multi_generator(pathnames):
    from os.path import isdir
    for pathname in pathnames:
        if isdir(pathname):
            for entry in directory_generator(pathname):
                yield entry
        else:
            yield pathname, file_chunk(pathname)



def single_generator(pathname):
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
        entries = multi_generator(rest[1:])
    else:
        entries = single_generator(rest[1])

    mf = Manifest()
    
    for name,chunks in entries:
        sec = mf.append_section()
        sec["Name"] = name

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
