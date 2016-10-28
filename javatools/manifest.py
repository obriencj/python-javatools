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

from __future__ import print_function

from builtins import zip
from future.utils import viewitems, listitems, listvalues

import hashlib
import os
import sys

from base64 import b64encode
from collections import OrderedDict
from io import StringIO
from os.path import isdir, join, sep, split
from os import walk
from zipfile import ZipFile

from .change import GenericChange, SuperChange
from .change import Addition, Removal
from .dirutils import fnmatches, makedirsp

__all__ = (
    "ManifestChange", "ManifestSectionChange",
    "ManifestSectionAdded", "ManifestSectionRemoved",
    "Manifest", "ManifestSection",
    "SignatureManifest",
    "ManifestKeyException", "MalformedManifest",
    "main", "cli",
    "cli_create", "cli_query", "cli_verify",
)


_BUFFERING = 2 ** 14



class UnsupportedDigest(Exception):
    """
    Indicates an algorithm was requested for which we had no matching
    digest support
    """
    pass


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


# Digests classes by Java name that have been found present in hashlib
NAMED_DIGESTS = {}

def _add_digest(java_name, hashlib_name):
    digest = getattr(hashlib, hashlib_name, None)
    if digest:
        NAMED_DIGESTS[java_name] = digest

def _get_digest(java_name):
    try:
        return NAMED_DIGESTS[java_name]
    except KeyError:
        raise UnsupportedDigest(java_name)

# Note 1: Java supports also MD2, but hashlib does not
_add_digest("MD2", "md2")
_add_digest("MD5", "md5")

# Note 2: Oracle specifies "SHA-1" algorithm name in their
# documentation, but it's called "SHA1" elsewhere and that is what
# jarsigner uses as well.
_add_digest("SHA1", "sha1")
_add_digest("SHA-256", "sha256")
_add_digest("SHA-384", "sha384")
_add_digest("SHA-512", "sha512")


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
            lset = viewitems(self.ldata)
            rset = viewitems(self.rdata)
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
            lset = viewitems(self.ldata)
            rset = viewitems(self.rdata)
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


    def __init__(self, name=None):
        OrderedDict.__init__(self)
        self[self.primary_key] = name


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
        """
        The primary value for this section
        """

        return self.get(self.primary_key)


    def load(self, items):
        """
        Populate this section from an iteration of the parse_items call
        """

        for k, vals in items:
            self[k] = "".join(vals)


    def store(self, stream, linesep=os.linesep):
        """
        Serialize this section and write it to a stream
        """

        for k, v in listitems(self):
            write_key_val(stream, k, v, linesep)

        stream.write(linesep)


    def get_data(self, linesep=os.linesep):
        """
        Serialize the section and return it as a string
        """

        stream = StringIO()
        self.store(stream, linesep)
        return stream.getvalue()


    def keys_with_suffix(self, suffix):
        """
        :return: list of keys ending with given :suffix:.
        """
        return [k.rstrip(suffix) for k in list(self) if k.endswith(suffix)]


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


    def __init__(self, version="1.0", linesep=None):
        # can't use super, because we're a child of a non-object
        ManifestSection.__init__(self, version)
        self.sub_sections = OrderedDict([])
        self.linesep = linesep


    def create_section(self, name, overwrite=True):
        """
        create and return a new sub-section of this manifest, with the
        given Name attribute. If a sub-section already exists with
        that name, it will be lost unless overwrite is False in which
        case the existing sub-section will be returned.
        """

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
        """
        Parse the given file, and attempt to detect the line separator.
        """

        with open(filename, "r", _BUFFERING) as stream:
            self.parse(stream)


    def parse(self, data):
        """
        populate instance with values and sub-sections from data in a
        stream, string, or buffer
        """

        self.linesep = detect_linesep(data)

        # the first section is the main one for the manifest. It's
        # also where we will check for our newline seperator
        sections = parse_sections(data)
        self.load(next(sections))

        # and all following sections are considered sub-sections
        for section in sections:
            next_section = ManifestSection(None)
            next_section.load(section)
            self.sub_sections[next_section.primary()] = next_section


    def store(self, stream, linesep=None):
        """
        Serialize the Manifest to a stream
        """

        # either specified here, specified on the instance, or the OS
        # default
        linesep = linesep or self.linesep or os.linesep

        ManifestSection.store(self, stream, linesep)
        for sect in sorted(self.sub_sections.values()):
            sect.store(stream, linesep)


    def get_main_section(self, linesep=None):
        """
        Serialize just the main section of the manifest and return it as a
        string
        """

        linesep = linesep or self.linesep or os.linesep

        stream = StringIO()
        ManifestSection.store(self, stream, linesep)
        return stream.getvalue()


    def get_data(self, linesep=None):
        """
        Serialize the entire manifest and return it as a string
        """

        linesep = linesep or self.linesep or os.linesep

        stream = StringIO()
        self.store(stream, linesep)
        return stream.getvalue()


    def verify_jar_checksums(self, jar_file):
        """
        Verify checksums, present in the manifest, against the JAR content.
        :return: error_message, or None if verification succeeds
        """

        error_message = ""
        zip_file = ZipFile(jar_file)
        for filename in zip_file.namelist():
            if file_is_signature_related(filename):
                continue

            file_section = self.create_section(filename, overwrite=False)
            at_least_one_digest_matches = False
            for java_digest in file_section.keys_with_suffix("-Digest"):
                read_digest = file_section.get(java_digest + "-Digest")
                calculated_digest = b64_encoded_digest(
                    zip_file.read(filename),
                    NAMED_DIGESTS[java_digest]
                )

                if calculated_digest == read_digest:
                    at_least_one_digest_matches = True
                    break

            if not at_least_one_digest_matches:
                error_message += "No valid checksum of jar member %s\n" % filename

        return None if error_message == "" else error_message


    def clear(self):
        """
        removes all items from this manifest, and clears and removes all
        sub-sections
        """

        for sub in listvalues(self.sub_sections):
            sub.clear()
        self.sub_sections.clear()

        ManifestSection.clear(self)


    def __del__(self):
        self.clear()


