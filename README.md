# Reversing Swift

This documentation was created to better understand the underlying layer of swift code execution. Here we'll cover how each Swift "concept" is actually translated into binary form.

You may run the following python script in IDA (Alt+F7) to help you
reverse the code more efficiently: [`ida_script.py`](./ida_script.py)

> **NOTE:** This script is practically is and probably always will be a work-in-progress, adding more and more types to make our lives better at reversing swift. Please submit PRs if you find stuff you're missing.

## Primitive types

```c
typedef long long s64;
typedef unsigned long long u64;

typedef s64 Int;
typedef u64 Bool;

struct Swift_String
{
  u64 _countAndFlagsBits;
  void *_object;
};

union Swift_ElementAny {
    Swift_String stringElement;
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
```

## Advanced types

### Struct

Structs are a kind of "optimized classes", whereas the actual struct data is stored
either on local registers or inside a global residing inside the `__common` section of the binary.

In general, as long as the struct's size <= `sizeof(u64) * 4`, it's whole data structure is returned on registers `X0`-`X3` from the init method and if we are required to re-purpose this registers, they are then immediately copied to their corresponding global residing inside the `__common` section.
Any struct bigger than that, is returned on register `X8` and is also immediately copied to the same global region. Meaning - it's enough to declare the global residing in this region with it's correct type in order to correctly reverse usages of that return value.

Please note `Swift::String` is also one such example of a Swift struct, whereas it has two members named:

- `_countAndFlagsBits` containing it's length OR'ed with flags bitmask
- `_object` containing the actual c-string

This means each time the data structure is returned, it's returned on `X0`-`X1` and passed on two registers each time aswell.

### Class

Class representation is somwhat more resembling C++. Each class contains a hidden `__allocating_init(RTTI *classRTTI)` method which allocates the required memory using `swift_allocObject` and only then calls the user's `init()` method. The RTTI reference is passed to the constructor and is stored as the first value inside the class (resembling C++'s `vptr` behavior).
Unlike C++, each declared method is virtual by definition, meaning, in order to reverse the usage of each class we'll have to create a correct struct for it.

For example:

```c
struct SomeClassRTTI {
    // This is actually an ObjC type!
    Class classObject;

    // More metadata about class layout...
    Unknown metadata;

    // methods
    (void (*)(SomeClass *self)) someMethod1;
    (void (*)(SomeClass *self)) someMethod2;
};

struct SomeClass {
    SomeClassRTTI *rtti;

    u64 ivar1;
    u64 ivar2;
    // ...
};
```

Getters and setters on the other hand, aren't represented their and are compiled as they would in C++ - normal global functions getting their `self` objects from `X20`.

### Type metadata

Many of the global swift objects are stored globally in the `__common` section. When initializing a global of any type, the following snippet is generated (assuming we allocate the global `globalVar` of type `globalVar_t`)

```c
// repalce TYPE with the actual type
void *typeMetadata = __swift_instantiateConcreteTypeFromMangledName(&demangling cache variable for type metadata for globalVar_t);
__swift_allocate_value_buffer(typeMetadata, &globalVar);
__swift_project_value_buffer(typeMetadata, &globalVar);
```

These two functions, `__swift_allocate_value_buffer` and `__swift_project_value_buffer` are basically to allocate the variable memory space and get a pointer to it, after consulting with the type metadata, if it allows the actual data to be in-place or use a pointer to an external space.

> **NOTE:** Telling of the object storage type is handled in offset `-0x08` from its type metadata, prividing a vtable used to allocate this space and tell where was this space allocated (That's why you'll notice while reversing these weird offsets).

### va_list

When calling a function which receives a variadic length of arguments, such as `print`, the compiler will use `_allocateUninitializedArray<A>(_:)` to create an array of type `Array<Any>` to create this as a single parameter. We represent this datatype as `Swift_ArrayAny`.

Let's examine now a call to `print(_:separator:terminator:)`.

We'll need to make this function signature as:

```c
void __fastcall print___separator_terminator__(Swift_ArrayAny *printString, Swift_String seperator, Swift_String terminator);
```

### Template functions

Many of the Swift functions often handle tempaltes. This is usually seen in method signature as: `doSomething<A>()`. In order to trigger the correct method to handle such invocations, the compiler adds an additional argument as the last one which acts the the "type metadata" - practically a vtable. While reversing, assuming we are only focused on understanding the code-flow, this parameter is usually not very important.

The templates signatures usually look something like this:

```c
// _finalizeUninitializedArray<A>(_:)
Swift_ArrayAny *__fastcall _allocateUninitializedArray_A(u64 count, void *arrayType);
```

And triggering these functions looks like this:

```c
// typeAny = &type metadata for Any + 8
// The type witness is located at offset 8 from the actual type information
_finalizeUninitializedArray<A>(_:)(array, typeAny);
```

## References

- <https://hex-rays.com/blog/igors-tip-of-the-week-51-custom-calling-conventions/>
- <https://www.swift.org/documentation/>
