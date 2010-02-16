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
    lines to 72 bytes (not including the terminating newlines). Any
    key:value pair that would be longer must be split up over multiple
    continuing lines """

    from StringIO import StringIO

    v = v or ""
    if len(k) + len(v) > 70:
        s = StringIO()
        s.write(k)
        s.write(": ")
        s.write(v)
        k = s.getvalue()
        s.close()

        s = StringIO(k)
        stream.write(s.read(72))

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



def entry_generator(pathname):
    from os.path import isdir, join, sep, walk
    from zipfile import ZipFile

    if isdir(pathname):
        def gather(collect, dirname, fnames):
            for fname in fnames:
                f = join(dirname, fname)
                if not isdir(f):
                    collect.append(f)
        collect = []
        walk(pathname, gather, collect)
        l = len(pathname)
        if pathname[-1] != sep:
            l += 1
        for f in collect:
            yield f[l:], file_chunk(f)

    else:
        zf = ZipFile(pathname)
        for f in zf.namelist():
            yield f, zipentry_chunk(zf, f)
        zf.close()



def cli_create(options, rest):

    output = sys.stdout
    if options.manifest:
        output = open(options.manifest, "wt")

    mf = Manifest()
    
    fileset = rest[1]
    for name,chunks in entry_generator(fileset):
        md5,sha1 = digests(chunks())

        sec = mf.append_section()
        sec["Name"] = name
        sec["SHA1-Digest"] = sha1
        sec["MD5-Digest"] = md5

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
