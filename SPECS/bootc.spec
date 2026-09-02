## START: Set by rpmautospec
## (rpmautospec version 0.8.4)
## RPMAUTOSPEC: autorelease, autochangelog
%define autorelease(e:s:pb:n) %{?-p:0.}%{lua:
    release_number = 1;
    base_release_number = tonumber(rpm.expand("%{?-b*}%{!?-b:1}"));
    print(release_number + base_release_number - 1);
}%{?-e:.%{-e*}}%{?-s:.%{-s*}}%{!?-n:%{?dist}}
## END: Set by rpmautospec

%bcond_without check
%bcond_with tests
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

%global rust_minor %(rustc --version | cut -f2 -d" " | cut -f2 -d".")

# https://github.com/bootc-dev/bootc/issues/1640
%if 0%{?fedora} || 0%{?rhel} >= 10 || 0%{?rust_minor} >= 89
    %global new_cargo_macros 1
%else
    %global new_cargo_macros 0
%endif

Name:           bootc
Version:        1.16.4
Release:        %{autorelease}
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
URL:            https://github.com/bootc-dev/bootc
Source0:        %{url}/releases/download/v%{version}/bootc-%{version}.tar.zstd
Source1:        %{url}/releases/download/v%{version}/bootc-%{version}-vendor.tar.zstd

# https://fedoraproject.org/wiki/Changes/EncourageI686LeafRemoval
ExcludeArch:    %{ix86}

BuildRequires: libzstd-devel
BuildRequires: make
BuildRequires: ostree-devel
BuildRequires: openssl-devel
BuildRequires: go-md2man
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
# Keep this list in sync with workspace.metadata.binary-dependencies until we sync
# it automatically
Requires: ostree
Requires: skopeo
Requires: podman
Requires: util-linux-core
Requires: /usr/bin/chcon
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

%if %{with tests}
%package tests
Summary: Integration tests for bootc
Requires: %{name} = %{version}-%{release}

%description tests
This package contains the integration test suite for bootc.
%endif

%global system_reinstall_bootc_install_podman_path %{_prefix}/lib/system-reinstall-bootc/install-podman

%if 0%{?container_build}
# Source is already at /src, no subdirectory
%global _buildsubdir .
%endif

%prep
%if ! 0%{?container_build}
%autosetup -p1 -a1
# Default -v vendor config doesn't support non-crates.io deps (i.e. git)
cp .cargo/vendor-config.toml .
%cargo_prep -N
cat vendor-config.toml >> .cargo/config.toml
rm vendor-config.toml
%else
# Container build: source already at _builddir (/src), nothing to extract
# RPM's %mkbuilddir creates a subdirectory; symlink it back to the source
cd ..
rm -rf %{name}-%{version}-build
ln -s . %{name}-%{version}-build
cd %{name}-%{version}-build
%endif

%build
export SYSTEM_REINSTALL_BOOTC_INSTALL_PODMAN_PATH=%{system_reinstall_bootc_install_podman_path}
# Build this first to avoid feature skew
make manpages

# Build all binaries
%if 0%{?container_build}
# Container build: use cargo directly with cached dependencies to avoid RPM macro overhead
cargo build -j%{_smp_build_ncpus} --release %{?with_rhsm:--features rhsm} --bins
%else
# Non-container build: use RPM macros for proper dependency tracking
%if %new_cargo_macros
    %cargo_build %{?with_rhsm:-f rhsm} -- --bins
%else
    %cargo_build %{?with_rhsm:--features rhsm} -- --bins
%endif
%endif

%if ! 0%{?container_build}
%cargo_vendor_manifest
# https://pagure.io/fedora-rust/rust-packaging/issue/33
sed -i -e '/https:\/\//d' cargo-vendor.txt
%cargo_license_summary
%{cargo_license} > LICENSE.dependencies
%endif

%install
# Pass CARGO_FEATURES explicitly to prevent auto-detection rebuild in install environment
%make_install INSTALL="install -p -c" CARGO_FEATURES="%{?with_rhsm:rhsm}"
%if %{with ostree_ext}
make install-ostree-hooks DESTDIR=%{?buildroot}
%endif
%if %{with tests}
install -D -m 0755 target/release/tests-integration %{buildroot}%{_bindir}/bootc-integration-tests
%endif
mkdir -p %{buildroot}/%{dirname:%{system_reinstall_bootc_install_podman_path}}
cat >%{?buildroot}/%{system_reinstall_bootc_install_podman_path} <<EOF
#!/bin/bash
exec dnf -y install podman
EOF
chmod +x %{?buildroot}/%{system_reinstall_bootc_install_podman_path}
# generate doc file list excluding directories; workaround for
# https://github.com/coreos/rpm-ostree/issues/5420
touch %{?buildroot}/%{_docdir}/bootc/baseimage/base/sysroot/.keepdir
find %{?buildroot}/%{_docdir} ! -type d -printf '%{_docdir}/%%P\n' | sort > bootcdoclist.txt

rm -f %{buildroot}/%{_datadir}/elvish/lib/bootc.elv
rm -f %{buildroot}/%{_datadir}/powershell/Modules/Bootc/Bootc.psm1

