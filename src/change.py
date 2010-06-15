"""

Some abstraction of the changes.

author: Christopher O'Brien  <obriencj@gmail.com>

"""


class GenericChange(object):
    
    """ A generalized test for a single change on two objects: a left
    and a right """

    label = "Generic Change"

    def __init__(self, ldata, rdata):
        self.ldata = ldata
        self.rdata = rdata
    
    def is_change(self):
        
        """ override to be a True/False result, indicating whether
        there was a detected change between the left and right data
        provided to this instance at __init__ """

        return False

    def is_ignored(self, options):

        """ override to be a True/False result, indicating whether the
        changes detected were ignorable given the options provided. It
        can be presumed that this method will only be called if
        is_change has also been called and had returned True """

        return False



class SuperChange(GenericChange):

    """ A collection of GenericChange instances """

    label = "Super Change"

    # override with change classes
    change_tests = ()


    def __init__(self, ldata, rdata):
        GenericChange.__init__(self, ldata, rdata)
        self.changes = ()


    def test(self):
        """ instanciates each of the classes in the overriden
        change_tests field with the left and right data, and collects
        the instances in self.changes """

        l,r = self.ldata, self.rdata

        if not self.changes:
            self.changes = [test(l,r) for test in self.change_tests]
        
            
    def is_change(self):
        self.test()

        for change in self.changes:
            if change.is_change():
                return True
        return False
            

    def is_ignored(self, cli_options):
        self.test()

        for change in self.changes:
            if not change.is_ignored(cli_options):
                return False
        return True



#
# The end.
