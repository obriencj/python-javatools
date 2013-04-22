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
Module for reading and writing MANIFEST.MF files.

http://docs.oracle.com/javase/1.5.0/docs/guide/jar/index.html
http://java.sun.com/j2se/1.5.0/docs/guide/jar/jar.html#JAR%20Manifest

author: Christopher O'Brien  <obriencj@gmail.com>
license: LGPL
"""



from os.path import isdir, join, sep, split, walk
from cStringIO import StringIO

from .change import GenericChange, SuperChange
from .change import Addition, Removal
from .dirutils import fnmatches, makedirsp


_BUFFERING = 2 ** 14



class ManifestSectionChange(GenericChange):
    label = "Manifest Subsection"


    def get_description(self):
        m = self.ldata or self.rdata
        entry = m.primary()
        if self.is_change():
            return "%s Changed: %s" % (self.label, entry)
        else:
            return "%s Unchanged: %s" % (self.label, entry)


    def is_ignored(self, options):
        return getattr(options, "ignore_manifest_subsections", False)



class ManifestSectionAdded(ManifestSectionChange, Addition):
    label = "Manifest Subsection Added"

    def get_description(self):
        return "%s: %s" % (self.label, self.rdata.primary())



class ManifestSectionRemoved(ManifestSectionChange, Removal):
    label = "Manifest Subsection Removed"

    def get_description(self):
        return "%s: %s" % (self.label, self.ldata.primary())



class ManifestMainChange(GenericChange):
    label = "Manifest Main Section"

    def get_description(self):
        if self.is_change():
            return "%s has changed" % self.label
        else:
            return "%s is unchanged" % self.label



class ManifestChange(SuperChange):
    label = "Manifest"

    def collect_impl(self):
        lm, rm = self.ldata, self.rdata
        yield ManifestMainChange(lm, rm)

        l_sections = set(lm.sub_sections.keys())
        r_sections = set(rm.sub_sections.keys())

        for s in l_sections.intersection(r_sections):
            yield ManifestSectionChange(lm.sub_sections[s], rm.sub_sections[s])

        for s in l_sections.difference(r_sections):
            yield ManifestSectionRemoved(lm.sub_sections[s], None)

        for s in r_sections.difference(l_sections):
            yield ManifestSectionAdded(None, rm.sub_sections[s])


    def is_ignored(self, options):
        return getattr(options, "ignore_manifest", False)



class ManifestSection(dict):

    primary_key = "Name"


    def __init__(self, name=None):
        dict.__init__(self)
        self[self.primary_key] = name


    def __setitem__(self, k, v):
        # our keys should always be strings, as should our values

        k = str(k)
        if len(k) > 68:
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

    """ Represents a Java Manifest. In essence a dictionary
    representing the key:value pairs from the main section of the
    manifest, and zero or more sub-dictionaries of key:value pairs
    representing the sections following the main section. The sections
    are referenced by the value of their 'Name' pair, which must be
    unique to the Manifest as a whole. """


    primary_key = "Manifest-Version"


    def __init__(self, version="1.0"):
        ManifestSection.__init__(self, version)
        self.sub_sections = {}


    def create_section(self, name, overwrite=True):

        """ create and return a new sub-section of this manifest, with
        the given Name attribute. If a sub-section already exists with
        that name, it will be lost unless overwrite is False in which
        case the existing sub-section will be returned. """

        if overwrite:
            sect = ManifestSection(name)
            self.sub_sections[name] = sect

        else:
            sect = self.sub_sections.get(name, None)
            if sect is None:
                sect = ManifestSection(name)
                self.sub_sections[name] = sect

        return sect



    def parse_file(self, filename):
        with open(filename, "rt", _BUFFERING) as stream:
            self.parse(stream)


    def parse(self, data):

        """ populate instance with values and sub-sections from data
        in a stream or a string"""

        sections = parse_sections(data)
        self.load(sections.next())

        for section in sections:
            ms = ManifestSection(None)
            ms.load(section)
            self.sub_sections[ms.primary()] = ms


    def store(self, stream):

        """ write Manifest to a stream """

        ManifestSection.store(self, stream)
        for _name, sect in sorted(self.sub_sections.items()):
            sect.store(stream)


    def clear(self):

        """ removes all items from this manifest, and clears and
        removes all sub-sections """

        for sub in self.sub_sections.values():
            sub.clear()
        self.sub_sections.clear()

        ManifestSection.clear(self)


    def __del__(self):
        self.clear()



def store_item(key, val, stream):

    """ The MANIFEST specification limits the width of individual
    lines to 72 bytes (including the terminating newlines). Any key
    and value pair that would be longer must be split up over multiple
    continuing lines"""

    key = key or ""
    val = val or ""

    if not (0 < len(key) < 69):
        raise Exception("Invalid key length: %i" % len(key))

    if len(key) + len(val) > 68:
        kvbuffer = StringIO(": ".join((key, val)))

        # first grab 70 (which is 72 after the trailing newline)
        stream.write(kvbuffer.read(70))

        # now only 69 at a time, because we need a leading space and a
        # trailing \n
        part = kvbuffer.read(69)
        while part:
            stream.write("\n ")
            stream.write(part)
            part = kvbuffer.read(69)
        kvbuffer.close()

    else:
        stream.write(key)
        stream.write(": ")
        stream.write(val)

    stream.write("\n")



def parse_sections(data):

    """ yields one section at a time in the form

    [ (key, [val, ...]), ... ]

    where key is a string and val is a string representing a single
    line of any value associated with the key. Multiple vals may be
    present if the value is long enough to require line continuations
    in which case simply concatenate the vals together to get the full
    value.
    """

    if not data:
        return

    if isinstance(data, (str, buffer)):
        data = StringIO(data)

    # our current section
    curr = None

    for line in data:

        # Clean up the line
        cleanline = line.replace('\x00', '').splitlines()[0]

        if not cleanline:
            # blank line means end of current section (if any)
            if curr:
                yield curr
                curr = None

        elif cleanline[0] == ' ':
            # line beginning with a space means a continuation
            if curr is None:
                raise Exception("malformed Manifest, bad continuation")
            else:
                curr[-1][1].append(cleanline[1:])

        else:
            # otherwise the beginning of a new k:v pair
            if curr is None:
                curr = list()

            key, val = cleanline.split(':', 1)
            curr.append((key, [val[1:]]))

    # yield and leftovers
    if curr:
        yield curr



def digest_chunks(chunks):

    """ returns a base64 rep of the MD5 and SHA1 digests from the
    chunks of data """

    #pylint: disable=E0611, E1101
    from hashlib import md5, sha1

    from base64 import b64encode

    hashes = (md5(), sha1())

    for chunk in chunks:
        for h in hashes:
            h.update(chunk)

    return [b64encode(h.digest()) for h in hashes]



def file_chunk(filename, size=_BUFFERING):

    """ returns a generator function which when called will emit
    x-sized chunks of filename's contents"""

    def chunks():
        with open(filename, "rb", _BUFFERING) as fd:
            buf = fd.read(size)
            while buf:
                yield buf
                buf = fd.read(size)
    return chunks



