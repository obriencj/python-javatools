Summary: Tools for inspecting and comparing binary Java class files
Name: python-javaclass
Version: 1.0
Release: 1
License: LGPL
Group: Application/System
URL: https://github.com/obriencj/python-javaclass/
Source0: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root

BuildRequires: python2-devel

%description

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
%doc
%{python_sitelib}/*
%{_bindir}/*


%changelog

* Fri Apr 27 2012 Christopher O'Brien <obriencj@gmail.com> - javaclass-1
- Initial build.

