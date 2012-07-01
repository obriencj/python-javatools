#! /bin/sh



# Grabs two copies of JBoss AS (6.0.0 and 6.1.0) and uses them to
# produce a timed, multi-processing-enabled run of distdiff with all
# reports enabled, and a profiled (via cProfile) single-process run of
# distdiff with all reports enabled.


# this is currently the closest that we come to having test-suite
# coverage.



PROFILE_DIR=build/profiling

SAMPLE_URL_LEFT=http://sourceforge.net/projects/jboss/files/JBoss/JBoss-6.0.0.Final/jboss-as-distribution-6.0.0.Final.zip/download
SAMPLE_FILE_LEFT=$PROFILE_DIR/jboss-as-distribution-6.0.0.Final.zip
SAMPLE_DIR_LEFT=$PROFILE_DIR/jboss-6.0.0.Final

SAMPLE_URL_RIGHT=http://download.jboss.org/jbossas/6.1/jboss-as-distribution-6.1.0.Final.zip
SAMPLE_FILE_RIGHT=$PROFILE_DIR/jboss-as-distribution-6.1.0.Final.zip
SAMPLE_DIR_RIGHT=$PROFILE_DIR/jboss-6.1.0.Final



echo "Fetching sample data if needed"
if test ! -d "$SAMPLE_DIR_LEFT" ; then
    if test ! -f "$SAMPLE_FILE_LEFT" ; then
	wget -c "$SAMPLE_URL_LEFT" -O "$SAMPLE_FILE_LEFT"
    fi
    unzip -q "$SAMPLE_FILE_LEFT" -d "$PROFILE_DIR/"
fi

if test ! -d "$SAMPLE_DIR_RIGHT" ; then
    if test ! -f "$SAMPLE_FILE_RIGHT" ; then
	wget -c "$SAMPLE_URL_RIGHT" -O "$SAMPLE_FILE_RIGHT"
    fi
    unzip -q "$SAMPLE_FILE_RIGHT" -d "$PROFILE_DIR/"
fi



echo "Building"
./setup.py pylint || exit 1



echo "Running full-speed report for timing"

PYTHONPATH=build/lib/ \
/usr/bin/time -v -o $PROFILE_DIR/distdiff.time \
    build/scripts-2.7/distdiff \
    -q --show-ignored \
    --ignore=version,platform,lines,pool \
    --ignore=manifest_subsections,jar_signature \
    --ignore=trailing_whitespace \
    --report=html,txt,json \
    --report=html,txt,json \
    --report-dir=$PROFILE_DIR/timed/reports \
    --html-copy-data=$PROFILE_DIR/timed/resources \
    "$SAMPLE_DIR_LEFT" "$SAMPLE_DIR_RIGHT"

cat $PROFILE_DIR/distdiff.time



echo "Running single-process report for profiling dump"

PYTHONPATH=build/lib/ \
python -m cProfile -o $PROFILE_DIR/distdiff.dump \
    build/scripts-2.7/distdiff \
    -q --show-ignored --processes=0 \
    --ignore=version,platform,lines,pool \
    --ignore=manifest_subsections,jar_signature \
    --ignore=trailing_whitespace \
    --report=html,txt,json \
    --report-dir=$PROFILE_DIR/profiled/reports \
    --html-copy-data=$PROFILE_DIR/profiled/resources \
    "$SAMPLE_DIR_LEFT" "$SAMPLE_DIR_RIGHT"



echo "Done!"



#
# The end.
