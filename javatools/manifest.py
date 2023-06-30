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

import argparse
import hashlib
import os
import sys

from base64 import b64encode
from collections import OrderedDict
from os.path import isdir, join, sep, split
from os import walk
from six import BytesIO
from six.moves import zip
from zipfile import ZipFile

from .change import GenericChange, SuperChange
from .change import Addition, Removal
from .dirutils import fnmatches, makedirsp

try:
    buffer
except NameError:
    buffer = memoryview

__all__ = (
    "ManifestChange", "ManifestSectionChange",
    "ManifestSectionAdded", "ManifestSectionRemoved",
    "Manifest", "ManifestSection",
    "SignatureManifest",
    "ManifestKeyException", "MalformedManifest",
    "main", "cli_create", "cli_query", "cli_verify", )


_BUFFERING = 2 ** 14


SIG_FILE_PATTERN = "*.SF"
SIG_BLOCK_PATTERNS = ("*.RSA", "*.DSA", "*.EC", "SIG-*", )


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
JAVA_TO_OPENSSL_DIGESTS = {}
JAVA_TO_OPENSSL_DIGEST_NAMES = {}


def _add_digest(java_name, hashlib_name):
    digest = getattr(hashlib, hashlib_name, None)
    if digest:
        JAVA_TO_OPENSSL_DIGESTS[java_name] = digest
        JAVA_TO_OPENSSL_DIGEST_NAMES[java_name] = hashlib_name


def _get_digest(java_name, as_string=False):
    try:
        return JAVA_TO_OPENSSL_DIGEST_NAMES[java_name] if as_string \
            else JAVA_TO_OPENSSL_DIGESTS[java_name]
    except KeyError:
        raise UnsupportedDigest("Unsupported digest %s. Supported: %s" %
                                (java_name, ", ".join(sorted(
                                 JAVA_TO_OPENSSL_DIGESTS.keys()))))


# Note 1: Java supports also MD2, but hashlib does not
_add_digest("MD2", "md2")
_add_digest("MD5", "md5")

