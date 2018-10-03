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

:author: Christopher O'Brien  <obriencj@gmail.com>
:license: LGPL
"""


from functools import wraps


__all__ = (
    "squash",
    "collect_by_typename", "collect_by_type",
    "iterate_by_type", "yield_sorted_by_type",
    "Change", "Addition", "Removal",
    "GenericChange", "SuperChange",
    "SquashedChange", "SquashedAddition", "SquashedRemoval", )


def collect_by_typename(obj_sequence, cache=None):
    """
    collects objects from obj_sequence and stores them into buckets by
    type name. cache is an optional dict into which we collect the
    results.
    """

    if cache is None:
        cache = {}

    for val in obj_sequence:
        key = type(val).__name__

        bucket = cache.get(key, None)
        if bucket is not None:
            bucket.append(val)
        else:
            cache[key] = [val]

    return cache


def collect_by_type(obj_sequence, cache=None):
    """
    collects objects from obj_sequence and stores them into buckets by
    type. cache is an optional dict into which we collect the results.
    """

    if cache is None:
        cache = {}

    for val in obj_sequence:
        key = type(val)

        bucket = cache.get(key, None)
        if bucket is not None:
            bucket.append(val)
        else:
            cache[key] = [val]

    return cache


def iterate_by_type(objs, typelist):
    """
    collects a sequence of objs into buckets by type, then re-emits
    objs from the buckets, sorting through the buckets in the order
    specified by typelist. Any objects of a type not specified in
    typelist will be emitted last in no guaranteed order (but still
    grouped by type).
    """

    cache = collect_by_type(objs)

    for t in typelist:
        for val in cache.pop(t, tuple()):
            yield val

    for tl in cache.values():
        for val in tl:
            yield val


def yield_sorted_by_type(*typelist):
    """
    a useful decorator for the collect_impl method of SuperChange
    subclasses. Caches the yielded changes, and re-emits them
    collected by their type. The order of the types can be specified
    by listing the types as arguments to this decorator. Unlisted
    types will be yielded last in no guaranteed order.

    Grouping happens by exact type match only. Inheritance is not
    taken into consideration for grouping.
    """

    def decorate(fun):
        @wraps(fun)
        def decorated(*args, **kwds):
            return iterate_by_type(fun(*args, **kwds), typelist)
        return decorated

    return decorate


class Change(object):
    """
    Base class for representing a specific change between two objects
    """

    label = "Change"


    def __init__(self, ldata, rdata):
        self.ldata = ldata
        self.rdata = rdata
        self.description = None
        self.changed = False
        self.entry = None


    def __del__(self):
        self.clear()


    def clear(self):
        self.ldata = None
        self.rdata = None
        self.description = None
        self.changed = False
        self.entry = None


    def check(self):
        pass


    def get_ldata(self):
        return self.ldata


    def get_rdata(self):
        return self.rdata


    def is_change(self):
        return self.changed


    def is_ignored(self, options):
        """
        is this change ignorable, given parameters on the options
        object.
        """

        return False


    def get_description(self):
        return self.description or \
            (self.label + (" changed" if self.is_change() else " unchanged"))


    def collect(self, force=False):
        return tuple()


    def simplify(self, options=None):
        """
        returns a dict describing a simple snapshot of this change, and
        its children if any.
        """

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
    """
    A type of change indicating that something was removed
    """

    label = "Removal"


    def is_change(self):
        return True


class Addition(Change):
    """
    A type of change indicating that something was added
    """

    label = "Addition"


    def is_change(self):
        return True


class GenericChange(Change):
    """
    A generalized test for a single change on two objects: a left and
    a right. Subclasses should override the label and the check_impl
    method at a minimum.
    """

    label = "Generic Change"


    def fn_data(self, side_data):
        """
        Get the data to be used in fn_differ from side_data. By default,
        this method is the identity
        """

        return side_data


    def fn_pretty(self, side_data):
        """
        override to provide a way to show the pretty version of the left
        or right data. Defaults to fn_data
        """

        return self.fn_data(side_data)


    def fn_pretty_desc(self, side_data):
        """
        override to provide a way to describe the data left or right
        data. Defaults to fn_pretty
        """

        return self.fn_pretty(side_data)


    def fn_differ(self, left_data, right_data):
        """
        override to provide the check for whether get_ldata() and
        get_rdata() differ. defaults to an inequality (!=) check
        """

        return left_data != right_data


    def get_ldata(self):
        """
        returns fn_data of ldata
        """

        return self.fn_data(self.ldata)


    def get_rdata(self):
        """
        returns fn_data of rdata
        """

        return self.fn_data(self.rdata)


    def pretty_ldata(self):
        """
        returns fn_pretty of ldata (NOT the fn_pretty of get_ldata)
        """

        return self.fn_pretty(self.ldata)


    def pretty_rdata(self):
        """
        returns fn_pretty of rdata (NOT the fn_pretty of get_rdata)
        """

        return self.fn_pretty(self.rdata)


    def pretty_ldata_desc(self):
        """
        returns fn_pretty_desc of ldata (NOT the fn_pretty_desc of
        get_ldata)
        """

        return self.fn_pretty_desc(self.ldata)


    def pretty_rdata_desc(self):
        """
        returns fn_pretty_desc of rdata (NOT the fn_pretty_desc of
        get_rdata)
        """

        return self.fn_pretty_desc(self.rdata)


    def check_impl(self):
        """
        returns a tuple of (is_change,description) which are then stored
        in self.changed and self.description

        The default implementation will get the data from the left and
        right sides by calling self.fn_data, then compare them via
        self.fn_differ. If they do differ, a message will be
        constructed using self.fn_pretty to create human-readable
        versions of the data that changed.
        """

        if self.fn_differ(self.get_ldata(), self.get_rdata()):

            left = self.pretty_ldata_desc()
            right = self.pretty_rdata_desc()
            msg = "%s changed: %s to %s" % (self.label, left, right)

            return True, msg

        else:
            return False, None


    def check(self):
        """
        if necessary, override check_impl to change the behaviour of
        subclasses of GenericChange.
        """

        self.changed, self.description = self.check_impl()


    def simplify(self, options=None):
        """
        provide a simple representation of this change as a dictionary
        """

        # TODO: we might want to get rid of this method and just move
        # it into the JSONEncoder in report.py

        simple = super(GenericChange, self).simplify(options)

        ld = self.pretty_ldata()
        if ld is not None:
            simple["old_data"] = ld

        rd = self.pretty_rdata()
        if rd is not None:
            simple["new_data"] = rd

        return simple


class SuperChange(GenericChange):
    """
    A collection of changes.

    For simplest use, override the change_types class field with a
    list of Change subclasses. When the default collect_impl is called
    from collect, an instance of each type will be created with the
    same left and right data as the SuperChange instance was created
    with. The check_impl (called from check) will iterate over the
    instances and call their check method in-turn.

    An instance of SuperChange is considered unchanged if all of its
    sub-changes are also unchanged (or if there were no sub-changes).

    An instance of SuperChange is considered ignored if it was a
    change and all of its changed children were also ignored.
    """

    label = "Super Change"


    # override with change classes
    change_types = tuple()


    def __init__(self, ldata, rdata):
        super(SuperChange, self).__init__(ldata, rdata)
        self.changes = tuple()


    def fn_pretty(self, c):
        return None


    def clear(self):
        """
        clears all child changes and drops the reference to them
        """

        super(SuperChange, self).clear()

        for c in self.changes:
            c.clear()
        self.changes = tuple()


    def collect_impl(self):
        """
        instantiates each of the entries in in the overriden change_types
        field with the left and right data
        """

        ldata = self.get_ldata()
        rdata = self.get_rdata()

        for change_type in self.change_types:
            yield change_type(ldata, rdata)


    def collect(self, force=False):
        """
        calls collect_impl and stores the results as the child changes of
        this super-change. Returns a tuple of the data generated from
        collect_impl. Caches the result rather than re-computing each
        time, unless force is True
        """

        if force or not self.changes:
            self.changes = tuple(self.collect_impl())
        return self.changes


    def check_impl(self):
        """
        sets self.changes to the result of self.changes_impl, then if any
        member of those checks shows as a change, will return
        True,None
        """

        c = False
        for change in self.collect():
            change.check()
            c = c or change.is_change()
        return c, None


    def is_ignored(self, options):
        """
        If we have changed children and all the children which are changes
        are ignored, then we are ignored. Otherwise, we are not
        ignored
        """

        if not self.is_change():
            return False

        changes = self.collect()
        if not changes:
            return False

        for change in changes:
            if change.is_change() and not change.is_ignored(options):
                return False
        return True


    def simplify(self, options=None):
        """
        generate a simple dict representing this change data, and
        collecting all of the sub-change instances (which are NOT
        immediately simplified themselves)
        """

        data = super(SuperChange, self).simplify(options)

        show_ignored = False
        show_unchanged = False

        if options:
            show_ignored = getattr(options, "show_ignored", show_ignored)
            show_unchanged = getattr(options, "show_unchanged", show_unchanged)

        # build a list of sub-changes honoring show-ignored and
        # show-unchanged

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
        """
        reduces the memory footprint of this super-change by converting
        all child changes into squashed changes
        """

        oldsubs = self.collect()
        self.changes = tuple(squash(c, options=options) for c in oldsubs)

        for change in oldsubs:
            change.clear()


class SquashedChange(Change):
    """
    For when you want to keep just the overall data from a change,
    including whether it was ignored, but want to discard the more
    in-depth information.
    """

    label = "SquashedChange"


    def __init__(self, change, is_ignored=False):
        super(SquashedChange, self).__init__(None, None)

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
        simple = super(SquashedChange, self).simplify(options)
        simple["original_class"] = self.origclass.__name__
        return simple


    def clear(self):
        pass


class SquashedRemoval(SquashedChange, Removal):
    """
    Squashed change indicating something was removed
    """

    label = "SquashedRemoval"


class SquashedAddition(SquashedChange, Addition):
    """
    Squashed change indicating something was added
    """

    label = "SquashedAddition"


def squash(change, is_ignored=False, options=None):
    """
    squashes the in-depth information of a change to a simplified (and
    less memory-intensive) form
    """

    if options:
        is_ignored = change.is_ignored(options)

    if isinstance(change, Removal):
        result = SquashedRemoval(change, is_ignored)
    elif isinstance(change, Addition):
        result = SquashedAddition(change, is_ignored)
    else:
        result = SquashedChange(change, is_ignored)

    return result


#
# The end.
