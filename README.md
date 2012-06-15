
# Overview of python-javaclass

A python module for unpacking and inspecting Java Class files, JARs,
and collections of either.

It can do deep checking of classes to perform comparisons of
functionality, and output reports in multiple formats.


## Install

This module uses distutils, so simply run `python setup.py install`

If you'd prefer to build an RPM, see the wiki entry for [Building as an RPM](wiki/Building-as-an-RPM)


## Scripts Installed

* classinfo - similar to the javap utility included with most
  JVMs. Also does provides/requires tracking.

* classdiff - attempts to find differences between two Java class
  files

* jarinfo - prints information about a JAR. Also does
  provides/requires tracking.

* jardiff - prints the deltas between the contents of a JAR, and runs
  classdiff on differing Java class files contained in the JARs

* manifest - creates and verifies class checksum manifests

* distinfo - prints information about a mixed multi-jar/class
  distribution, such as provides/requires lists.

* distdiff - attempts to find differences between two distributions,
  deep-checking any JARs or Java class files found in either
  directory.


## Contact

author: Christopher O'Brien <obriencj@gmail.com>


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

