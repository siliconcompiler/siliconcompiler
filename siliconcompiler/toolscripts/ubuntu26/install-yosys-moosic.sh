#!/bin/bash

set -ex

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

# Install prerequisites only when they are missing
. "${src_path}/_prereqs.sh"

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL=sudo
else
    SUDO_INSTALL=""
fi

install_prereqs git

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool yosys-moosic --field git-url) yosys-moosic
cd yosys-moosic
git checkout $(python3 ${src_path}/_tools.py --tool yosys-moosic --field git-commit)

# Yosys 0.71 made IdString an index into a per-design TwinePool: log_id() and
# IdString::c_str() are gone, a std::string no longer converts to an IdString,
# and ID() takes only names in kernel/constids.inc ($_NMUX was a typo).
git apply - <<'EOF'
diff --git a/src/cmd_direct_locking.cpp b/src/cmd_direct_locking.cpp
index ce3303a..fbfd7f6 100644
--- a/src/cmd_direct_locking.cpp
+++ b/src/cmd_direct_locking.cpp
@@ -31,15 +31,15 @@ struct LogicLockingDirectLockingPass : public Pass {
 					break;
 				std::string name = args[++argidx];
 				log("<%s> will be xored\n", name.c_str());
-				gates_to_lock.emplace_back(name);
+				gates_to_lock.emplace_back(design->twines().add(name));
 				continue;
 			}
 			if (arg == "-mix-gate") {
 				if (argidx + 2 >= args.size())
 					break;
-				IdString n1 = args[++argidx];
-				IdString n2 = args[++argidx];
-				log("<%s> and <%s> will be mixed\n", n1.c_str(), n2.c_str());
+				IdString n1 = design->twines().add(args[++argidx]);
+				IdString n2 = design->twines().add(args[++argidx]);
+				log("<%s> and <%s> will be mixed\n", design->twines().str(n1), design->twines().str(n2));
 				gates_to_mix.emplace_back(n1, n2);
 				continue;
 			}
diff --git a/src/cmd_show.cpp b/src/cmd_show.cpp
index cc883a9..f49397e 100644
--- a/src/cmd_show.cpp
+++ b/src/cmd_show.cpp
@@ -56,12 +56,12 @@ struct LogicLockingShowPass : public Pass {
 			SigBit sig = locked_signals[i];
 			std::stringstream sig_repr;
 			if (sig.wire) {
-				sig_repr << log_id(sig.wire->name);
+				sig_repr << sig.wire->name.unescape();
 				if (sig.wire->width > 1) {
 					sig_repr << "[" << sig.offset << "]";
 				}
 			}
-			log("\t%d\t%s\t%s\n", i + 1, log_id(cell->name), sig_repr.str().c_str());
+			log("\t%d\t%s\t%s\n", i + 1, cell->name.unescape(), sig_repr.str().c_str());
 		}
 	}
 
diff --git a/src/command_utils.cpp b/src/command_utils.cpp
index 9c1eafc..b61401f 100644
--- a/src/command_utils.cpp
+++ b/src/command_utils.cpp
@@ -173,7 +173,7 @@ Yosys::RTLIL::IdString get_output_portname(Yosys::RTLIL::Cell *cell)
 			return it.first;
 		}
 	}
-	Yosys::log_error("No output port found on cell %s\n", Yosys::log_id(cell->name));
+	Yosys::log_error("No output port found on cell %s\n", cell->name.unescape());
 }
 
 Yosys::RTLIL::SigBit get_output_signal(Yosys::RTLIL::Cell *cell)
