"""

Some abstraction of changes. Useful for the classdiff and jardiff
modules.

author: Christopher O'Brien  <obriencj@gmail.com>

"""



def _indent(stream, indent, indentstr, *msgs):
    for x in xrange(0,indent):
        stream.write(indentstr)
    for x in msgs:
        stream.write(x)
    stream.write("\n")



def yield_sorted_by_type(*typelist):
    """ a useful decorator for the collect_impl method of SuperChange
    subclasses. Caches the yielded changes, and re-emits them
    collected by their type. The order of the types can be specified
    by listing the types as arguments to this decorator. Unlisted
    types will be yielded last in no guaranteed order.

    Grouping happens by exact type match only. Inheritance is not
    taken into consideration for grouping. """

    def decorate(fun):
        cache = {}

        def decorated(*args,**kwds):
            # gather the emitted values by type
            for val in fun(*args, **kwds):
                key = val.__class__
                tl = cache.get(key, None)
                if not tl:
                    tl = list()
                    cache[key] = tl
                tl.append(val)

            # emit what we've gethered
            for t in typelist:
                for val in cache.pop(t, ()):
                    yield val

            # emit the leftovers
            for t,tl in cache.values():
                for val in tl:
                    yield val

        decorated.__doc__ = fun.__doc__
        decorated.func_name = fun.func_name
        decorated.func_doc = fun.func_doc
        return decorated
    return decorate



class Change(object):

    label = "Change"


    def __init__(self, ldata, rdata):
        self.ldata = ldata
        self.rdata = rdata
        self.description = None
        self.changed = False
        self.entry = None


    def clear(self):
        del self.ldata
        del self.rdata


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


    def write(self, options, indent=0, indentstr="  ", outstream=None):
        import sys

        out = outstream
        if not out:
            if options.output:
                out = open(options.output, "wt")
            else:
                out = sys.stdout

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

        if not outstream and options.output:
            out.close()



class Removal(Change):

    def is_change(self):
        return True



class Addition(Change):
    
    def is_change(self):
        return True


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


    def clear(self):
        GenericChange.clear(self)
        for c in self.changes:
            c.clear()
        del self.changes


    def collect_impl(self):
        """ instanciates each of the entries in in the overriden
        change_types field with the left and right data, and collects
        the instances in self.changes """
        
        l, r = self.ldata, self.rdata
        return (c(l,r) for c in self.change_types)


    def check_impl(self):
        """ sets self.changes to the result of self.changes_impl, then
        if any member of those checks shows as a change, will return
        True,None """

        self.changes = tuple(self.collect_impl())
        
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



class SquashedChange(Change):

    """ For when you want to keep just the overall data from a change,
    including whether it was ignored, but want to discard the more
    in-depth information. """

    def __init__(self, change, is_change, is_ignored):
        self.label = change.label
        self.description = change.get_description()
        self.changed = is_change
        self.ignored = is_ignored
        self.origclass = type(change)
        self.entry = getattr(change, "entry", None)

    def is_ignored(self, options):
        return self.ignored

    def is_change(self):
        return self.is_change



class SquashedRemoval(SquashedChange, Removal):
    pass



class SquashedAddition(SquashedChange, Addition):
    pass



def squash(change, is_change, is_ignored):
    if isinstance(change, Removal):
        return SquashedRemoval(change, is_change, is_ignored)
    elif isinstance(change, Addition):
        return SquashedAddition(change, is_change, is_ignored)
    else:
        return SquashedChange(change, is_change, is_ignored)



#
# The end.
