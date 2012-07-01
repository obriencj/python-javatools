#! /bin/sh


PROFILE_DIR=build/profiling


SAMPLE_URL_LEFT=http://download.jboss.org/jbossas/7.0/jboss-as-7.0.2.Final/jboss-as-web-7.0.2.Final.zip
SAMPLE_FILE_LEFT=$PROFILE_DIR/jboss-as-web-7.0.2.Final.zip
SAMPLE_DIR_LEFT=$PROFILE_DIR/jboss-as-web-7.0.2.Final


SAMPLE_URL_RIGHT=http://download.jboss.org/jbossas/7.1/jboss-as-7.1.1.Final/jboss-as-7.1.1.Final.zip
SAMPLE_FILE_RIGHT=$PROFILE_DIR/jboss-as-7.1.1.Final.zip
SAMPLE_DIR_RIGHT=$PROFILE_DIR/jboss-as-7.1.1.Final



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



export PYTHONPATH=build/lib/



echo "Running full-speed report for timing"

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



unset PYTHONPATH
echo "Done!"


#
# The end.