diff --git a/src/gate_insertion.cpp b/src/gate_insertion.cpp
index cd46d72..06ead31 100644
--- a/src/gate_insertion.cpp
+++ b/src/gate_insertion.cpp
@@ -33,7 +33,7 @@ Cell *insert_xor_locking_gate(Module *module, Cell *locked_cell, IdString locked
 	locked_cell->unsetPort(locked_port);
 	locked_cell->setPort(locked_port, locked_bitwire);
 
-	log_debug("Inserting locking gate at cell %s\n", log_id(locked_cell->name));
+	log_debug("Inserting locking gate at cell %s\n", locked_cell->name.unescape());
 
 	if (key_value) {
 		return module->addXnor(NEW_ID, locked_bit, key_bit, out_bit);
@@ -67,7 +67,7 @@ Cell *insert_mux_locking_gate(Module *module, Cell *locked_cell1, IdString locke
 	locked_cell1->unsetPort(locked_port1);
 	locked_cell1->setPort(locked_port1, locked_bitwire);
 
-	log_debug("Inserting mixing gate at cell %s with cell %s\n", log_id(locked_cell1->name), log_id(locked_cell2->name));
+	log_debug("Inserting mixing gate at cell %s with cell %s\n", locked_cell1->name.unescape(), locked_cell2->name.unescape());
 
 	if (key_value) {
 		return module->addMux(NEW_ID, mix_bit, locked_bit, key_bit, out_bit);
@@ -78,9 +78,9 @@ Cell *insert_mux_locking_gate(Module *module, Cell *locked_cell1, IdString locke
 
 Wire *add_key_input(Module *module, int width, const std::string &port_name)
 {
-	IdString name = escape_id(port_name);
+	IdString name = module->twines().add(escape_id(port_name));
 	if (module->wire(name)) {
-		log_cmd_error("Wire %s is already present in the module. Did you run logic locking twice?\n", log_id(name));
+		log_cmd_error("Wire %s is already present in the module. Did you run logic locking twice?\n", module->twines().unescaped_str(name));
 	}
 	Wire *wire = module->addWire(name, width);
 	wire->port_input = true;
@@ -119,7 +119,7 @@ void lock_gates(Module *module, const std::vector<IdString> &names, SigSpec key,
 		if (cell) {
 			cells.push_back(cell);
 		} else {
-			log_cmd_error("Cell %s not found in module\n", name.c_str());
+			log_cmd_error("Cell %s not found in module\n", module->twines().str(name));
 		}
 	}
 	lock_gates(module, cells, key, key_values);
@@ -158,9 +158,9 @@ void mix_gates(Module *module, const std::vector<std::pair<IdString, IdString>>
 		if (c1 && c2) {
 			cells.emplace_back(c1, c2);
 		} else if (!c1) {
-			log_cmd_error("Cell %s not found in module\n", names[i].first.c_str());
+			log_cmd_error("Cell %s not found in module\n", module->twines().str(names[i].first));
 		} else {
-			log_cmd_error("Cell %s not found in module\n", names[i].second.c_str());
+			log_cmd_error("Cell %s not found in module\n", module->twines().str(names[i].second));
 		}
 	}
 	mix_gates(module, cells, key, key_values);
diff --git a/src/logic_locking_analyzer.cpp b/src/logic_locking_analyzer.cpp
index e3458f9..5faa63f 100644
--- a/src/logic_locking_analyzer.cpp
+++ b/src/logic_locking_analyzer.cpp
@@ -185,7 +185,7 @@ void LogicLockingAnalyzer::init_wire_to_wires()
 			}
 			wire_to_wires_[sig_b].emplace(sig_a);
 
-			log_debug("Adding direct connection %s --> %s\n", log_id(sig_b.wire->name), log_id(sig_a.wire->name));
+			log_debug("Adding direct connection %s --> %s\n", sig_b.wire->name.unescape(), sig_a.wire->name.unescape());
 		}
 	}
 }
@@ -205,7 +205,7 @@ void LogicLockingAnalyzer::init_aig()
 	}
 	for (SigBit bit : comb_inputs_) {
 		wire_to_aig_.emplace(bit, aig_.getInput(i));
-		log_debug("Adding input %s --> %d\n", log_id(bit.wire->name), aig_.getInput(i).variable());
+		log_debug("Adding input %s --> %d\n", bit.wire->name.unescape(), aig_.getInput(i).variable());
 		++i;
 		dirty_bits_.insert(bit);
 	}
@@ -218,12 +218,12 @@ void LogicLockingAnalyzer::init_aig()
 			SigBit sig_a = a[i];
 			SigBit sig_b = b[i];
 			if (sig_a.is_wire() && !sig_b.is_wire()) {
-				log_debug("Adding constant wire %s\n", log_id(sig_a.wire->name));
+				log_debug("Adding constant wire %s\n", sig_a.wire->name.unescape());
 				wire_to_aig_[sig_a] = sig_b.data == State::S1 ? Lit::one() : Lit::zero();
 				dirty_bits_.emplace(sig_a);
 			}
 			if (sig_b.is_wire() && !sig_a.is_wire()) {
-				log_warning("Detected connection of wire %s driving a constant; skipped.\n", log_id(sig_b.wire->name));
+				log_warning("Detected connection of wire %s driving a constant; skipped.\n", sig_b.wire->name.unescape());
 			}
 		}
 	}
