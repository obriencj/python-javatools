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
Module for reading and writing files, related to JAR manifest.

References
----------
* http://docs.oracle.com/javase/1.5.0/docs/guide/jar/index.html
* http://java.sun.com/j2se/1.5.0/docs/guide/jar/jar.html#JAR%20Manifest

:author: Christopher O'Brien  <obriencj@gmail.com>
:license: LGPL
"""

import hashlib
import os
import sys

from base64 import b64encode
from collections import OrderedDict
from cStringIO import StringIO
from os.path import isdir, join, sep, split, walk
from zipfile import ZipFile

from .change import GenericChange, SuperChange
from .change import Addition, Removal
from .dirutils import fnmatches, makedirsp


__all__ = (
    "ManifestChange", "ManifestSectionChange",
    "ManifestSectionAdded", "ManifestSectionRemoved",
    "Manifest", "ManifestSection",
    "SignatureFile",
    "parse_sections", "digest_chunks",
    "main", "cli",
    "cli_create", "cli_query", "cli_sign",
)


_BUFFERING = 2 ** 14

# Note 1: Java supports also MD2, but hashlib does not
# Note 2: Oracle specifies "SHA-1" algorithm name in their documentation
# http://docs.oracle.com/javase/7/docs/technotes/guides/security/StandardNames.html#MessageDigest,
# which is referred by the manifest file specification
# http://docs.oracle.com/javase/7/docs/technotes/guides/jar/jar.html#Manifest-Overview.
# But jarsigner produces 'SHA1'.
JAVA_TO_HASHLIB_DIGESTS = {
    "MD5": "md5",
    "SHA1": "sha1",
    "SHA-256": "sha256",
    "SHA-384": "sha384",
    "SHA-512": "sha512"
}


class ManifestKeyException(Exception):
    """
    Indicates there was an issue with the key used in a manifest
    section
    """
    pass


class MalformedManifest(Exception):
    """
    Indicates there was a problem in parsing a manifest
    """
    pass


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
        if getattr(options, "ignore_manifest_subsections", False):
            return True

        ikeys = set(getattr(options, "ignore_manifest_key", set()))
        if ikeys:
            lset = set(self.ldata.items())
            rset = set(self.rdata.items())
            changed = set(k for k,v in lset.symmetric_difference(rset))
            return changed.issubset(ikeys)

        else:
            return False


class ManifestSectionAdded(ManifestSectionChange, Addition):

    label = "Manifest Subsection Added"

    def get_description(self):
        return "%s: %s" % (self.label, self.rdata.primary())


    def is_ignored(self, options):
        return getattr(options, "ignore_manifest_subsections", False)


class ManifestSectionRemoved(ManifestSectionChange, Removal):

    label = "Manifest Subsection Removed"

    def get_description(self):
        return "%s: %s" % (self.label, self.ldata.primary())


    def is_ignored(self, options):
        return getattr(options, "ignore_manifest_subsections", False)


class ManifestMainChange(GenericChange):

    label = "Manifest Main Section"


    def get_description(self):
        if self.is_change():
            return "%s has changed" % self.label
        else:
            return "%s is unchanged" % self.label


    def is_ignored(self, options):
        ikeys = set(getattr(options, "ignore_manifest_key", set()))
        if ikeys:
            lset = set(self.ldata.items())
            rset = set(self.rdata.items())
            changed = set(k for k,v in lset.symmetric_difference(rset))
            return changed.issubset(ikeys)

        else:
            return False


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
        return getattr(options, "ignore_manifest", False) or \
            SuperChange.is_ignored(self, options)


class ManifestSection(OrderedDict):

    primary_key = "Name"


    def __init__(self, name=None, linesep='\n'):
        OrderedDict.__init__(self)
        self[self.primary_key] = name
        self.linesep = linesep


    def __setitem__(self, k, v):
        #pylint: disable=W0221
        # we want the behavior of OrderedDict, but don't take the
        # additional parameter

        # our keys should always be strings, as should our values. We
        # also have an upper limit on the length we can permit for
        # keys, per the JAR MANIFEST specification.
        k = str(k)
        if len(k) > 68:
            raise ManifestKeyException("key too long", k)
        else:
            OrderedDict.__setitem__(self, k, str(v))


    def primary(self):
        return self.get(self.primary_key)


    def load(self, items):
        for k,vals in items:
            self[k] = "".join(vals)


    def store(self, stream):
        # when written to a stream, the primary key must be the first
        # written

        for k, v in self.items():
            self.store_item(k, v, stream)

        stream.write(self.linesep)


    def store_item(self, key, val, stream):
        """
        The MANIFEST specification limits the width of individual lines to
        72 bytes (including the terminating newlines). Any key and
        value pair that would be longer must be split up over multiple
        continuing lines
        """

        key = key or ""
        val = val or ""

        if not (0 < len(key) < 69):
            raise ManifestKeyException("key too long", key)

        if len(key) + len(val) > 68:
            kvbuffer = StringIO(": ".join((key, val)))

            # first grab 70 (which is 72 after the trailing newline)
            stream.write(kvbuffer.read(70))

            # now only 69 at a time, because we need a leading space and a
            # trailing \n
            part = kvbuffer.read(69)
            while part:
                stream.write(self.linesep + " ")
                stream.write(part)
                part = kvbuffer.read(69)
            kvbuffer.close()

        else:
            stream.write(key)
            stream.write(": ")
            stream.write(val)

        stream.write(self.linesep)


    def get_data(self):
        """ Result of 'store' method """
        stream = StringIO()
        self.store(stream)
        return stream.getvalue()


class Manifest(ManifestSection):
    """
    Represents a Java Manifest as an ordered dictionary containing
    the key:value pairs from the main section of the manifest, and
    zero or more sub-dictionaries of key:value pairs representing the
    sections following the main section. The sections are referenced
    by the value of their 'Name' pair, which must be unique to the
    Manifest as a whole.
    """

    primary_key = "Manifest-Version"


    def __init__(self, version="1.0", linesep="\n"):
        # can't use super, because we're a child of a non-object
        ManifestSection.__init__(self, version, linesep)
        self.sub_sections = OrderedDict([])


    def create_section(self, name, overwrite=True):
        """
        create and return a new sub-section of this manifest, with the
        given Name attribute. If a sub-section already exists with
        that name, it will be lost unless overwrite is False in which
        case the existing sub-section will be returned.
        """

        if overwrite:
            sect = ManifestSection(name, linesep=self.linesep)
            self.sub_sections[name] = sect

        else:
            sect = self.sub_sections.get(name, None)
            if sect is None:
                sect = ManifestSection(name, linesep=self.linesep)
                self.sub_sections[name] = sect

        return sect


    def parse_file(self, filename):
        """
        Parse and attempt to detect the line separator
        """

        with open(filename, "U", _BUFFERING) as stream:
            self.parse(stream)


    def parse(self, data):
        """
        populate instance with values and sub-sections from data in a
        stream or a string
        """

        # the parse_sections function would automatically wrap this
        # for us, but we want to be able to check the newlines
        # attribute of the stream in order to set our linesep
        # attribute
        if isinstance(data, (str, buffer)):
            data = StringIO(data)

        sections = parse_sections(data)
        self.load(sections.next())

        self.linesep = data.newlines

        for section in sections:
            next_section = ManifestSection(None, linesep=self.linesep)
            next_section.load(section)
            self.sub_sections[next_section.primary()] = next_section


    def store(self, stream):
        """
        write Manifest to a stream
        """

        ManifestSection.store(self, stream)
        for sect in sorted(self.sub_sections.values()):
            sect.store(stream)


    def get_main_section(self):
        stream = StringIO()
        ManifestSection.store(self, stream)
        return stream.getvalue()


    def get_data(self):
        stream = StringIO()
        self.store(stream)
        return stream.getvalue()


    def clear(self):
        """
        removes all items from this manifest, and clears and removes all
        sub-sections
        """

        for sub in self.sub_sections.values():
            sub.clear()
        self.sub_sections.clear()

        ManifestSection.clear(self)


    def __del__(self):
        self.clear()


class SignatureFile(Manifest):
    """
    Represents a KEY.SF signature file.
    Structure is similar to that of Manifest.
    """

    primary_key = "Signature-Version"

    def __init__(self, algorithm, version="1.0"):
        Manifest.__init__(self, version)
        self.algorithm = getattr(hashlib, JAVA_TO_HASHLIB_DIGESTS[algorithm])
        self.main_attributes_key = algorithm + \
            "-Digest-Manifest-Main-Attributes"
        self.all_attributes_key = algorithm + "-Digest-Manifest"
        self.sub_section_key = algorithm + "-Digest"


    def load(self, manifest):
        self.linesep = manifest.linesep
        h_all = self.algorithm()
        h_all.update(manifest.get_main_section())
        self[self.main_attributes_key] = b64encode(h_all.digest())

        for sub_section in manifest.sub_sections.values():
            h_all.update(sub_section.get_data())
        self[self.all_attributes_key] = b64encode(h_all.digest())

        for sub_section in manifest.sub_sections.values():
            h_section = self.algorithm()
            h_section.update(sub_section.get_data())
            sf_section = self.create_section(sub_section.primary())
            sf_section[self.sub_section_key] = b64encode(h_section.digest())


    def get_signature(self, certificate, private_key):
        """
        There seems to be no Python crypto library, which would produce a
        JAR-compatible signature. So this is a wrapper around external
        command.  OpenSSL is known to work.

        Any other command which reads data on stdin and returns
        JAR-compatible "signature file block" on stdout can be used.
        Note: Oracle does not specify the content of the "signature
        file block", friendly saying that "These are binary files not
        intended to be interpreted by humans":

        http://docs.oracle.com/javase/7/docs/technotes/guides/jar/jar.html#Digital_Signatures

        Parameters
        ----------
        certificate : `str` filename
          certificate to embed into the signature (PEM format)
        private_key : `str` filename
          RSA private key used to sign (PEM format)

        Returns
        -------
        signature : `str`
          content of the signature block file as though produced by
          jarsigner.
        """

        from subprocess import Popen, PIPE, CalledProcessError

        # TODO: handle also DSA and ECDSA keys
        external_cmd = "openssl cms -sign -binary -noattr -md SHA256" \
                       " -signer %s -inkey %s -outform der" \
                       % (certificate, private_key)

        proc = Popen(external_cmd.split(),
                     stdin=PIPE, stdout=PIPE, stderr=PIPE)

        (proc_stdout, proc_stderr) = proc.communicate(input=self.get_data())

        if proc.returncode != 0:
            print proc_stderr
            raise CalledProcessError(proc.returncode, external_cmd, sys.stderr)
        else:
            return proc_stdout


def parse_sections(data):
    """
    yields one section at a time in the form

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

    for lineno,line in enumerate(data):

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
                raise MalformedManifest("bad line continuation, "
                                        " line: %i" % lineno)
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


