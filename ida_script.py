import idc

DECLS = """
typedef long long s64;
typedef unsigned long long u64;

typedef s64 Int;
typedef u64 Bool;

struct Swift::String
{
  u64 _countAndFlagsBits;
  void *_object;
};

union Swift_ElementAny {
    Swift::String stringElement;
};

struct Swift_Any {
    Swift_ElementAny element;
    u64 unknown;
    s64 type;
};

struct Swift_ArrayAny {
    s64 length;
    Swift_Any *items;
};
"""

FUNCTIONS_SIGNATURES = {
    # Foundation.URL
    '_$s10Foundation3URLV6stringACSgSSh_tcfC':
        'void __swiftcall URL_init_string__(__int64 *__return_ptr, Swift::String url)',
    '_$s10Foundation3URLV4pathSSvg':
        'Swift::String __usercall URL_path_getter@<X0:X1>(void *@<X20>)',
    '_$s10Foundation3URLV22appendingPathComponentyACSSF': '__int64 __usercall URL_appendingPathComponent____@<X0>(void *@<X20>, Swift::String@<X0:X1>)',

    # print()
    '_$ss5print_9separator10terminatoryypd_S2StF':
        'void __fastcall print___separator_terminator__(Swift_ArrayAny *, Swift::String, Swift::String)',
    '_$ss10debugPrint_9separator10terminatoryypd_S2StFfA0_':
        'Swift::String default_argument_1_of_debugPrint___separator_terminator__(void)',

    # Arrays
    '_$ss27_allocateUninitializedArrayySayxG_BptBwlF':
        'Swift_ArrayAny *__fastcall _allocateUninitializedArray_A(u64 count, void *arrayType)',
    '_$ss27_finalizeUninitializedArrayySayxGABnlF':
        'Swift_ArrayAny *__fastcall _finalizeUninitializedArray_A(Swift_ArrayAny *, void *arrayType)',

    # Bridging
    '_$sSS10FoundationE36_unconditionallyBridgeFromObjectiveCySSSo8NSStringCSgFZ':
        'Swift::String __fastcall static_String__unconditionallyBridgeFromObjectiveC____(id)',
    '_$sSS10FoundationE19_bridgeToObjectiveCSo8NSStringCyF':
        'NSString __swiftcall String__bridgeToObjectiveC__(Swift::String)',
    '_swift_bridgeObjectRelease': 'void swift_bridgeObjectRelease(id)',
    '_swift_bridgeObjectRetain': 'id swift_bridgeObjectRetain(id)',

    # Allocating global objects
    '___swift_allocate_value_buffer': 'void *__fastcall __swift_allocate_value_buffer(void *typeInfo, void **pObject)',
    '___swift_project_value_buffer': '__int64 __fastcall __swift_project_value_buffer(void *typeInfo, void *object)',

    # String operations
    '_$ss27_stringCompareWithSmolCheck__9expectingSbs11_StringGutsV_ADs01_G16ComparisonResultOtF':
        '__int64 __fastcall _stringCompareWithSmolCheck_____expecting__(Swift::String, Swift::String, _QWORD)',
    '_$sSS9hasPrefixySbSSF': 'Swift::Bool __swiftcall String_hasPrefix____(Swift::String, Swift::String)',
    '_$sSS12ProxymanCoreE5toSHASSSgyF': 'Swift::String_optional __swiftcall String_toSHA__(Swift::String)',
    '_$sSy10FoundationE4data5using20allowLossyConversionAA4DataVSgSSAAE8EncodingV_SbtF': 'Swift::String __fastcall StringProtocol_data_using_allowLossyConversion__(_QWORD, _QWORD, _QWORD, _QWORD);',
    '_$sSS5countSivg': '__int64 __usercall String_count_getter@<X0>(void *@<X20>, Swift::String@<X0:X1>)',
    '_$sSS10FoundationE10contentsOf8encodingSSAA3URLVh_SSAAE8EncodingVtKcfC': 'Swift::String __usercall __spoils<X21> String_init_contentsOf_encoding__@<X0:X1>(Swift::String@<X0:X1>)',

    # Data operations
    '_$s10Foundation4DataV19_bridgeToObjectiveCSo6NSDataCyF': 'NSData __swiftcall Data__bridgeToObjectiveC__(Swift::String)',
    '_$s10Foundation4DataV11referencingACSo6NSDataCh_tcfC': 'Swift::String __fastcall Data_init_referencing__(_QWORD)',

    # String interpolation
    '_$ss26DefaultStringInterpolationV13appendLiteralyySSF': 'Swift::Void __usercall DefaultStringInterpolation_appendLiteral____(void *@<X20>, Swift::String@<X0:X1>)',
    '_$ss26DefaultStringInterpolationV06appendC0yyxlF': 'Swift::Void __usercall DefaultStringInterpolation_appendInterpolation_A(void *@<X20>, Swift::String@<X0:X1>)',
    '_$ss26DefaultStringInterpolationV15literalCapacity18interpolationCountABSi_SitcfC':
        'Swift::String __swiftcall __spoils<X8> DefaultStringInterpolation_init_literalCapacity_interpolationCount__(_QWORD, _QWORD)',
    '_$sSS19stringInterpolationSSs013DefaultStringB0V_tcfC':
        'Swift::String __fastcall String_init_stringInterpolation__(Swift::String)',
    '_$ss26DefaultStringInterpolationV15literalCapacity18interpolationCountABSi_SitcfC':
        'Swift::String __fastcall DefaultStringInterpolation_init_literalCapacity_interpolationCount__(_QWORD, _QWORD)',
}


def fix_swift_types() -> None:
    idc.parse_decls(DECLS)

    for name, sig in FUNCTIONS_SIGNATURES.items():
        ea = idc.get_name_ea_simple(name)
        if ea == idc.BADADDR:
            continue
        idc.SetType(ea, sig)


if __name__ == '__main__':
    fix_swift_types()
