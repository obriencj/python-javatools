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
pylint setuptools/distutils command

author: Christopher O'Brien  <obriencj@gmail.com>
license: LGPL v.3
"""


from itertools import izip
from os.path import join
from distutils.core import Command

import sys

try:
    from pylint.lint import PyLinter
    from pylint import checkers
except ImportError:
    FOUND_PYLINT = False
else:
    FOUND_PYLINT = True


DEFAULT_LINTCONFIG = "extras/pylintrc"


class pylint_cmd(Command):
    """
    Setuptools (or Distutils) command to run pylint on the built
    output and emit its results into build/pylint
    """

    user_options = [
        ("lint-config=", None, "pylint configuration to load"),
    ]


    def initialize_options(self):
        self.lint_config = None
        self.build_base = None
        self.build_lib = None
        self.build_scripts = None


    def finalize_options(self):
        self.set_undefined_options('build',
                                   ('build_base', 'build_base'),
                                   ('build_lib', 'build_lib'),
                                   ('build_scripts', 'build_scripts'))

        self.packages = self.distribution.packages
        self.report = join(self.build_base, "pylint")

        if not self.lint_config:
            self.lint_config = DEFAULT_LINTCONFIG


    def announce_overview(self, linter, report_fn):
        stats = linter.stats

        m_types = ('error', 'warning', 'refactor', 'convention')
        m_counts = (stats.get(mt, 0) for mt in m_types)
        msg = ", ".join("%s: %i" % p for p in izip(m_types, m_counts))
        self.announce(" "+msg, 2)

        note = eval(linter.config.evaluation, {}, stats)
        self.announce(" overall score: %.1f%%" % (note * 10), 2)
        self.announce(" full details at %s" % report_fn, 2)

        errs = stats.get('error', 0)
        if errs:
            self.warn("pylint identified %i error(s), terminating" % errs)
            sys.exit(1)


    def run_linter(self):
        linter = PyLinter(pylintrc=self.lint_config)

        # load_default_plugins will call checkers.initialize if
        # implemented, but some older versions of pylint don't have
        # this method so we fall back to calling is manually.
        if hasattr(linter, 'load_default_plugins'):
            linter.load_default_plugins()
        else:
            checkers.initialize(linter)

        linter.read_config_file()
        linter.load_config_file()

        # don't emit messages about suppressed or useless suppressed
        # configs, it's just annoying and doesn't help.
        #linter.disable('suppressed-message')
        #linter.disable('useless-suppression')

        if self.packages:
            self.announce("pylint is checking packages", 2)
            report_fn = "packages_report." + linter.reporter.extension
            report_fn = join(self.build_base, report_fn)
            with open(report_fn, "wt") as out:
                linter.reporter.set_output(out)
                linter.check(self.packages)

            self.announce_overview(linter, report_fn)

        if self.build_scripts:
            self.announce("pylint is checking scripts", 2)
            report_fn = "scripts_report." + linter.reporter.extension
            report_fn = join(self.build_base, report_fn)
            with open(report_fn, "wt") as out:
                linter.reporter.set_output(out)
                linter.check(self.build_scripts)

            self.announce_overview(linter, report_fn)


    def run(self):
        if not FOUND_PYLINT:
            self.warn("pylint module not found, skipping")
            return

        # since we process the build output, we need to ensure build
        # is run first
        self.run_command("build")

        # we'll be running our linter on the contents of the build_lib
        sys.path.insert(0, self.build_lib)
        try:
            self.run_linter()
        finally:
            sys.path.pop(0)


#
# The end.
