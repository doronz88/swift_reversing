typedef long long s64;
typedef unsigned long long u64;

typedef s64 Int;
typedef u64 Bool;

typedef struct {
    s64 length; 
    char *ptr; 
} String;

typedef struct {
    s64 intValue;
    char *ptr;
    u64 unknown;
    s64 type;
} Any;

typedef struct {
    s64 length;
    Any *items;
} ArrayAny;


// String.init(_builtinStringLiteral:utf8CodeUnitCount:isASCII:)
String __usercall __spoils<> String_init__builtinStringLiteral_utf8CodeUnitCount_isASCII__@<X1:X0>(char *_builtinStringLiteral@<X0>, u64 utf8CodeUnitCount@<X1>, u64 isASCII@<X2>);

// _allocateUninitializedArray<A>(_:)
ArrayAny __usercall __spoils<> _allocateUninitializedArray_A_____@<X1:X0>();

// default argument 1 of print(_:separator:terminator:)
String __usercall __spoils<> default_argument_1_of_print___separator_terminator__@<X1:X0>();

// default argument 2 of print(_:separator:terminator:)
String __usercall __spoils<> default_argument_2_of_print___separator_terminator__@<X1:X0>();

// print(_:separator:terminator:)
void __usercall __spoils<> print___separator_terminator__(ArrayAny *items@<X0>, String separator@<X2:X1>, String terminator@<X4:X3>); 
