#! /bin/sh


# Grabs two copies of JBoss AS (6.0.0 and 6.1.0) and uses them to
# produce a timed, multi-processing-enabled run of distdiff with all
# reports enabled, and a profiled (via cProfile) single-process run of
# distdiff with all reports enabled.


# this is currently the closest that we come to having test-suite
# coverage. I'm slowly fixing that problem.


OUTPUT_DIR=build/sample
DO_TIMED=
DO_PROFILED=


# the data for the left-side of the comparison
SAMPLE_URL_LEFT="http://downloads.sourceforge.net/project/jboss/JBoss/JBoss-6.0.0.Final/jboss-as-distribution-6.0.0.Final.zip?use_mirror=tcpdiag"
SAMPLE_FILE_LEFT=$OUTPUT_DIR/jboss-as-distribution-6.0.0.Final.zip
SAMPLE_DIR_LEFT=$OUTPUT_DIR/jboss-6.0.0.Final


# the data for the right-side of the comparison
SAMPLE_URL_RIGHT=http://download.jboss.org/jbossas/6.1/jboss-as-distribution-6.1.0.Final.zip
SAMPLE_FILE_RIGHT=$OUTPUT_DIR/jboss-as-distribution-6.1.0.Final.zip
SAMPLE_DIR_RIGHT=$OUTPUT_DIR/jboss-6.1.0.Final


function run_help() {
    echo "Usage: $0 [OPTIONS]"
    echo "Fetches sample distributions and runs a full report"
    echo
    echo " Options:"
    echo "   --help        print this message"
    echo "   --time        run a timed report"
    echo "   --profile     run a profiled report"
    echo "   --output=DIR  directory to write work into"
    echo "                 default: $OUTPUT_DIR"
    echo
}


for arg in "$@" ; do
    case "$arg" in
	--help)
	    run_help
	    exit 1
	    ;;

	--time)
	    DO_TIMED=1
	    ;;

	--profile)
	    DO_PROFILED=1
	    ;;

	--output=*)
	    OUTPUT_DIR="${arg#--output=}"
	    ;;
    esac
done


mkdir -p $OUTPUT_DIR


echo "Fetching sample data if needed"
if test ! -d "$SAMPLE_DIR_LEFT" ; then
    if test ! -f "$SAMPLE_FILE_LEFT" ; then
	wget -c "$SAMPLE_URL_LEFT" -O "$SAMPLE_FILE_LEFT"
    fi
    unzip -q "$SAMPLE_FILE_LEFT" -d "$OUTPUT_DIR/"
fi

if test ! -d "$SAMPLE_DIR_RIGHT" ; then
    if test ! -f "$SAMPLE_FILE_RIGHT" ; then
	wget -c "$SAMPLE_URL_RIGHT" -O "$SAMPLE_FILE_RIGHT"
    fi
    unzip -q "$SAMPLE_FILE_RIGHT" -d "$OUTPUT_DIR/"
fi


function just_run() {
    echo "Running normal report"

    PYTHONPATH=build/lib/ \
	build/scripts-2.7/distdiff \
	-q --show-ignored \
	--ignore=version,platform,lines,pool \
	--ignore=manifest_subsections,jar_signature \
	--ignore=trailing_whitespace \
	--report=html,txt,json \
	--report=html,txt,json \
	--report-dir=$OUTPUT_DIR/normal/reports \
	--html-copy-data=$OUTPUT_DIR/normal/resources \
	"$SAMPLE_DIR_LEFT" "$SAMPLE_DIR_RIGHT"

    echo "Report output written at $OUTPUT_DIR/normal/reports"
}


function run_timed() {
    echo "Running full-speed report for timing"

    PYTHONPATH=build/lib/ \
	/usr/bin/time -v -o $OUTPUT_DIR/timed/distdiff.time \
	build/scripts-2.7/distdiff \
	-q --show-ignored \
	--ignore=version,platform,lines,pool \
	--ignore=manifest_subsections,jar_signature \
	--ignore=trailing_whitespace \
	--report=html,txt,json \
	--report=html,txt,json \
	--report-dir=$OUTPUT_DIR/timed/reports \
	--html-copy-data=$OUTPUT_DIR/timed/resources \
	"$SAMPLE_DIR_LEFT" "$SAMPLE_DIR_RIGHT"

    cat $OUTPUT_DIR/distdiff.time
    echo "Timing data saved at $OUTPUT_DIR/timed/distdiff.time"
    echo "Report output written at $OUTPUT_DIR/timed/reports"
}


function run_profiled() {
    echo "Running single-process report for profiling dump"

    PYTHONPATH=build/lib/ \
	python -m cProfile -o $OUTPUT_DIR/profiled/distdiff.dump \
	build/scripts-2.7/distdiff \
	-q --show-ignored --processes=0 \
	--ignore=version,platform,lines,pool \
	--ignore=manifest_subsections,jar_signature \
	--ignore=trailing_whitespace \
	--report=html,txt,json \
	--report-dir=$OUTPUT_DIR/profiled/reports \
	--html-copy-data=$OUTPUT_DIR/profiled/resources \
	"$SAMPLE_DIR_LEFT" "$SAMPLE_DIR_RIGHT"

    echo "Profiling data saved at $OUTPUT_DIR/profiled/distdiff.dump"
    echo "Report output written at $OUTPUT_DIR/profiled/reports"
}


echo "Building"
./setup.py clean build || exit 1


if test "$DO_TIMED" ; then run_timed ; fi
if test "$DO_PROFILED" ; then run_profiled ; fi

if test ! "$DO_TIMED$DO_PROFILED" ; then just_run ; fi


#
# The end.
