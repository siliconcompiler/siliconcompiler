package glibc_random_helpers is
    procedure srand (v : integer);
    attribute foreign of srand : procedure is "VHPIDIRECT srand";

    function random return integer;
    attribute foreign of random : function is "VHPIDIRECT random";
end glibc_random_helpers;

package body glibc_random_helpers is
    procedure srand (v : integer) is
    begin
        assert false severity failure;
    end srand;

    function random return integer is
    begin
        assert false severity failure;
    end random;
end glibc_random_helpers;
