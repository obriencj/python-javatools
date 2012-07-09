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

author: Christopher O'Brien  <obriencj@gmail.com>
license: LGPL
"""



from distutils.core import setup, Command
from distutils.command.build_py import build_py as _build_py



class build_py(_build_py):

    """ Distutils build_py command with some special handling for
    Cheetah tmpl files. Takes tmpl from package source directories and
    compiles them for distribution. This allows me to write tmpl files
    in the src dir of my project, and have them get compiled to
    py/pyc/pyo files during the build process. """

    # Note: it's important to override build_py rather than to add a
    # sub-command to build. The build command doesn't collate the
    # get_outputs of its sub-commands, and install specifically looks
    # for build_py and build_ext for the list of files to install.

    def initialize_options(self):
        _build_py.initialize_options(self)


    def find_package_templates(self, package, package_dir):
        # template files will be located under src, and will end in .tmpl

        from os.path import basename, join, splitext
        from glob import glob

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

        """ Compile the cheetah template in src into a python file in
        build """

        from Cheetah.Compiler import Compiler
        from os import makedirs
        from os.path import exists, join
        from distutils.util import newer

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
        from os.path import join

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
        # Overridden to append our compiled templates

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



class pylint_cmd(Command):

    """ Distutils command to run pylint on the built output and emit
    its results into build/pylint """


    user_options = [("lint-config=", None, "pylint configuration to load")]


    def initialize_options(self):
        self.lint_config = None
        self.build_base = None
        self.build_lib = None
        self.build_scripts = None


    def finalize_options(self):
        from os.path import join

        self.set_undefined_options('build',
                                   ('build_base', 'build_base'),
                                   ('build_lib', 'build_lib'),
                                   ('build_scripts', 'build_scripts'))

        self.packages = self.distribution.packages
        self.report = join(self.build_base, "pylint")

        if not self.lint_config:
            self.lint_config = "extras/pylintrc"


    def has_pylint(self):
        try:
            from pylint import lint
        except ImportError:
            return False
        else:
            return True


    def announce_overview(self, linter, report_fn):
        from itertools import izip
        import sys

        stats = linter.stats

        m_types = ('error', 'warning', 'refactor', 'convention')
        m_counts = (stats.get(mt, 0) for mt in m_types)
        msg = ", ".join("%s: %i" % p for p in izip(m_types, m_counts))
        self.announce(" "+msg, 2)

        try:
            note = eval(linter.config.evaluation, {}, stats)
        except Exception:
            pass
        else:
            self.announce(" overall score: %.1f%%" % (note * 10), 2)

        self.announce(" full details at %s" % report_fn, 2)

        errs = stats.get('error', 0)
        if errs:
            self.warn("There were %i errors, terminating" % errs)
            sys.exit(1)


    def run_linter(self):
        from pylint.lint import PyLinter
        from pylint import checkers
        from os.path import join

        linter = PyLinter(pylintrc=self.lint_config)

        # same, but not all pylint versions have load_default_plugins
        #linter.load_default_plugins()
        checkers.initialize(linter)

        linter.read_config_file()
        linter.load_config_file()

        if self.packages:
            self.announce("checking packages", 2)
            report_fn = "packages_report." + linter.reporter.extension
            report_fn = join(self.build_base, report_fn)
            with open(report_fn, "wt") as out:
                linter.reporter.set_output(out)
                linter.check(self.packages)

            self.announce_overview(linter, report_fn)

        if self.build_scripts:
            self.announce("checking scripts", 2)
            report_fn = "scripts_report." + linter.reporter.extension
            report_fn = join(self.build_base, report_fn)
            with open(report_fn, "wt") as out:
                linter.reporter.set_output(out)
                linter.check(self.build_scripts)

            self.announce_overview(linter, report_fn)


    def run(self):
        import sys

        if not self.has_pylint():
            self.warn("pylint not present")
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



setup(name = "javatools",
      version = "1.3",

      packages = ["javatools",
                  "javatools.cheetah"],

      package_dir = {"javatools": "src",
                     "javatools.cheetah": "src/cheetah"},

      package_data = {"javatools.cheetah": ["data/*.css",
                                            "data/*.js",
                                            "data/*.png"]},

      scripts = ["src/scripts/classdiff",
                 "src/scripts/classinfo",
                 "src/scripts/distdiff",
                 "src/scripts/distinfo",
                 "src/scripts/jardiff",
                 "src/scripts/jarinfo",
                 "src/scripts/manifest"],

      # PyPI information
      author = "Christopher O'Brien",
      author_email = "obriencj@gmail.com",
      url = "https://github.com/obriencj/python-javatools",
      license = "GNU Lesser General Public License",

      description = "Tools for finding meaningful deltas in Java"
      " class files and JARs",

      provides = ["javatools"],
      requires = ["Cheetah", "PyXML"],
      platforms = ["python2 >= 2.6"],

      classifiers = ["Development Status :: 5 - Production/Stable",
                     "Environment :: Console",
                     "Intended Audience :: Developers",
                     "Intended Audience :: Information Technology",
                     "Natural Language :: English",
                     "Programming Language :: Python :: 2",
                     "Topic :: Software Development :: Disassemblers"],

      # dirty stuff
      cmdclass = {'build_py': build_py,
                  'pylint': pylint_cmd})



#
# The end.
