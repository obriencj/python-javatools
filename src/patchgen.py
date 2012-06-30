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
Utilities for generating a JON-appropriate patch to move from one
level of a distribution to another

This tooling is currently of extremely limited use outside of
JON-deployments of JBoss.

author: Christopher O'Brien  <obriencj@gmail.com>
license: LGPL
"""


# TODO: This whole thing feels like a hack. We need to see if there is
# a better way to give JON instructions on upgrading an AS instance.



from .dirutils import makedirsp



CONFIG_PATTERN = (
    "*.bat",
    "*.cfg",
    "*.conf",
    "*.ini",
    "*.properties",
    "*.sh",
    "*.xml")



_INSTRUCTION_BASE = '''
<process-definition name="process">
  <start-state>
    <transition to="main_process/pre_1" />
  </start-state>

  <super-state name="main_process">
    <node name="pre_1">
      <action class="com.jboss.jbossnetwork.product.jbpm.handlers.JONServerDownloadActionHandler" config-type="bean" />
      <transition name="success" to="pre_2" />
    </node>

    <node name="pre_2">
      <action class="com.jboss.jbossnetwork.product.jbpm.handlers.CompareDigestActionHandler" config-type="bean">
        <algorithm>MD5</algorithm>
        <fileToBeCheckedLocation>#{downloadFolder}/#{software.filename}</fileToBeCheckedLocation>
        <expectedDigest>#{software.MD5}</expectedDigest>
      </action>
      <transition name="success" to="pre_3" />
    </node>

    <node name="pre_3">
      <action class="com.jboss.jbossnetwork.product.jbpm.handlers.UnzipActionHandler" config-type="bean">
        <fileToBeUnzippedLocation>#{downloadFolder}/#{software.filename}</fileToBeUnzippedLocation>
        <destinationDirectoryLocation>#{patchFolder}</destinationDirectoryLocation>
      </action>
      <transition name="success" to="pre_4" />
    </node>

    <node name="pre_4">
      <action class='com.jboss.jbossnetwork.product.jbpm.handlers.ControlActionHandler' config-type='bean'>
      <actionName>stopIfRunning</actionName>
      </action>
      <transition name="success" to="1" />
    </node>

    <node name="complete">
      <action class="com.jboss.jbossnetwork.product.jbpm.handlers.NotificationActionHandler" config-type="bean">
        <notification>Start your JBoss instance. If you are using JON to monitor your JBoss instance, perform
        a scan to update the version string. Go to your JBoss instance, choose the Inventory tab, edit the
        Configuration Properties and click OK</notification>
      </action>
      <transition name="success" to="../end" />
    </node>

    <transition name="error" to="end">
      <action class="com.jboss.jbossnetwork.product.jbpm.handlers.SetProcessStatusActionHandler" config-type="bean">
      <status>false</status>
      </action>
    </transition>

  </super-state>

  <end-state name="end" />

</process-definition>
'''



def append_node(state, index):
    #print "append_node", state, index

    doc = state.ownerDocument
    node = doc.createElement("node")
    node.setAttribute("name", str(index))
    state.appendChild(node)
    state.appendChild(doc.createTextNode("\n"))
    return node



def append_transition(node, name, targetname):
    #print "append_transition", node, name, targetname

    doc = node.ownerDocument
    trans = doc.createElement("transition")
    trans.setAttribute("name", name)
    trans.setAttribute("to", str(targetname))
    node.appendChild(trans)
    node.appendChild(doc.createTextNode("\n"))
    return trans



def append_action(node, nodeclass):
    #print "append_action", node, nodeclass

    doc = node.ownerDocument
    act = doc.createElement("action")
    act.setAttribute("config-type", "bean")
    act.setAttribute("class", nodeclass)
    node.appendChild(act)
    node.appendChild(doc.createTextNode("\n"))
    return act



def copyfile(fn, orig, patchdir):

    from os.path import join, split
    from shutil import copy

    print "copy file %s from %s into %s" % (fn, orig, patchdir)

    a, b = split(fn)

    orig_fn = join(orig, fn)
    dest = join(patchdir, a)
    ret = join("#{patchFolder}", a, b)

    makedirsp(dest)
    copy(orig_fn, dest)
    return ret



def copypatch(fn, orig, patched, patchdir):
    from shutil import copy
    from os.path import join, split

    a, b = split(fn)

    dest = join(patchdir, "config-patches", a)
    dest_fn = join(dest, b)

    print "copy patch %s into %s" % (fn, patchdir)

    makedirsp(dest)

    copy(join(orig, fn),  "%s.orig" % dest_fn)
    copy(join(patched, fn), "%s.patched" % dest_fn)

    return join("#{patchFolder}", "config-patches", fn)



_pkg = "com.jboss.jbossnetwork.product.jbpm.handlers"
_BackupAndReplaceFile = _pkg + ".BackupAndReplaceFileActionHandler"
_Notification = _pkg + ".NotificationActionHandler"



def sieve_changes(delta, options, copies, removals, patches):
    from .change import SquashedChange
    from .dirutils import fnmatches
    from javatools import distdiff

    for change in delta.collect():
        if not change.is_change():
            print "skipping unchanged", change.get_description()
            continue

        if change.is_ignored(options):
            print "sieving ignored change", change.get_description()
            continue

        changetype = type(change)
        if isinstance(change, SquashedChange):
            changetype = change.origclass

        if issubclass(changetype, (distdiff.DistContentAdded,
                                   distdiff.DistJarChange,
                                   distdiff.DistClassChange)):
            copies.append(change)

        elif issubclass(changetype, distdiff.DistContentRemoved):
            removals.append(change)

        elif issubclass(changetype, distdiff.DistContentChange):
            if fnmatches(change.entry, *CONFIG_PATTERN):
                patches.append(change)
            else:
                copies.append(change)

        else:
            print "unhandled change type %s" % changetype

    return copies, removals, patches



def repath(pathmap, pathstr):

    """ given pathmap (a dict of sub-paths to path monikers), match
    the longest moniker to pathstr and substitute. """

    found = ""
    for key in pathmap.keys():
        if pathstr.startswith(key):
            if len(key) > len(found):
                found = key

    if found:
        return pathmap[found] + pathstr[len(found):]
    else:
        return pathstr



def generate_patch(delta, options):

    from os.path import join
    from xml.dom.minidom import parseString
    import xml.xpath

    # get the lists of files we'll be copying, removing, or patching
    copies, removals, patches = [], [], []
    sieve_changes(delta, options, copies, removals, patches)

    pathmap = options.pathmap
    patchdir = options.patch_dir

    # get the base XML document that we'll be starting from
    doc = parseString(_INSTRUCTION_BASE)
    state = xml.xpath.Evaluate("/process-definition/super-state", doc)[0]
    end = xml.xpath.Evaluate("node[@name='complete']", state)[0]
    end.parentNode.removeChild(end)

    index = 1

    # used for sorting changes by entry
    entry_key = lambda i: i.entry

    for change in sorted(copies, key=entry_key):
        tmp = copyfile(change.entry, delta.rdata, patchdir)
        fn = repath(pathmap, change.entry)

        node = append_node(state, index)
        act = append_action(node, _BackupAndReplaceFile)

        o = doc.createElement("originalFileLocation")
        act.appendChild(o)
        t = doc.createTextNode(fn)
        o.appendChild(t)

        o = doc.createElement("replacementFileLocation")
        act.appendChild(o)
        t = doc.createTextNode(tmp)
        o.appendChild(t)

        index = index + 1
        append_transition(node, "originalFileNotFound", index)
        append_transition(node, "success", index)

    for change in sorted(removals, key=entry_key):
        node = append_node(state, index)
        act = append_action(node, _Notification)
        fn = repath(pathmap, change.entry)

        o = doc.createElement("notification")
        act.appendChild(o)
        t = doc.createTextNode("Remove the old file " + fn)
        o.appendChild(t)

        index = index + 1
        append_transition(node, "success", index)

    for change in sorted(patches, key=entry_key):
        tmp = copypatch(change.entry, delta.ldata, delta.rdata, patchdir)
        fn = repath(pathmap, change.entry)

        node = append_node(state, index)
        act = append_action(node, _Notification)

        o = doc.createElement("notification")
        act.appendChild(o)
        t = doc.createTextNode("Use the original file " + tmp + ".orig and"
                               " the patched file " + tmp + ".patched to"
                               " update your file " + fn)
        o.appendChild(t)

        index = index + 1
        append_transition(node, "success", index)

    # put the end back on.
    end.setAttribute("name", str(index))
    state.appendChild(end)

    # write the doc to file
    tmp = join(patchdir, "install-instructions.xml")
    with open(tmp, "wb") as fd:
        doc.writexml(fd)



def cli_patchgen(parser, options, left, right):

    """ very similar to running a distdiff report, but the final
    results are also used to create patching instructions """

    from .report import quick_report, Reporter
    from .report import JSONReportFormat, TextReportFormat
    from .distdiff import DistReport

    rdir = options.report_dir or "./"

    rpt = Reporter(rdir, "DistReport", options)
    rpt.add_formats_by_name(getattr(options, "reports", tuple()))

    delta = DistReport(left, right, rpt)
    delta.check()

    if not options.silent:
        if options.json:
            quick_report(JSONReportFormat, delta, options)
        else:
            quick_report(TextReportFormat, delta, options)

    # begin patch generation
    makedirsp(options.patch_dir)
    generate_patch(delta, options)

    return 0



def cli(parser, options, rest):
    if len(rest) != 3:
        parser.error("wrong number of arguments.")

    left, right = rest[1:3]

    return cli_patchgen(parser, options, left, right)



def _opt_cb_path_map(opt, opt_str, value, parser):

    """ handle the --path-map CLI option """

    options = parser.values
    pathmap = getattr(options, "pathmap", None)

    if pathmap is None:
        pathmap = dict()
        options.pathmap = pathmap

    if not ':' in value:
        parser.error("invalid --path-map argument %r, should be a"
                     " path:variable pair")

    k, v = value.split(':', 1)
    pathmap[k] = v



def patchgen_optgroup(parser):

    """ Option group relating to the patch generation actions of
    distpatchgen """

    from optparse import OptionGroup

    og = OptionGroup(parser, "Distribution Patch Generator Options")

    og.add_option("--patch-dir", action="store", default="patch",
                  help="Directory into which output patch data should"
                  " be written and copied. Defaults to ./patch")

    og.add_option("--path-map", type="string",
                  action="callback", callback=_opt_cb_path_map,
                  help="Can be specified multiple times. Each is a"
                  " path:variable mapping which will be used to swap"
                  " out the path names in the generated instructions")

    return og



def create_optparser():

    """ an OptionParser instance filled with options and groups
    appropriate for use with the distpatchgen command """

    from optparse import OptionParser
    from .distdiff import distdiff_optgroup
    from .jardiff import jardiff_optgroup
    from .classdiff import classdiff_optgroup, general_optgroup
    from javatools import report

    parser = OptionParser(usage="%prog [OPTIONS] OLD_DIST NEW_DIST")

    parser.add_option_group(general_optgroup(parser))
    parser.add_option_group(patchgen_optgroup(parser))
    parser.add_option_group(distdiff_optgroup(parser))
    parser.add_option_group(jardiff_optgroup(parser))
    parser.add_option_group(classdiff_optgroup(parser))

    parser.add_option_group(report.general_report_optgroup(parser))
    parser.add_option_group(report.json_report_optgroup(parser))
    parser.add_option_group(report.html_report_optgroup(parser))

    return parser



def default_patchgen_options(updates=None):

    """ generate an options object with the appropriate default values
    in place for API usage of patchgen features. overrides is an
    optional dictionary which will be used to update fields on the
    options object. """

    parser = create_optparser()
    options, _args = parser.parse_args(list())

    if updates:
        #pylint: disable=W0212
        options._update_careful(updates)

    return options



def main(args):

    """ main entry point for CLI usage of the dist patch generator """

    parser = create_optparser()
    return cli(parser, *parser.parse_args(args))



#
# The end.
