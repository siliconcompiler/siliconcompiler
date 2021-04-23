
# PErequisites
# sudo apt-get install pandoc
# sudo apt-get install texlive
# sudo apt-get install texlive-fonts-recommended texlive-fonts-extra

pandoc sc_reftable.md -V geometry:landscape --columns 1000 --pdf-engine=xelatex -o sc_reftable.pdf

pandoc sc_refmanual.md --pdf-engine=xelatex -o sc_refmanual.pdf


