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


import os.path



CONFIG_PATTERN = (
    "*.bat",
    "*.conf",
    "*.ini",
    "*.properties",
    "*.sh",
    "*.xml")



INSTRUCTION_BASE = '''
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



def chunks(stream, x=(1024*64)):
    buf = stream.read(x)
    while buf:
        yield buf
        buf = stream.read(x)



def sha256sum(fn):
    from hashlib import sha256

    fd = open(fn, "rb")
    cs = sha256()

    for chunk in chunks(fd):
        cs.update(chunk)
    fd.close()

    return cs.hexdigest()



def copyfile(fn, orig, patchdir, squash=None,
             pathsquash=None, pathsquashed=None):

    from shutil import copy

    print "copy file %s from %s into %s" % (fn, orig, patchdir)

    a, b = os.path.split(fn)

    orig_fn = os.path.join(orig, fn)
    dest = os.path.join(patchdir, a)
    dest_fn = os.path.join(patchdir, a, b)
    ret = os.path.join("#{patchFolder}", a, b)

    if pathsquash is not None:
        ps = None
        for k in pathsquash:
            if fn.startswith(k):
                ps = fn[len(k):]
                break

        if ps:
            check = pathsquashed.get(ps)
            if check:
                print "path squashing file %s as a copy of %s" % (fn, check)
                return check
            else:
                pathsquashed[ps] = ret
                mkdirp(dest)
                copy(orig_fn, dest)
                return ret

    if squash is None:
        mkdirp(dest)
        copy(orig_fn, dest)
        return ret

    else:
        squashkey = sha256sum(orig_fn)
        squashed = squash.get(squashkey)
        
        if squashed:
            print "sha256 squashing file %s as a copy of %s" % (fn, squashed)
            return squashed

        else:
            squash[squashkey] = ret
            mkdirp(dest)
            copy(orig_fn, dest)
            return ret



def copypatch(fn, orig, patched, patchdir):
    from shutil import copy

    print "copy patch %s from %s into %s" % (fn, orig, patchdir)

    a, b = os.path.split(fn)

    dest = os.path.join(patchdir, "config-patches", a)
    dest_fn = os.path.join(dest, b)

    mkdirp(dest)
    copy(os.path.join(orig, fn),  "%s.orig" % dest_fn)
    copy(os.path.join(patched, fn), "%s.patched" % dest_fn)

    return os.path.join("#{patchFolder}", "config-patches", fn)



def mkdirp(dirname):
    from os import makedirs
    if not os.path.exists(dirname):
        makedirs(dirname)



pkg = "com.jboss.jbossnetwork.product.jbpm.handlers"
BackupAndReplaceFile = pkg + ".BackupAndReplaceFileActionHandler"
Notification = pkg + ".NotificationActionHandler"



def sieve_changes(delta, options, copies, removals, patches):
    from dirutils import fnmatches
    import distdiff

    for change in delta.get_subchanges():
        if not change.is_change():
            print "skipping unchanged", change.get_description()
            continue

        if change.is_ignored(options):
            print "sieving ignored change", change.get_description()
            continue

        if issubclass(change.origclass, (distdiff.DistContentAdded,
                                         distdiff.DistJarChange,
                                         distdiff.DistClassChange)):
            copies.append(change)

        elif issubclass(change.origclass, distdiff.DistContentRemoved):
            removals.append(change)

        elif issubclass(change.origclass, distdiff.DistContentChange):
            if fnmatches(change.entry, *CONFIG_PATTERN):
                patches.append(change)
            else:
                copies.append(change)

        else:
            pass

    return copies, removals, patches



def repath(pathmap, pathstr):
    found = ""
    for key in pathmap.keys():
        if pathstr.startswith(key):
            if len(key) > len(found):
                found = key
    
    if found:
        return pathmap[found] + "/" + pathstr[len(found):]
    else:
        return pathstr



def sort_by_entry(changeset):
    tmp = {}
    for c in changeset:
        tmp[c.entry] = c
    keys = tmp.keys()
    keys.sort()
    for k in keys:
        yield tmp[k]



def generate_patch(delta, options):

    from xml.dom.minidom import parseString
    import xml.xpath
    
    copies, removals, patches = [], [], []
    sieve_changes(delta, options, copies, removals, patches)

    pathmap = options.pathmap

    doc = parseString(INSTRUCTION_BASE)
    state = xml.xpath.Evaluate("/process-definition/super-state", doc)[0]
    end = xml.xpath.Evaluate("node[@name='complete']", state)[0]
    end.parentNode.removeChild(end)

    #print doc
    #print state
    #print end

    index = 1

    patchdir = options.patch_dir
    
    squash = None
    if options.squash_256:
        squash = {}

    spaths = None
    spmap = None
    if options.squash_path:
        spaths = options.squash_path
        spmap = {}

    for change in sort_by_entry(copies):
        tmp = copyfile(change.entry, delta.rdata, patchdir,
                       squash, spaths, spmap)

        fn = repath(pathmap, change.entry)

        node = append_node(state, index)
        act = append_action(node, BackupAndReplaceFile)
        
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

    for change in sort_by_entry(removals):
        node = append_node(state, index)
        act = append_action(node, Notification)
        fn = repath(pathmap, change.entry)

        o = doc.createElement("notification")
        act.appendChild(o)
        t = doc.createTextNode("Remove the old file " + fn)
        o.appendChild(t)
        
        index = index + 1
        append_transition(node, "success", index)

    for change in sort_by_entry(patches):
        tmp = copypatch(change.entry, delta.ldata, delta.rdata, patchdir)
        fn = repath(pathmap, change.entry)

        node = append_node(state, index)
        act = append_action(node, Notification)

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
    tmp = os.path.join(patchdir, "install-instructions.xml")
    fd = open(tmp, "wb")
    doc.writexml(fd)
    fd.close()



def options_magic(options):
    import distdiff

    distdiff.options_magic(options)

    pathmap = {}
    for m in options.path_map:
        k,v = m.split(":",1)
        pathmap[k] = v

    options.pathmap = pathmap



def cli(options, rest):
    from distdiff import DistReport

    options_magic(options)

    left, right = rest[1:3]
    
    mkdirp(options.patch_dir)

    print "creating DistReport"
    delta = DistReport(left, right, options)

    print "running DistReport.check"
    delta.check()

    print "generating patch"
    generate_patch(delta, options)

    print "done"



def create_optparser():
    from distdiff import create_optparser
    parser = create_optparser()

    parser.add_option("--patch-dir", action="store", default="patch")
    parser.add_option("--path-map", action="append", default=[])

    parser.add_option("--squash-256", action="store_true",
                      default=False)

    parser.add_option("--squash-path", action="append", default=[])

    return parser



def main(args):
    parser = create_optparser()
    return cli(*parser.parse_args(args))



#
# The end.
