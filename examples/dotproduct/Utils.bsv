package Utils;

ActionValue #(Bit #(32)) cur_cycle = actionvalue
        Bit #(32) t <- $stime;
        return t / 10;
endactionvalue;

endpackage: Utils
