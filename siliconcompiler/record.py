# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

import distro
import getpass
import platform
import psutil
import socket
import time

from datetime import datetime
from enum import Enum

from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import EditableSchema, Parameter, PerNode, Scope
from siliconcompiler.schema.utils import trim

from siliconcompiler import _metadata


class RecordTime(Enum):
    START = "starttime"
    END = "endtime"


class RecordSchema(BaseSchema):
    __TIMEFORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self):
        super().__init__()

        schema_record(self)

    def clear(self, step, index, keep=None):
        if not keep:
            keep = []

        for record in self.getkeys():
            if record in keep:
                continue
            param = self.get(record, field=None)

            if param.get(field='pernode').is_never():
                param.unset()
            else:
                param.unset(step=step, index=index)

    def record_python_packages(self):
        try:
            from pip._internal.operations.freeze import freeze
        except:  # noqa E722
            freeze = None

        if freeze:
            # clear record
            self.set('pythonpackage', [])

            for pkg in freeze():
                self.add('pythonpackage', pkg)

    def record_version(self, step, index):
        self.set('scversion', _metadata.version, step=step, index=index)
        self.set('pythonversion', platform.python_version(), step=step, index=index)

    def record_inputnodes(self, step, index, nodes):
        self.set('inputnode', nodes, step=step, index=index)

    def record_status(self, step, index, status):
        self.set('status', status, step=step, index=index)

    @staticmethod
    def get_cloud_information():
        # TODO: add logic to figure out if we're running on a remote cluster and
        # extract the region in a provider-specific way.
        return {"region": "local"}

    @staticmethod
    def get_ip_information():
        try:
            for interface, addrs in psutil.net_if_addrs().items():
                if interface == 'lo':
                    # don't consider loopback device
                    continue

                if not addrs:
                    # skip missing addrs
                    continue

                use_addr = False
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        if not addr.address.startswith('127.'):
                            use_addr = True
                        break
                    if addr.family == socket.AF_INET6:
                        if addr.address != "::1":
                            use_addr = True
                        break

                if use_addr:
                    ipaddr = None
                    macaddr = None
                    for addr in addrs:
                        if not ipaddr and addr.family == socket.AF_INET:
                            ipaddr = addr.address
                        if not ipaddr and addr.family == socket.AF_INET6:
                            ipaddr = addr.address
                        if not macaddr and addr.family == psutil.AF_LINK:
                            macaddr = addr.address

                    return {"ip": ipaddr, "mac": macaddr}
        except:  # noqa E722
            pass

        return {"ip": None, "mac": None}

    @staticmethod
    def get_machine_information():
        system = platform.system()
        if system == 'Darwin':
            lower_sys_name = 'macos'
        else:
            lower_sys_name = system.lower()

        if system == 'Linux':
            distro_name = distro.id()
        else:
            distro_name = None

        if system == 'Darwin':
            osversion, _, _ = platform.mac_ver()
        elif system == 'Linux':
            osversion = distro.version()
        else:
            osversion = platform.release()

        kernelversion = None
        if system == 'Linux':
            kernelversion = platform.release()
        elif system == 'Windows':
            kernelversion = platform.version()
        elif system == 'Darwin':
            kernelversion = platform.release()

        return {'name': platform.node(),
                'system': lower_sys_name,
                'distro': distro_name,
                'osversion': osversion,
                'kernelversion': kernelversion,
                'arch': platform.machine()}

    @staticmethod
    def get_user_information():
        return {'username': getpass.getuser()}

    def record_userinformation(self, step, index):
        machine_info = RecordSchema.get_machine_information()
        user_info = RecordSchema.get_user_information()
        cloud_info = RecordSchema.get_cloud_information()
        ip_information = RecordSchema.get_ip_information()

        self.set('platform', machine_info['system'], step=step, index=index)
        if machine_info['distro']:
            self.set('distro', machine_info['distro'], step=step, index=index)
        self.set('osversion', machine_info['osversion'], step=step, index=index)
        if machine_info['kernelversion']:
            self.set('kernelversion', machine_info['kernelversion'], step=step, index=index)
        self.set('arch', machine_info['arch'], step=step, index=index)
        self.set('machine', machine_info['name'], step=step, index=index)
        self.set('userid', user_info['username'], step=step, index=index)
        self.set('region', cloud_info['region'], step=step, index=index)

        if ip_information['ip']:
            self.set('ipaddr', ip_information['ip'], step=step, index=index)
        if ip_information['mac']:
            self.set('macaddr', ip_information['mac'], step=step, index=index)

    def record_time(self, step, index, type):
        type = RecordTime(type)

        now = time.time()

        self.set(type.value,
                 datetime.fromtimestamp(now).strftime(RecordSchema.__TIMEFORMAT),
                 step=step, index=index)

        return now

    def get_recorded_time(self, step, index, type):
        type = RecordTime(type)
        return datetime.strptime(
            self.get(type.value, step=step, index=index),
            RecordSchema.__TIMEFORMAT).timestamp()

    def record_toolinformation(self, step, index, version=None, path=None):
        if version:
            self.set('toolversion', version, step=step, index=index)

        if path:
            self.set('toolpath', path, step=step, index=index)

    def record_toolargs(self, step, index, args):
        self.set('toolargs',
                 ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in args),
                 step=step, index=index)

    def record_toolexitcode(self, step, index, code):
        self.set('toolexitcode', code, step=step, index=index)


