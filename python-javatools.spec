%global srcproj javatools
%global srcname python-%{srcproj}
%global srcver 1.6.0
%global srcrel 1


# There's two distinct eras of RPM packaging for python, with
# different macros and different expectations. Generally speaking the
# new features are available in RHEL 8+ and Fedora 22+

%define old_rhel ( 0%{?rhel} && 0%{?rhel} < 8 )
%define old_fedora ( 0%{?fedora} && 0%{?fedora} < 22 )

%if %{old_rhel} || %{old_fedora}
  # old python 2.6 support
  %define with_old_python 1
  %undefine with_python2
  %undefine with_python3
%else
  # newer pythons, with cooler macros
  %undefine with_old_python
  %bcond_with python2
  %bcond_without python3
%endif


# we don't generate binaries, let's turn the debuginfo part off
%global debug_package %{nil}


Summary: Tools for inspecting and comparing binary Java class files
Name: %{srcname}
Version: %{srcver}
Release: %{srcrel}%{?dist}
License: LGPLv3
Group: Application/System
URL: https://github.com/obriencj/python-javatools/
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
BuildArch: noarch

Source0: %{srcname}-%{srcver}.tar.gz


%description
Tools for inspecting and comparing binary Java class files, JARs, and
JAR-based distributions


%prep
%setup -q


%build

%if %{with old_python}
  %{__python} setup.py build
%endif

%if %{with python2}
  %py2_build_wheel
%endif

%if %{with python3}
  %py3_build_wheel
%endif


%install
%__rm -rf $RPM_BUILD_ROOT

%if %{with old_python}
  %{__python} setup.py install --skip-build --root %{buildroot}
%endif

%if %{with python2}
  %py2_install_wheel %{srcproj}-%{version}-py2-none-any.whl
%endif

%if %{with python3}
  %py3_install_wheel %{srcproj}-%{version}-py3-none-any.whl
%endif


%clean
rm -rf %{buildroot}


%if %{with old_python}
# package support for older python systems (centos 6, fedora
# 19) with only python 2.6 available.

%package -n python2-%{srcproj}
Summary:        %{summary}
BuildRequires:  python-devel python-setuptools
BuildRequires:  python-cheetah python-six
Requires:	python python-argparse python-setuptools
Requires:       python-cheetah python-six
%{?python_provide:%python_provide python2-%{srcproj}}

%description -n python2-%{srcproj}
Python Java Tools

%files -n python2-%{srcproj}
%defattr(-,root,root,-)
%{python2_sitelib}/javatools/
%{python2_sitelib}/javatools-%{version}.dist-info
%{_bindir}/*

%doc AUTHORS ChangeLog README.md
%license LICENSE

%endif


%if %{with python2}

%package -n python2-%{srcproj}
Summary:        %{summary}
BuildRequires:  python2-devel
BuildRequires:  python2-pip python2-setuptools python2-wheel
BuildRequires:  python2-cheetah python2-six
Requires:	python2 python2-setuptools
Requires:       python2-cheetah python2-six
%{?python_provide:%python_provide python2-%{srcproj}}
%{?py_provides:%py_provides python2-%{srcproj}}

%description -n python2-%{srcproj}
Python Java Tools

%files -n python2-%{srcproj}
%defattr(-,root,root,-)
%{python2_sitelib}/javatools/
%{python2_sitelib}/javatools-%{version}.dist-info
%{_bindir}/*

%doc AUTHORS ChangeLog README.md
%license LICENSE

%endif


%if %{with python3}

%package -n python3-%{srcproj}
Summary:        %{summary}
BuildRequires:  python3-devel
BuildRequires:  python3-pip python3-setuptools python3-wheel
BuildRequires:  python3-cheetah python3-six
Requires:	python3 python3-setuptools
Requires:       python3-cheetah python3-six
%{?python_provide:%python_provide python3-%{srcproj}}
%{?py_provides:%py_provides python3-%{srcproj}}

%description -n python3-%{srcproj}
Python Java Tools

%files -n python3-%{srcproj}
%defattr(-,root,root,-)
%{python3_sitelib}/javatools/
%{python3_sitelib}/javatools-%{version}.dist-info
%{_bindir}/*

%doc AUTHORS ChangeLog README.md
%license LICENSE

%endif


%changelog

* Sun Jul 2 2023 Christopher O'Brien <obriencj@gmail.com> - 1.6.0-0
- version 1.6.0
- m2crypto is runtime optional

* Sun Jun 21 2020 Christopher O'Brien <obriencj@gmail.com> - 1.5.0-1
- version 1.5.0

* Thu Jan 21 2014 Christopher O'Brien <obriencj@gmail.com> - 1.4.0-1
- version 1.4.0
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
