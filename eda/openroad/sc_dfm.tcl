


#########################
# Delete Obstructions
#########################
set db [ord::get_db]
set chip [$db getChip]
set block [$chip getBlock]
set obstructions [$block getObstructions]
foreach obstruction $obstructions {
    odb::dbObstruction_destroy $obstruction
}

#########################
# Delete Obstructions
#########################

#{
#    "layers" : {
#        "met1" : {
#            "layer":                   36,
#            "name":                    "met1",
#            "dir":                     "H",
#            "datatype":                 0,
#            "space_to_outline":         70,
#            "non-opc": {
#                "datatype":             0,
#                "width":                [2.00, 1.00, 0.58, 0.3],
#                "height":               [2.00, 1.00, 0.58, 0.3],
#                "space_to_fill":        0.3,
#                "space_to_non_fill":    3
#            }
#        },

#density_fill -rules "fill.json'