# Note 2: Oracle specifies "SHA-1" algorithm name in their
# documentation, but it's called "SHA1" elsewhere and that is what
# jarsigner uses as well.
# http://docs.oracle.com/javase/8/docs/technotes/guides/security/StandardNames.html#MessageDigest
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
            lset = set(self.ldata.items())
            rset = set(self.rdata.items())
            changed = set(k for k, _v in lset.symmetric_difference(rset))
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
            changed = set(k for k, _v in lset.symmetric_difference(rset))
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


    def __gt__(self, other_section):
        # we need just some ordering, no matter which.
        return self.get_data() > other_section.get_data()

    def __setitem__(self, k, v):
        # pylint: disable=W0221
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
        Serialize this section and write it to a binary stream
        """

        if hasattr(stream, 'buffer'):
            stream = stream.buffer

        for k, v in self.items():
            write_key_val(stream, k, v, linesep)

        stream.write(linesep.encode('utf-8'))


    def get_data(self, linesep=os.linesep):
        """
        Serialize the section and return it as bytes
        :return bytes
        """

        stream = BytesIO()
        self.store(stream, linesep)
        return stream.getvalue()


    def keys_with_suffix(self, suffix):
        """
        :return: list of keys ending with given :suffix:.
        """
        return [k.rstrip(suffix) for k in self.keys() if k.endswith(suffix)]


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
        Load self from the file, such as "MANIFEST.MF" or "SIGNATURE.SF".
        :param filename: contains UTF-8 encoded manifest
        """

        with open(filename, "rb", _BUFFERING) as stream:
            self.parse(stream.read())


    def load_from_jar(self, jarfile):
        # Can't be imported at top level:
        from javatools.jarutil import MissingManifestError
        with ZipFile(jarfile) as jar:
            if "META-INF/MANIFEST.MF" not in jar.namelist():
                raise MissingManifestError(
                    "META-INF/MANIFEST.MF not found in %s" % jarfile)
            data = jar.read("META-INF/MANIFEST.MF")
            self.parse(data)


    def parse(self, data):
        """
        populate instance with values and sub-sections
        :param data: UTF-8 encoded manifest
        :type data: bytes
        """

        # we want at least some data, thus we ignore unknown characters
        data = data.decode('utf-8', errors="ignore")
        self.linesep = detect_linesep(data)

        # the first section is the main one for the manifest. It's
        # also where we will check for our newline separator
        sections = parse_sections(data)
        self.load(next(sections))

        # and all following sections are considered sub-sections
        for section in sections:
            next_section = ManifestSection(None)
            next_section.load(section)
            self.sub_sections[next_section.primary()] = next_section


    def store(self, stream, linesep=None):
        """
        Serialize the Manifest to a binary stream
        """

        # either specified here, specified on the instance, or the OS
        # default
        linesep = linesep or self.linesep or os.linesep

        ManifestSection.store(self, stream, linesep)
        for sect in sorted(self.sub_sections.values()):
            sect.store(stream, linesep)


    def get_main_section(self, linesep=None):
        """
        Serialize just the main section of the manifest and return it as bytes
        :return bytes
        """

        linesep = linesep or self.linesep or os.linesep

        stream = BytesIO()
        ManifestSection.store(self, stream, linesep)
        return stream.getvalue()


    def get_data(self, linesep=None):
        """
        Serialize the entire manifest and return it as bytes
        :return bytes
        """

        linesep = linesep or self.linesep or os.linesep

        stream = BytesIO()
        self.store(stream, linesep)
        return stream.getvalue()


    def verify_jar_checksums(self, jar_file, strict=True):
        """
        Verify checksums, present in the manifest, against the JAR content.
        :return: list of entries for which verification has failed
        """

        verify_failures = []

        zip_file = ZipFile(jar_file)
        for filename in zip_file.namelist():
            if file_skips_verification(filename):
                continue

            file_section = self.create_section(filename, overwrite=False)

            digests = file_section.keys_with_suffix("-Digest")
            if not digests and strict:
                verify_failures.append(filename)
                continue

            for java_digest in digests:
                read_digest = file_section.get(java_digest + "-Digest")
                calculated_digest = b64_encoded_digest(
                    zip_file.read(filename),
                    _get_digest(java_digest))

                if calculated_digest == read_digest:
                    # found a match
                    break
            else:
                # for all the digests, not one of them matched. Add
                # this filename to the error list
                verify_failures.append(filename)

        return verify_failures


    def add_jar_entries(self, jar_file, digest_name="SHA-256"):
        """
        Add manifest sections for all but signature-related entries
        of :param jar_file.
        :param digest_name The digest algorithm to use
        :return None
        TODO: join code with cli_create
        """

        key_digest = digest_name + "-Digest"
        digest = _get_digest(digest_name)

        with ZipFile(jar_file, 'r') as jar:
            for entry in jar.namelist():
                if file_skips_verification(entry):
                    continue
                section = self.create_section(entry)
                section[key_digest] = b64_encoded_digest(jar.read(entry),
                                                         digest)


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

        digest = _get_digest(java_algorithm)
        accum = manifest.get_main_section()
        self[main_key] = b64_encoded_digest(accum, digest)

        for sub_section in manifest.sub_sections.values():
            sub_data = sub_section.get_data(linesep)
            sf_sect = self.create_section(sub_section.primary())
            sf_sect[sect_key] = b64_encoded_digest(sub_data, digest)
            accum += sub_data

        self[all_key] = b64_encoded_digest(accum, digest)


    def verify_manifest_main_checksum(self, manifest):
        """
        Verify the checksum over the manifest main section.

        :return: True if the signature over main section verifies
        """

        # NOTE: JAR spec does not state whether there can be >1 digest used,
        # and should the validator require any or all digests to match.
        # We allow mismatching digests and require just one to be correct.
        # We see no security risk: it is the signer of the .SF file
        # who shall check, what is being signed.
        for java_digest in self.keys_with_suffix("-Digest-Manifest"):
            whole_mf_digest = b64_encoded_digest(
                manifest.get_data(),
                _get_digest(java_digest))

            # It is enough for at least one digest to be correct
            if whole_mf_digest == self.get(java_digest + "-Digest-Manifest"):
                return True

        return False


    def verify_manifest_main_attributes_checksum(self, manifest):
        # JAR spec allows for the checksum of the whole manifest to mismatch.
        # There is a second chance for the verification to succeed:
        # checksum for the main section matches,
        # plus checksum for every subsection matches.

        keys = self.keys_with_suffix("-Digest-Manifest-Main-Attributes")
        for java_digest in keys:
            mf_main_attr_digest = b64_encoded_digest(
                manifest.get_main_section(),
                _get_digest(java_digest))

            attr = java_digest + "-Digest-Manifest-Main-Attributes"
            if mf_main_attr_digest == self.get(attr):
                return True
        else:
            return False


    def verify_manifest_entry_checksums(self, manifest, strict=True):
        """
        Verifies the checksums over the given manifest. If strict is True
        then entries which had no digests will fail verification. If
        strict is False then entries with no digests will not be
        considered failing.

        :return: List of entries which failed to verify.

        Reference:
        http://docs.oracle.com/javase/7/docs/technotes/guides/jar/jar.html#Signature_Validation
        """

        # TODO: this behavior is probably wrong -- surely if there are
        # multiple digests, they should ALL match, or verification would
        # fail?

        failures = []

        for s in manifest.sub_sections.values():
            sf_section = self.create_section(s.primary(), overwrite=False)

            digests = s.keys_with_suffix("-Digest")
            if not digests and strict:
                failures.append(s.primary())
                continue

            for java_digest in digests:
                section_digest = b64_encoded_digest(
                    s.get_data(manifest.linesep),
                    _get_digest(java_digest))

                if section_digest == sf_section.get(java_digest + "-Digest"):
                    # found a match, verified
                    break
            else:
                # no matches found for the digests present
                failures.append(s.primary())

        return failures


    def verify_manifest(self, manifest):
        if self.verify_manifest_main_checksum(manifest):
            return []
        # Main checksum does not validate, but there is a second chance.
        if not self.verify_manifest_main_attributes_checksum(manifest):
            # Let's return the manifest itself - such return value can be
            # interpreted only in exactly this way
            return ["META-INF/MANIFEST.MF"]

        return self.verify_manifest_entry_checksums(manifest)


    def get_signature(self, certificate, private_key, extra_certs,
                      digest_algorithm="SHA-256"):

        from .crypto import create_signature_block

        openssl_digest = _get_digest(digest_algorithm, as_string=True)
        return create_signature_block(openssl_digest, certificate, private_key,
                                      extra_certs, self.get_data())