class SignatureManifest(Manifest):
    """
    Represents a KEY.SF signature file.  Structure is similar to that
    of Manifest. Each section represents a crypto checksum of a matching
    section from a MANIFEST.MF
    """

    primary_key = "Signature-Version"


    def digest_manifest(self, manifest, java_algorithm="SHA-256"):
        """
        Create a main section checksum and sub-section checksums based off
        of the data from an existing manifest using an algorithm given
        by Java-style name.
        """

        # pick a line separator for creating checksums of the manifest
        # contents. We want to use either the one from the given
        # manifest, or the OS default if it hasn't specified one.
        linesep = manifest.linesep or os.linesep

        all_key = java_algorithm + "-Digest-Manifest"
        main_key = java_algorithm + "-Digest-Manifest-Main-Attributes"
        sect_key = java_algorithm + "-Digest"

        # determine a digest class to use based on the java-style
        # algorithm name
        digest = _get_digest(java_algorithm)

        # calculate the checksum for the main manifest section. We'll
        # be re-using this digest to also calculate the total
        # checksum.
        h_all = digest()
        h_all.update(manifest.get_main_section())
        self[main_key] = b64encode(h_all.digest())

        for sub_section in listvalues(manifest.sub_sections):
            sub_data = sub_section.get_data(linesep)

            # create the checksum of the section body and store it as a
            # sub-section of our own
            h_section = digest()
            h_section.update(sub_data)
            sf_sect = self.create_section(sub_section.primary())
            sf_sect[sect_key] = b64encode(h_section.digest())

            # push this data into this total as well.
            h_all.update(sub_data)

        # after traversing all the sub sections, we now have the
        # digest of the whole manifest.
        self[all_key] = b64encode(h_all.digest())


    def verify_manifest_checksums(self, manifest):
        """
        Verifies the checksums over the given manifest.
        :return: error message, or None if verification succeeds
        Reference:
        http://docs.oracle.com/javase/7/docs/technotes/guides/jar/jar.html#Signature_Validation
        """

        # NOTE: JAR spec does not state whether there can be >1 digest used,
        # and should the validator require any or all digests to match.
        # We allow mismatching digests and require just one to be correct.
        # We see no security risk: it is the signer of the .SF file
        # who shall check, what is being signed.
        for java_digest in self.keys_with_suffix("-Digest-Manifest"):
            whole_mf_digest = b64_encoded_digest(
                manifest.get_data(),
                NAMED_DIGESTS[java_digest]
            )

            # It is enough for at least one digest to be correct
            if whole_mf_digest == self.get(java_digest + "-Digest-Manifest"):
                return None

        # JAR spec allows for the checksum of the whole manifest to mismatch.
        # There is a second chance for the verification to succeed:
        # checksum for the main section matches,
        # plus checksum for every subsection matches.

        at_least_one_main_attr_digest_matches = False
        for java_digest in self.keys_with_suffix(
                "-Digest-Manifest-Main-Attributes"):
            mf_main_attr_digest = b64_encoded_digest(
                manifest.get_main_section(),
                NAMED_DIGESTS[java_digest]
            )

            if mf_main_attr_digest == self.get(
                    java_digest + "-Digest-Manifest-Main-Attributes"):
                at_least_one_main_attr_digest_matches = True
                break

        if not at_least_one_main_attr_digest_matches:
            return "No matching checksum of the whole manifest and no " \
                   "matching checksum of the manifest main attributes found"

        for s in listvalues(manifest.sub_sections):
            at_least_one_section_digest_matches = False
            sf_section = self.create_section(s.primary(), overwrite=False)
            for java_digest in s.keys_with_suffix("-Digest"):
                section_digest = b64_encoded_digest(
                    s.get_data(manifest.linesep),
                    NAMED_DIGESTS[java_digest]
                )
                if section_digest == sf_section.get(java_digest + "-Digest"):
                    at_least_one_section_digest_matches = True
                    break

            if not at_least_one_section_digest_matches:
                return "No matching checksum of the whole manifest and " \
                       "no matching checksum for subsection %s found" \
                           % s.primary()
        return None


    def get_signature(self, certificate, private_key,
                      digest_algorithm="SHA-256"):

        from .crypto import create_signature_block

        JAVA_TO_OPENSSL_DIGESTS = {
            "MD5": "MD5",
            "SHA1": "SHA1",
            "SHA-256": "SHA256",
            "SHA-384": "SHA384",
            "SHA-512": "SHA512"
        }

        try:
            openssl_digest = JAVA_TO_OPENSSL_DIGESTS[digest_algorithm]
        except KeyError:
            raise Exception("Unknown Java digest %s" % digest_algorithm)

        return create_signature_block(openssl_digest, certificate, private_key,
                                      self.get_data())


