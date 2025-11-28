from typing import Union, List, Tuple, Callable, Dict, Optional, Final

from siliconcompiler.schema import BaseSchema, EditableSchema, Parameter, Scope, PerNode
from siliconcompiler.schema.utils import trim
from siliconcompiler.utils.multiprocessing import MPManager


class SchedulerSchema(BaseSchema):
    """
    Schema for configuring job scheduler settings.

    This class defines all parameters related to the job scheduler, such as
    the scheduler type, resource constraints (cores, memory), and notification
    settings. It provides getter and setter methods for each parameter to
    allow for easy manipulation of the configuration.
    """
    def __init__(self):
        """Initializes the scheduler schema and defines all its parameters."""
        super().__init__()

        # Initialize schema
        schema = EditableSchema(self)

        # job scheduler
        schema.insert(
            'name',
            Parameter(
                '<slurm,lsf,sge,docker>',
                scope=Scope.GLOBAL,
                pernode=PerNode.OPTIONAL,
                shorthelp="Option: scheduler platform",
                switch="-scheduler <str>",
                example=[
                    "cli: -scheduler slurm",
                    "api: option.set('name', 'slurm')"],
                help="""
                Sets the type of job scheduler to be used for each individual
                flowgraph steps. If the parameter is undefined, the steps are executed
                on the same machine that the SC was launched on. If 'slurm' is used,
                the host running the 'sc' command must be running a 'slurmctld' daemon
                managing a Slurm cluster. Additionally, the build directory
                (:keypath:`option,builddir`) must be located in shared storage which
                can be accessed by all hosts in the cluster."""))

        schema.insert(
            'cores',
            Parameter(
                'int',
                scope=Scope.GLOBAL,
                pernode=PerNode.OPTIONAL,
                shorthelp="Option: Scheduler core constraint",
                switch="-cores <int>",
                example=["cli: -cores 48",
                         "api: option.set('cores', 48)"],
                help="""
                Specifies the number CPU cores required to run the job.
                For the slurm scheduler, this translates to the '-c'
                switch. For more information, see the job scheduler
                documentation"""))

        schema.insert(
            'memory',
            Parameter(
                'int',
                unit='MB',
                scope=Scope.GLOBAL,
                pernode=PerNode.OPTIONAL,
                shorthelp="Option: scheduler memory constraint",
                switch="-memory <int>",
                example=["cli: -memory 8000",
                         "api: option.set('memory', 8000)"],
                help="""
                Specifies the amount of memory required to run the job,
                specified in MB. For the slurm scheduler, this translates to
                the '--mem' switch. For more information, see the job
                scheduler documentation"""))

        schema.insert(
            'queue',
            Parameter(
                'str',
                scope=Scope.GLOBAL,
                pernode=PerNode.OPTIONAL,
                shorthelp="Option: scheduler queue",
                switch="-queue <str>",
                example=["cli: -queue nightrun",
                         "api: option.set('queue', 'nightrun')"],
                help="""
                Send the job to the specified queue. With slurm, this
                translates to 'partition'. The queue name must match
                the name of an existing job scheduler queue. For more information,
                see the job scheduler documentation"""))

        schema.insert(
            'defer',
            Parameter(
                'str',
                scope=Scope.GLOBAL,
                pernode=PerNode.OPTIONAL,
                shorthelp="Option: scheduler start time",
                switch="-defer <str>",
                example=["cli: -defer 16:00",
                         "api: option.set('defer', '16:00')"],
                help="""
                Defer initiation of job until the specified time. The parameter
                is pass through string for remote job scheduler such as slurm.
                For more information about the exact format specification, see
                the job scheduler documentation. Examples of valid slurm specific
                values include: now+1hour, 16:00, 010-01-20T12:34:00. For more
                information, see the job scheduler documentation."""))

        schema.insert(
            'options',
            Parameter(
                '[str]',
                scope=Scope.GLOBAL,
                pernode=PerNode.OPTIONAL,
                shorthelp="Option: scheduler arguments",
                switch="-scheduler_options <str>",
                example=[
                    "cli: -scheduler_options \"--pty\"",
                    "api: option.set('options', \"--pty\")"],
                help="""
                Advanced/export options passed through unchanged to the job
                scheduler as-is. (The user specified options must be compatible
                with the rest of the scheduler parameters entered.(memory etc).
                For more information, see the job scheduler documentation."""))

        schema.insert(
            'msgevent',
            Parameter(
                '{<all,summary,begin,end,timeout,fail>}',
                scope=Scope.GLOBAL,
                pernode=PerNode.OPTIONAL,
                shorthelp="Option: message event trigger",
                switch="-msgevent <str>",
                example=[
                    "cli: -msgevent all",
                    "api: option.set('msgevent', 'all')"],
                help="""
                Directs job scheduler to send a message to the user in
                :keypath:`option,scheduler,msgcontact` when certain events occur
                during a task.

                * fail: send an email on failures
                * timeout: send an email on timeouts
                * begin: send an email at the start of a node task
                * end: send an email at the end of a node task
                * summary: send a summary email at the end of the run
                * all: send an email on any event
                """))

        schema.insert(
            'msgcontact',
            Parameter(
                '{str}',
                scope=Scope.GLOBAL,
                pernode=PerNode.OPTIONAL,
                shorthelp="Option: message contact",
                switch="-msgcontact <str>",
                example=[
                    "cli: -msgcontact 'wile.e.coyote@acme.com'",
                    "api: option.set('msgcontact', 'wiley@acme.com')"],
                help="""
                List of email addresses to message on a :keypath:`option,scheduler,msgevent`.
                Support for email messages relies on job scheduler daemon support.
                For more information, see the job scheduler documentation. """))

        schema.insert(
            'maxnodes',
            Parameter(
                'int',
                scope=Scope.GLOBAL,
                shorthelp="Option: maximum concurrent nodes",
                switch="-maxnodes <int>",
                example=["cli: -maxnodes 4",
                          "api: option.set('maxnodes', 4)"],
                help="""
                Maximum number of concurrent nodes to run in a job. If not set this will default
                to the number of cpu cores available."""))

        schema.insert(
            'maxthreads',
            Parameter(
                'int',
                scope=Scope.GLOBAL,
                shorthelp="Option: maximum number of threads to assign a task",
                example=["api: option.set('maxthreads', 4)"],
                help="""
                Maximum number of threads for each task in a job. If not set this will default
                to the number of cpu cores available."""))

    def get_name(self, step: Optional[str] = None, index: Optional[str] = None) -> str:
        """Gets the scheduler platform name.

        Args:
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.

        Returns:
            str: The name of the scheduler (e.g., 'slurm', 'lsf').
        """
        return self.get('name', step=step, index=index)

    def set_name(self, value: str, step: Optional[str] = None, index: Optional[str] = None):
        """Sets the scheduler platform name.

        Args:
            value (str): The name of the scheduler to set.
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.
        """
        self.set('name', value, step=step, index=index)

    def get_cores(self, step: Optional[str] = None, index: Optional[str] = None) -> int:
        """Gets the number of CPU cores required for the job.

        Args:
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.

        Returns:
            int: The number of CPU cores.
        """
        return self.get('cores', step=step, index=index)

    def set_cores(self, value: int, step: Optional[str] = None, index: Optional[str] = None):
        """Sets the number of CPU cores required for the job.

        Args:
            value (int): The number of CPU cores to set.
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.
        """
        self.set('cores', value, step=step, index=index)

    def get_memory(self, step: Optional[str] = None, index: Optional[str] = None) -> int:
        """Gets the memory required for the job in megabytes.

        Args:
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.

        Returns:
            int: The amount of memory in MB.
        """
        return self.get('memory', step=step, index=index)

    def set_memory(self, value: int, step: Optional[str] = None, index: Optional[str] = None):
        """Sets the memory required for the job in megabytes.

        Args:
            value (int): The amount of memory in MB to set.
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.
        """
        self.set('memory', value, step=step, index=index)

    def get_queue(self, step: Optional[str] = None, index: Optional[str] = None) -> str:
        """Gets the scheduler queue (or partition) for the job.

        Args:
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.

        Returns:
            str: The name of the queue.
        """
        return self.get('queue', step=step, index=index)

    def set_queue(self, value: str, step: Optional[str] = None, index: Optional[str] = None):
        """Sets the scheduler queue (or partition) for the job.

        Args:
            value (str): The name of the queue to set.
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.
        """
        self.set('queue', value, step=step, index=index)

    def get_defer(self, step: Optional[str] = None, index: Optional[str] = None) -> str:
        """Gets the deferred start time for the job.

        Args:
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.

        Returns:
            str: The defer time string (e.g., '16:00', 'now+1hour').
        """
        return self.get('defer', step=step, index=index)

    def set_defer(self, value: str, step: Optional[str] = None, index: Optional[str] = None):
        """Sets the deferred start time for the job.

        Args:
            value (str): The defer time string to set.
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.
        """
        self.set('defer', value, step=step, index=index)

    def get_options(self, step: Optional[str] = None, index: Optional[str] = None) -> List[str]:
        """Gets the advanced pass-through options for the scheduler.

        Args:
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.

        Returns:
            List[str]: A list of scheduler options.
        """
        return self.get('options', step=step, index=index)

    def add_options(self, value: Union[List[str], str],
                    step: Optional[str] = None, index: Optional[str] = None,
                    clobber: bool = False):
        """Adds or sets advanced pass-through options for the scheduler.

        Args:
            value (Union[List[str], str]): A single option or a list of options.
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.
            clobber (bool, optional): If True, replaces existing options.
                If False, appends to them. Defaults to False.
        """
        if clobber:
            self.set('options', value, step=step, index=index)
        else:
            self.add('options', value, step=step, index=index)

    def get_msgevent(self, step: Optional[str] = None, index: Optional[str] = None) -> List[str]:
        """Gets the event triggers for sending messages.

        Args:
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.

        Returns:
            List[str]: A list of message event triggers (e.g., 'fail', 'end').
        """
        return self.get('msgevent', step=step, index=index)

    def add_msgevent(self, value: Union[List[str], str],
                     step: Optional[str] = None, index: Optional[str] = None,
                     clobber: bool = False):
        """Adds or sets the event triggers for sending messages.

        Args:
            value (Union[List[str], str]): A single event or a list of events.
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.
            clobber (bool, optional): If True, replaces existing events.
                If False, appends to them. Defaults to False.
        """
        if clobber:
            self.set('msgevent', value, step=step, index=index)
        else:
            self.add('msgevent', value, step=step, index=index)

    def get_msgcontact(self, step: Optional[str] = None, index: Optional[str] = None) -> List[str]:
        """Gets the contact list for scheduler event messages.

        Args:
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.

        Returns:
            List[str]: A list of email addresses.
        """
        return self.get('msgcontact', step=step, index=index)

    def add_msgcontact(self, value: Union[List[str], str],
                       step: Optional[str] = None, index: Optional[str] = None,
                       clobber: bool = False):
        """Adds or sets the contact list for scheduler event messages.

        Args:
            value (Union[List[str], str]): An email address or a list of them.
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.
            clobber (bool, optional): If True, replaces the existing contact list.
                If False, appends to it. Defaults to False.
        """
        if clobber:
            self.set('msgcontact', value, step=step, index=index)
        else:
            self.add('msgcontact', value, step=step, index=index)

    def get_maxnodes(self) -> int:
        """Gets the maximum number of concurrent nodes for a job.

        Returns:
            int: The maximum number of nodes.
        """
        return self.get('maxnodes')

    def set_maxnodes(self, value: int):
        """Sets the maximum number of concurrent nodes for a job.

        Args:
            value (int): The maximum number of nodes to set.
        """
        self.set('maxnodes', value)

    def get_maxthreads(self) -> int:
        """Gets the maximum number of threads for each task in a job.

        Returns:
            int: The maximum number of threads.
        """
        return self.get('maxthreads')

    def set_maxthreads(self, value: int):
        """Sets the maximum number of threads for each task in a job.

        Args:
            value (int): The maximum number of threads to set.
        """
        self.set('maxthreads', value)


