# Generic keyword/flag/positional argument parser for sc procs.
#
# A single entry point, sc::parse_args, drives parsing from a declarative spec.
# It fills a result dict (via upvar) and also returns it, so both styles work:
#
#     proc my_proc { args } {
#         sc::parse_args opts {
#             -name      {default "top"}
#             -threads   {default 1}
#             -mode      {default "fast" choices {fast slow}}
#             -outdir    {required}
#             -verbose   {flag}
#             positional {min 1 max -1 name files}
#         } $args
#
#         puts "name:    [dict get $opts name]"
#         puts "verbose: [dict get $opts verbose]"
#         foreach f [dict get $opts files] { puts "file: $f" }
#     }
#
# Spec format (a flat list of {key attrs} pairs):
#   Option keys start with "-". Their attrs list may contain:
#     default <value>   value used when the option is not supplied (else "")
#     flag              boolean option that consumes no value; present => 1,
#                       absent => its default (0 unless overridden)
#     required          error if the option is not supplied
#     choices {a b ...} error unless the supplied value is one of these
#
#   The reserved key "positional" configures leftover (non-option) arguments:
#     min  <n>          minimum required (default 0)
#     max  <n>          maximum allowed, -1 for unlimited (default -1)
#     name <key>        result key for the collected list (default "positional")
#
# Parsing notes:
#   - Result keys have the leading "-" stripped (dict get $opts name).
#   - "--" terminates option parsing; everything after it is positional.
#   - An unknown "-token" is an error; a bare token is treated as positional.
#   - A value option always consumes the next token as its value, even if that
#     token starts with "-" (so negative numbers work).

namespace eval sc {
    namespace eval utils {
        # Best-effort name of the proc that called the proc invoking get_caller.
        # The optional level shifts further up the call stack (0 == direct
        # caller's caller). Returns "" when the stack is too shallow.
        proc get_caller { { level 0 } } {
            set frame [expr { -2 - $level }]
            if { [info level] >= -$frame } {
                return [lindex [info level $frame] 0]
            }
            return ""
        }
    }

    proc parse_args { result_var spec arglist } {
        upvar 1 $result_var result

        set caller [sc::utils::get_caller]
        if { $caller eq "" } {
            set caller "sc::parse_args"
        }

        # Split the spec into option definitions and the positional definition.
        set opt_spec [dict create]
        set pos_spec {}
        foreach { key attrs } $spec {
            if { $key eq "positional" } {
                set pos_spec $attrs
            } elseif { [string index $key 0] eq "-" } {
                dict set opt_spec $key $attrs
            } else {
                error "$caller: invalid spec key \"$key\", options must start with \"-\""
            }
        }

        # Seed the result with defaults.
        set result [dict create]
        dict for { opt attrs } $opt_spec {
            set name [string range $opt 1 end]
            if { [dict exists $attrs default] } {
                dict set result $name [dict get $attrs default]
            } elseif { "flag" in $attrs } {
                dict set result $name 0
            } else {
                dict set result $name ""
            }
        }

        set positional [list]
        set provided [list]

        # Walk the supplied arguments.
        set n [llength $arglist]
        for { set i 0 } { $i < $n } { incr i } {
            set token [lindex $arglist $i]

            if { $token eq "--" } {
                # Everything after "--" is positional.
                foreach val [lrange $arglist [expr { $i + 1 }] end] {
                    lappend positional $val
                }
                break
            }

            if { [string index $token 0] eq "-" && [dict exists $opt_spec $token] } {
                set attrs [dict get $opt_spec $token]
                set name [string range $token 1 end]
                lappend provided $token

                if { "flag" in $attrs } {
                    dict set result $name 1
                    continue
                }

                # Value option: consume the next token.
                incr i
                if { $i >= $n } {
                    error "$caller: option \"$token\" requires a value"
                }
                set value [lindex $arglist $i]

                if { [dict exists $attrs choices] } {
                    set choices [dict get $attrs choices]
                    if { $value ni $choices } {
                        error "$caller: invalid value \"$value\" for \"$token\",\
                            must be one of: [join $choices {, }]"
                    }
                }

                dict set result $name $value
            } elseif { [string index $token 0] eq "-" } {
                error "$caller: unknown option \"$token\""
            } else {
                lappend positional $token
            }
        }

        # Enforce required options.
        dict for { opt attrs } $opt_spec {
            if { "required" in $attrs && $opt ni $provided } {
                error "$caller: missing required option \"$opt\""
            }
        }

        # Validate and store positional arguments.
        set pos_min 0
        set pos_max -1
        set pos_name "positional"
        if { [dict exists $pos_spec min] } {
            set pos_min [dict get $pos_spec min]
        }
        if { [dict exists $pos_spec max] } {
            set pos_max [dict get $pos_spec max]
        }
        if { [dict exists $pos_spec name] } {
            set pos_name [dict get $pos_spec name]
        }

        set pos_count [llength $positional]
        if { $pos_count < $pos_min } {
            error "$caller: expected at least $pos_min positional argument(s),\
                got $pos_count"
        }
        if { $pos_max >= 0 && $pos_count > $pos_max } {
            error "$caller: expected at most $pos_max positional argument(s),\
                got $pos_count"
        }
        dict set result $pos_name $positional

        return $result
    }
}