class SignatureManifestChange(ManifestChange):
    label = "Signature File"

    def is_ignored(self, options):
        return getattr(options, "ignore_jar_signature", False) or \
            SuperChange.is_ignored(self, options)


class SignatureBlockFileChange(GenericChange):
    label = "Signature Block File"

    def get_description(self):
        return "[binary data change]"

    def fn_pretty(self, side_data):
        return "[binary data]"


def _b64encode_to_str(data):
    """
    Wrapper around b64encode which takes and returns same-named types
    on both Python 2 and Python 3.
    :type data: bytes
    :return: str
    """
    ret = b64encode(data)
    if not isinstance(ret, str):  # Python3
        return ret.decode('ascii')
    else:
        return ret


def b64_encoded_digest(data, algorithm):
    """
    :type data: bytes
    :return: str
    """
    h = algorithm()
    h.update(data)
    return _b64encode_to_str(h.digest())


def detect_linesep(data):
    """
    :type data: unicode in Py2, str in Py3
    """
    return "\r\n" if "\r\n" in data else "\n"


def parse_sections(data):
    """
    yields one section at a time in the form

    [ (key, [val, ...]), ... ]

    where key is a string and val is a string representing a single
    line of any value associated with the key. Multiple vals may be
    present if the value is long enough to require line continuations
    in which case simply concatenate the vals together to get the full
    value.
    :type data: unicode in Py2, str in Py3
    """

    if not data:
        return

    # our current section
    curr = None

    for lineno, line in enumerate(data.splitlines()):
        # Clean up the line
        cleanline = line.replace('\x00', '')

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
                # pylint: disable=unsubscriptable-object
                curr[-1][1].append(cleanline[1:])

        else:
            # otherwise the beginning of a new k:v pair
            if curr is None:
                curr = list()

            try:
                key, val = cleanline.split(':', 1)
                curr.append((key, [val[1:]]))
            except ValueError:
                raise MalformedManifest(
                    "Invalid manifest line: %i; line contents: %s"
                    % (lineno, cleanline))


    # yield and leftovers
    if curr:
        yield curr


def write_key_val(stream, key, val, linesep=os.linesep):
    """
    The MANIFEST specification limits the width of individual lines to
    72 bytes (including the terminating newlines). Any key and value
    pair that would be longer must be split up over multiple
    continuing lines
    :type key, val: str in Py3, str or unicode in Py2
    :type stream: binary
    """

    if hasattr(stream, 'buffer'):
        stream = stream.buffer

    key = key.encode('utf-8') or ""
    val = val.encode('utf-8') or ""
    linesep = linesep.encode('utf-8')

    if not (0 < len(key) < 69):
        raise ManifestKeyException("bad key length", key)

    if len(key) + len(val) > 68:
        kvbuffer = BytesIO(b": ".join((key, val)))

        # first grab 70 (which is 72 after the trailing newline)
        stream.write(kvbuffer.read(70))

        # now only 69 at a time, because we need a leading space and a
        # trailing \n
        part = kvbuffer.read(69)
        while part:
            stream.write(linesep + b" ")
            stream.write(part)
            part = kvbuffer.read(69)
        kvbuffer.close()

    else:
        stream.write(key)
        stream.write(b": ")
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

    return [_b64encode_to_str(h.digest()) for h in hashes]


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

    for dirpath, dirnames, filenames in walk(dirname):
        for fname in filenames:
            yield join(dirpath, fname[trim:]), file_chunk(join(dirpath, fname))


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


