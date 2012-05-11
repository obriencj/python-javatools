Summary: Tools for inspecting and comparing binary Java class files
Name: python-javaclass
Version: 1.2
Release: 1
License: LGPL
Group: Application/System
URL: https://github.com/obriencj/python-javaclass/
Source0: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
BuildArch: noarch

Requires: python2 >= 2.6
BuildRequires: python2-devel
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
%doc LICENSE README TODO
%{python2_sitelib}/*
%{_bindir}/*


%changelog

* Fri May 11 2012 Christopher O'Brien <obriencj@gmail.com> - 1.2-1
- require python 2.6 and later rather than trying to fight with
  library alternatives
- added classes to compartmentalize distinfo and jarinfo data
- reworked dependency information into a dep tree rather than a simple
  list

* Sun May 6 2012 Christopher O'Brien <obriencj@gmail.com> - 1.1-1
- dependency features, license files

* Fri Apr 27 2012 Christopher O'Brien <obriencj@gmail.com> - 1.0-1
- Initial build.
