# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
# -W turns warnings into errors so broken references and malformed markup fail
# the build instead of scrolling past. --keep-going reports every problem in one
# run rather than stopping at the first. Nitpicky mode (-n) is deliberately not
# enabled: it adds ~1800 warnings, most of them unresolved type names in
# docstrings, which would drown the signal.
SPHINXOPTS    ?= -W --keep-going
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