class OptionSchema(BaseSchema):
    """
    Schema for top-level configuration options.

    This class defines global and job-specific parameters that control the
    compiler's behavior, such as flow control, logging, build settings, and
    remote execution. It provides getter and setter methods for each parameter.
    """
    __OPTIONS: Final[str] = "schema-options"

    def __init__(self):
        """Initializes the options schema and defines all its parameters."""
        super().__init__()

        self.__callbacks: Dict[str, Callable] = {}

        # Initialize schema
        schema = EditableSchema(self)

        schema.insert(
            'remote',
            Parameter(
                'bool',
                scope=Scope.GLOBAL,
                shorthelp="Option: enable remote processing",
                switch="-remote <bool>",
                example=[
                    "cli: -remote",
                    "api: option.set('remote', True)"],
                help="""
                Sends job for remote processing if set to true. The remote
                option requires a credentials file to be placed in the home
                directory. Fore more information, see the credentials
                parameter."""))

        schema.insert(
            'credentials',
            Parameter(
                'file',
                scope=Scope.GLOBAL,
                shorthelp="Option: user credentials file",
                switch="-credentials <file>",
                example=[
                    "cli: -credentials /home/user/.sc/credentials",
                    "api: option.set('credentials', '/home/user/.sc/credentials')"],
                help="""
                Filepath to credentials used for remote processing. If the
                credentials parameter is empty, the remote processing client program
                tries to access the ".sc/credentials" file in the user's home
                directory. The file supports the following fields:

                address=<server address>
                port=<server port> (optional)
                username=<user id> (optional)
                password=<password / key used for authentication> (optional)"""))

        schema.insert(
            'cachedir',
            Parameter(
                'dir',
                scope=Scope.GLOBAL,
                shorthelp="Option: user cache directory",
                switch="-cachedir <dir>",
                example=[
                    "cli: -cachedir /home/user/.sc/cache",
                    "api: option.set('cachedir', '/home/user/.sc/cache')"],
                help="""
                Filepath to cache used for package data sources. If the
                cache parameter is empty, ".sc/cache" directory in the user's home
                directory will be used."""))

        schema.insert(
            'nice',
            Parameter(
                'int',
                scope=Scope.GLOBAL,
                pernode=PerNode.OPTIONAL,
                shorthelp="Option: tool scheduling priority",
                switch="-nice <int>",
                example=[
                    "cli: -nice 5",
                    "api: option.set('nice', 5)"],
                help="""
                Sets the type of execution priority of each individual flowgraph steps.
                If the parameter is undefined, nice will not be used. For more information see
                `Unix 'nice' <https://en.wikipedia.org/wiki/Nice_(Unix)>`_."""))

        schema.insert(
            'flow',
            Parameter(
                'str',
                scope=Scope.GLOBAL,
                shorthelp="Option: flow target",
                switch="-flow <str>",
                example=["cli: -flow asicflow",
                         "api: option.set('flow', 'asicflow')"],
                help="""
                Sets the flow for the current run. The flow name
                must match up with a 'flow' in the flowgraph"""))

        schema.insert(
            'optmode',
            Parameter(
                'int',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                defvalue=0,
                shorthelp="Option: optimization mode",
                switch=["-O<str>",
                        "-optmode <str>"],
                example=["cli: -O3",
                         "cli: -optmode 3",
                         "api: option.set('optmode', 'O3')"],
                help="""
                The compiler has modes to prioritize run time and ppa. Modes
                include.

                (O0) = Exploration mode for debugging setup
                (O1) = Higher effort and better PPA than O0
                (O2) = Higher effort and better PPA than O1
                (O3) = Signoff quality. Better PPA and higher run times than O2
                (O4-O98) = Reserved (compiler/target dependent)
                (O99) = Experimental highest possible effort, may be unstable
                """))

        schema.insert(
            'builddir',
            Parameter(
                'dir',
                scope=Scope.GLOBAL,
                defvalue='build',
                shorthelp="Option: build directory",
                switch="-builddir <dir>",
                example=[
                    "cli: -builddir ./build_the_future",
                    "api: option.set('builddir', './build_the_future')"],
                help="""
                The default build directory is in the local './build' where SC was
                executed. This can be used to set an alternate
                compilation directory path."""))

        schema.insert(
            'jobname',
            Parameter(
                'str',
                scope=Scope.GLOBAL,
                defvalue='job0',
                shorthelp="Option: job name",
                switch="-jobname <str>",
                example=[
                    "cli: -jobname may1",
                    "api: option.set('jobname', 'may1')"],
                help="""
                Jobname during invocation of :meth:`.Project.run()`. The jobname combined with a
                defined director structure (<dir>/<design>/<jobname>/<step>/<index>)
                enables multiple levels of transparent job, step, and index
                introspection."""))

        schema.insert(
            'from',
            Parameter(
                '[str]',
                scope=Scope.JOB,
                shorthelp="Option: starting step",
                switch="-from <str>",
                example=[
                    "cli: -from 'import'",
                    "api: option.set('from', 'import')"],
                help="""
                Inclusive list of steps to start execution from. The default is to start
                at all entry steps in the flow graph."""))

        schema.insert(
            'to',
            Parameter(
                '[str]',
                scope=Scope.JOB,
                shorthelp="Option: ending step",
                switch="-to <str>",
                example=[
                    "cli: -to 'syn'",
                    "api: option.set('to', 'syn')"],
                help="""
                Inclusive list of steps to end execution with. The default is to go
                to all exit steps in the flow graph."""))

        schema.insert(
            'prune',
            Parameter(
                '[(str,str)]',
                scope=Scope.JOB,
                shorthelp="Option: flowgraph pruning",
                switch="-prune 'node <(str,str)>'",
                example=[
                    "cli: -prune (syn,0)",
                    "api: option.set('prune', ('syn', '0'))"],
                help="""
                List of starting nodes for branches to be pruned.
                The default is to not prune any nodes/branches."""))

        schema.insert(
            'breakpoint',
            Parameter(
                'bool',
                scope=Scope.JOB,
                pernode=PerNode.OPTIONAL,
                shorthelp="Option: breakpoint list",
                switch="-breakpoint <bool>",
                example=[
                    "cli: -breakpoint true",
                    "api: option.set('breakpoint', True)"],
                help="""
                Set a breakpoint on specific steps. If the step is a TCL
                based tool, then the breakpoints stops the flow inside the
                EDA tool. If the step is a command line tool, then the flow
                drops into a Python interpreter."""))

        schema.insert(
            'clean',
            Parameter(
                'bool',
                scope=Scope.GLOBAL,
                shorthelp="Option: cleanup previous job",
                switch="-clean <bool>",
                example=["cli: -clean",
                         "api: option.set('clean', True)"],
                help="""
                Run a job from the start and do not use any of the previous job.
                If :keypath:`option, jobincr` is True, the old job is preserved and
                a new job number is assigned.
                """))

        schema.insert(
            'hash',
            Parameter(
                'bool',
                scope=Scope.GLOBAL,
                shorthelp="Option: file hashing",
                switch="-hash <bool>",
                example=["cli: -hash",
                         "api: option.set('hash', True)"],
                help="""
                Enables hashing of all inputs and outputs during
                compilation. The hash values are stored in the hashvalue
                field of the individual parameters."""))

        schema.insert(
            'nodisplay',
            Parameter(
                'bool',
                scope=Scope.GLOBAL,
                shorthelp="Option: headless execution",
                switch="-nodisplay <bool>",
                example=["cli: -nodisplay",
                         "api: option.set('nodisplay', True)"],
                help="""
                This flag prevents SiliconCompiler from opening GUI windows."""))

        schema.insert(
            'quiet',
            Parameter(
                'bool',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Option: quiet execution",
                switch="-quiet <bool>",
                example=["cli: -quiet",
                         "api: option.set('quiet', True)"],
                help="""
                The -quiet option forces all steps to print to a log file.
                This can be useful with Modern EDA tools which print
                significant content to the screen."""))

        schema.insert(
            'jobincr',
            Parameter(
                'bool',
                scope=Scope.GLOBAL,
                shorthelp="Option: autoincrement jobname",
                switch="-jobincr <bool>",
                example=["cli: -jobincr",
                         "api: option.set('jobincr', True)"],
                help="""
                Forces an auto-update of the jobname parameter if a directory
                matching the jobname is found in the build directory. If the
                jobname does not include a trailing digit, then the number
                '1' is added to the jobname before updating the jobname
                parameter."""))

        schema.insert(
            'novercheck',
            Parameter(
                'bool',
                pernode=PerNode.OPTIONAL,
                defvalue=False,
                scope=Scope.GLOBAL,
                shorthelp="Option: disable version checking",
                switch="-novercheck <bool>",
                example=["cli: -novercheck",
                         "api: option.set('novercheck', True)"],
                help="""
                Disables strict version checking on all invoked tools if True.
                The list of supported version numbers is defined in the
                :keypath:`tool,<tool>,task,<task>,version`."""))

        schema.insert(
            'track',
            Parameter(
                'bool',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Option: enable provenance tracking",
                switch="-track <bool>",
                example=["cli: -track",
                         "api: option.set('track', True)"],
                help="""
                Turns on tracking of all 'record' parameters during each
                task, otherwise only tool and runtime information will be recorded.
                Tracking will result in potentially sensitive data
                being recorded in the manifest so only turn on this feature
                if you have control of the final manifest."""))

        schema.insert(
            'continue',
            Parameter(
                'bool',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp='Option: continue-on-error',
                switch='-continue <bool>',
                example=["cli: -continue",
                         "api: option.set('continue', True)"],
                help="""
                Attempt to continue even when errors are encountered in the SC
                implementation. The default behavior is to quit executing the flow
                if a task ends and the errors metric is greater than 0. Note that
                the flow will always cease executing if the tool returns a nonzero
                status code.
                """))

        schema.insert(
            'timeout',
            Parameter(
                'float',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                unit='s',
                shorthelp="Option: timeout value",
                switch="-timeout <float>",
                example=["cli: -timeout 3600",
                         "api: option.set('timeout', 3600)"],
                help="""
                Timeout value in seconds. The timeout value is compared
                against the wall time tracked by the SC runtime to determine
                if an operation should continue."""))

        schema.insert(
            "env", "default",
            Parameter(
                "str",
                scope=Scope.GLOBAL,
                shorthelp="Option: environment variables",
                example=["api: option.set('env', 'PDK_HOME', '/disk/mypdk')"],
                help=trim("""
                    Certain tools and reference flows require global environment
                    variables to be set. These variables can be managed externally or
                    specified through the env variable.""")))

        schema.insert(
            "design",
            Parameter(
                "str",
                scope=Scope.GLOBAL,
                shorthelp="Option: Design library name",
                example=["cli: -design hello_world",
                         "api: option.set('design', 'hello_world')"],
                switch=["-design <str>"],
                help="Name of the top level library"))

        schema.insert(
            "alias",
            Parameter(
                "[(str,str,str,str)]",
                scope=Scope.GLOBAL,
                shorthelp="Option: Fileset alias mapping",
                example=[
                    "api: option.set('alias', ('design', 'rtl', 'lambda', 'rtl'))"],
                help=trim("""List of filesets to alias during a run. When an alias is specific
                    it will be used instead of the source fileset. It is useful when you
                    want to substitute a fileset from one library with a fileset from another,
                    without changing the original design's code.
                    For example, you might use it to swap in a different version of an IP
                    block or a specific test environment.""")))
        schema.insert(
            "fileset",
            Parameter(
                "[str]",
                scope=Scope.GLOBAL,
                shorthelp="Option: Selected design filesets",
                example=["api: option.set('fileset', 'rtl')"],
                help=trim("""List of filesets to use from the selected design library""")))

        schema.insert(
            "nodashboard",
            Parameter(
                "bool",
                defvalue=False,
                scope=Scope.GLOBAL,
                switch=["-nodashboard <bool>"],
                shorthelp="Option: Disables the dashboard",
                example=["api: option.set('nodashboard', True)"],
                help=trim("""Disables the dashboard during execution""")))

        schema.insert(
            "autoissue",
            Parameter(
                "bool",
                defvalue=False,
                scope=Scope.GLOBAL,
                switch=["-autoissue <bool>"],
                shorthelp="Option: Enables automatic generation of testcases",
                example=["api: option.set('autoissue', True)"],
                help=trim("""Enables automatic generation of testcases
                          if the specific node fails""")))

        schema.insert('scheduler', SchedulerSchema())

        self.__load_defaults()

    def __load_defaults(self) -> None:
        """Loads and applies settings from the default options file.

        This method reads the configuration file specified by the settings
        manager. It iterates through the list of option
        objects in the file.

        For each object, it checks for a "key" and a "value". If the key
        is recognized (exists in `self.allkeys()`), it attempts to apply
        the value using `self.set()`.

        Errors during value setting (`ValueError`) are silently ignored.
        """
        options = MPManager.get_settings().get_category(OptionSchema.__OPTIONS)

        if not options:
            return

        allkeys = self.allkeys()
        for key, value in options.items():
            if key is None:
                continue

            key = tuple(key.split(","))
            if key not in allkeys:
                continue

            try:
                self.set(*key, value)
            except ValueError:
                pass

    def write_defaults(self) -> None:
        """Saves all non-default settings to the configuration file.

        This method iterates through all parameters known to the system
        (via `self.allkeys()`). It compares the current value of each
        parameter against its default value.

        Any parameter whose current value differs from its default is
        collected. This list of non-default settings is then
        serialized as a JSON array to the file specified by
        `default_options_file()`.

        If all parameters are set to their default values, the list
        will be empty, and no file will be written.
        """
        transientkeys = {
            # Flow information
            ("flow",),
            ("from",),
            ("to",),
            ("prune",),

            # Design information
            ("design",),
            ("alias",),
            ("fileset",),
        }

        settings = MPManager.get_settings()
        settings.delete(OptionSchema.__OPTIONS)

        for key in self.allkeys():
            if key in transientkeys:
                continue

            param: Parameter = self.get(*key, field=None)

            value = param.get()
            if value != param.default.get():
                settings.set(OptionSchema.__OPTIONS, ",".join(key), value)

        if settings.get_category(OptionSchema.__OPTIONS):
            settings.save()

    # Getters and Setters
    def get_remote(self) -> bool:
        """Gets the remote processing flag.

        Returns:
            bool: True if remote processing is enabled.
        """
        return self.get('remote')

    def set_remote(self, value: bool):
        """Sets the remote processing flag.

        Args:
            value (bool): The value to set for the remote flag.
        """
        self.set('remote', value)

    def get_credentials(self) -> str:
        """Gets the path to the user credentials file.

        Returns:
            str: The filepath to the credentials file.
        """
        return self.get('credentials')

    def set_credentials(self, value: str):
        """Sets the path to the user credentials file.

        Args:
            value (str): The filepath to the credentials file.
        """
        self.set('credentials', value)

    def get_cachedir(self) -> str:
        """Gets the path to the user cache directory.

        Returns:
            str: The filepath to the cache directory.
        """
        return self.get('cachedir')

    def set_cachedir(self, value: str):
        """Sets the path to the user cache directory.

        Args:
            value (str): The filepath to the cache directory.
        """
        self.set('cachedir', value)

    def get_nice(self, step: Optional[str] = None, index: Optional[str] = None) -> int:
        """Gets the tool scheduling priority (nice level).

        Args:
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.

        Returns:
            int: The nice value.
        """
        return self.get('nice', step=step, index=index)

    def set_nice(self, value: int, step: Optional[str] = None, index: Optional[str] = None):
        """Sets the tool scheduling priority (nice level).

        Args:
            value (int): The nice value to set.
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.
        """
        self.set('nice', value, step=step, index=index)

    def get_flow(self) -> str:
        """Gets the target flow name.

        Returns:
            str: The name of the flow.
        """
        return self.get('flow')

    def set_flow(self, value: str):
        """Sets the target flow name.

        Args:
            value (str): The name of the flow to set.
        """
        self.set('flow', value)

    def get_optmode(self, step: Optional[str] = None, index: Optional[str] = None) -> int:
        """Gets the optimization mode.

        Args:
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.

        Returns:
            int: The optimization mode level.
        """
        return self.get('optmode', step=step, index=index)

    def set_optmode(self, value: int, step: Optional[str] = None, index: Optional[str] = None):
        """Sets the optimization mode.

        Args:
            value (int): The optimization mode level to set.
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.
        """
        self.set('optmode', value, step=step, index=index)

    def get_builddir(self) -> str:
        """Gets the build directory path.

        Returns:
            str: The path to the build directory.
        """
        return self.get('builddir')

    def set_builddir(self, value: str):
        """Sets the build directory path.

        Args:
            value (str): The path to the build directory.
        """
        self.set('builddir', value)

    def get_jobname(self) -> str:
        """Gets the job name.

        Returns:
            str: The name of the job.
        """
        return self.get('jobname')

    def set_jobname(self, value: str):
        """Sets the job name.

        Args:
            value (str): The name of the job.
        """
        self.set('jobname', value)

    def get_from(self) -> List[str]:
        """Gets the list of starting steps for execution.

        Returns:
            List[str]: A list of step names.
        """
        return self.get('from')

    def add_from(self, value: Union[List[str], str], clobber: bool = False):
        """Adds or sets the starting step(s) for execution.

        Args:
            value (Union[List[str], str]): The step or steps to add.
            clobber (bool, optional): If True, replaces existing steps.
                If False, appends to them. Defaults to False.
        """
        if clobber:
            self.set('from', value)
        else:
            self.add('from', value)

    def get_to(self) -> List[str]:
        """Gets the list of ending steps for execution.

        Returns:
            List[str]: A list of step names.
        """
        return self.get('to')

    def add_to(self, value: Union[List[str], str], clobber: bool = False):
        """Adds or sets the ending step(s) for execution.

        Args:
            value (Union[List[str], str]): The step or steps to add.
            clobber (bool, optional): If True, replaces existing steps.
                If False, appends to them. Defaults to False.
        """
        if clobber:
            self.set('to', value)
        else:
            self.add('to', value)

    def get_prune(self) -> List[Tuple[str, str]]:
        """Gets the list of nodes to prune from the flowgraph.

        Returns:
            List[Tuple[str, str]]: A list of (step, index) tuples to prune.
        """
        return self.get('prune')

    def add_prune(self, value: Union[List[Tuple[str, str]], Tuple[str, str]],
                  clobber: bool = False):
        """Adds or sets nodes to prune from the flowgraph.

        Args:
            value (Union[List[Tuple[str, str]], Tuple[str, str]]): The node or
                nodes to add.
            clobber (bool, optional): If True, replaces existing nodes.
                If False, appends to them. Defaults to False.
        """
        if clobber:
            self.set('prune', value)
        else:
            self.add('prune', value)

    def get_breakpoint(self, step: Optional[str] = None, index: Optional[str] = None) -> bool:
        """Checks if a breakpoint is set on a specific step.

        Args:
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.

        Returns:
            bool: True if a breakpoint is set.
        """
        return self.get('breakpoint', step=step, index=index)

    def set_breakpoint(self, value: bool, step: Optional[str] = None, index: Optional[str] = None):
        """Sets a breakpoint on a specific step.

        Args:
            value (bool): The value to set for the breakpoint flag.
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.
        """
        self.set('breakpoint', value, step=step, index=index)

    def get_clean(self) -> bool:
        """Gets the clean job flag.

        Returns:
            bool: True if the previous job should be cleaned up.
        """
        return self.get('clean')

    def set_clean(self, value: bool):
        """Sets the clean job flag.

        Args:
            value (bool): The value to set for the clean flag.
        """
        self.set('clean', value)

    def get_hash(self) -> bool:
        """Gets the file hashing flag.

        Returns:
            bool: True if file hashing is enabled.
        """
        return self.get('hash')

    def set_hash(self, value: bool):
        """Sets the file hashing flag.

        Args:
            value (bool): The value to set for the hash flag.
        """
        self.set('hash', value)

    def get_nodisplay(self) -> bool:
        """Gets the headless execution (no-display) flag.

        Returns:
            bool: True if GUI windows are disabled.
        """
        return self.get('nodisplay')

    def set_nodisplay(self, value: bool):
        """Sets the headless execution (no-display) flag.

        Args:
            value (bool): The value to set for the no-display flag.
        """
        self.set('nodisplay', value)

    def get_quiet(self, step: Optional[str] = None, index: Optional[str] = None) -> bool:
        """Gets the quiet execution flag for a step.

        Args:
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.

        Returns:
            bool: True if quiet execution is enabled.
        """
        return self.get('quiet', step=step, index=index)

    def set_quiet(self, value: bool, step: Optional[str] = None, index: Optional[str] = None):
        """Sets the quiet execution flag for a step.

        Args:
            value (bool): The value to set for the quiet flag.
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.
        """
        self.set('quiet', value, step=step, index=index)

    def get_jobincr(self) -> bool:
        """Gets the job name auto-increment flag.

        Returns:
            bool: True if job name auto-increment is enabled.
        """
        return self.get('jobincr')

    def set_jobincr(self, value: bool):
        """Sets the job name auto-increment flag.

        Args:
            value (bool): The value for the job-increment flag.
        """
        self.set('jobincr', value)

    def get_novercheck(self, step: Optional[str] = None, index: Optional[str] = None) -> bool:
        """Gets the version checking disable flag for a step.

        Args:
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.

        Returns:
            bool: True if version checking is disabled.
        """
        return self.get('novercheck', step=step, index=index)

    def set_novercheck(self, value: bool, step: Optional[str] = None, index: Optional[str] = None):
        """Sets the version checking disable flag for a step.

        Args:
            value (bool): The value for the no-version-check flag.
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.
        """
        self.set('novercheck', value, step=step, index=index)

    def get_track(self, step: Optional[str] = None, index: Optional[str] = None) -> bool:
        """Gets the provenance tracking flag for a step.

        Args:
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.

        Returns:
            bool: True if tracking is enabled.
        """
        return self.get('track', step=step, index=index)

    def set_track(self, value: bool, step: Optional[str] = None, index: Optional[str] = None):
        """Sets the provenance tracking flag for a step.

        Args:
            value (bool): The value for the track flag.
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.
        """
        self.set('track', value, step=step, index=index)

    def get_continue(self, step: Optional[str] = None, index: Optional[str] = None) -> bool:
        """Gets the continue-on-error flag for a step.

        Args:
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.

        Returns:
            bool: True if the flow should continue on error.
        """
        return self.get('continue', step=step, index=index)

    def set_continue(self, value: bool, step: Optional[str] = None, index: Optional[str] = None):
        """Sets the continue-on-error flag for a step.

        Args:
            value (bool): The value for the continue flag.
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.
        """
        self.set('continue', value, step=step, index=index)

    def get_timeout(self, step: Optional[str] = None, index: Optional[str] = None) -> float:
        """Gets the timeout value for a step in seconds.

        Args:
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.

        Returns:
            float: The timeout value in seconds.
        """
        return self.get('timeout', step=step, index=index)

    def set_timeout(self, value: float, step: Optional[str] = None, index: Optional[str] = None):
        """Sets the timeout value for a step in seconds.

        Args:
            value (float): The timeout value in seconds.
            step (str, optional): The flowgraph step. Defaults to None.
            index (str, optional): The flowgraph step index. Defaults to None.
        """
        self.set('timeout', value, step=step, index=index)

    def get_env(self, key: str) -> str:
        """Gets an environment variable.

        Args:
            key (str): The name of the environment variable.

        Returns:
            str: The value of the environment variable.
        """
        return self.get('env', key)

    def set_env(self, key: str, value: str):
        """Sets an environment variable.

        Args:
            key (str): The name of the environment variable.
            value (str): The value to set.
        """
        self.set('env', key, value)

    def get_design(self) -> str:
        """Gets the top-level design library name.

        Returns:
            str: The name of the design.
        """
        return self.get('design')

    def set_design(self, value: str):
        """Sets the top-level design library name.

        Args:
            value (str): The name of the design.
        """
        self.set('design', value)

    def get_alias(self) -> List[Tuple[str, str, str, str]]:
        """Gets the list of fileset aliases.

        Returns:
            List[Tuple[str, str, str, str]]: A list of alias tuples.
        """
        return self.get('alias')

    def add_alias(self,
                  value: Union[List[Tuple[str, str, str, str]], Tuple[str, str, str, str]],
                  clobber: bool = False):
        """Adds or sets fileset aliases.

        Args:
            value (Union[List[Tuple[str, str, str, str]], Tuple[str, str, str, str]]):
                The alias or aliases to add.
            clobber (bool, optional): If True, replaces existing aliases.
                If False, appends to them. Defaults to False.
        """
        if clobber:
            self.set('alias', value)
        else:
            self.add('alias', value)

    def get_fileset(self) -> List[str]:
        """Gets the list of selected design filesets.

        Returns:
            List[str]: A list of fileset names.
        """
        return self.get('fileset')

    def add_fileset(self, value: Union[List[str], str], clobber: bool = False):
        """Adds or sets selected design filesets.

        Args:
            value (Union[List[str], str]): The fileset or filesets to add.
            clobber (bool, optional): If True, replaces existing filesets.
                If False, appends to them. Defaults to False.
        """
        if clobber:
            self.set('fileset', value)
        else:
            self.add('fileset', value)

    def get_nodashboard(self) -> bool:
        """Gets the dashboard disable flag.

        Returns:
            bool: True if the dashboard is disabled.
        """
        return self.get('nodashboard')

    def set_nodashboard(self, value: bool):
        """Sets the dashboard disable flag.

        Args:
            value (bool): The value for the no-dashboard flag.
        """
        self.set('nodashboard', value)

    def get_autoissue(self) -> bool:
        """Gets the autoissue flag.

        Returns:
            bool: The current value of the autoissue flag.
        """
        return self.get('autoissue')

    def set_autoissue(self, value: bool):
        """Sets the autoissue flag.

        Args:
            value (bool): The desired value for the autoissue flag.
        """
        self.set('autoissue', value)

    @property
    def scheduler(self) -> SchedulerSchema:
        """Provides access to the scheduler sub-schema.

        Returns:
            SchedulerSchema: The schema object for scheduler settings.
        """
        return self.get("scheduler", field="schema")

    def _add_callback(self, key: str, callback: Callable):
        """Registers a callback function to be executed when a key is set.

        Args:
            key (str): The schema key to attach the callback to.
            callback (Callable): The function to execute when the key is set.

        Raises:
            KeyError: If the provided key is not a valid schema parameter.
        """
        if key not in self.getkeys():
            raise KeyError(f"{key} is not supported for callbacks")
        self.__callbacks[key] = callback

    def set(self, *args, field='value', clobber=True, step=None, index=None):
        ret = super().set(*args, field=field, clobber=clobber, step=step, index=index)

        if args[0] in self.__callbacks:
            self.__callbacks[args[0]]()

        return ret

    def __getstate__(self):
        """
        Prepares the schema's state for serialization (pickling).

        This method removes non-serializable objects, specifically the internal
        `__callbacks` dictionary, before the object is pickled.

        Returns:
            dict: The serializable state of the object.
        """
        # Ensure a copy of the state is used
        state = self.__dict__.copy()

        # Remove callbacks since they are not serializable
        del state["_OptionSchema__callbacks"]

        return state

    def __setstate__(self, state):
        """
        Restores the schema's state from a deserialized (unpickled) state.

        This method restores the core object dictionary and then re-initializes
        the `__callbacks` dictionary, as it was removed during serialization.

        Args:
            state (dict): The deserialized state of the object.
        """
        self.__dict__ = state

        # Reinitialize callback object on restore
        self.__callbacks = {}
