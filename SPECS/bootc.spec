%bcond_without check
%if 0%{?rhel} >= 9 || 0%{?fedora} > 41
    %bcond_without ostree_ext
%else
    %bcond_with ostree_ext
%endif

%if 0%{?rhel}
    %bcond_without rhsm
%else
    %bcond_with rhsm
%endif

Name:           bootc
Version:        1.8.0
Release:        3%{?dist}
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

# Don't remove, downstream patch only
# Patch for integration test RHEL 9.x and 10.x support
Patch0: 0000-bootc-inistall-provision.patch
Patch1: 0001-bootc-inistall-provision.patch

# https://fedoraproject.org/wiki/Changes/EncourageI686LeafRemoval
ExcludeArch:    %{ix86}

BuildRequires: libzstd-devel
BuildRequires: make
BuildRequires: ostree-devel
BuildRequires: openssl-devel
%if 0%{?rhel}
BuildRequires: rust-toolset
%else
BuildRequires: cargo-rpm-macros >= 25
%endif
BuildRequires: systemd
# For tests
BuildRequires: skopeo ostree

# Backing storage tooling https://github.com/containers/composefs/issues/125
Requires: composefs
# For OS updates
Requires: ostree
Requires: skopeo
Requires: podman
# For bootloader updates
Recommends: bootupd

# A made up provides so that rpm-ostree can depend on it
%if %{with ostree_ext}
Provides: ostree-cli(ostree-container)
%endif

%description
%{summary}

# (-n because we don't want the subpackage name to start with bootc-)
%package -n system-reinstall-bootc
Summary: Utility to reinstall the current system using bootc
Recommends: podman
# The reinstall subpackage intentionally does not require bootc, as it pulls in many unnecessary dependencies

%description -n system-reinstall-bootc
This package provides a utility to simplify reinstalling the current system to a given bootc image.

%global system_reinstall_bootc_install_podman_path %{_prefix}/lib/system-reinstall-bootc/install-podman

%prep
%autosetup -p1 -a1
# Default -v vendor config doesn't support non-crates.io deps (i.e. git)
cp .cargo/vendor-config.toml .
%cargo_prep -N
cat vendor-config.toml >> .cargo/config.toml
rm vendor-config.toml

%build
# Build the main bootc binary
%if 0%{?fedora} || 0%{?rhel} >= 10
    %cargo_build %{?with_rhsm:-f rhsm}
%else
    %cargo_build %{?with_rhsm:--features rhsm}
%endif

# Build the system reinstallation CLI binary
%global cargo_args -p system-reinstall-bootc
export SYSTEM_REINSTALL_BOOTC_INSTALL_PODMAN_PATH=%{system_reinstall_bootc_install_podman_path}
%if 0%{?fedora} || 0%{?rhel} >= 10
    # In cargo-rpm-macros, the cargo_build macro does flag processing,
    # so we need to pass '--' to signify that cargo_args is not part
    # of the macro args
    %cargo_build -- %cargo_args
%else
    # Older macros from rust-toolset do *not* do flag processing, so
    # '--' would be passed through to cargo directly, which is not
    # what we want.
    %cargo_build %cargo_args
%endif

%cargo_vendor_manifest
# https://pagure.io/fedora-rust/rust-packaging/issue/33
sed -i -e '/https:\/\//d' cargo-vendor.txt
%cargo_license_summary
%{cargo_license} > LICENSE.dependencies

%install
%make_install INSTALL="install -p -c"
%if %{with ostree_ext}
make install-ostree-hooks DESTDIR=%{?buildroot}
%endif
mkdir -p %{buildroot}/%{dirname:%{system_reinstall_bootc_install_podman_path}}
cat >%{?buildroot}/%{system_reinstall_bootc_install_podman_path} <<EOF
#!/bin/bash
exec dnf -y install podman
EOF
chmod +x %{?buildroot}/%{system_reinstall_bootc_install_podman_path}

%if %{with check}
%check
%cargo_test
%endif

%files
%license LICENSE-MIT
%license LICENSE-APACHE
%license LICENSE.dependencies
%license cargo-vendor.txt
%doc README.md
%{_bindir}/bootc
%{_prefix}/lib/bootc/
%{_prefix}/lib/systemd/system-generators/*
%if %{with ostree_ext}
%{_prefix}/libexec/libostree/ext/*
%endif
%{_unitdir}/*
%{_docdir}/bootc/*
%{_mandir}/man*/bootc*

%files -n system-reinstall-bootc
%{_bindir}/system-reinstall-bootc
%{system_reinstall_bootc_install_podman_path}

%changelog
* Wed Sep 10 2025 Joseph Marrero <jmarrero@fedoraproject.org> - 1.8.0-3
- Bump release as rhpkg needed an update to tag for 9.7.z
  Resolves: #RHEL-113361

* Fri Sep 05 2025 Colin Walters <walters@verbum.org> - 1.8.0-2
- Update to 1.8.0

* Thu Aug 21 2025 Joseph Marrero <jmarrero@fedoraproject.org> - 1.7.0-1
- Update to 1.7.0
- Resolves: #RHEL-109555

* Fri Jul 22 2025 Gursewak Mangat <gurssing@redhat.com> - 1.5.1-1
- Update to 1.5.1
- Resolves: #RHEL-104335

* Fri Jul 11 2025 Gursewak Mangat <gurssing@redhat.com> - 1.4.0-1
- Update to 1.4.0
- Resolves: #RHEL-103125

* Fri May 30 2025 Joseph Marrero <jmarrero@fedoraproject.org> - 1.3.0-1
- Update to 1.3.0
- Resolves: #RHEL-94597

* Tue Apr 15 2025 John Eckersberg <jeckersb@redhat.com> - 1.1.7-1
- Update to 1.1.7
- Resolves: #RHEL-87207

* Thu Mar 06 2025 Joseph Marrero <jmarrero@fedoraproject.org> - 1.1.6-3
- Backport https://github.com/containers/bootc/pull/1167
- Resolves: #RHEL-82293

* Wed Feb 19 2025 John Eckersberg <jeckersb@redhat.com> - 1.1.5-2
- Sync specfile from upstream
- Resolves: #RHEL-80264
- Resolves: #RHEL-81981

* Mon Feb 10 2025 Joseph Marrero <jmarrero@fedoraproject.org> - 1.1.5-1
- Update to 1.1.5
- Resolves: #RHEL-77733

* Thu Jan 23 2025 John Eckersberg <jeckersb@redhat.com> - 1.1.4-2
- Cherry pick patches for bootc-status-updated
- Resolves: #RHEL-72862

* Tue Jan 14 2025 Joseph Marrero <jmarrero@fedoraproject.org> - 1.1.4-1
- Update to 1.1.4
  Resolves: #RHEL-72862

* Thu Nov 07 2024 Joseph Marrero <jmarrero@fedoraproject.org> - 1.1.2-1
- Update to 1.1.2
  Resolves: #RHEL-66258

* Thu Oct 17 2024 Joseph Marrero <jmarrero@fedoraproject.org> - 1.1.0-1
- Update to 1.1.0
  Resolves: #RHEL-63018

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

