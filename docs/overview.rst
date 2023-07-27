Overview of python-javatools
============================

A `python <http://python.org>`__ module for unpacking and inspecting
`Java <http://www.oracle.com/technetwork/java/index.html>`__ Class
files, JARs, and collections of either. Supporting features up to JDK 8.

It can do deep checking of classes to perform comparisons of
functionality, and output reports in multiple formats.

-  `python-javatools on
   GitHub <https://github.com/obriencj/python-javatools/>`__
-  `python-javatools on PyPI <http://pypi.python.org/pypi/javatools>`__

If you have suggestions, please use the `issue
tracker <https://github.com/obriencj/python-javatools/issues>`__ on
github. Or heck, just fork it!

Requirements
------------

-  `Python <http://python.org>`__ 2.7, 3.7, 3.8, 3.9, 3.10, 3.11
-  `Setuptools <https://pypi.org/project/setuptools/>`__
-  `Six <https://pypi.org/project/six/>`__
-  `Cheetah3 <http://www.cheetahtemplate.org>`__ is used in the
   generation of HTML reports
-  `M2Crypto <https://gitlab.com/m2crypto/m2crypto/>`__ (optional) is
   used for cryptographic operations

In addition, the following tools are used in building and testing the
project.

-  `Tox <https://pypi.org/project/tox>`__
-  `GNU Make <http://www.gnu.org/software/make/>`__
-  `Flake8 <https://pypi.org/project/flake8/>`__

All of these packages are available in most linux distributions (eg.
Fedora), and for OSX via `MacPorts <http://www.macports.org>`__ and
`HomeBrew <https://brew.sh/>`__, or available directly from pip.

M2Crypto can be difficult on some platforms, and so is set as an
optional dependency. If an execution path attempts to perform an action
which requires M2Crypto (primarily Jar signing and Jar signature
verification), then a ``CryptoDisabled`` exception will be raised, or a
message will be printed to stdout explaining that the feature is
unavailable. See the `M2Crypto Install
Guide <https://gitlab.com/m2crypto/m2crypto/-/blob/master/INSTALL.rst>`__
for workarounds in your environment.

Building
--------

This module uses `setuptools <https://pypi.org/project/setuptools/>`__,
so running the following will build the project:

``python setup.py build``

to install, run:

``python -m pip install . --user``

Testing
~~~~~~~

Tests are written as ``unittest`` test cases. If you’d like to run the
tests, simply invoke:

``python setup.py test``

or invoke tests across a wider range of platforms via ``tox``

RPM
~~~

If you’d prefer to build an RPM, see the wiki entry for `Building as an
RPM <https://github.com/obriencj/python-javatools/wiki/Building-as-an-RPM>`__.

Javatools Scripts
-----------------

-  classinfo - similar to the javap utility included with most JVMs.
   Also does provides/requires tracking.

-  classdiff - attempts to find differences between two Java class files

-  jarinfo - prints information about a JAR. Also does provides/requires
   tracking.

-  jardiff - prints the deltas between the contents of a JAR, and runs
   classdiff on differing Java class files contained in the JARs

-  jarutil - creates and signs JARs, verifies JAR signatures

-  manifest - creates and queries JAR manifests

-  distinfo - prints information about a mixed multi-jar/class
   distribution, such as provides/requires lists.

-  distdiff - attempts to find differences between two distributions,
   deep-checking any JARs or Java class files found in either directory.

Additional References
---------------------

-  Oracle’s Java Virtual Machine Specification `Chapter 4 “The class
   File
   Format” <http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html>`__
-  `Java Archive (JAR)
   Files <http://docs.oracle.com/javase/1.5.0/docs/guide/jar/index.html>`__

Contact
-------

Author: Christopher O’Brien obriencj@gmail.com

If you’re interested in my other projects, feel free to visit `my
blog <http://obriencj.preoccupied.net/>`__.

Original Git Repository: https://github.com/obriencj/python-javatools

License
-------

This library is free software; you can redistribute it and/or modify it
under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation; either version 3 of the License, or (at
your option) any later version.

This library is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser
General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this library; if not, see http://www.gnu.org/licenses/.
