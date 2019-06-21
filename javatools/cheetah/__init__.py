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
Collects available Cheetah templates for use with the HTML report

author: Christopher O'Brien <obriencj@gmail.com>
license: LGPL
"""


from pkgutil import iter_modules


def _iter_templates():
    """
    uses reflection to yield the Cheetah templates under this module
    """

    # pylint: disable=W0406
    # needed for introspection
    import javatools.cheetah
    from Cheetah.Template import Template

    for _, name, _ in iter_modules(__path__):
        if name == "setuptools":
            continue

        __import__("javatools.cheetah." + name)
        found = getattr(getattr(javatools.cheetah, name), name)
        if issubclass(found, Template):
            yield found


def get_templates():
    """
    The Cheetah Template classes contained within this module
    """

    return tuple(_iter_templates())


def xml_entity_escape(data):
    """
    replace special characters with their XML entity versions
    """

    data = data.replace("&", "&amp;")
    data = data.replace(">", "&gt;")
    data = data.replace("<", "&lt;")
    return data


#
# The end.
