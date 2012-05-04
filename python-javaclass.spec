Summary: Tools for inspecting and comparing binary Java class files
Name: python-javaclass
Version: 1.0
Release: 1
License: LGPL
Group: Application/System
URL: https://github.com/obriencj/python-javaclass/
Source0: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
BuildArch: noarch

Requires: python2
BuildRequires: python2-devel
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
%{__python} setup.py install --record=INSTALLED --root %{buildroot}

%clean
rm -rf %{buildroot}


%files -f INSTALLED
%defattr(-,root,root,-)


%changelog

* Fri Apr 27 2012 Christopher O'Brien <obriencj@gmail.com> - 1.0-1
- Initial build.