@@ -270,14 +270,14 @@ void LogicLockingAnalyzer::init_aig()
 	for (SigBit bit : comb_outputs_) {
 		if (!wire_to_aig_.count(bit)) {
 			if (bit.wire) {
-				log_error("Missing output %s\n", log_id(bit.wire->name));
+				log_error("Missing output %s\n", bit.wire->name.unescape());
 			} else {
 				log_error("Missing constant output\n");
 			}
 		}
 
 		if (bit.wire) {
-			log_debug("Adding output %s --> %d\n", log_id(bit.wire->name), wire_to_aig_.at(bit).variable());
+			log_debug("Adding output %s --> %d\n", bit.wire->name.unescape(), wire_to_aig_.at(bit).variable());
 		} else {
 			log_debug("Adding constant output\n");
 		}
@@ -301,11 +301,11 @@ void LogicLockingAnalyzer::report_conversion_issues() const
 					SigBit input = conn.second;
 					if (!wire_to_aig_.count(input)) {
 						if (input.wire) {
-							log("Missing port %s on cell %s (output %s) with wire %s\n", log_id(id), log_id(c->name),
-							    log_id(output.wire->name), log_id(input.wire->name));
+							log("Missing port %s on cell %s (output %s) with wire %s\n", c->twines().unescaped_str(id), c->name.unescape(),
+							    output.wire->name.unescape(), input.wire->name.unescape());
 						} else {
-							log("Missing port %s on cell %s (output %s) with value %d\n", log_id(id), log_id(c->name),
-							    log_id(output.wire->name), input.data);
+							log("Missing port %s on cell %s (output %s) with value %d\n", c->twines().unescaped_str(id), c->name.unescape(),
+							    output.wire->name.unescape(), input.data);
 						}
 					}
 				}
@@ -384,7 +384,7 @@ void LogicLockingAnalyzer::cell_to_aig(Cell *cell)
 			else if (cell->type.in(ID($_ORNOT_)))
 				res = aig_.addOr(sig_a, sig_b.inv());
 			else
-				log_cmd_error("Cell type %s not handled", log_id(cell->type));
+				log_cmd_error("Cell type %s not handled", cell->type.unescape());
 
 			wire_to_aig_[cell->getPort(ID::Y)] = res;
 			dirty_bits_.insert(cell->getPort(ID::Y));
@@ -392,7 +392,7 @@ void LogicLockingAnalyzer::cell_to_aig(Cell *cell)
 	} else if (cell->type.in(ID($mux), ID($_MUX_), ID($_NMUX_))) {
 		if (has_a && has_b && has_s) {
 			Lit res = aig_.addMux(sig_s, sig_a, sig_b);
-			if (cell->type.in(ID($_NMUX))) {
+			if (cell->type.in(ID($_NMUX_))) {
 				res = res.inv();
 			}
 			wire_to_aig_[cell->getPort(ID::Y)] = res;
@@ -423,11 +423,11 @@ void LogicLockingAnalyzer::cell_to_aig(Cell *cell)
 			dirty_bits_.insert(cell->getPort(ID::Y));
 		}
 	} else {
-		log_cmd_error("Cell %s has type %s which is not supported. Did you run synthesis before?\n", log_id(cell->name), log_id(cell->type));
+		log_cmd_error("Cell %s has type %s which is not supported. Did you run synthesis before?\n", cell->name.unescape(), cell->type.unescape());
 	}
 	if (wire_to_aig_.count(cell->getPort(ID::Y))) {
-		log_debug("Converting cell %s of type %s, wire %s\n", log_id(cell->name), log_id(cell->type),
-			  log_id(cell->getPort(ID::Y).as_bit().wire->name));
+		log_debug("Converting cell %s of type %s, wire %s\n", cell->name.unescape(), cell->type.unescape(),
+			  cell->getPort(ID::Y).as_bit().wire->name.unescape());
 		wire_to_driver_[cell->getPort(ID::Y)] = cell;
 	}
 }