def digest_chunks(chunks, algorithms=("md5", "sha1")):
    """
    returns a base64 rep of the requested digests from the chunks of
    data
    """

    hashes = []
    for algorithm in algorithms:
        hashes.append(getattr(hashlib, algorithm)())

    for chunk in chunks:
        for h in hashes:
            h.update(chunk)

    return [b64encode(h.digest()) for h in hashes]


def file_chunk(filename, size=_BUFFERING):
    """
    returns a generator function which when called will emit x-sized
    chunks of filename's contents
    """

    def chunks():
        with open(filename, "rb", _BUFFERING) as fd:
            buf = fd.read(size)
            while buf:
                yield buf
                buf = fd.read(size)
    return chunks


def zipentry_chunk(zipfile, name, size=_BUFFERING):
    """
    returns a generator function which when called will emit x-sized
    chunks of the named entry in the zipfile object
    """

    def chunks():
        with zipfile.open(name) as fd:
            buf = fd.read(size)
            while buf:
                yield buf
                buf = fd.read(size)
    return chunks


def directory_generator(dirname, trim=0):
    """
    yields a tuple of (relative filename, chunking function). The
    chunking function can be called to open and iterate over the
    contents of the filename.
    """

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
    """
    yields (name,chunkgen) for all of the files found under the list
    of pathnames given. This is recursive, so directories will have
    their contents emitted. chunkgen is a function that can called and
    iterated over to obtain the contents of the file in multiple
    reads.
    """

    for pathname in pathnames:
        if isdir(pathname):
            for entry in directory_generator(pathname):
                yield entry
        else:
            yield pathname, file_chunk(pathname)


