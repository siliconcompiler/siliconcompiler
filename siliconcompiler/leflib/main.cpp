#include <pybind11/pybind11.h>
#include <pybind11/functional.h> // necessary to support function callbacks
#include <pybind11/stl.h>

#include <stdio.h>

#include "lefrReader.hpp"

#define STRINGIFY(x) #x
#define MACRO_STRINGIFY(x) STRINGIFY(x)
#define NONE py::cast<py::none>(Py_None)

namespace py = pybind11;

typedef std::map<std::string, py::object> PyDict;

typedef struct LefData {
    double version;
    bool has_version = false;
    double mfg_grid;
    bool has_mfg_grid = false;
    PyDict units;
    std::map<std::string, PyDict> layers;
    std::map<std::string, PyDict> macros;
} LefData;

int doubleCbk(LefDefParser::lefrCallbackType_e type, double v, void* data) {
    auto lef = (LefData*) data;
    switch (type) {
        case lefrManufacturingCbkType:
            lef->mfg_grid = v;
            lef->has_mfg_grid = true;
            break;
        case lefrVersionCbkType:
            lef->version = v;
            lef->has_version = true;
            break;
        default:
            break;
    }

    return 0;
}

int unitsCbk(LefDefParser::lefrCallbackType_e type, lefiUnits* units, void* data) {
    auto lef = (LefData*) data;
    if (units->hasDatabase())
        lef->units.insert(std::make_pair("db", py::cast(units->databaseNumber())));
    if (units->hasCapacitance())
        lef->units.insert(std::make_pair("capacitance", py::cast(units->capacitance())));
    if (units->hasResistance())
        lef->units.insert(std::make_pair("resistance", py::cast(units->resistance())));
    if (units->hasTime())
        lef->units.insert(std::make_pair("time", py::cast(units->time())));
    if (units->hasPower())
        lef->units.insert(std::make_pair("power", py::cast(units->power())));
    if (units->hasCurrent())
        lef->units.insert(std::make_pair("current", py::cast(units->current())));
    if (units->hasVoltage())
        lef->units.insert(std::make_pair("voltage", py::cast(units->voltage())));
    if (units->hasFrequency())
        lef->units.insert(std::make_pair("frequency", py::cast(units->frequency())));

    return 0;
}

int layerCbk(lefrCallbackType_e typ, lefiLayer* layer, lefiUserData data) {
    auto lef = (LefData*) data;
    PyDict l;
    if (layer->hasWidth())
        l.insert(std::make_pair("width", py::cast(layer->width())));
    if (layer->hasDirection())
        l.insert(std::make_pair("direction", py::cast(layer->direction())));

    lef->layers.insert(std::make_pair(layer->name(), l));

    return 0;
}

int macroCbk(LefDefParser::lefrCallbackType_e type, lefiMacro* macro, void* data) {
    PyDict m;
    if (macro->hasSize()) {
        m.insert(std::make_pair("width", py::cast(macro->sizeX())));
        m.insert(std::make_pair("height", py::cast(macro->sizeY())));
    }

    ((LefData*) data)->macros.insert(std::make_pair(macro->name(), m));

    return 0;
}

py::object lef_parse(std::string path) {
    if (lefrInit() != 0) {
        return NONE;
    }

    lefrSetVersionCbk(doubleCbk);
    lefrSetManufacturingCbk(doubleCbk);
    lefrSetUnitsCbk(unitsCbk);
    lefrSetLayerCbk(layerCbk);
    lefrSetMacroCbk(macroCbk);

    FILE* f;
    int res;
    if ((f = fopen(path.c_str(), "r")) == 0) {
        printf("Couldn't open file '%s'\n", path.c_str());
        return NONE;
    }

    LefData mydata;

    res = lefrRead(f, path.c_str(), &mydata);
    if (res != 0) {
        printf("LEF parser returns an error\n");
        return NONE;
    }

    fclose(f);

    return py::cast(mydata);
}

PYBIND11_MODULE(_core, m) {
    m.doc() = R"pbdoc(
        PyLEF
        ------

        .. currentmodule:: pylef

        .. autosummary::
           :toctree: _generate

           parse
    )pbdoc";

    m.def("parse", &lef_parse, R"pbdoc(
        Parse LEF file.

        Arguments:
            path (str): path to LEF file.
        Returns:
            LefData if successful, None on error.
    )pbdoc");

    py::class_<LefData>(m, "LefData")
        .def_property_readonly("version", [](LefData &d) -> py::object {
            if (d.has_version)
                return py::cast(d.version);
            return NONE;
        })
        .def_property_readonly("mfg_grid", [](LefData &d) -> py::object {
            if (d.has_mfg_grid)
                return py::cast(d.mfg_grid);
            return NONE;
        })
        .def_readwrite("units", &LefData::units)
        .def_readwrite("layers", &LefData::layers)
        .def_readwrite("macros", &LefData::macros);

#ifdef VERSION_INFO
    m.attr("__version__") = MACRO_STRINGIFY(VERSION_INFO);
#else
    m.attr("__version__") = "dev";
#endif
}