@@ -480,7 +480,7 @@ dict<SigBit, State> LogicLockingAnalyzer::get_output_state() const
 		if (state_.count(bit)) {
 			ret[bit] = state_.at(bit);
 		} else {
-			log_error("Signal not found in output %s\n", log_id(wire->name));
+			log_error("Signal not found in output %s\n", wire->name.unescape());
 		}
 	}
 	for (RTLIL::Cell *cell : module_->cells()) {
@@ -491,7 +491,7 @@ dict<SigBit, State> LogicLockingAnalyzer::get_output_state() const
 					if (state_.count(bit)) {
 						ret[bit] = state_.at(bit);
 					} else {
-						log_error("Signal not found in cell input %s\n", log_id(cell->name));
+						log_error("Signal not found in cell input %s\n", cell->name.unescape());
 					}
 				}
 			}
@@ -580,7 +580,7 @@ std::vector<std::uint64_t> LogicLockingAnalyzer::simulate_basic(int tv, const po
 		for (RTLIL::Wire *wire : module_->wires()) {
 			SigBit bit(wire);
 			if (!state_.count(bit)) {
-				log_error("\tWire %s not simulated\n", log_id(wire->name));
+				log_error("\tWire %s not simulated\n", wire->name.unescape());
 			}
 		}
 		for (auto it : wire_to_aig_) {
@@ -679,7 +679,7 @@ void LogicLockingAnalyzer::simulate_cell(RTLIL::Cell *cell)
 			return;
 		}
 
-		log_cmd_error("Cell %s of type %s cannot be evaluated", log_id(cell->name), log_id(cell->type));
+		log_cmd_error("Cell %s of type %s cannot be evaluated", cell->name.unescape(), cell->type.unescape());
 	}
 }
 
@@ -856,11 +856,11 @@ std::vector<std::pair<Cell *, Cell *>> LogicLockingAnalyzer::compute_pairwise_se
 
 	std::vector<std::pair<Cell *, Cell *>> ret;
 	for (int i = 0; i < GetSize(signals); ++i) {
-		log_debug("\tSimulating %s (%d/%d)\n", log_id(cells[i]->name), i + 1, GetSize(signals));
+		log_debug("\tSimulating %s (%d/%d)\n", cells[i]->name.unescape(), i + 1, GetSize(signals));
 		for (int j = i + 1; j < GetSize(signals); ++j) {
 			if (is_pairwise_secure(signals[i], signals[j], ignore_duplicates)) {
 				ret.emplace_back(cells[i], cells[j]);
-				log_debug("\t\tPairwise secure %s <-> %s\n", log_id(cells[i]->name), log_id(cells[j]->name));
+				log_debug("\t\tPairwise secure %s <-> %s\n", cells[i]->name.unescape(), cells[j]->name.unescape());
 			}
 		}
 	}
@@ -876,7 +876,7 @@ std::vector<std::pair<Cell *, Cell *>> LogicLockingAnalyzer::compute_pairwise_se
 		++nb_secure[p.second];
 	}
 	for (int i = 0; i < GetSize(cells); ++i) {
-		log_debug("\tCell %s: %d pairwise secure\n", log_id(cells[i]->name), nb_secure[cells[i]]);
+		log_debug("\tCell %s: %d pairwise secure\n", cells[i]->name.unescape(), nb_secure[cells[i]]);
 	}
 	return ret;
 }
diff --git a/src/sat_attack.cpp b/src/sat_attack.cpp
index 18f2041..e43983e 100644
--- a/src/sat_attack.cpp
+++ b/src/sat_attack.cpp
@@ -474,10 +474,10 @@ std::vector<bool> SatAttack::toAigInputs(const std::vector<bool> &inputs, const
 
 RTLIL::Wire *SatAttack::getKeyPort()
 {
-	IdString name = RTLIL::escape_id(keyPortName_);
+	std::string name = RTLIL::escape_id(keyPortName_);
 	RTLIL::Wire *keyPort = mod_->wire(name);
 	if (keyPort == nullptr) {
-		log_cmd_error("Could not find port %s in module %s\n", keyPortName_.c_str(), log_id(mod_->name));
+		log_cmd_error("Could not find port %s in module %s\n", keyPortName_.c_str(), mod_->name.unescape());
 	}
 	return keyPort;
 }
EOF

make -j${NPROC:-$(nproc)}
$SUDO_INSTALL make install
cd -