def _in_sig_related_dir(filename):
    path_components = filename.split("/")
    return len(path_components) == 2 and path_components[0] == "META-INF"


def file_matches_sigfile(filename):
    return _in_sig_related_dir(filename) \
        and fnmatches(filename.upper(), SIG_FILE_PATTERN)


def file_matches_sigblock(filename):
    return _in_sig_related_dir(filename) \
        and fnmatches(filename[len("META-INF/"):].upper(), *SIG_BLOCK_PATTERNS)


def file_skips_verification(filename):
    # http://docs.oracle.com/javase/8/docs/technotes/guides/jar/jar.html#SignedJar-Overview

    filename = filename.upper()
    return filename == "META-INF/MANIFEST.MF" \
        or filename.endswith("/") \
        or file_matches_sigblock(filename) \
        or file_matches_sigfile(filename)


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


def cli_create(argument_list):
    """
    command-line call to create a manifest from a JAR file or a
    directory
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("content", help="file or directory")
    # TODO: shouldn't we always process directories recursively?
    parser.add_argument("-r", "--recursive", action='store_true',
                        help="process directories recursively")
    parser.add_argument("-i", "--ignore", nargs="+", action="append",
                        help="patterns to ignore "
                             "(can be given more than once)")
    parser.add_argument("-m", "--manifest", default=None,
                        help="output file (default is stdout)")
    parser.add_argument("-d", "--digest",
                        help="digest(s) to use, comma-separated")

    args = parser.parse_args(argument_list)

    # TODO: remove digest from here, they are created when signing!
    if args.digest is None:
        args.digest = "MD5,SHA1"
    requested_digests = args.digest.split(",")
    use_digests = [_get_digest(digest) for digest in requested_digests]

    if args.recursive:
        entries = multi_path_generator(args.content)
    else:
        entries = single_path_generator(args.content)

    mf = Manifest()

    ignores = ["META-INF/*"]
    if args.ignore:
        ignores.extend(*args.ignore)

    for name, chunks in entries:
        # skip the stuff that we were told to ignore
        if ignores and fnmatches(name, *ignores):
            continue

        sec = mf.create_section(name)

        digests = zip(requested_digests, digest_chunks(chunks(), use_digests))
        for digest_name, digest_value in digests:
            sec[digest_name + "-Digest"] = digest_value

    if args.manifest:
        # we'll output to the manifest file if specified, and we'll
        # even create parent directories for it, if necessary
        makedirsp(split(args.manifest)[0])
        output = open(args.manifest, "wb")
    else:
        output = sys.stdout

    mf.store(output)

    if args.manifest:
        output.close()


def cli_verify(args):
    if len(args) != 1 or "-h" in args:
        print("Usage: manifest v [--ignore=PATH] file.jar")
        return 2

    jarfn = args[0]
    mf = Manifest()
    mf.load_from_jar(jarfn)

    errors = mf.verify_jar_checksums(jarfn)
    if len(errors) > 0:
        print("Verify failed, no matching checksums for files: %s"
              % ", ".join(errors))
        return 1

    else:
        return 0


def cli_query(args):
    if len(args) < 2 or "-h" in args:
        print("Usage: manifest q file.jar key_to_query...")
        return 1

    mf = Manifest()
    mf.load_from_jar(args[0])

    for q in args[1:]:
        s = q.split(':', 1)
        if len(s) > 1:
            mfs = mf.sub_sections.get(s[0])
            if mfs:
                print(q, "=", mfs.get(s[1]))
            else:
                print(q, ": No such section")

        else:
            print(q, "=", mf.get(s[0]))


def usage(error_msg=None):
    if error_msg is not None:
        print(error_msg)
    print("Usage: manifest <command> [options] <argument>")
    print("Commands:")
    print("    c: create a manifest")
    print("    q: query manifest for values")
    print("    v: verify manifest checksums")
    print("Give option \"-h\" for help on a particular command.")
    return 1


def main(args=sys.argv):
    """
    main entry point for the manifest CLI
    """

    if len(args) < 2:
        return usage("Command expected")

    command = args[1]
    rest = args[2:]

    if "create".startswith(command):
        return cli_create(rest)
    elif "query".startswith(command):
        return cli_query(rest)
    elif "verify".startswith(command):
        return cli_verify(rest)
    else:
        return usage("Unknown command: %s" % command)
#
# The end.
