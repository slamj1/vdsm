# Copyright 2015-2017 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#

from __future__ import absolute_import
from __future__ import division

import io

from vdsm.common import cmdutils
from vdsm.common import commands
from vdsm.common.libvirtconnection import libvirt_password, SASL_USERNAME

from . import YES, NO, MAYBE


_SASLDBLISTUSERS2 = cmdutils.CommandPath("sasldblistusers2",
                                         "/usr/sbin/sasldblistusers2",
                                         )
_LIBVIRT_SASLDB = "/etc/libvirt/passwd.db"
_SASL2_CONF = "/etc/sasl2/libvirt.conf"
_SASLPASSWD2 = cmdutils.CommandPath("saslpasswd2",
                                    "/usr/sbin/saslpasswd2",
                                    )


def isconfigured():
    ret = passwd_isconfigured()
    if ret == NO:
        return ret
    return libvirt_sasl_isconfigured()


def libvirt_sasl_isconfigured():
    with io.open(_SASL2_CONF, 'r', encoding='utf8') as f:
        lines = f.readlines()
        # check for new default configuration - since libvirt 3.2
        if 'mech_list: gssapi\n' in lines:
            return NO
    return MAYBE


def passwd_isconfigured():
    script = (str(_SASLDBLISTUSERS2), '-f', _LIBVIRT_SASLDB)
    _, out, _ = commands.execCmd(script)
    for user in out:
        if SASL_USERNAME in user:
            return YES
    return NO


def configure():
    configure_libvirt_sasl()
    configure_passwd()


def removeConf():
    if passwd_isconfigured() == YES:
        rc, out, err = commands.execCmd(
            (
                str(_SASLPASSWD2),
                '-p',
                '-a', 'libvirt',
                '-d', SASL_USERNAME,
            ),
        )
        if rc != 0:
            raise RuntimeError("Remove password failed: %s" % (err,))


def configure_libvirt_sasl():
    with io.open(_SASL2_CONF, 'w', encoding='utf8') as f:
        f.writelines([u'## start vdsm-4.20.0 configuration\n',
                      u'mech_list: scram-sha-1\n',
                      u'sasldb_path: %s\n' % (_LIBVIRT_SASLDB),
                      u'## end vdsm configuration']
                     )


def configure_passwd():
    script = (str(_SASLPASSWD2), '-p', '-a', 'libvirt', SASL_USERNAME)
    rc, _, err = commands.execCmd(script, data=libvirt_password())
    if rc != 0:
        raise RuntimeError("Set password failed: %s" % (err,))
