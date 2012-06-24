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
Some abstraction of changes. Useful for the classdiff and jardiff
modules.

author: Christopher O'Brien  <obriencj@gmail.com>
license: LGPL
"""



def collect_by_type(objs):
    cache = {}
    for val in objs:
        key = val.__class__
        tl = cache.get(key, None)
        if not tl:
            tl = list()
            cache[key] = tl
        tl.append(val)
    return cache



def iterate_by_type(objs, *typelist):
    cache = collect_by_type(objs)
    for t in typelist:
        for val in cache.pop(t, tuple()):
            yield val
    for tl in cache.values():
        for val in tl:
            yield val



def yield_sorted_by_type(*typelist):
    """ a useful decorator for the collect_impl method of SuperChange
    subclasses. Caches the yielded changes, and re-emits them
    collected by their type. The order of the types can be specified
    by listing the types as arguments to this decorator. Unlisted
    types will be yielded last in no guaranteed order.

    Grouping happens by exact type match only. Inheritance is not
    taken into consideration for grouping. """

    def decorate(fun):
        def decorated(*args,**kwds):
            return iterate_by_type(fun(*args, **kwds), *typelist)

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
        self.changed = True
        self.entry = None


    def clear(self):
        self.ldata = None
        self.rdata = None


    def check(self):
        pass


    def get_ldata(self):
        return self.ldata


    def get_rdata(self):
        return self.rdata


    def is_change(self):
        return self.changed


    def is_ignored(self, options):
        
        """ is this change ignorable, given parameters on the options
        object. """

        return False


    def get_description(self):
        return self.description or \
               (self.label + (" unchanged", " changed")[self.is_change()])


    def collect(self):
        return tuple()


    def simplify(self, options=None):

        """ returns a dict describing a simple snapshot of this
        change, and its children if any. """

        simple = {
            "class": type(self).__name__,
            "is_change": self.is_change(),
            "description": self.get_description(),
            "label": self.label,
            }

        if options:
            simple["is_ignored"] = self.is_ignored(options)

        if isinstance(self, Addition):
            simple["is_addition"] = True

        if isinstance(self, Removal):
            simple["is_removal"] = True

        if self.entry:
            simple["entry"] = self.entry

        return simple



class Removal(Change):

    """ Something was removed """

    def is_change(self):
        return True



class Addition(Change):
    
    """ Something was added """

    def is_change(self):
        return True



class GenericChange(Change):
    
    """ A generalized test for a single change on two objects: a left
    and a right. Subclasses should override the label and the check_impl """

    label = "Generic Change"


    def __init__(self, ldata, rdata):
        Change.__init__(self, ldata, rdata)
        self.changed = False


    def fn_data(self, c):
        
        """ Get the data to be used in fn_differ from c. By default,
        this method is the identity """

        return c


    def fn_pretty(self, c):
        """ override to provide a way to show the pretty version of the
        left or right data. Defaults to fn_data """

        return self.fn_data(c)

    
    def fn_pretty_desc(self, c):
        """ override to provide a way to describe the data left or right
        data. Defaults to fn_pretty """

        return self.fn_pretty(c)


    def fn_differ(self, ld, rd):
        """ override to provide the check for whether ld and rd differ.
        defaults to an equality check """

        return ld != rd


    def get_ldata(self):
        """ returns fn_data of ldata """

        return self.fn_data(self.ldata)


    def get_rdata(self):
        """ returns fn_data of rdata """

        return self.fn_data(self.rdata)


    def pretty_ldata(self):
        """ returns fn_pretty of ldata """

        return self.fn_pretty(self.ldata)


    def pretty_rdata(self):
        """ returns fn_pretty of rdata """

        return self.fn_pretty(self.rdata)


    def pretty_ldata_desc(self):
        """ returns fn_pretty_desc of ldata """

        return self.fn_pretty_desc(self.ldata)


    def pretty_rdata_desc(self):
        """ returns fn_pretty_desc of rdata """
        
        return self.fn_pretty_desc(self.rdata)


    def check_impl(self):

        """ returns a tuple of (is_change,description) which are then
        stored in self.changed and self.description

        The default implementation will get the data from the left and
        right sides by calling self.fn_data, then compare them via
        self.fn_differ. If they do differ, a message will be
        constructed using self.fn_pretty to create human-readable
        versions of the data that changed. """
        
        l, r = self.get_ldata(), self.get_rdata()
        if self.fn_differ(l, r):
            l, r = self.pretty_ldata_desc(), self.pretty_rdata_desc()
            return True, "%s changed: %s to %s" % (self.label, l, r)
        else:
            return False, None


    def check(self):

        """ if necessary, override check_impl to change the behaviour of
        subclasses of GenericChange. """

        changed, msg = self.check_impl()
        self.changed = changed
        self.description = msg


    def simplify(self, options=None):
        simple = Change.simplify(self, options)

        ld = self.pretty_ldata()
        if ld is not None:
            simple["old_data"] = ld

        rd = self.pretty_rdata()
        if rd is not None:
            simple["new_data"] = rd
        
        return simple



class SuperChange(GenericChange):

    """ A collection of GenericChange instances """

    label = "Super Change"

    # override with change classes
    change_types = tuple()


    def __init__(self, ldata, rdata):
        GenericChange.__init__(self, ldata, rdata)
        self.changes = tuple()


    def fn_pretty(self, c):
        return None


    def clear(self):
        GenericChange.clear(self)

        for c in self.changes:
            c.clear()
        self.changes = tuple()


    def collect_impl(self):
        """ instanciates each of the entries in in the overriden
        change_types field with the left and right data """
        
        l, r = self.ldata, self.rdata
        return (c(l,r) for c in self.change_types)


    def collect(self):
        """ calls collect_impl and stores the results as the child
        changes of this super-change """

        if not self.changes:
            self.changes = tuple(self.collect_impl())
        return self.changes


    def check_impl(self):
        """ sets self.changes to the result of self.changes_impl, then
        if any member of those checks shows as a change, will return
        True,None """

        c = False
        for change in self.collect():
            change.check()
            c = c or change.is_change()
        return c, None
            

    def is_ignored(self, options):
        if self.is_change():
            for change in self.collect():
                if change.is_change() and not change.is_ignored(options):
                    return False
            return True
        else:
            return False


    def simplify(self, options=None):
        data = GenericChange.simplify(self, options)

        # build a list of sub-changes honoring show-ignored and
        # show-unchanged

        show_ignored = False
        show_unchanged = False

        if options:
            show_ignored = getattr(options, "show_ignored", show_ignored)
            show_unchanged = getattr(options, "show_unchanged", show_unchanged)

        subs = list()
        for s in self.collect():
            if s.is_change():
                if show_ignored or not s.is_ignored(options):
                    subs.append(s)
            elif show_unchanged:
                subs.append(s)

        data["children"] = subs
        return data


    def squash_children(self, options):

        """ reduces the memory footprint of this super-change by
        converting all child changes into squashed changes """

        subs = (squash(c, options=options) for c in self.collect())

        oldsubs = self.changes
        self.changes = tuple(subs)

        for change in oldsubs:
            change.clear()



class SquashedChange(Change):

    """ For when you want to keep just the overall data from a change,
    including whether it was ignored, but want to discard the more
    in-depth information. """

    def __init__(self, change, is_ignored=False):
        Change.__init__(self)
        self.label = change.label
        self.description = change.get_description()
        self.changed = change.is_change()
        self.ignored = is_ignored
        self.origclass = type(change)
        self.entry = getattr(change, "entry", None)

    def is_ignored(self, options):
        return self.ignored

    def is_change(self):
        return self.changed

    def simplify(self, options=None):
        simple = Change.simplify(self, options)
        simple["original_class"] = self.origclass.__name__
        return simple

    def clear(self):
        pass



class SquashedRemoval(SquashedChange, Removal):
    pass



class SquashedAddition(SquashedChange, Addition):
    pass



def squash(change, is_ignored=False, options=None):

    """ squashes the in-depth information of a change to a simplified
    (and less memory-intensive) form """

    if options:
        is_ignored = change.is_ignored(options)

    if isinstance(change, Removal):
        return SquashedRemoval(change, is_ignored)
    elif isinstance(change, Addition):
        return SquashedAddition(change, is_ignored)
    else:
        return SquashedChange(change, is_ignored)



#
# The end.
