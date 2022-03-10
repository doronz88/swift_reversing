# Reversing Swift

This documentation was created to better understand the underlying layer of swift code execution. Here we'll cover how each Swift "concept" is actually translated into binary form.

You may import the following C header file to IDA (Ctrl+F9) to help you
reverse the code more efficiently: [ida_header.h](./ida_header.h)

## Primitive types

```c

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

// Array<Any>
typedef struct {
    s64 length;
    Any *items;
} ArrayAny;

typedef struct {
    s64 length;
    TYPE *items;
} Array<TYPE>;

```

## Advanced types

### Struct

Structs are a kind of "optimized classes", whereas the actual struct data is stored
either on local registers or inside a global residing inside the `__common` section of the binary.

In general, as long as the struct's size <= `sizeof(u64) * 4`, it's whole data structure is returned on registers `X0`-`X3` from the init method and if we are required to re-purpose this registers, they are then immediately copied to their corresponding global residing inside the `__common` section.
Any struct bigger than that, is returned on register `X8` and is also immediately copied to the same global region. Meaning - it's enough to declare the global residing in this region with it's correct type in order to correctly reverse usages of that return value.

Since `String` is also a struct, created for instance using: `String.init(_builtinStringLiteral:utf8CodeUnitCount:isASCII:)`, in order to declare this function properly inside IDA, we'll have to use the following horrible line:

```c
String __usercall __spoils<> String_init__builtinStringLiteral_utf8CodeUnitCount_isASCII__@<X1:X0>(char *_builtinStringLiteral@<X0>, u64 utf8CodeUnitCount@<X1>, u64 isASCII@<X2>);
```

Now to explain:

* This isn't a normal calling convention (such as `__cdecl`),  so we are required to specify it as `__usercall`.
* The return type of this function is a `Struct` object of size <= `sizeof(u64) * 4`, meaning it's returned using `X0` & `X1`.
* Since this is a `__usercall`, we are required to spcify the register which each argument is taken from.

In order to refer to `self` within the method:

* If object's size <= `sizeof(u64) * 4`, its arguments are passed as normal parameters each time.
* We mark this functions as one which "spoils" since it touches non-standard registers.
* Otherwise, `X20` is used for referring `self` and rest of arguments are packed as normal.

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

### va_list

When calling a function which receives a variadic length of arguments, such as `print`, the compiler will use `_allocateUninitializedArray<A>(_:)` to create an array of type `Array<Any>` to create this as a single parameter.

Let's examine now a call to `print(_:separator:terminator:)`.

We'll need to make this function signature as:

```c
void __usercall __spoils<> print___separator_terminator__(ArrayAny *items@<X0>, String separator@<X2:X1>, String terminator@<X4:X3>)
```

What this horrible piece of code means is:

* This is also a `__usercall`.
* First argument is a `va_list` which is actually an `ArrayAny`.
* Second and thrid arguments are of type `String` - which is again a `Struct` object of two elements that are passed via two registers (since its size is <= `sizeof(u64) * 4`))

## References

* <https://hex-rays.com/blog/igors-tip-of-the-week-51-custom-calling-conventions/>
* <https://www.swift.org/documentation/>
