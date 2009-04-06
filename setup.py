"""

author: Christopher O'Brien  <siege@preoccupied.net>

"""


from distutils.core import setup


setup( name = "javaclass",
       version = "1.0",
       package_dir = {"javaclass": "src"},
       packages = ["javaclass"],
       scripts = ["scripts/classdiff",
                  "scripts/classinfo",
                  "scripts/jardiff"])


#
# The end.