def zipentry_chunk(zipfile, name, size=_BUFFERING):

    """ returns a generator function which when called will emit
    x-sized chunks of the named entry in the zipfile object"""

    def chunks():
        with zipfile.open(name) as fd:
            buf = fd.read(size)
            while buf:
                yield buf
                buf = fd.read(size)
    return chunks



def directory_generator(dirname, trim=0):

    """ yields a tuple of (relative filename, chunking function). The
    chunking function can be called to open and iterate over the
    contents of the filename. """

    def gather(collect, dirname, fnames):
        for fname in fnames:
            df = join(dirname, fname)
            if not isdir(df):
                collect.append(df)

    collect = list()
    walk(dirname, gather, collect)
    for fname in collect:
        yield fname[trim:], file_chunk(fname)



def multi_path_generator(pathnames):

    """ yields (name,chunkgen) for all of the files found under the
    list of pathnames given. This is recursive, so directories will
    have their contents emitted. chunkgen is a function that can
    called and iterated over to obtain the contents of the file in
    multiple reads. """

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
            if f[-1] != '/':
                yield f, zipentry_chunk(zf, f)
        zf.close()



def cli_create(options, rest):
    import sys

    if options.recursive:
        entries = multi_path_generator(rest[1:])
    else:
        entries = single_path_generator(rest[1])

    mf = Manifest()

    ignores = options.ignore

    for name,chunks in entries:

        # skip the stuff that we were told to ignore
        if ignores and fnmatches(name, *ignores):
            continue

        sec = mf.create_section(name)

        md5,sha1 = digest_chunks(chunks())
        sec["SHA1-Digest"] = sha1
        sec["MD5-Digest"] = md5

    output = sys.stdout

    if options.manifest:
        # we'll output to the manifest file if specified, and we'll
        # even create parent directories for it, if necessary

        makedirsp(split(options.manifest)[0])
        output = open(options.manifest, "wt")

    mf.store(output)

    if options.manifest:
        output.close()



def cli_query(options, rest):
    from zipfile import ZipFile

    if(len(rest) != 2):
        print "Please specify a single JAR to query"
        return 1

    zf = ZipFile(rest[1])
    mf = Manifest()
    mf.parse(zf.read("META-INF/MANIFEST.MF"))

    for q in options.query:
        s = q.split(':', 1)
        if(len(s) > 1):
            mfs = mf.sub_sections.get(s[0])
            if mfs:
                print q, "=", mfs.get(s[1])
            else:
                print q, ": No such section"

        else:
            print q, "=", mf.get(s[0])



def cli_verify(options, rest):
    # TODO: read in the manifest, and then verify the digests for every
    # file listed.

    print "NYI"
    return 0



def cli(options, rest):
    if options.verify:
        return cli_verify(options, rest)

    elif options.create:
        return cli_create(options, rest)

    elif options.query:
        return cli_query(options, rest)

    else:
        print "specify one of --verify, --query, or --create"
        return 0



def create_optparser():
    from optparse import OptionParser

    parse = OptionParser(usage="Create or verify a MANIFEST for a JAR/ZIP"
                         " or directory")

    parse.add_option("-v", "--verify", action="store_true")
    parse.add_option("-c", "--create", action="store_true")
    parse.add_option("-q", "--query", action="append",
                     default=[],
                     help="Query the manifest for keys")
    parse.add_option("-r", "--recursive", action="store_true")
    parse.add_option("-m", "--manifest", action="store", default=None,
                     help="manifest file, default is stdout for create"
                     " or the argument-relative META-INF/MANIFEST.MF"
                     " for verify.")
    parse.add_option("-i", "--ignore", action="append",
                     default=["META-INF/*"],
                     help="patterns to ignore when creating or checking"
                     " files")

    return parse



def main(args):

    """ main entry point for the manifest CLI """

    parser = create_optparser()
    return cli(*parser.parse_args(args))



#
# The end.