%if %{with check}
%check
if grep -qEe 'Seccomp:.*0$' /proc/self/status; then
    %cargo_test
else
    echo "skipping unit tests due to https://github.com/rpm-software-management/mock/pull/1613#issuecomment-3421908652"
fi
%endif

%files -f bootcdoclist.txt
%license LICENSE-MIT
%license LICENSE-APACHE
%if ! 0%{?container_build}
%license LICENSE.dependencies
%license cargo-vendor.txt
%endif
%doc README.md
%{_bindir}/bootc
%{_prefix}/lib/bootc/
%{_prefix}/lib/systemd/system-generators/*
%{_prefix}/lib/dracut/modules.d/51bootc/
%if %{with ostree_ext}
%{_prefix}/libexec/libostree/ext/*
%endif
%{_unitdir}/*
%{_mandir}/man*/*bootc*
%if 0%{?rhel} && 0%{?rhel} <= 9
%{_datadir}/bash-completion/completions/bootc
%{_datadir}/zsh/site-functions/_bootc
%{_datadir}/fish/vendor_completions.d/bootc.fish
%else
%{bash_completions_dir}/bootc
%{zsh_completions_dir}/_bootc
%{fish_completions_dir}/bootc.fish
%endif

%files -n system-reinstall-bootc
%{_bindir}/system-reinstall-bootc
%{system_reinstall_bootc_install_podman_path}

%if %{with tests}
%files tests
%{_bindir}/bootc-integration-tests
%endif

%changelog
## START: Generated by rpmautospec
* Wed Jul 22 2026 ckyrouac <ckyrouac@redhat.com> - 1.16.4-1
- spec: new upstream version 1.16.4

* Tue May 05 2026 Joseph Marrero Corchado <jmarrero@redhat.com> - 1.15.2-1
- Release 1.15.2

* Tue Apr 14 2026 Joseph Marrero Corchado <jmarrero@redhat.com> - 1.15.1-1
- Release 1.15.1

* Fri Mar 20 2026 Colin Walters <walters@verbum.org> - 1.14.1-1
- Update to 1.14.1

* Tue Feb 24 2026 Colin Walters <walters@verbum.org> - 1.13.0-1
- Release 1.13.0
- Update to bootc 1.13.0
- Pass CARGO_FEATURES explicitly to make install to prevent auto-detection
  rebuild in install environment (workaround for upstream Makefile issue)
- Package shell completions (bash, zsh, fish)

* Mon Jan 19 2026 Xiaofeng Wang <xiaofwan@redhat.com> - 1.12.1-2
- Skip rpminspect checking for symbolic link /usr/lib/bootc/storage

* Fri Jan 16 2026 Colin Walters <walters@verbum.org> - 1.12.1-1
- Release 1.12.1

* Fri Jan 09 2026 Colin Walters <walters@verbum.org> - 1.12.0-1
- Release 1.12.0

* Tue Dec 09 2025 Joseph Marrero Corchado <jmarrero@redhat.com> - 1.11.0-1
- Release 1.11.0

* Wed Nov 05 2025 Xiaofeng Wang <xiaofwan@redhat.com> - 1.10.0-2
- Fix gating test

* Fri Oct 31 2025 Joseph Marrero Corchado <jmarrero@redhat.com> - 1.10.0-1
- Release 1.10.0

* Fri Sep 05 2025 Colin Walters <walters@verbum.org> - 1.8.0-1
- Rebase to 1.8.0

* Tue Aug 26 2025 Joseph Marrero Corchado <jmarrero@redhat.com> - 1.7.1-1
- Release 1.7.1

* Fri Aug 22 2025 Joseph Marrero Corchado <jmarrero@redhat.com> - 1.7.0-1
- Release 1.7.0

* Fri Aug 08 2025 Xiaofeng Wang <xiaofwan@redhat.com> - 1.5.1-2
- Add 0001-bootc-inistall-provision.patch for TF 2025-06.1 change

* Tue Jul 22 2025 gursewak1997 <gursmangat@gmail.com> - 1.5.1-1
- Release 1.5.1

* Tue Jul 15 2025 gursewak1997 <gursmangat@gmail.com> - 1.4.0-2
- Add integration test patch back for RHEL support

* Fri Jul 11 2025 gursewak1997 <gursmangat@gmail.com> - 1.4.0-1
- Release 1.4.0

* Fri May 30 2025 Xiaofeng Wang <xiaofwan@redhat.com> - 1.3.0-2
- Enable gating test

* Fri May 30 2025 Joseph Marrero Corchado <jmarrero@redhat.com> - 1.3.0-1
- Release 1.3.0

* Tue Apr 15 2025 John Eckersberg <jeckersb@redhat.com> - 1.1.7-1
- Release 1.1.7

* Thu Mar 06 2025 Joseph Marrero Corchado <jmarrero@redhat.com> - 1.1.6-2
- Backport https://github.com/containers/bootc/pull/1167

* Mon Mar 03 2025 Colin Walters <walters@verbum.org> - 1.1.6-1
- Update to 1.1.6

