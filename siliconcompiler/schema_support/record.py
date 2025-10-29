# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

import distro
import getpass
import platform
import psutil
import shlex
import socket

from typing import Dict, Union, List, Optional, Set, Tuple

from datetime import datetime, timezone
from enum import Enum

from siliconcompiler.schema import BaseSchema, LazyLoad
from siliconcompiler.schema import EditableSchema, Parameter, PerNode, Scope
from siliconcompiler.schema.utils import trim

from siliconcompiler import _metadata


class RecordTime(Enum):
    """
    Enumeration of time record types.
    """
    START = "starttime"
    END = "endtime"


class RecordTool(Enum):
    """
    Enumeration of tool record types.
    """
    EXITCODE = "toolexitcode"
    VERSION = "toolversion"
    PATH = "toolpath"
    ARGS = "toolargs"


class RecordSchema(BaseSchema):
    """
    A class for managing run record data.
    """
    __TIMEFORMAT = "%Y-%m-%d %H:%M:%S.%f"

    def __init__(self):
        """
        Initializes the RecordSchema object.
        """
        super().__init__()

        schema_record(self)

    def _from_dict(self, manifest: Dict,
                   keypath: Union[List[str], Tuple[str, ...]],
                   version: Optional[Tuple[int, ...]] = None,
                   lazyload: LazyLoad = LazyLoad.ON) \
            -> Tuple[Set[Tuple[str, ...]], Set[Tuple[str, ...]]]:
        """
        Constructs a schema from a dictionary.

        Args:
            manifest (dict): Dictionary to construct from.
            keypath (list): List of keys representing the path to the current dictionary.
            version (str, optional): Version of the manifest. Defaults to None.

        Returns:
            dict: The constructed dictionary.
        """
        ret = super()._from_dict(manifest, keypath, version=version, lazyload=lazyload)

        # Correct for change specification
        if not lazyload.is_enforced and version and version < (0, 50, 4):
            for timekey in RecordTime:
                start_param = self.get(timekey.value, field=None)
                for value, step, index in start_param.getvalues():
                    start_param.set(f"{value}.000000", step=step, index=index)

        return ret

    def clear(self, step: str, index: Union[str, int], keep: Optional[List[str]] = None) -> None:
        '''
        Clear all saved metrics for a given step and index.

        Args:
            step (str): Step name to clear.
            index (str or int): Index name to clear.
            keep (list of str): list of records to keep.
        '''

        if not keep:
            keep = []

        for record in self.getkeys():
            if record in keep:
                continue
            param: Parameter = self.get(record, field=None)

            if param.get(field='pernode').is_never():
                param.unset()
            else:
                param.unset(step=step, index=index)

    def record_python_packages(self) -> None:
        '''
        Record the python packages currently available in the environment.
        '''
        try:
            from pip._internal.operations.freeze import freeze
        except:  # noqa E722
            freeze = None

        if freeze:
            # clear record
            self.set('pythonpackage', [])

            for pkg in freeze():
                self.add('pythonpackage', pkg)

    def record_version(self, step: str, index: Union[str, int]) -> None:
        '''
        Records the versions for SiliconCompiler and python.

        Args:
            step (str): Step name to associate.
            index (str or int): Index name to associate.
        '''
        self.set('scversion', _metadata.version, step=step, index=index)
        self.set('pythonversion', platform.python_version(), step=step, index=index)

    @staticmethod
    def get_cloud_information() -> Dict[str, Optional[str]]:
        '''
        Return information about the cloud environment.

        Returns:
            {
            "region": str
            }
        '''
        # TODO: add logic to figure out if we're running on a remote cluster and
        # extract the region in a provider-specific way.
        return {"region": "local"}

    @staticmethod
    def get_ip_information() -> Dict[str, Optional[str]]:
        '''
        Return information about the ip and mac address of this machine.

        Returns:
            {
            "ip": str,
            "mac": str
            }
        '''
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
    def get_machine_information() -> Dict[str, Optional[str]]:
        '''
        Return information about the machine.

        Returns:
            {
            "name": str,
            "system": str,
            "distro": str,
            "osversion": str,
            "kernelversion": str,
            "arch": str
            }
        '''
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
    def get_user_information() -> Dict[str, Optional[str]]:
        '''
        Return information about the user.

        Return format: {"username": str}
        '''
        return {'username': getpass.getuser()}

    def record_userinformation(self, step: str, index: Union[str, int]) -> None:
        '''
        Records information about the current machine and user.
        Uses information from :meth:`get_machine_information`, :meth:`get_user_information`,
        :meth:`get_cloud_information`, and :meth:`get_ip_information`.

        Args:
            step (str): Step name to associate.
            index (str or int): Index name to associate.
        '''
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

    def record_time(self, step: str, index: Union[str, int], type: RecordTime) -> float:
        '''
        Record the time of the record.

        Returns:
            time recorded.

        Args:
            step (str): Step name to associate.
            index (str or int): Index name to associate.
            type (:class:`RecordTime`): type of time to record
        '''
        type = RecordTime(type)

        now = datetime.now(timezone.utc)

        self.set(type.value,
                 now.strftime(RecordSchema.__TIMEFORMAT),
                 step=step, index=index)

        return now.timestamp()

    def get_recorded_time(self, step: str, index: Union[str, int],
                          type: RecordTime) -> Optional[float]:
        '''
        Returns the time recorded for a given record, or None if nothing is recorded.

        Args:
            step (str): Step name to associate.
            index (str or int): Index name to associate.
            type (:class:`RecordTime`): type of time to record
        '''
        type = RecordTime(type)
        record_time: Optional[str] = self.get(type.value, step=step, index=index)
        if record_time is None:
            return None

        return datetime.strptime(
            record_time+"+0000",
            RecordSchema.__TIMEFORMAT+"%z").timestamp()

    def get_earliest_time(self, type: RecordTime) -> Optional[float]:
        '''
        Returns the earliest recorded time.

        Args:
            type (:class:`RecordTime`): type of time to record
        '''
        type = RecordTime(type)
        record_param = self.get(type.value, field=None)

        times = set()
        for _, step, index in record_param.getvalues():
            times.add(self.get_recorded_time(step, index, type))

        if not times:
            return None

        return min(times)

    def get_latest_time(self, type: RecordTime) -> Optional[float]:
        '''
        Returns the last recorded time.

        Args:
            type (:class:`RecordTime`): type of time to record
        '''
        type = RecordTime(type)
        record_param: Parameter = self.get(type.value, field=None)

        times = set()
        for _, step, index in record_param.getvalues():
            times.add(self.get_recorded_time(step, index, type))

        if not times:
            return None

        return max(times)

    def record_tool(self, step: str, index: Union[str, int],
                    info: Union[str, List[str], int], type: RecordTool) -> None:
        '''
        Record information about the tool used during this record.

        Args:
            step (str): Step name to associate.
            index (str or int): Index name to associate.
            info (any): Information to record.
            type (:class:`RecordTool`): type of tool information being recorded
        '''
        if type == RecordTool.ARGS:
            info = shlex.join(info)
        self.set(type.value, info, step=step, index=index)

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the meta data for getdict
        """

        return RecordSchema.__name__


###########################################################################
# Run Record
###########################################################################
def schema_record(schema):
    """
    Adds record schema parameters to the given schema.

    Args:
        schema (EditableSchema): The schema to modify.
    """
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
                             '\"2021-09-06 12:20:20.000000\"',
                             'Time is recorded with the format YYYY-MM-DD HR:MIN:SEC.MICROSEC for '
                             'UTC'],
               'endtime': ['end time',
                           '\"2021-09-06 12:20:20.000000\"',
                           'Time is recorded with the format YYYY-MM-DD HR:MIN:SEC.MICROSEC for '
                           'UTC'],
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
                    f"api: schema.set('record', '{key}', '{example}', step='dfm', index=0)"],
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
                "api: schema.set('record', 'toolexitcode', 0, step='dfm', index=0)"],
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
                "api: schema.set('record', 'remoteid', '0123456789abcdeffedcba9876543210')"],
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
                "api: schema.set('record', 'pythonpackage', 'siliconcompiler==0.28.0')"],
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
                "api: schema.set('record', 'status', 'success', step='syn', index='0')"],
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
                "api: schema.set('record', 'inputnode', ('place', '42'), step='syn', index='0')"],
            help=trim("""
            List of selected inputs for the current step/index specified as
            (in_step, in_index) tuple.""")
        ))
