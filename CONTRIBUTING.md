How to contribute to SiliconCompiler
=====================================

Thank you for considering contributing to the SiliconCompiler project!

## General guidelines
- Start small, relationships need time to grow
- All new features must come with pytests
- Keep PRs short to simplify review
- Large PRs should be preceded by discussions
- Discuss with core team before proposing core changes
- PRs should include changes only to files related to change
- Comply with coding guidelines/style of project
- Avoid style only code based PRs

#### Reporting issues

Include the following information in your post:

- Describe what you expected to happen.
- Include a [minimal reproducible example](https://stackoverflow.com/help/minimal-reproducible-example)
- Describe what actually happened.
- Include the full traceback if there was an exception.
- List your Python and SiliconCompiler versions.
- Check if this issue is already fixed in the latest releases

## Submitting patches

If there is not an open issue for what you want to submit, prefer opening one
for discussion before working on a PR. You can work on any issue that doesn't
have an open PR linked to it or a maintainer assigned to it. These show up in
the sidebar. No need to ask if you can work on an issue that interests you.

Include the following in your patch:

- Include tests if your patch adds or changes code.(should fail w/o patch)
- Update any relevant docs pages and docstrings.


## First time setup

- Download and install [git](https://git-scm.com/downloads)

- Configure your [git username](https://docs.github.com/en/github/using-git/setting-your-username-in-git)

- Configure your [git email](https://docs.github.com/en/github/setting-up-and-managing-your-github-user-account/setting-your-commit-email-address)

```sh
$ git config --global user.name 'your name'
$ git config --global user.email 'your email'
```
- Make sure you have a [github account](https://github.com/join)


## Clone/Fork Repository

- [Fork SiliconCompiler]( https://github.com/siliconcompiler/siliconcompiler/fork) to your GitHub account (external contributors only)

- [Clone](https://docs.github.com/en/github/getting-started-with-github/fork-a-repo#step-2-create-a-local-clone-of-your-fork) the main repository locally.

```sh
$ git clone https://github.com/{username}/siliconcompiler
$ cd siliconcompiler
```

-  Add fork as a remote to push your work to. (external contributors only)

```sh
$ git remote add fork https://github.com/{username}/siliconcompiler
```



## Install Python Requirements

-  Create a virtualenv.
```sh
$ python3 -m venv env
$ . env/bin/activate
```

- Upgrade pip and setuptools.
```sh
$ python3 -m pip install --upgrade pip setuptools
```

- Install the development dependencies
```sh
$ python3 -m pip install -e .[test,docs]
```

## Start coding

-  Create a branch to identify the issue you would like to work on.

```sh
$ git fetch origin
$ git checkout -b your-branch-name origin/main
```
- Using your favorite editor, make your changes, and [commit](https://dont-be-afraid-to-commit.readthedocs.io/en/latest/git/commandlinegit.html#commit-your-changes)

- Include tests that cover any code changes you make. Make sure the test fails without your patch. Run the tests as described below.

- Push your commits to your fork on GitHub (external contributors)

```sh
$ git push --set-upstream fork your-branch-name
```

- Push your commits to your SiliCompiler branch on GitHub (team contributors)
```sh
$ git push -u origin your-branch-name
```


## Running the tests

- Run the basic test suite with pytest.
```sh
$ pytest -m "not eda"
```
- This runs the tests for the current environment, without invoking any tools.

- Run the entire test suite with pytest. Note that this will require all tools to be installed for the tests to pass.
```sh
$ pytest
```

- For more information on the test suite, see [tests/README.md](tests/README.md).

## Create a Pull Request

- Create a [pull request](https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request) through github.

## Running linter

- Running linter on complete project
```sh
$ flake8 .
```

- Running linter on a specific module
```sh
$ flake8 siliconcompiler/schema.py
```


## Building the docs

- Build the docs in the ``docs`` directory using [Sphinx](https://www.sphinx-doc.org/en/stable/).

```sh
$ cd docs
$ make html
```
- Open ``_build/html/index.html`` in your browser to view the docs.


## Resources ###

Original version based on [Flask contribution guidelines](https://flask.palletsprojects.com/en/2.0.x/contributing/)
