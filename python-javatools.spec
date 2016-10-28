Summary: Tools for inspecting and comparing binary Java class files
Name: python-javatools
Version: 1.5.0
Release: 0
License: LGPL
Group: Application/System
URL: https://github.com/obriencj/python-javatools/
Source0: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
BuildArch: noarch

# Don't believe we can do this, as there really was a "javaclass"
# module already, and we do not want to Obsolete it by accident
#Obsoletes: python-javaclass

Requires: python >= 2.6
Requires: M2Crypto

BuildRequires: python2-devel
BuildRequires: python-setuptools
BuildRequires: coreutils


%description
Tools for inspecting and comparing binary Java class files, JARs, and
JAR-based distributions


%prep
%setup -q


%build
%{__python} setup.py build


%install
rm -rf %{buildroot}
%{__python} setup.py install --skip-build --root %{buildroot}


%clean
rm -rf %{buildroot}


%files
%defattr(-,root,root,-)
%doc AUTHORS ChangeLog LICENSE README.md TODO
%{python2_sitelib}/*
%{_bindir}/*


%changelog

* Fri Oct 28 2016 Marcus LaFerrera (@mlaferrera) - 1.5.0-0
- Added support for Python3
- Removed Cheetah requirements as it is not longer maintained
  breaks support for Python3
- bump to 1.5

* Thu Jan 21 2014 Christopher O'Brien <obriencj@gmail.com> - 1.4.0-0
- bump to 1.4.0
- added ChangeLog as its own file
- move to setuptools

* Thu May 23 2013 Christopher O'Brien <obriencj@gmail.com> - 1.3-1
- bump to 1.3

* Thu Jun 14 2012 Christopher O'Brien <obriencj@gmail.com> - 1.2-1
- require python 2.6 and later

* Sun May 6 2012 Christopher O'Brien <obriencj@gmail.com> - 1.1-1
- dependency features, license files

* Fri Apr 27 2012 Christopher O'Brien <obriencj@gmail.com> - 1.0-1
- Initial build.