def single_path_generator(pathname):
    """
    emits name,chunkgen pairs for the given file at pathname. If
    pathname is a directory, will act recursively and will emit for
    each file in the directory tree chunkgen is a generator that can
    be iterated over to obtain the contents of the file in multiple
    parts
    """

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
    """
    command-line call to create a manifest from a JAR file or a
    directory
    """

    if len(rest) != 2:
        print "Usage: manifest --create [-r|--recursive]" \
              " [-i|--ignore pattern] [-d|--digest algo[,algo ...]]" \
              " [-m manifest] file|directory"
        return 1

    requested_digests = options.digest.split(",")
    use_digests = []

    for digest in requested_digests:
        if digest in JAVA_TO_HASHLIB_DIGESTS:
            use_digests.append(JAVA_TO_HASHLIB_DIGESTS[digest])
        else:
            print "Unknown digest algorithm", digest
            print "Supported algorithms:", ",".join(
                sorted(JAVA_TO_HASHLIB_DIGESTS.keys()))
            return 1

    if options.recursive:
        entries = multi_path_generator(rest[1:])
    else:
        entries = single_path_generator(rest[1])

    mf = Manifest(linesep=os.linesep)

    ignores = options.ignore

    for name,chunks in entries:
        # skip the stuff that we were told to ignore
        if ignores and fnmatches(name, *ignores):
            continue

        sec = mf.create_section(name)

        for digest, digest_value in zip(
                requested_digests, digest_chunks(chunks(), use_digests)):
            sec[digest + "-Digest"] = digest_value

    output = sys.stdout
    if options.manifest:
        # we'll output to the manifest file if specified, and we'll
        # even create parent directories for it, if necessary
        makedirsp(split(options.manifest)[0])
        output = open(options.manifest, "w")

    mf.store(output)

    if options.manifest:
        output.close()


