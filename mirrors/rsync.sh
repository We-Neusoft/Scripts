#!/bin/bash

LOCK=/tmp/rsyncing
ROOT=/storage/mirror

[ -f $LOCK ] && exit 0

touch $LOCK

function set_status {
   echo -e "set $1_status 0 0 ${#2} noreply\r\n$2\r" | nc memcache0 11211
   echo $2 > $ROOT/.$1.status
}

function rsync {
   /usr/bin/rsync -aHq $3 --timeout=90 $2 $ROOT/$1/ > /dev/null
}

function rsync_call {
   set_status $1 -1

   case $3 in
   0) rsync $1 $2 "--delete-delay $4"
      ;;
   1) rsync $1 $2 "$4"
      return
      ;;
   2) rsync $1 $2 "--delete-delay"
      ;;
   esac

   RESULT=$?
   set_status $1 $RESULT
   if [ $RESULT -eq 0 ]; then
      /root/shell/count.sh $1 &
   fi
}

function rsync_debian {
   rsync_call $1 $2 $3 "--exclude=\"*Packages*\" --exclude=\"*Sources*\" --exclude=\"*Release\""
}

function rsync_common {
   rsync_call $1 $2 $3 "$4"
}

# centos
rsync_common centos msync.centos.org::CentOS 0
unset RESULT

# epel
rsync_common epel mirrors.ustc.edu.cn::fedora-epel 0
if [ $RESULT -eq 0 ]; then
   /usr/bin/report_mirror > /dev/null
fi
unset RESULT

# atomic
rsync_common atomic www5.atomicorp.com::atomic 0 "--delete-excluded --exclude=fedora/"
unset RESULT

# repoforge
rsync_common repoforge apt.sw.be::pub/freshrpms/pub/dag/ 0
unset RESULT

# kali-images
rsync_debian kali-images archive.kali.org::kali-images 0
unset RESULT

# raspbian
rsync_debian raspbian archive.raspbian.org::archive 0
unset RESULT

# ubuntu-releases
rsync_common ubuntu-releases mirrors.ustc.edu.cn::ubuntu-releases 1
rsync_common ubuntu-releases rsync.releases.ubuntu.com::releases 2
if [ $RESULT -eq 0 ]; then
   date -u > $ROOT/ubuntu-releases/.trace/mirrors.neusoft.edu.cn
fi
unset RESULT

# archlinux
rsync_common archlinux ftp.tku.edu.tw::archlinux 0
unset RESULT

# gentoo
rsync_common gentoo ftp.ussg.iu.edu::gentoo-distfiles 0
unset RESULT

# gentoo-portage
rsync_common gentoo-portage rsync.us.gentoo.org::gentoo-portage 0
unset RESULT

# mariadb
rsync_common mariadb rsync.osuosl.org::mariadb 0
unset RESULT

# pypi
set_status pypi -1
/usr/bin/scl enable python27 "bandersnatch mirror" 2> /dev/null
RESULT=$?
set_status pypi $RESULT
if [ $RESULT -eq 0 ]; then
   /root/shell/count.sh pypi &
fi
unset RESULT

# rubygems
set_status rubygems -1
/usr/bin/gem mirror > /dev/null
RESULT=$?
set_status rubygems $RESULT
if [ $RESULT -eq 0 ]; then
   /root/shell/count.sh rubygems &
fi
unset RESULT

# cygwin
rsync_common cygwin mirrors.kernel.org::sourceware/cygwin/ 0
unset RESULT

# eclipse
rsync_common eclipse download.eclipse.org::eclipseMirror 0
unset RESULT

# putty
rsync_common putty rsync.chiark.greenend.org.uk::ftp/users/sgtatham/putty-website-mirror/ 0
unset RESULT

# android
set_status android -1
/root/shell/android-mirror.py > /dev/null
RESULT=$?
set_status android $RESULT
if [ $RESULT -eq 0 ]; then
   /root/shell/count.sh android &
fi
unset RESULT

# qt
rsync_common qt master.qt-project.org::qt-all 0 "--delete-excluded --exclude=archive/ --exclude=snapshots/"
unset RESULT

# ldp
rsync_common ldp ftp.ibiblio.org::ldp_mirror 0
unset RESULT

# lfs
rsync_common lfs rsync.osuosl.org::lfs 0
unset RESULT

# blfs
rsync_common blfs rsync.osuosl.org::blfs 0
unset RESULT

rm -f $LOCK
