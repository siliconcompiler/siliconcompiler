from siliconcompiler.schema import BaseSchema, EditableSchema, Parameter, Scope, PerNode


class OptionSchema(BaseSchema):
    def __init__(self):
        super().__init__()

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
                    "api: option.set('option', 'breakpoint', True)"],
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
                This flag prevents SiliconCompiler from opening GUI windows such as
                the final metrics report."""))

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

        # job scheduler
        schema.insert(
            'scheduler', 'name',
            Parameter(
                '<slurm,lsf,sge,docker>',
                scope=Scope.GLOBAL,
                pernode=PerNode.OPTIONAL,
                shorthelp="Option: scheduler platform",
                switch="-scheduler <str>",
                example=[
                    "cli: -scheduler slurm",
                    "api: option.set('scheduler', 'name', 'slurm')"],
                help="""
                Sets the type of job scheduler to be used for each individual
                flowgraph steps. If the parameter is undefined, the steps are executed
                on the same machine that the SC was launched on. If 'slurm' is used,
                the host running the 'sc' command must be running a 'slurmctld' daemon
                managing a Slurm cluster. Additionally, the build directory
                (:keypath:`option,builddir`) must be located in shared storage which
                can be accessed by all hosts in the cluster."""))

        schema.insert(
            'scheduler', 'cores',
            Parameter(
                'int',
                scope=Scope.GLOBAL,
                pernode=PerNode.OPTIONAL,
                shorthelp="Option: Scheduler core constraint",
                switch="-cores <int>",
                example=["cli: -cores 48",
                         "api: option.set('scheduler', 'cores', 48)"],
                help="""
                Specifies the number CPU cores required to run the job.
                For the slurm scheduler, this translates to the '-c'
                switch. For more information, see the job scheduler
                documentation"""))

        schema.insert(
            'scheduler', 'memory',
            Parameter(
                'int',
                unit='MB',
                scope=Scope.GLOBAL,
                pernode=PerNode.OPTIONAL,
                shorthelp="Option: scheduler memory constraint",
                switch="-memory <int>",
                example=["cli: -memory 8000",
                         "api: option.set('scheduler', 'memory', 8000)"],
                help="""
                Specifies the amount of memory required to run the job,
                specified in MB. For the slurm scheduler, this translates to
                the '--mem' switch. For more information, see the job
                scheduler documentation"""))

        schema.insert(
            'scheduler', 'queue',
            Parameter(
                'str',
                scope=Scope.GLOBAL,
                pernode=PerNode.OPTIONAL,
                shorthelp="Option: scheduler queue",
                switch="-queue <str>",
                example=["cli: -queue nightrun",
                         "api: option.set('scheduler', 'queue', 'nightrun')"],
                help="""
                Send the job to the specified queue. With slurm, this
                translates to 'partition'. The queue name must match
                the name of an existing job scheduler queue. For more information,
                see the job scheduler documentation"""))

        schema.insert(
            'scheduler', 'defer',
            Parameter(
                'str',
                scope=Scope.GLOBAL,
                pernode=PerNode.OPTIONAL,
                shorthelp="Option: scheduler start time",
                switch="-defer <str>",
                example=["cli: -defer 16:00",
                         "api: option.set('scheduler', 'defer', '16:00')"],
                help="""
                Defer initiation of job until the specified time. The parameter
                is pass through string for remote job scheduler such as slurm.
                For more information about the exact format specification, see
                the job scheduler documentation. Examples of valid slurm specific
                values include: now+1hour, 16:00, 010-01-20T12:34:00. For more
                information, see the job scheduler documentation."""))

        schema.insert(
            'scheduler', 'options',
            Parameter(
                '[str]',
                scope=Scope.GLOBAL,
                pernode=PerNode.OPTIONAL,
                shorthelp="Option: scheduler arguments",
                switch="-scheduler_options <str>",
                example=[
                    "cli: -scheduler_options \"--pty\"",
                    "api: option.set('scheduler', 'options', \"--pty\")"],
                help="""
                Advanced/export options passed through unchanged to the job
                scheduler as-is. (The user specified options must be compatible
                with the rest of the scheduler parameters entered.(memory etc).
                For more information, see the job scheduler documentation."""))

        schema.insert(
            'scheduler', 'msgevent',
            Parameter(
                '{<all,summary,begin,end,timeout,fail>}',
                scope=Scope.GLOBAL,
                pernode=PerNode.OPTIONAL,
                shorthelp="Option: message event trigger",
                switch="-msgevent <str>",
                example=[
                    "cli: -msgevent all",
                    "api: option.set('scheduler', 'msgevent', 'all')"],
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
            'scheduler', 'msgcontact',
            Parameter(
                '{str}',
                scope=Scope.GLOBAL,
                pernode=PerNode.OPTIONAL,
                shorthelp="Option: message contact",
                switch="-msgcontact <str>",
                example=[
                    "cli: -msgcontact 'wile.e.coyote@acme.com'",
                    "api: option.set('scheduler', 'msgcontact', 'wiley@acme.com')"],
                help="""
                List of email addresses to message on a :keypath:`option,scheduler,msgevent`.
                Support for email messages relies on job scheduler daemon support.
                For more information, see the job scheduler documentation. """))

        schema.insert(
            'scheduler', 'maxnodes',
            Parameter(
                'int',
                scope=Scope.GLOBAL,
                shorthelp="Option: maximum concurrent nodes",
                switch="-maxnodes <int>",
                example=["cli: -maxnodes 4",
                          "api: option.set('scheduler', 'maxnodes', 4)"],
                help="""
                Maximum number of concurrent nodes to run in a job. If not set this will default
                to the number of cpu cores available."""))
