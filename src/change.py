"""

Some abstraction of changes. Useful for the classdiff and jardiff
modules.

author: Christopher O'Brien  <obriencj@gmail.com>

"""



import sys


def _indent(stream, indent, indentstr, *msgs):
    for x in xrange(0,indent):
        stream.write(indentstr)
    for x in msgs:
        stream.write(x)
    stream.write("\n")



class Change(object):

    label = "Change"


    def __init__(self, ldata, rdata):
        self.ldata = ldata
        self.rdata = rdata
        self.description = None
        self.changed = False


    def check(self):
        pass


    def is_change(self):
        return self.changed


    def is_ignored(self, options):
        return False


    def get_description(self):
        return self.description or \
               (self.label + (" unchanged", " changed")[self.is_change()])


    def get_subchanges(self):
        return tuple()


    def write(self, options, indent=0, indentstr="  ", out=sys.stdout):
        if self.is_change():
            if self.is_ignored(options):
                if getattr(options, "show_ignored", False):
                    _indent(out,indent,indentstr,
                            self.get_description(),
                            " [IGNORED]")
            else:
                _indent(out,indent,indentstr,
                        self.get_description())
                
        elif getattr(options, "show_unchanged", False):
            _indent(out,indent,indentstr,
                    self.get_description())

        for sub in self.get_subchanges():
            sub.write(options, indent+1, indentstr, out)
        


class GenericChange(Change):
    
    """ A generalized test for a single change on two objects: a left
    and a right """

    label = "Generic Change"


    def __init__(self, ldata, rdata):
        Change.__init__(self, ldata, rdata)
        self.changed = False


    def fn_data(self, c):
        return None


    def fn_pretty(self, c):
        return self.fn_data(c)


    def fn_differ(self, ld, rd):
        return ld != rd


    def check_impl(self):

        """ returns a tuple of (is_change,description) which are then
        stored in self.changed and self.description

        The default implementation will get the data from the left and
        right sides by calling self.fn_data, then compare them via
        self.fn_differ. If they do differ, a message will be
        constructed using self.fn_pretty to create human-readable
        versions of the data that changed. """
        
        l, r = self.fn_data(self.ldata), self.fn_data(self.rdata)
        if self.fn_differ(l, r):
            l, r = self.fn_pretty(self.ldata), self.fn_pretty(self.rdata)
            return True, "%s changed: %r to %r" % (self.label, l, r)
        else:
            return False, None


    def check(self):

        """ if necessary, override check_impl to change the behaviour of
        subclasses of GenericChange. """

        changed, msg = self.check_impl()
        self.changed = changed
        self.description = msg



class SuperChange(GenericChange):

    """ A collection of GenericChange instances """

    label = "Super Change"

    # override with change classes
    change_types = ()


    def __init__(self, ldata, rdata):
        GenericChange.__init__(self, ldata, rdata)
        self.changes = ()


    def changes_impl(self):
        """ instanciates each of the entries in in the overriden
        change_types field with the left and right data, and collects
        the instances in self.changes """
        
        l, r = self.ldata, self.rdata
        return (c(l,r) for c in self.change_types)


    def check_impl(self):
        """ sets self.changes to the result of self.changes_impl, then
        if any member of those checks shows as a change, will return
        True,None """

        self.changes = tuple(self.changes_impl())
        
        c = False
        for change in self.changes:
            change.check()
            c = c or change.is_change()
        return c, None
            

    def is_ignored(self, options):
        for change in self.changes:
            if change.is_change() and not change.is_ignored(options):
                return False
        return True


    def get_subchanges(self):
        return self.changes



#
# The end.
