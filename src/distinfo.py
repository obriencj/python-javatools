"""

author: Christopher O'Brien  <obriencj@gmail.com>

"""



DIST_JAR = "jar"
DIST_CLASS = "class"



JAR_PATTERNS = ( "*.ear",
                 "*.jar",
                 "*.rar",
                 "*.sar",
                 "*.war", )



def _collect_dist(pathn):
    # walk down pathn looking for .class and .jar

    from dirdelta import fnmatches
    from os import walk
    from os.path import isdir, join

    if not isdir(pathn):
        #TODO: support exploding dist zips
        return

    for r,d,fs in walk(pathn):
        for f in fs:
            if f.endswith(".class"):
                yield (DIST_CLASS, join(r, f))
            elif fnmatches(f, *JAR_PATTERNS):
                yield (DIST_JAR, join(r, f))



def collect_dist(pathn):
    return list(_collect_dist(pathn))



def get_dist_jar_class_infos(path):
    from zipfile import ZipFile
    from jarinfo import get_jar_class_info_map

    zf = ZipFile(path)
    cim = get_jar_class_info_map(zf)
    zf.close()

    return cim.values()



def get_dist_jar_provides(path):
    from jarinfo import get_class_infos_provides
    return get_class_infos_provides(get_dist_jar_class_infos(path))    



def get_dist_class_provides(path):
    from javaclass import unpack_classfile

    info = unpack_classfile(path)
    return info.get_provides()



def get_dist_jar_requires(path):
    from jarinfo import get_class_infos_requires
    return get_class_infos_requires(get_dist_jar_class_infos(path))    



def get_dist_class_requires(path):
    from javaclass import unpack_classfile

    info = unpack_classfile(path)
    return info.get_requires()



def get_dist_provides(dist):
    prov = list()
    for ptype,path in dist:
        if ptype == DIST_JAR:
            prov.extend(get_dist_jar_provides(path))
        elif ptype == DIST_CLASS:
            prov.extend(get_dist_class_provides(path))
    return set(prov)



def get_dist_requires(dist):
    deps = list()
    for ptype,path in dist:
        if ptype == DIST_JAR:
            deps.extend(get_dist_jar_requires(path))
        elif ptype == DIST_CLASS:
            deps.extend(get_dist_class_requires(path))
    deps = set(deps)

    prov = get_dist_provides(dist)
    return deps.difference(prov)



def cli_dist_api_provides(options, pathn):
    from dirdelta import fnmatches

    dist = collect_dist(pathn)
    provides = list(get_dist_provides(dist))
    provides.sort()

    print "distribution %s provides:" % pathn

    for provided in provides:
        if not fnmatches(provided, *options.api_ignore):
            print " ", provided
    print



def cli_dist_api_requires(options, pathn):
    from dirdelta import fnmatches

    dist = collect_dist(pathn)
    requires = list(get_dist_requires(dist))
    requires.sort()

    print "distribution %s requires:" % pathn

    for required in requires:
        if not fnmatches(required, *options.api_ignore):
            print " ", required
    print



def cli(options, rest):

    pathn = rest[1]

    if options.api_provides or options.api_requires:
        if options.api_provides:
            cli_dist_api_provides(options, pathn)
        if options.api_requires:
            cli_dist_api_requires(options, pathn)
        return

    #TODO: simple things like listing JARs and non-JAR files

    return 0



def create_optparser():
    from jarinfo import create_optparser

    parser = create_optparser()

    return parser



def main(args):
    parser = create_optparser()
    return cli(*parser.parse_args(args))



if __name__ == "__main__":
    sys.exit(main(sys.argv))



#
# The end.
