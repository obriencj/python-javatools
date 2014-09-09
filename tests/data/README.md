# python-javatools test data

This directory contains sample Java class files for the
python-javatools unit tests to run against.


## Rebuilding

Both the source files and the binaries are included in git. You may
opt to rebuild the sources, but be warned that doing so may change the
validity of some of the tests. For example, the ordering of the
constants pool may vary depending on the version of the javac used to
compile the binaries, and this will most certainly result in some of
the tests failing.

Suitably warned, to rebuild the samples simply run:

```make clean all```


## Sample 1

- Source: Sample1.java
- Binary: Sample1.class

This sample tests the simplest set of features. fields, methods,
constant pool, method code, line number tables.


## Sample 2

- Sources: Sample2I.java, Sample2A.java, Sample2.java
- Binaries: Sample2I.class, Sample2A.class, Sample2.class

This sample tests interfaces and abstract classes, and bridge
methods. It also tests large-sized constants (double and float)


## Sample 3

- Source: Sample3.java
- Binary: Sample3.class

Synchronized method, synchronized static method. Methods that throw,
methods with try/catch.


## Sample 4

TODO -- annotations


## Manifest Samples

- Files: manifest-sample1.jar, manifest.SHA-512.mf, manifest.SHA1.mf,
  manifest.ignores.mf

Tests the reading and writing of the manifest file format, and
checksum features.


## JAR Signing Samples

- Files:  manifest-sample2.jar


## Example Certificate

- Files: javatools.pem, javatools-cert.pem, keystore.jks

Sample openssl key and certificate, and java key store with cert
imported. The signing key is unencrypted, so no passphrase
required. The keystore passphrase is "javatools" but that's only
needed when adding keys to it.