* Wed Feb 19 2025 John Eckersberg <jeckersb@redhat.com> - 1.1.5-2
- resync specfile from upstream

* Mon Feb 10 2025 Joseph Marrero Corchado <jmarrero@redhat.com> - 1.1.5-1
- Rebase to bootc 1.1.5

* Thu Jan 23 2025 John Eckersberg <jeckersb@redhat.com> - 1.1.4-3
- Cherry pick patch for bootc-status-updated-onboot

* Tue Jan 21 2025 Colin Walters <walters@verbum.org> - 1.1.4-2
- Cherry pick patch for bootc-status-updated

* Wed Jan 15 2025 Joseph Marrero Corchado <jmarrero@redhat.com> - 1.1.4-1
- Release bootc 1.1.4

* Fri Jan 03 2025 Colin Walters <walters@verbum.org> - 1.1.3-4
- Reapply "Flip bcond ostree_ext on"

* Fri Jan 03 2025 Colin Walters <walters@verbum.org> - 1.1.3-3
- Revert "Flip bcond ostree_ext on"

* Thu Jan 02 2025 Colin Walters <walters@verbum.org> - 1.1.3-2
- Flip bcond ostree_ext on

* Thu Jan 02 2025 Colin Walters <walters@verbum.org> - 1.1.3-1
- Update to 1.1.3

* Thu Jan 02 2025 Colin Walters <walters@verbum.org> - 1.1.2-2
- Add a bcond with ostree_ext

* Thu Nov 07 2024 Joseph Marrero Corchado <jmarrero@redhat.com> - 1.1.2-1
- Upgrade to 1.1.2

* Tue Oct 29 2024 Troy Dawson <tdawson@redhat.com> - 1.1.0-2
- Bump release for October 2024 mass rebuild:

* Thu Oct 17 2024 Joseph Marrero Corchado <jmarrero@redhat.com> - 1.1.0-1
- Upgrade to 1.1.0

* Fri Sep 20 2024 Joseph Marrero Corchado <jmarrero@redhat.com> - 0.1.16-2
- rebuild

* Thu Sep 12 2024 Colin Walters <walters@verbum.org> - 0.1.16-1
- https://github.com/containers/bootc/releases/tag/v0.1.16

* Fri Aug 16 2024 Colin Walters <walters@verbum.org> - 0.1.15-1
- Update to 0.1.15

* Thu Jul 25 2024 Joseph Marrero <jmarrero@redhat.com> - 0.1.14-1
- Update to 0.1.14

* Fri Jun 28 2024 Colin Walters <walters@verbum.org> - 0.1.13-1
- Update to 0.1.13

* Wed Jun 26 2024 Wei Shi <wshi@redhat.com> - 0.1.12-2
- Add gating test for c10s

* Tue Jun 25 2024 Colin Walters <walters@verbum.org> - 0.1.12-1
- Release 0.1.12

* Mon Jun 24 2024 Troy Dawson <tdawson@redhat.com> - 0.1.11-2
- Bump release for June 2024 mass rebuild

* Sat Jun 08 2024 Colin Walters <walters@verbum.org> - 0.1.11-1
- bootc: Update to 0.1.11

* Thu Feb 01 2024 Yaakov Selkowitz <yselkowi@redhat.com> - 0.1.6-3
- Update Rust macro usage

* Tue Jan 23 2024 Colin Walters <walters@verbum.org> - 0.1.6-2
- Update %%files section

* Tue Jan 23 2024 Colin Walters <walters@verbum.org> - 0.1.6-1
- https://github.com/containers/bootc/releases/tag/v0.1.6

* Tue Jan 23 2024 Fedora Release Engineering <releng@fedoraproject.org> - 0.1.5-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_40_Mass_Rebuild

* Fri Jan 19 2024 Fedora Release Engineering <releng@fedoraproject.org> - 0.1.5-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_40_Mass_Rebuild

* Tue Dec 19 2023 Colin Walters <walters@verbum.org> - 0.1.5-1
- https://github.com/containers/bootc/releases/tag/v0.1.5

* Mon Dec 11 2023 Colin Walters <walters@verbum.org> - 0.1.4-3
- ExcludeArch: %%{ix86}

* Tue Dec 05 2023 Colin Walters <walters@verbum.org> - 0.1.4-2
- Requires: composefs

* Fri Nov 10 2023 Colin Walters <walters@verbum.org> - 0.1.4-1
- Update to 0.1.4

* Wed Nov 08 2023 Yaakov Selkowitz <yselkowi@redhat.com> - 0.1.3-2
- Fix build with rust-toolset

* Mon Nov 06 2023 Colin Walters <walters@verbum.org> - 0.1.3-1
- local build

* Tue Oct 24 2023 Colin Walters <walters@verbum.org> - 0.1.2-3
- Add Recommends: bootupd

* Sat Oct 21 2023 Colin Walters <walters@verbum.org> - 0.1.2-2
- Add a requirement on skopeo

* Sat Oct 21 2023 Colin Walters <walters@verbum.org> - 0.1.2-1
- Initial import
## END: Generated by rpmautospec