class SignatureManifestChange(ManifestChange):
    label = "Signature File"

    def is_ignored(self, options):
        return getattr(options, "ignore_jar_signature", False) or \
            SuperChange.is_ignored(self, options)


class SignatureBlockFileChange(GenericChange):
    label = "Signature Block File"

    def get_description(self):
        return "[binary file change]"


def b64_encoded_digest(data, algorithm):
    h = algorithm()
    h.update(data)
    return b64encode(h.digest())

def detect_linesep(data):
    if isinstance(data, (str, memoryview)):
        data = StringIO(data)

    offset = data.tell()
    line = data.readline()
    data.seek(offset)

    if line[-2:] == "\r\n":
        return "\r\n"
    else:
        return line[-1]


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

    if isinstance(data, (str, memoryview)):
        data = StringIO(data)


    # our current section
    curr = None

    for lineno,line in enumerate(data):
        # Clean up the line
        cleanline = line.splitlines()[0].replace('\x00', '')

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


def write_key_val(stream, key, val, linesep=os.linesep):
    """
    The MANIFEST specification limits the width of individual lines to
    72 bytes (including the terminating newlines). Any key and value
    pair that would be longer must be split up over multiple
    continuing lines
    """

    key = key or ""
    val = val or ""

    if not (0 < len(key) < 69):
        raise ManifestKeyException("bad key length", key)

    if len(key) + len(val) > 68:
        kvbuffer = StringIO(": ".join((key, val)))

        # first grab 70 (which is 72 after the trailing newline)
        stream.write(kvbuffer.read(70))

        # now only 69 at a time, because we need a leading space and a
        # trailing \n
        part = kvbuffer.read(69)
        while part:
            stream.write(linesep + " ")
            stream.write(part)
            part = kvbuffer.read(69)
        kvbuffer.close()

    else:
        stream.write(key)
        stream.write(": ")
        stream.write(val)

    stream.write(linesep)


