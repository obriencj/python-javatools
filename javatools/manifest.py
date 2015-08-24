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
from itertools import izip
from os.path import isdir, join, sep, split, walk
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
    "cli_create", "cli_query", "cli_sign",
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

        for k,vals in items:
            self[k] = "".join(vals)


    def store(self, stream, linesep=os.linesep):
        """
        Serialize this section and write it to a stream
        """

        for k, v in self.items():
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
        self.load(sections.next())

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
                return "No valid checksum of JAR member %s found" % filename

        return None


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

        # determine a digest class to use based on the java-style
        # algorithm name
        digest = _get_digest(java_algorithm)

        # calculate the checksum for the main manifest section. We'll
        # be re-using this digest to also calculate the total
        # checksum.
        h_all = digest()
        h_all.update(manifest.get_main_section())
        self[main_key] = b64encode(h_all.digest())

        for sub_section in manifest.sub_sections.values():
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

        for s in manifest.sub_sections.values():
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
        """
        Produces a signature block for the contents of this signature
        manifest. Executes the `openssl` binary in order to calculate
        this. TODO: replace this with a pyopenssl call

        References
        ----------
        http://docs.oracle.com/javase/7/docs/technotes/guides/jar/jar.html#Digital_Signatures

        Parameters
        ----------
        certificate : `str` filename
          certificate to embed into the signature (PEM format)
        private_key : `str` filename
          private key used to sign (PEM format)
        digest_algorithm : `str`
          Java-style algorithm name (must be supported by OpenSSL too)

        Returns
        -------
        signature : `str`
          content of the signature block file as though produced by
          jarsigner.

        Raises
        ------
        cpe : `CalledProcessError`
          if there was a non-zero return code from running the
          underlying openssl exec
        """

        # There seems to be no Python crypto library, which would
        # produce a JAR-compatible signature. So this is a wrapper
        # around external command.  OpenSSL is known to work.

        # Any other command which reads data on stdin and returns
        # JAR-compatible "signature file block" on stdout can be used.
        # Note: Oracle does not specify the content of the "signature
        # file block", friendly saying that "These are binary files
        # not intended to be interpreted by humans"

        from subprocess import Popen, PIPE, CalledProcessError

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

        external_cmd = "openssl cms -sign -binary -noattr -md %s" \
                       " -signer %s -inkey %s -outform der" \
                       % (openssl_digest, certificate, private_key)

        proc = Popen(external_cmd.split(),
                     stdin=PIPE, stdout=PIPE, stderr=PIPE)

        (proc_stdout, proc_stderr) = proc.communicate(input=self.get_data())

        if proc.returncode != 0:
            print proc_stderr
            raise CalledProcessError(proc.returncode, external_cmd, sys.stderr)
        else:
            return proc_stdout


def b64_encoded_digest(data, algorithm):
    h = algorithm()
    h.update(data)
    return b64encode(h.digest())

def detect_linesep(data):
    if isinstance(data, (str, buffer)):
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

    if isinstance(data, (str, buffer)):
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


def verify_signature_block(certificate_file, content_file, signature):
    """
    A wrapper over 'OpenSSL cms -verify'.
    Verifies the 'signature_stream' over the 'content' with the 'certificate'.
    :return: Error message, or None if the signature validates.
    """

    from subprocess import Popen, PIPE, STDOUT

    external_cmd = "openssl cms -verify -CAfile %s -content %s " \
                   "-inform der" % (certificate_file, content_file)

    proc = Popen(external_cmd.split(),
                 stdin=PIPE, stdout=PIPE, stderr=STDOUT)

    proc_output = proc.communicate(input=signature)[0]

    if proc.returncode != 0:
        return "Command \"%s\" returned %s: %s" \
               % (external_cmd, proc.returncode, proc_output)

    return None


def private_key_type(private_key_file):
    import subprocess
    import re

    algorithms = ("RSA", "DSA", "EC")
    # Grepping for a string will work for PKCS8 keys, but not for PKCS1.
    with open(private_key_file, "r") as f:
        # We can't just take the first line. PKCS8 may have other headers.
        for line in f:
            for algorithm in algorithms:
                if re.match("-----BEGIN %s PRIVATE KEY-----" % algorithm,
                            line):
                    return algorithm

    # No luck.
    # Anything less ugly and more efficient, but working with all key types??
    # PyOpenssl has Pkey.type()...
    with open(os.devnull, "wb") as DEVNULL:
        for algorithm in algorithms:
            if not subprocess.call(
                    ["openssl", algorithm.lower(), "-in", private_key_file],
                    stdout=DEVNULL, stderr=subprocess.STDOUT):
                return algorithm
    return None