def cli_query(options, rest):
    if(len(rest) != 2):
        print "Usage: manifest --query=key file.jar"
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


def cli_sign(options, rest):
    """
    Signs the jar (almost) identically to jarsigner.
    """
    if len(rest) != 5:
        print "Usage: \
            manifest --sign certificate private_key key_alias file.jar"
        return 1

    certificate = rest[1]
    private_key = rest[2]
    key_alias = rest[3]
    jar_file = ZipFile(rest[4], "a")
    if not "META-INF/MANIFEST.MF" in jar_file.namelist():
        print "META-INF/MANIFEST.MF not found in the JAR"
        return 1

    mf = Manifest()
    mf.parse(jar_file.read("META-INF/MANIFEST.MF"))
    sf = SignatureFile("SHA-256")
    sf.load(mf)
    jar_file.writestr("META-INF/" + key_alias + ".SF", sf.get_data())
    jar_file.writestr("META-INF/" + key_alias + ".RSA",
                      sf.get_signature(certificate, private_key))

    return 0


def cli(options, rest):
    if options.verify:
        return cli_verify(options, rest)

    elif options.create:
        return cli_create(options, rest)

    elif options.query:
        return cli_query(options, rest)

    elif options.sign:
        return cli_sign(options, rest)

    else:
        print "specify one of --verify, --query, --sign, or --create"
        return 0


def create_optparser():
    from optparse import OptionParser

    parse = OptionParser(usage="Create, sign or verify a MANIFEST for"
                         " a JAR, ZIP, or directory")

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
    parse.add_option("-d", "--digest", action="store", default="MD5,SHA1",
                     help="comma-separated list of digest algorithms to use"
                     " in the manifest")
    parse.add_option("-s", "--sign", action="store_true",
                     help="sign the JAR file with OpenSSL"
                     " (must be followed with: "
                     "certificate.pem, private_key.pem, key_alias)")
    return parse


def main(args):
    """
    main entry point for the manifest CLI
    """

    parser = create_optparser()
    return cli(*parser.parse_args(args))


#
# The end.