def digest_chunks(chunks, algorithms=(hashlib.md5, hashlib.sha1)):
    """
    returns a base64 rep of the given digest algorithms from the
    chunks of data
    """

    hashes = [algorithm() for algorithm in algorithms]

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


def file_is_signature_related(filename):
    # http://docs.oracle.com/javase/8/docs/technotes/guides/jar/jar.html#SignedJar-Overview
    # Specifies files, which are considered "signature-related":

    if not filename.startswith("META-INF/"):
        return False

    basename = filename[9:]
    # Files in subdirectories are not signature-related:
    if "/" in basename:
        return False

    # Case-insensitive variants are "reserved" and also not checked:
    basename = basename.upper()

    return basename == "" \
        or basename == "MANIFEST.MF" \
        or basename.startswith("SIG-") \
        or basename.endswith(".SF") \
        or basename.endswith(".RSA") \
        or basename.endswith(".DSA") \
        or basename.endswith(".EC")


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
        print("Usage: manifest --create [-r|--recursive]" \
              " [-i|--ignore pattern] [-d|--digest algo[,algo ...]]" \
              " [-m manifest] file|directory")
        return 1

    if options.digest is None:
        options.digest = "MD5,SHA1"
    requested_digests = options.digest.split(",")
    try:
        use_digests = [_get_digest(digest) for digest in requested_digests]
    except UnsupportedDigest:
        print("Unknown digest algorithm %r" % digest)
        print("Supported algorithms:", ",".join(sorted(NAMED_DIGESTS.keys())))
        return 1

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

        for digest_name, digest_value in \
            zip(requested_digests, digest_chunks(chunks(), use_digests)):
            sec[digest_name + "-Digest"] = digest_value

    output = sys.stdout
    if options.manifest:
        # we'll output to the manifest file if specified, and we'll
        # even create parent directories for it, if necessary
        makedirsp(split(options.manifest)[0])
        output = open(options.manifest, "w")

    mf.store(output)

    if options.manifest:
        output.close()


def cli_verify(options, rest):
    # TODO: handle ignores
    if len(rest) != 1:
        print("Usage: manifest --verify [--ignore=PATH] JAR_FILE")
        return 2

    jar = ZipFile(rest[0])
    mf = Manifest()
    mf.parse(jar.read("META-INF/MANIFEST.MF"))
    error = mf.verify_jar_checksums(rest[0])
    if error is None:
        return 0
    print(error)
    return 1


def cli_query(options, rest):
    if len(rest) != 2:
        print("Usage: manifest --query=key file.jar")
        return 1

    zf = ZipFile(rest[1])
    mf = Manifest()
    mf.parse(zf.read("META-INF/MANIFEST.MF"))

    for q in options.query:
        s = q.split(':', 1)
        if(len(s) > 1):
            mfs = mf.sub_sections.get(s[0])
            if mfs:
                print(q, "=", mfs.get(s[1]))
            else:
                print(q, ": No such section")

        else:
            print(q, "=", mf.get(s[0]))


def cli(options, rest):
    if options.verify:
        return cli_verify(options, rest)

    elif options.create:
        return cli_create(options, rest)

    elif options.query:
        return cli_query(options, rest)

    else:
        print("specify one of --verify, --query or --create")
        return 0


def create_optparser():
    from optparse import OptionParser

    parse = OptionParser(usage="Create, query or verify a MANIFEST for"
                         " a JAR, ZIP, or directory")

    # TODO: first should be one non-optional command;
    # each option is applicable only to certain commands
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
    parse.add_option("-d", "--digest", action="store",
                     help="comma-separated list of digest"
                     " algorithms to use when creating a manifest")

    return parse


def main(args):
    """
    main entry point for the manifest CLI
    """

    parser = create_optparser()
    return cli(*parser.parse_args(args))


#
# The end.
