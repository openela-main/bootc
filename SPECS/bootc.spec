%bcond_without check

Name:           bootc
Version:        1.1.0
Release:        1%{?dist}
Summary:        Bootable container system

# Apache-2.0
# Apache-2.0 OR BSL-1.0
# Apache-2.0 OR MIT
# Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT
# BSD-3-Clause
# MIT
# MIT OR Apache-2.0
# Unlicense OR MIT
License:        Apache-2.0 AND BSD-3-Clause AND MIT AND (Apache-2.0 OR BSL-1.0) AND (Apache-2.0 OR MIT) AND (Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT) AND (Unlicense OR MIT)
URL:            https://github.com/containers/bootc
Source0:        %{url}/releases/download/v%{version}/bootc-%{version}.tar.zstd
Source1:        %{url}/releases/download/v%{version}/bootc-%{version}-vendor.tar.zstd

# https://fedoraproject.org/wiki/Changes/EncourageI686LeafRemoval
ExcludeArch:    %{ix86}

BuildRequires: libzstd-devel
BuildRequires: make
BuildRequires: ostree-devel
BuildRequires: openssl-devel
BuildRequires: libzstd-devel
%if 0%{?rhel}
BuildRequires: rust-toolset
%else
BuildRequires: cargo-rpm-macros >= 25
%endif
BuildRequires: systemd

# Backing storage tooling https://github.com/containers/composefs/issues/125
Recommends: composefs
# For OS updates
Requires: skopeo
# For bootloader updates
Recommends: bootupd

%description
%{summary}

%prep
%autosetup -p1 -a1
%if 0%{?rhel}
%cargo_prep -V 1
%else
%cargo_prep -v vendor
%endif

%build
%cargo_build
%if !0%{?rhel}
%cargo_vendor_manifest
%cargo_license_summary
%{cargo_license} > LICENSE.dependencies
%endif

%install
%make_install INSTALL="install -p -c"

%if %{with check}
%check
%cargo_test
%endif

%files
%license LICENSE-MIT
%license LICENSE-APACHE
%if !0%{?rhel}
%license LICENSE.dependencies
%license cargo-vendor.txt
%endif
%doc README.md
%{_bindir}/bootc
%{_prefix}/lib/bootc/
%{_prefix}/lib/systemd/system-generators/*
%{_unitdir}/*
%{_mandir}/man*/bootc*


%changelog
* Thu Oct 17 2024 Joseph Marrero <jmarrero@fedoraproject.org> - 1.1.0-1
- Update to 1.1.0
  Resolves: #RHEL-62891

* Fri Aug 16 2024 Colin Walters <walters@verbum.org> - 0.1.15-1
- Update to 0.1.15
  Resolves: #RHEL-50625

* Thu Jul 25 2024 Joseph Marrero <jmarrero@fedoraproject.org> - 0.1.14-1
- Update to 0.1.14
  Resolves: #RHEL-50625, #RHEL-45325, #RHEL-36003

* Fri Jun 28 2024 Colin Walters <walters@verbum.org> - 0.1.13-2
- Update to 0.1.13

* Tue Jun 25 2024 Colin Walters <walters@verbum.org> - 0.1.12-3
- Update to 0.1.12

* Wed May 15 2024 Colin Walters <walters@verbum.org> - 0.1.11-2
- Update to 0.1.11

* Fri Apr 26 2024 Colin Walters <walters@verbum.org> - 0.1.10-2
- Release 0.1.10

* Mon Apr 08 2024 Colin Walters <walters@verbum.org> - 0.1.9-4
- Correct JIRA link
  Resolves: #RHEL-30878

* Thu Mar 28 2024 Colin Walters <walters@verbum.org> - 0.1.9-3
- Backport rollback
  Related: #RHEL-30466

* Wed Mar 27 2024 Colin Walters <walters@verbum.org> - 0.1.9-2
- https://github.com/containers/bootc/releases/tag/v0.1.9
  Resolves: #RHEL-30466

* Tue Mar 19 2024 Colin Walters <walters@verbum.org> - 0.1.8-2
- https://github.com/containers/bootc/releases/tag/v0.1.8

* Wed Feb 14 2024 Colin Walters <walters@verbum.org> - 0.1.7-4
- https://github.com/containers/bootc/releases/tag/v0.1.7

* Tue Jan 23 2024 Colin Walters <walters@verbum.org> - 0.1.6-2
- https://github.com/containers/bootc/releases/tag/v0.1.6

* Fri Jan 12 2024 Joseph Marrero <jmarrero@redhat.com> - 0.1.5-1
- Update to https://github.com/containers/bootc/releases/tag/v0.1.5

* Thu Jan 11 2024 Colin Walters <walters@verbum.org> - 0.1.4-3
- Loosen composefs requirement until it makes it into c9s

* Mon Dec 11 2023 Colin Walters <walters@verbum.org> - 0.1.4-2
- Initial import from fedora

