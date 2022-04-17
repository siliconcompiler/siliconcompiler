class Package:

    ###########################################################################
    def package(self, filename, prune=True):
        '''
        Create sanitized project package. (WIP)

        The SiliconCompiler project is filtered and exported as a JSON file.
        If the prune option is set to True, then all metrics, records and
        results are pruned from the package file.

        Args:
            filename (filepath): Output filepath
            prune (bool): If True, only essential source parameters are
                 included in the package.

        Examples:
            >>> chip.package('package.json')
            Write project information to 'package.json'
        '''

        return(0)

    ###########################################################################
    def publish(self, filename):
        '''
        Publishes package to registry. (WIP)

        The filename is uploaed to a central package registry based on the
        the user credentials found in ~/.sc/credentials.

        Args:
            filename (filepath): Package filename

        Examples:
            >>> chip.publish('hello.json')
            Publish hello.json to central repository.
        '''

        return(0)