###########################################################################
# Run Record
###########################################################################
def schema_record(schema):
    schema = EditableSchema(schema)
    records = {'userid': ['userid',
                          'wiley',
                          ''],
               'publickey': ['public key',
                             '<key>',
                             ''],
               'machine': ['machine name',
                           'carbon',
                           '(myhost, localhost, ...'],
               'macaddr': ['MAC address',
                           '<addr>',
                           ''],
               'ipaddr': ['IP address',
                          '<addr>',
                          ''],
               'platform': ['platform name',
                            'linux',
                            '(linux, windows, freebsd)'],
               'distro': ['distro name',
                          'ubuntu',
                          '(ubuntu, redhat, centos)'],
               'arch': ['hardware architecture',
                        'x86_64',
                        '(x86_64, rv64imafdc)'],
               'starttime': ['start time',
                             '\"2021-09-06 12:20:20\"',
                             'Time is reported in the ISO 8601 format YYYY-MM-DD HR:MIN:SEC'],
               'endtime': ['end time',
                           '\"2021-09-06 12:20:20\"',
                           'Time is reported in the ISO 8601 format YYYY-MM-DD HR:MIN:SEC'],
               'region': ['cloud region',
                          '\"US Gov Boston\"',
                          """Recommended naming methodology:

                          * local: node is the local machine
                          * onprem: node in on-premises IT infrastructure
                          * public: generic public cloud
                          * govcloud: generic US government cloud
                          * <region>: cloud and entity specific region string name
                          """],
               'scversion': ['software version',
                             '1.0',
                             """Version number for the SiliconCompiler software."""],
               'toolversion': ['tool version',
                               '1.0',
                               """The tool version captured corresponds to the 'tool'
                               parameter within the 'tool' dictionary."""],
               'toolpath': ['tool path',
                            '/usr/bin/openroad',
                            """Full path to tool executable used to run this
                            task."""],
               'toolargs': ['tool CLI arguments',
                            '\"-I include/ foo.v\"',
                            'Arguments passed to tool via CLI.'],
               'pythonversion': ['Python version',
                                 '3.12.3',
                                 """Version of python used to run this task."""],
               'osversion': ['O/S version',
                             '20.04.1-Ubuntu',
                             """Since there is not standard version system for operating
                             systems, extracting information from is platform dependent.
                             For Linux based operating systems, the 'osversion' is the
                             version of the distro."""],
               'kernelversion': ['O/S kernel version',
                                 '5.11.0-34-generic',
                                 """Used for platforms that support a distinction
                                 between os kernels and os distributions."""]}

    for key, (shorthelp, example, longhelp) in records.items():
        schema.insert(
            key,
            Parameter(
                "str",
                scope=Scope.JOB,
                shorthelp=f"Record: {shorthelp}",
                switch=f"-record_{key} 'step index <str>'",
                example=[
                    f"cli: -record_{key} 'dfm 0 {example}'",
                    f"api: chip.set('record', '{key}', '{example}', step='dfm', index=0)"],
                pernode=PerNode.REQUIRED,
                help=f'Record tracking the {shorthelp} per step and index basis.'
                     f'{" " + trim(longhelp) if longhelp else ""}'
            ))

    schema.insert(
        "toolexitcode",
        Parameter(
            "int",
            scope=Scope.JOB,
            shorthelp="Record: tool exit code",
            switch="-record_toolexitcode 'step index <int>'",
            example=[
                "cli: -record_toolexitcode 'dfm 0 0'",
                "api: chip.set('record', 'toolexitcode', 0, step='dfm', index=0)"],
            pernode=PerNode.REQUIRED,
            help='Record tracking the tool exit code per step and index basis.'
        ))

    # Non-per-node records.
    schema.insert(
        "remoteid",
        Parameter(
            "str",
            scope=Scope.JOB,
            shorthelp="Record: remote job ID",
            switch="-record_remoteid '<str>'",
            example=[
                "cli: -record_remoteid '0123456789abcdeffedcba9876543210'",
                "api: chip.set('record', 'remoteid', '0123456789abcdeffedcba9876543210')"],
            help='Record tracking the job ID for a remote run.'
        ))

    schema.insert(
        "pythonpackage",
        Parameter(
            "[str]",
            scope=Scope.JOB,
            shorthelp="Record: python packages",
            switch="-record_pythonpackage '<str>'",
            example=[
                "cli: -record_pythonpackage 'siliconcompiler==0.28.0'",
                "api: chip.set('record', 'pythonpackage', 'siliconcompiler==0.28.0')"],
            help='Record tracking for the python packages installed.'
        ))

    # flowgraph status
    schema.insert(
        "status",
        Parameter(
            "<pending,queued,running,success,error,skipped,timeout>",  # sync with NodeStatus
            pernode=PerNode.REQUIRED,
            scope=Scope.JOB,
            shorthelp="Record: node execution status",
            switch="-record_status 'step index <str>'",
            example=[
                "cli: -record_status 'syn 0 success'",
                "api: chip.set('record', 'status', 'success', step='syn', index='0')"],
            help="""Record tracking for the status of a node."""
        ))

    # flowgraph select
    schema.insert(
        "inputnode",
        Parameter(
            "[(str,str)]",
            pernode=PerNode.REQUIRED,
            scope=Scope.JOB,
            shorthelp="Record: node inputs",
            switch="-record_inputnode 'step index <(str,str)>'",
            example=[
                "cli: -record_inputnode 'cts 0 (place,42)'",
                "api: chip.set('record', 'inputnode', ('place', '42'), step='syn', index='0')"],
            help=trim("""
            List of selected inputs for the current step/index specified as
            (in_step, in_index) tuple.""")
        ))
