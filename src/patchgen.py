"""

"""


import sys
import os.path



INSTRUCTION_BASE = """
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
"""


def append_node(state, index):
    print "append_node", state, index

    doc = state.ownerDocument
    node = doc.createElement("node")
    node.setAttribute("name", str(index))
    state.appendChild(node)
    state.appendChild(doc.createTextNode("\n"))
    return node


def append_transition(node, name, targetname):
    print "append_transition", node, name, targetname
    
    doc = node.ownerDocument
    trans = doc.createElement("transition")
    trans.setAttribute("name", name)
    trans.setAttribute("to", str(targetname))
    node.appendChild(trans)
    node.appendChild(doc.createTextNode("\n"))
    return trans


def append_action(node, nodeclass):
    print "append_action", node, nodeclass

    doc = node.ownerDocument
    act = doc.createElement("action")
    act.setAttribute("config-type", "bean")
    act.setAttribute("class", nodeclass)
    node.appendChild(act)
    node.appendChild(doc.createTextNode("\n"))
    return act



def copyfile(fn, orig, patchdir):
    from shutil import copy

    print "copy file %s from %s into %s" % (fn, orig, patchdir)

    a, b = os.path.split(fn)

    dest = os.path.join(patchdir, a)
    dest_fn = os.path.join(patchdir, a, b)

    mkdirp(dest)
    copy(os.path.join(orig, fn), dest)

    return os.path.join("#{patchFolder}", a, b)



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
    from dirdelta import fnmatches
    import distdiff

    for change in delta.get_subchanges():
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
            if fnmatches(change.entry, "*.xml", "*.sh", "*.bat", "*.conf"):
                patches.append(change)
            else:
                copies.append(change)

        else:
            pass

    return copies, removals, patches



def generate_patch(delta, options):

    from xml.dom.minidom import parseString
    import xml.xpath
    
    copies, removals, patches = [], [], []
    sieve_changes(delta, options, copies, removals, patches)

    doc = parseString(INSTRUCTION_BASE)
    state = xml.xpath.Evaluate("/process-definition/super-state", doc)[0]
    end = xml.xpath.Evaluate("node[@name='complete']", state)[0]
    end.parentNode.removeChild(end)

    print doc
    print state
    print end

    index = 1

    patchdir = options.patch_dir
    
    for change in copies:
        tmp = copyfile(change.entry, delta.rdata, patchdir)

        node = append_node(state, index)
        act = append_action(node, BackupAndReplaceFile)
        
        o = doc.createElement("originalFileLocation")
        act.appendChild(o)
        t = doc.createTextNode(change.entry)
        o.appendChild(t)

        o = doc.createElement("replacementFileLocation")
        act.appendChild(o)
        t = doc.createTextNode(tmp)
        o.appendChild(t)

        index = index + 1
        append_transition(act, "originalFileNotFound", index)
        append_transition(act, "success", index)

    for change in removals:
        node = append_node(state, index)
        act = append_action(node, Notification)

        o = doc.createElement("notification")
        act.appendChild(o)
        t = doc.createTextNode("Remove the old file " + change.entry)
        o.appendChild(t)
        
        index = index + 1
        append_transition(node, "success", index)

    for change in patches:
        tmp = copypatch(change.entry, delta.ldata, delta.rdata, patchdir)

        node = append_node(state, index)
        act = append_action(node, Notification)

        o = doc.createElement("notification")
        act.appendChild(o)
        t = doc.createTextNode("Use the original file " + tmp + ".orig and"
                               " the patched file " + tmp + ".patched to"
                               " update your file " + change.entry)
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



def cli(options, rest):
    from distdiff import DistReport, options_magic

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

    return parser



def main(args):
    parser = create_optparser()
    return cli(*parser.parse_args(args))



if __name__ == "__main__":
    sys.exit(main(sys.argv))



#
# The end.
