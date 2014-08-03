#! /usr/bin/env python2

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
Python Javatools

author: Christopher O'Brien  <obriencj@gmail.com>
license: LGPL v.3
"""


from distutils.util import newer
from glob import glob
from itertools import izip
from os import makedirs
from os.path import basename, exists, join, splitext
from setuptools import setup, Command
from setuptools.command.build_py import build_py as _build_py
from pylint_cmd import pylint_cmd

import sys


class build_py(_build_py):
    """
    setuptools build_py command with some special handling for Cheetah
    template files. Takes tmpl from package source directories and
    compiles them for distribution. This allows me to write tmpl files
    in the src dir of my project, and have them get compiled to
    py/pyc/pyo files during the build process.
    """

    # Note: it's important to override build_py rather than to add a
    # sub-command to build. The build command doesn't collate the
    # get_outputs of its sub-commands, and install specifically looks
    # for build_py and build_ext for the list of files to install.

    # Update: now that I've switched from distutils to setuptools, it
    # may be possible to put this into a subcommand instead. Have to
    # investigate.

    def find_package_templates(self, package, package_dir):
        # template files will be located under src, and will end in .tmpl

        self.check_package(package, package_dir)
        template_files = glob(join(package_dir, "*.tmpl"))
        templates = []

        for f in template_files:
            template = splitext(basename(f))[0]
            templates.append((package, template, f))
        return templates


    def build_package_templates(self):
        for package in self.packages:
            package_dir = self.get_package_dir(package)
            templates = self.find_package_templates(package, package_dir)

            for package_, template, template_file in templates:
                assert package == package_
                self.check_cheetah()
                self.build_template(template, template_file, package)


    def build_template(self, template, template_file, package):
        """
        Compile the cheetah template in src into a python file in build
        """

        from Cheetah.Compiler import Compiler

        comp = Compiler(file=template_file, moduleName=template)

        # load configuration if it exists
        conf_fn = "extras/cheetah.cfg"
        if exists(conf_fn):
            with open(conf_fn, "rt") as config:
                comp.updateSettingsFromConfigFileObj(config)

        # and just why can't I configure these?
        comp.setShBang("")
        comp.addModuleHeader("pylint: disable=C,W,R,F")

        outfd = join(self.build_lib, *package.split("."))
        outfn = join(outfd, template+".py")

        if not exists(outfd):
            makedirs(outfd)

        if newer(template_file, outfn):
            self.announce("compiling %s -> %s" % (template_file, outfd), 2)
            with open(outfn, "w") as output:
                output.write(str(comp))


    def get_template_outputs(self, include_bytecode=1):
        built = list()

        for package in self.packages:
            package_dir = self.get_package_dir(package)
            templates = self.find_package_templates(package, package_dir)
            for _, template, _ in templates:
                outfd = join(self.build_lib, *package.split("."))
                outfn = join(outfd, template+".py")

                built.append(outfn)

                if include_bytecode:
                    if self.compile:
                        built.append(outfn + "c")
                    if self.optimize > 0:
                        built.append(outfn + "o")

        return built


    def get_outputs(self, include_bytecode=1):
        # Overridden to append our compiled templates in addition to
        # the normal build outputs.

        outputs = _build_py.get_outputs(self, include_bytecode)
        outputs.extend(self.get_template_outputs(include_bytecode))

        return outputs


    def check_cheetah(self):
        try:
            import Cheetah.Compiler
        except ImportError:
            raise SystemExit("Cheetah.Compiler not present, cannot continue")
        else:
            return True


    def run(self):
        if self.packages:
            self.build_package_templates()

        _build_py.run(self)


setup(name = "javatools",
      version = "1.4.0",

      packages = [ "javatools",
                   "javatools.cheetah" ],

      package_data = { "javatools.cheetah": [ "data/*.css",
                                              "data/*.js",
                                              "data/*.png" ] },

      scripts = [ "scripts/classdiff",
                  "scripts/classinfo",
                  "scripts/distdiff",
                  "scripts/distinfo",
                  "scripts/jardiff",
                  "scripts/jarinfo",
                  "scripts/manifest" ],

      test_suite = "tests",

      # PyPI information
      author = "Christopher O'Brien",
      author_email = "obriencj@gmail.com",
      url = "https://github.com/obriencj/python-javatools",
      license = "GNU Lesser General Public License",

      description = "Tools for finding meaningful deltas in Java"
      " class files and JARs",

      provides = [ "javatools" ],
      requires = [ "Cheetah" ],
      platforms = [ "python2 >= 2.6" ],

      classifiers = [ "Development Status :: 5 - Production/Stable",
                      "Environment :: Console",
                      "Intended Audience :: Developers",
                      "Intended Audience :: Information Technology",
                      "Programming Language :: Python :: 2",
                      "Topic :: Software Development :: Disassemblers" ],

      # dirty stuff
      cmdclass = { 'build_py': build_py,
                   'pylint': pylint_cmd } )


#
# The end.
