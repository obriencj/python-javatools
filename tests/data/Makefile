SOURCES = $(wildcard *.java)
JAVAC = javac

.SUFFIXES: .java .class
.java.class:
	$(JAVAC) $<
default: all
all: $(SOURCES:.java=.class)
clean:
	$(RM) *.class
