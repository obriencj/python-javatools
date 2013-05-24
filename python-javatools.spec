Summary: Tools for inspecting and comparing binary Java class files
Name: python-javatools
Version: 1.3
Release: 1
License: LGPL
Group: Application/System
URL: https://github.com/obriencj/python-javatools/
Source0: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
BuildArch: noarch

# Don't believe we can do this, as there really was a "javaclass"
# module already, and we do not want to Obsolete it by accident
#Obsoletes: python-javaclass

Requires: python2 >= 2.6
Requires: python-cheetah
Requires: PyXML

BuildRequires: python2-devel
BuildRequires: python-cheetah
BuildRequires: coreutils


%description
Tools for inspecting and comparing binary Java class files, JARs, and
JAR-based distributions


%prep
%setup -q


%build
%{__python2} setup.py build


%install
rm -rf %{buildroot}
%{__python2} setup.py install --skip-build --root %{buildroot}


%clean
rm -rf %{buildroot}


%files
%defattr(-,root,root,-)
%doc LICENSE README.md TODO
%{python2_sitelib}/*
%{_bindir}/*


%changelog

* Thu May 23 2013 Christopher O'Brien <obriencj@gmail.com> - 1.3-1
- I think we've sat on these changes long enough, let's make a release
- expand on cheetah html reporting
- requires PyXML for xml.xpath
- renamed to python-javatools as there was already a javaclass
- significantly more testing before tagging a release
- distdiff and distpatchgen now use multiprocessing by default
- removed distpatchgen and javatools.patchgen
- added support for checking runtime annotations
- keep pylint happy

* Thu Jun 14 2012 Christopher O'Brien <obriencj@gmail.com> - 1.2-1
- require python 2.6 and later rather than trying to fight with
  library alternatives
- added classes to compartmentalize distinfo and jarinfo data
- reworked dependency information into a dep tree rather than a simple
  list
- rework options into groups
- fix for modified-utf8 in class constant pools
- added multiple output formats for reports (text, json, html)
- the html output is currently simplified, and will be expanded upon
  later

* Sun May 6 2012 Christopher O'Brien <obriencj@gmail.com> - 1.1-1
- dependency features, license files

* Fri Apr 27 2012 Christopher O'Brien <obriencj@gmail.com> - 1.0-1
- Initial build.
