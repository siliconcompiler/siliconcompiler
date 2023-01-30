# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import logging
import uuid

from siliconcompiler.schema import Schema, SCHEMA_VERSION
from siliconcompiler.core.error import SiliconCompilerError

class SchemaConsumer:
    """
    Superclass for objects which incorporate Schema objects as a core part of their operation.

    Contains helper methods to pass through calls such as get, set, add, etc.
    """


    ###########################################################################
    def __init__(self, loglevel=None):
        # Schema version tag.
        self.schemaversion = SCHEMA_VERSION

        # Core Schema object.
        self.schema = Schema()

        # Initialize logger.
        if loglevel:
            self.schema.set('option', 'loglevel', loglevel)
        self._init_logger()

    ###########################################################################
    def _init_logger(self, step=None, index=None, in_run=False):

        self.logger = logging.getLogger(uuid.uuid4().hex)

        # Don't propagate log messages to "root" handler (we get duplicate
        # messages without this)
        # TODO: this prevents us from being able to capture logs with pytest:
        # we should revisit it
        self.logger.propagate = False

        loglevel = self.get('option', 'loglevel')

        if loglevel=='DEBUG':
            prefix = '| %(levelname)-7s | %(funcName)-10s | %(lineno)-4s'
        else:
            prefix = '| %(levelname)-7s'

        if in_run:
            flow = self.get('option', 'flow')

            # Figure out how wide to make step and index fields
            max_step_len = 2
            max_index_len = 2
            for future_step in self.getkeys('flowgraph', flow):
                max_step_len = max(len(future_step) + 1, max_step_len)
                for future_index in self.getkeys('flowgraph', flow, future_step):
                    max_index_len = max(len(future_index) + 1, max_index_len)

            jobname = self.get('option', 'jobname')

            if step is None:
                step = '-' * max(max_step_len // 4, 1)
            if index is None:
                index = '-' * max(max_index_len // 4, 1)

            run_info = f'%s  | %-{max_step_len}s | %-{max_index_len}s' % (jobname, step, index)
            logformat = ' | '.join([prefix, run_info, '%(message)s'])
        else:
            logformat = ' | '.join([prefix, '%(message)s'])

        handler = logging.StreamHandler()
        formatter = logging.Formatter(logformat)

        handler.setFormatter(formatter)

        # Clear any existing handlers so we don't end up with duplicate messages
        # if repeat calls to _init_logger are made
        if len(self.logger.handlers) > 0:
            self.logger.handlers.clear()

        self.logger.addHandler(handler)
        self.logger.setLevel(loglevel)

    ###########################################################################
    def _deinit_logger(self):
        self.logger = None

    ###########################################################################
    def list_metrics(self):
        '''
        Returns a list of all metrics in the schema.

        '''

        return self.getkeys('metric','default','default')

    ###########################################################################
    def help(self, *keypath):
        """
        Returns a schema parameter description.

        Args:
            *keypath(str): Keypath to parameter.

        Returns:
            A formatted multi-line help paragraph for the parameter provided.

        Examples:
            >>> print(chip.help('asic','diearea'))
            Displays help information about the 'asic, diearea' parameter

        """

        self.logger.debug('Fetching help for %s', keypath)

        #Fetch Values

        description = self.get(*keypath, field='shorthelp')
        typestr = self.get(*keypath, field='type')
        switchstr = str(self.get(*keypath, field='switch'))
        defstr = str(self.get(*keypath, field='defvalue'))
        requirement = str(self.get(*keypath, field='require'))
        helpstr = self.get(*keypath, field='help')
        example = self.get(*keypath, field='example')

        examplestr = ("\nExamples:    " + example[0] + ''.join(
                     ["\n             " + ex for ex in example[1:]]))

        #Removing multiple spaces and newlines
        helpstr = helpstr.rstrip()
        helpstr = helpstr.replace("\n", "")
        helpstr = ' '.join(helpstr.split())

        for idx, item in enumerate(example):
            example[idx] = ' '.join(item.split())
            example[idx] = example[idx].replace(", ", ",")

        #Wrap text
        para = textwrap.TextWrapper(width=60)
        para_list = para.wrap(text=helpstr)

        #Full Doc String
        fullstr = ("-"*80 +
                   "\nDescription: " + description +
                   "\nSwitch:      " + switchstr +
                   "\nType:        " + typestr  +
                   "\nRequirement: " + requirement   +
                   "\nDefault:     " + defstr   +
                   examplestr +
                   "\nHelp:        " + para_list[0] + "\n")
        for line in para_list[1:]:
            fullstr = (fullstr +
                       " "*13 + line.lstrip() + "\n")

        return fullstr


    ###########################################################################
    def valid(self, *keypath, valid_keypaths=None, default_valid=False):
        """
        Checks validity of a keypath.

        Checks the validity of a parameter keypath and returns True if the
        keypath is valid and False if invalid.

        Args:
            keypath(list str): Variable length schema key list.
            default_valid (bool): Whether to consider "default" in valid
            keypaths as a wildcard. Defaults to False.

        Returns:
            Boolean indicating validity of keypath.

        Examples:
            >>> check = chip.valid('design')
            Returns True.
            >>> check = chip.valid('blah')
            Returns False.
            >>> check = chip.valid('metric', 'foo', '0', 'tasktime', default_valid=True)
            Returns True, even if "foo" and "0" aren't in current configuration.
        """
        return self.schema.valid(*keypath, valid_keypaths=valid_keypaths,
                                 default_valid=default_valid)

    ###########################################################################
    def get(self, *keypath, field='value', job=None, step=None, index=None):
        """
        Returns a schema parameter field.

        Returns a schema parameter field based on the keypath provided in the
        ``*keypath``. See the :ref:`Schema Reference Manual<SiliconCompiler
        Schema>` for documentation of all supported keypaths. The returned type
        is consistent with the type field of the parameter. Fetching parameters
        with empty or undefined value files returns None for scalar types and []
        (empty list) for list types.  Accessing a non-existent keypath produces
        a logger error message and raises the Chip object error flag.

        Args:
            keypath(list str): Variable length schema key list.
            field(str): Parameter field to fetch.
            job (str): Jobname to use for dictionary access in place of the
                current active jobname.

        Returns:
            Value found for the keypath and field provided.

        Examples:
            >>> foundry = chip.get('pdk', 'foundry')
            Returns the name of the foundry from the PDK.

        """
        self.logger.debug(f"Reading from {keypath}. Field = '{field}'")

        try:
            return self.schema.get(*keypath, field=field, job=job, step=step, index=index)
        except (ValueError, TypeError) as e:
            self.error(str(e))
            return None

    ###########################################################################
    def getkeys(self, *keypath, job=None):
        """
        Returns a list of schema dictionary keys.

        Searches the schema for the keypath provided and returns a list of
        keys found, excluding the generic 'default' key. Accessing a
        non-existent keypath produces a logger error message and raises the
        Chip object error flag.

        Args:
            keypath (list str): Variable length ordered schema key list
            job (str): Jobname to use for dictionary access in place of the
                current active jobname.

        Returns:
            List of keys found for the keypath provided.

        Examples:
            >>> keylist = chip.getkeys('pdk')
            Returns all keys for the 'pdk' keypath.
        """
        if len(keypath) > 0:
            self.logger.debug(f'Getting schema parameter keys for {keypath}')
        else:
            self.logger.debug('Getting all schema parameter keys.')

        try:
            return self.schema.getkeys(*keypath, job=job)
        except (ValueError, TypeError) as e:
            self.error(str(e))
            return None

    ###########################################################################
    def allkeys(self, *keypath_prefix):
        '''Returns all keypaths in the schema as a list of lists.

        Arg:
            keypath_prefix (list str): Keypath prefix to search under. The
                returned keypaths do not include the prefix.
        '''
        return self.schema.allkeys(*keypath_prefix)

    ###########################################################################
    def getdict(self, *keypath):
        """
        Returns a schema dictionary.

        Searches the schema for the keypath provided and returns a complete
        dictionary. Accessing a non-existent keypath produces a logger error
        message and raises the Chip object error flag.

        Args:
            keypath(list str): Variable length ordered schema key list

        Returns:
            A schema dictionary

        Examples:
            >>> pdk = chip.getdict('pdk')
            Returns the complete dictionary found for the keypath 'pdk'
        """
        self.logger.debug(f'Getting cfg for: {keypath}')

        try:
            return self.schema.getdict(*keypath)
        except (ValueError, TypeError) as e:
            self.error(str(e))
            return None

    ###########################################################################
    def set(self, *args, field='value', clobber=True, step=None, index=None):
        '''
        Sets a schema parameter field.

        Sets a schema parameter field based on the keypath and value provided in
        the ``*args``. See the :ref:`Schema Reference Manual<SiliconCompiler
        Schema>` for documentation of all supported keypaths. New schema
        dictionaries are automatically created for keypaths that overlap with
        'default' dictionaries. The write action is ignored if the parameter
        value is non-empty and the clobber option is set to False.

        The value provided must agree with the dictionary parameter 'type'.
        Accessing a non-existent keypath or providing a value that disagrees
        with the parameter type produces a logger error message and raises the
        Chip object error flag.

        Args:
            args (list): Parameter keypath followed by a value to set.
            field (str): Parameter field to set.
            clobber (bool): Existing value is overwritten if True.

        Examples:
            >>> chip.set('design', 'top')
            Sets the name of the design to 'top'
        '''
        keypath = args[:-1]
        value = args[-1]
        self.logger.debug(f'Setting {keypath} to {value}')

        # Special case to ensure loglevel is updated ASAP
        if keypath == ['option', 'loglevel'] and field == 'value':
            self.logger.setLevel(value)

        try:
            if not self.schema.set(
                *keypath, value, field=field, clobber=clobber, step=step, index=index
            ):
                # TODO: this message should be pushed down into Schema.set()
                # once we have a static logger.
                if clobber:
                    self.logger.debug(f'Failed to set value for {keypath}: '
                        'parameter is locked')
                else:
                    self.logger.debug(f'Failed to set value for {keypath}: '
                        'clobber is False and parameter may be locked')
        except (ValueError, TypeError) as e:
            self.error(e)

    ###########################################################################
    def clear(self, *keypath):
        '''
        Clears a schema parameter.

        Clearing a schema parameter causes the parameter to revert to its
        default value. A call to ``set()`` with ``clobber=False`` will once
        again be able to modify the value.

        Args:
            keypath (list): Parameter keypath to clear.
        '''
        self.logger.debug(f'Clearing {keypath}')

        if not self.schema.clear(*keypath):
            self.logger.debug(f'Failed to clear value for {keypath}: parameter is locked')

    ###########################################################################
    def add(self, *args, field='value', step=None, index=None):
        '''
        Adds item(s) to a schema parameter list.

        Adds item(s) to schema parameter list based on the keypath and value
        provided in the ``*args``.  See the :ref:`Schema Reference
        Manual<SiliconCompiler Schema>` for documentation of all supported
        keypaths. New schema dictionaries are automatically created for keypaths
        that overlap with 'default' dictionaries.

        The value provided must agree with the dictionary parameter 'type'.
        Accessing a non-existent keypath, providing a value that disagrees
        with the parameter type, or using add with a scalar parameter produces
        a logger error message and raises the Chip object error flag.

        Args:
            args (list): Parameter keypath followed by a value to add.
            field (str): Parameter field to set.

        Examples:
            >>> chip.add('input', 'rtl', 'verilog', 'hello.v')
            Adds the file 'hello.v' to the list of sources.
        '''
        keypath = args[:-1]
        value = args[-1]
        self.logger.debug(f'Appending value {value} to {keypath}')

        try:
            if not self.schema.add(*args, field=field, step=step, index=index):
                # TODO: this message should be pushed down into Schema.add()
                # once we have a static logger.
                self.logger.debug(f'Failed to add value for {keypath}: '
                    'parameter may be locked')
        except (ValueError, TypeError) as e:
            self.error(str(e))

    ###########################################################################
    def error(self, msg, fatal=False):
        '''Raises error.

        If fatal is False and :keypath:`option, continue` is set to True, this
        will log an error and set an internal error flag that will cause run()
        to quit. Otherwise, this will raise a SiliconCompilerError.

        Args:
            msg (str): Message associated with error
            fatal (bool): Whether error is always fatal
        '''
        if not fatal and self.get('option', 'continue'):
            self.logger.error(msg)
            self._error = True
            return

        raise SiliconCompilerError(msg) from None
