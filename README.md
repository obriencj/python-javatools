
# Overview of python-javatools

A python module for unpacking and inspecting Java Class files, JARs,
and collections of either.

It can do deep checking of classes to perform comparisons of
functionality, and output reports in multiple formats.

* [python-javatools on GitHub](https://github.com/obriencj/python-javatools/)
* [javatools on PyPI](http://pypi.python.org/pypi/javatools)

If you have suggestions, please use the [issue tracker on
github](https://github.com/obriencj/python-javatools/issues). Or heck,
just fork it!


## Switching to Setuptools

Please see [issue #3][issue] and leave a comment with your thoughts on
switching from distutils to setuptools. You can preview the change in
the setuptools branch.

[issue]: https://github.com/obriencj/python-javatools/issues/4


## Requirements

* [Python](http://python.org) 2.6 or later (no support for Python 3)
* [Cheetah](http://www.cheetahtemplate.org/)
* [PyXML](http://www.python.org/community/sigs/current/xml-sig/)

All of these packages are available from
[PyPI](http://pypi.python.org), most major Linux distributions, and
via [MacPorts](http://www.macports.org).


## Optional

* [pylint](http://pypi.python.org/pypi/pylint/) - If installed you may
  invoke `python setup.py pylint` to get an overview report and a
  detailed summary written to the build dir.


## Install

This module uses distutils, so simply run `python setup.py install`

If you'd prefer to build an RPM, see the wiki entry for [Building as an RPM](https://github.com/obriencj/python-javatools/wiki/Building-as-an-RPM)


## Scripts Installed

* classinfo - similar to the javap utility included with most
  JVMs. Also does provides/requires tracking.

* classdiff - attempts to find differences between two Java class
  files

* jarinfo - prints information about a JAR. Also does
  provides/requires tracking.

* jardiff - prints the deltas between the contents of a JAR, and runs
  classdiff on differing Java class files contained in the JARs

* manifest - creates and verifies class checksum manifests (needs work)

* distinfo - prints information about a mixed multi-jar/class
  distribution, such as provides/requires lists.

* distdiff - attempts to find differences between two distributions,
  deep-checking any JARs or Java class files found in either
  directory.


## References

* Oracle's Java Virtual Machine Specification [Chapter 4 "The class File Format"](http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html)

* [Java Archive (JAR) Files](http://docs.oracle.com/javase/1.5.0/docs/guide/jar/index.html)


## Contact

Christopher O'Brien <obriencj@gmail.com>


## License

This library is free software; you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as
published by the Free Software Foundation; either version 3 of the
License, or (at your option) any later version.

This library is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, see
<http://www.gnu.org/licenses/>.
