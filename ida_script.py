from typing import Generator

import ida_bytes
import ida_funcs
import ida_hexrays
import ida_kernwin
import ida_regfinder
import idc

SWIFT_PLUGIN_HOTKEY = 'Ctrl+5'

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


def set_comment(ea: int, comment: str) -> None:
    print(f'set cmt: 0x{ea:x} "{comment}"')
    ida_bytes.set_cmt(ea, comment, 0)
    cfunc = ida_hexrays.decompile(ea)
    eamap = cfunc.get_eamap()
    try:
        decomp_obj_addr = eamap[ea][0].ea

        tl = ida_hexrays.treeloc_t()
        tl.ea = decomp_obj_addr
        for itp in range(ida_hexrays.ITP_SEMI, ida_hexrays.ITP_COLON):
            tl.itp = itp
            cfunc.set_user_cmt(tl, comment)
            if not cfunc.has_orphan_cmts():
                break
    except:
        print('failed')
        return

    cfunc.save_user_cmts()


def fix_swift_types() -> None:
    idc.parse_decls(DECLS)

    for name, sig in FUNCTIONS_SIGNATURES.items():
        ea = idc.get_name_ea_simple(name)
        if ea == idc.BADADDR:
            continue
        idc.SetType(ea, sig)


def ida_find_all(expression: str, start_ea: int, end_ea: int) -> Generator[int, None, None]:
    ea = idc.find_binary(start_ea, idc.SEARCH_DOWN | idc.SEARCH_REGEX, expression)
    while ea != idc.BADADDR and ea < end_ea:
        yield ea
        ea = idc.find_binary(ea + 1, idc.SEARCH_DOWN | idc.SEARCH_REGEX, expression)


def add_swift_string_comments() -> None:
    func = ida_funcs.get_func(idc.get_screen_ea())

    # search for:
    #   SUB             Rd, Rt, #0x20
    #   ORR             X1, X8,  # 0x8000000000000000
    for ea in ida_find_all('?? ?? 00 D1 ?? ?? 41 B2', func.start_ea, func.end_ea):
        orr_ea = ea + 4
        reg_value = idc.get_operand_value(orr_ea, 1)
        string_assignment_ea = ida_regfinder.find_reg_value(orr_ea, reg_value)
        string = idc.get_strlit_contents(string_assignment_ea + 0x20, -1, 0).decode()
        set_comment(orr_ea, string)


def main() -> None:
    fix_swift_types()

    ida_kernwin.del_idc_hotkey(SWIFT_PLUGIN_HOTKEY)
    ida_kernwin.add_hotkey(SWIFT_PLUGIN_HOTKEY, add_swift_string_comments)


if __name__ == '__main__':
    main()
