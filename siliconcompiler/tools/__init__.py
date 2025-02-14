from siliconcompiler.tools import bambu
from siliconcompiler.tools import bluespec
from siliconcompiler.tools.builtin import builtin
from siliconcompiler.tools.chisel import chisel
from siliconcompiler.tools.execute import execute
from siliconcompiler.tools.genfasm import genfasm
from siliconcompiler.tools.ghdl import ghdl
from siliconcompiler.tools import gtkwave
from siliconcompiler.tools import graphviz
from siliconcompiler.tools.icarus import icarus
from siliconcompiler.tools.icepack import icepack
from siliconcompiler.tools.klayout import klayout
from siliconcompiler.tools.magic import magic
from siliconcompiler.tools.montage import montage
from siliconcompiler.tools.netgen import netgen
from siliconcompiler.tools.nextpnr import nextpnr
from siliconcompiler.tools import openroad
from siliconcompiler.tools import opensta
from siliconcompiler.tools import slang
from siliconcompiler.tools import surelog
from siliconcompiler.tools.sv2v import sv2v
from siliconcompiler.tools.verilator import verilator
from siliconcompiler.tools.vivado import vivado
from siliconcompiler.tools.vpr import vpr
from siliconcompiler.tools import xdm
from siliconcompiler.tools import xyce
from siliconcompiler.tools import yosys


def get_tools():
    '''
    Returns a dict of builtin tools
    '''
    return {
        module.__name__.split(".")[-1]: module for module in (
            bambu,
            bluespec,
            builtin,
            chisel,
            execute,
            genfasm,
            ghdl,
            graphviz,
            gtkwave,
            icarus,
            icepack,
            klayout,
            magic,
            montage,
            netgen,
            nextpnr,
            openroad,
            opensta,
            slang,
            surelog,
            sv2v,
            verilator,
            vivado,
            vpr,
            xdm,
            xyce,
            yosys
        )
    }