def verify(certificate, jar_file, key_alias):
    """
    Verifies signature of a JAR file.

    Limitations:
    - diagnostic is less verbose than of jarsigner
    :return: tuple (exit_status, result_message)

    Reference:
    http://docs.oracle.com/javase/7/docs/technotes/guides/jar/jar.html#Signature_Validation
    Note that the validation is done in three steps. Failure at any step is a failure
    of the whole validation.
    """

    from tempfile import mkstemp

    zip_file = ZipFile(jar_file)
    sf_data = zip_file.read("META-INF/%s.SF" % key_alias)

    # Step 1: check the crypto part.
    sf_file = mkstemp()[1]
    with open(sf_file, "w") as tmp_buf:
        tmp_buf.write(sf_data)
        tmp_buf.flush()
        file_list = zip_file.namelist()
        sig_block_filename = None
        # JAR specification lists only RSA and DSA; jarsigner also has EC
        signature_extensions = ("RSA", "DSA", "EC")
        for extension in signature_extensions:
            candidate_filename = "META-INF/%s.%s" % (key_alias, extension)
            if candidate_filename in file_list:
                sig_block_filename = candidate_filename
                break
        if sig_block_filename is None:
            return "None of %s found in JAR" % \
                   ", ".join(key_alias + "." + x for x in signature_extensions)

        sig_block_data = zip_file.read(sig_block_filename)
        error = verify_signature_block(certificate, sf_file, sig_block_data)
        os.unlink(sf_file)
        if error is not None:
            return error

    # KEYALIAS.SF is correctly signed.
    # Step 2: Check that it contains correct checksum of the manifest.
    signature_manifest = SignatureManifest()
    signature_manifest.parse(sf_data)

    jar_manifest = Manifest()
    jar_manifest.parse(zip_file.read("META-INF/MANIFEST.MF"))

    error = signature_manifest.verify_manifest_checksums(jar_manifest)
    if error is not None:
        return error

    # Checksums of MANIFEST.MF itself are correct.
    # Step 3: Check that it contains valid checksums for each file from the JAR.
    error = jar_manifest.verify_jar_checksums(jar_file)
    if error is not None:
        return error

    return None


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

    if options.digest is None:
        options.digest = "MD5,SHA1"
    requested_digests = options.digest.split(",")
    try:
        use_digests = [_get_digest(digest) for digest in requested_digests]
    except UnsupportedDigest:
        print "Unknown digest algorithm %r" % digest
        print "Supported algorithms:", ",".join(sorted(NAMED_DIGESTS.keys()))
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
            izip(requested_digests, digest_chunks(chunks(), use_digests)):
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
    """
    Command-line wrapper around verify()
    """

    if len(rest) != 4:
        print "Usage: manifest --verify certificate.pem file.jar key_alias"
        return 1

    certificate = rest[1]
    jar_file = rest[2]
    key_alias = rest[3]
    result_message = verify(certificate, jar_file, key_alias)
    if result_message is not None:
        print result_message
        return 1
    print "Jar verified."
    return 0


def cli_sign(options, rest):
    """
    Signs the jar (almost) identically to jarsigner.
    """

    # TODO: move this into jarutil, since it actually modifies a JAR
    # file. We can leave the majority of the signing implementation in
    # this module, but anything that modifies a JAR should wind up in
    # jarutil.

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

    sig_block_extension = private_key_type(private_key)
    if sig_block_extension is None:
        print "Cannot determine private key type (is it in PEM format?)"
        return 1

    mf = Manifest()
    mf.parse(jar_file.read("META-INF/MANIFEST.MF"))

    # create a signature manifest, and make it match the line separator
    # style of the manifest it'll be digesting.
    sf = SignatureManifest(linesep=mf.linesep)

    sf_digest_algorithm = options.digest or "SHA-256"
    sf.digest_manifest(mf, sf_digest_algorithm)
    jar_file.writestr("META-INF/%s.SF" % key_alias, sf.get_data())

    sig_digest_algorithm = sf_digest_algorithm  # No point to make it different
    jar_file.writestr("META-INF/%s.%s" % (key_alias, sig_block_extension),
        sf.get_signature(certificate, private_key, sig_digest_algorithm))

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
    parse.add_option("-d", "--digest", action="store",
                     help="with '-c/--create': comma-separated list of digest"
                     " algorithms to use in the manifest;\n"
                     "with '-s/--sign': digest algorithm to use"
                     " in the signature")
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
