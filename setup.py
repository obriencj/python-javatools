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



from distutils.core import setup
from distutils.command.build_py import build_py as _build_py



class build_py(_build_py):

    """ Distutils build_py command with some special handling for
    Cheetah tmpl files. Takes tmpl from package source directories and
    compiles them for distribution. This allows me to write tmpl files
    in the src dir of my project, and have them get compiled to
    py/pyc/pyo files during the build process. """


    def initialize_options(self):
        _build_py.initialize_options(self)
        self.built_templates = list()


    def find_package_templates(self, package, package_dir):
        from os.path import abspath, basename, join, splitext
        from glob import glob

        self.check_package(package, package_dir)
        template_files = glob(join(package_dir, "*.tmpl"))
        templates = []
        setup_script = abspath(self.distribution.script_name)

        for f in template_files:
            abs_f = abspath(f)
            if abs_f != setup_script:
                template = splitext(basename(f))[0]
                templates.append((package, template, f))
            else:
                self.debug_print("excluding %s" % setup_script)
        return templates


    def build_package_templates(self):
        for package in self.packages:
            package_dir = self.get_package_dir(package)
            templates = self.find_package_templates(package, package_dir)

            for package_, template, template_file in templates:
                assert package == package_
                self.build_template(template, template_file, package)


    def build_template(self, template, template_file, package):
        from Cheetah.Compiler import Compiler
        from os import makedirs
        from os.path import exists, join
        from distutils.util import newer

        comp = Compiler(file=template_file, moduleName=template)
        outfd = join(self.build_lib, *package.split("."))
        outfn = join(outfd, template+".py")

        if not exists(outfd):
            makedirs(outfd)

        if newer(template_file, outfn):
            print "compiling %s -> %s" % (template_file, outfd)
            with open(outfn, "w") as output:
                output.write(str(comp))

        self.built_templates.append(outfn)


    def get_outputs(self, include_bytecode=1):
        outputs = _build_py.get_outputs(self, include_bytecode)
        outputs.extend(self.built_templates)

        if include_bytecode:
            for filename in self.built_templates:
                if self.compile:
                    outputs.append(filename + "c")
                if self.optimize > 0:
                    outputs.append(filename + "o")

        return outputs

    
    def run(self):
        if self.packages:
            self.build_package_templates()
        _build_py.run(self)



setup(name = "javaclass",
      version = "1.2",
      
      packages = ["javaclass",
                  "javaclass.cheetah"],

      package_dir = {"javaclass": "src",
                     "javaclass.cheetah": "src/cheetah"},
      
      #package_data = {"javaclass.cheetah": ["html/*.js",
      #                                      "html/*.png"]},
      
      scripts = ["scripts/classdiff",
                 "scripts/classinfo",
                 "scripts/distdiff",
                 "scripts/distinfo",
                 "scripts/jardiff",
                 "scripts/jarinfo",
                 "scripts/manifest",
                 "scripts/distpatchgen",
                 ],

      cmdclass = {'build_py': build_py})


#
# The end.
