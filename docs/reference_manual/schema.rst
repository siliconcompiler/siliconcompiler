Configuration Schema
=====================

**Important Words**

*dictionary*
 Defined as Python’s implementation of a data structure that is more generally known as an associative array. A dictionary consists of a collection of key-value pairs.

*list*
 Defined as Python's implementation of a data structure that is a mutable, or changeable, ordered sequence of elements.

*schema*
 A nested dictionary of SC configuration parameters.

*parameter*
 A leaf cell dictionary within the SC schema with a fixed set of key/value pairs defined by the schema.

*keypath*
 An ordered list of keys used to access an SC schema parameter.

*default*
 A special 'keyword' that signifies that the dictionary key in question can hold any non-reserved string value'

*keywords*
 Reserved strings that cannot be used as key names. Reserved keywords include the 'default' string and all strings defined by the parameter keys list below.

**Mandatory schema parameter keys**

*type*
 Parameter type. Supported types include Python compatible types ('int', 'float', and 'bool') and two custom file types ('file' and 'dir'). The 'file' and 'dir' type specify that the parameter is a 'regular' file or directory as described by Posix. All types except for the 'bool' types can be specified as a Python compatible list type by enclosing the type value in brackets. (ie. [str] specifies that the parameter is a list of strings. Additionally strings, integers, and floats can be tagged as tuples, using the Python parentheses like syntax (eg. [(float,float)] specifies a list of 2-float tuples).
 Input arguments and return values of the set/get/add core methods are encoded as native Python types. The JSON format does not have natively support all of these data types, so to ensure platform interoperability, all SC schema parameters are converted to strings before being exported to a json file. Additionally, note that the parameter value 'None' gets translated to the "null", True gets translated to "true", and False gets translated to "false before JSON export.

*defvalue*
 Parameter default value. The defvalue ensures that every defined schema parameter has a legal value even when not setup explicitly by the user. The default value must agree with the parameter 'type'. To specify that a parameter has no default value, set the defvalue to [] (ie empty list) for a list type and to 'null' or None for a non-list/scalar type.

*requirement*
 Parameter requirement. A string that specifies scenarios conditions and modes for which the parameter must return a non-empty value. Valid requirement keywords include 'all' and 'fpga/asic'. The 'all' keyword specifies that the parameter must always have a non-zero value before running a flow. The fpga/asic keyword specifies that that the parameter must have a non-empty value when the respective mode is being executed.  All Boolean values have a valid True/False default values and requirements of 'all. The vast majority of schema parameters have requirements of None and empty values which can be override by the user based on need.

*lock*
 Parameter lock policy. A Boolean value dictating whether the parameter can be modified by the set/get/add core API methods. A value of True specifiers that the parameter is locked and cannot be modified. Attempts to write to to a locked parameter shall result in an exception/error that blocks compilation progress.

*switch*
 Command line interface switch. A string that specifies the equivalent switch to use in command line interfaces. The switch string must start with a '-' and cannot contain spaces.

*short_help*
 Short one line parameter help string to be used in cases where brevity matters. Use cases include JSON dictionary dumps and command line interface help functions.

*help*
 A complete parameter help doc string. The help string serves as ground truth for describing the parameter functionality and should be used for long help descriptions in command line interface programs and for automated schema document generation. The long help can be pruned/filtered before the schema is dumped into a JSON file.

*example*
 Parameter use case examples. The field consists of a list of two strings, the first string containing an example for specifying the parameter using a command line switch, and a second string for setting the value using the core Python API. The examples can be pruned/filtered before the schema is dumped into a JSON file.


**File type mandatory keys**

*filehash*
 File hash value. The filehash holds machine calculated hash values for each file specified in the list of files within the 'value' field of the a parameter. The hash calculation and checking calculation policy is under control of the user. A SHA256 based hash calculation has been implemented in the hash core API method.

*date*
 File access date. The data value records the data stamp (string) of each item in the list of files within 'value' parameter field. The 'date' field cab be used to validate the provenance of the data used for compilation.

*author*
 File author. The author string records the person/entity that authored/crated each each item in the list of files within 'value' parameter field. The 'author' field cab be used to validate the provenance of the data used for compilation.

*signature*
 File signature. The signature string records a unique machine calculated string for each item in the list of files within 'value' parameter field. The 'signature' field cab be used to validate the provenance of the data used for compilation.


.. schemagen::
