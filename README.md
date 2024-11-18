# Reversing Swift

This documentation was created to better understand the underlying layer of swift code execution.
Here we'll cover how each Swift "concept" is actually translated into binary form.

You may run the following python script in IDA (Alt+F7) to help you
reverse the code more efficiently: [`swift.py`](https://github.com/doronz88/ida-scripts/blob/main/swift.py)

The script adds the `Ctrl+5` HotKey to quickly parse the `Swift::String` occurences within the current function.  

> **NOTE:** This script is practically is and probably always will be a work-in-progress,
> adding more and more types to make our lives better at reversing swift.
> Please submit PRs if you find stuff you're missing.

## Swift segments

**NOTE: Read this <https://github.com/swiftlang/swift/blob/main/docs/Lexicon.md> before starting with this section**

One of the most important ideas introduced in Swift was the use of "relative pointers".
This idea enables these pointers not to be rebased thus improving efficiency.
This can be demonstrated in: <https://github.com/swiftlang/swift/blob/main/include/swift/Basic/RelativePointer.h>.

As stated:

```none
Some data structures emitted by the Swift compiler use relative indirect addresses in order to minimize startup cost for a process. By referring to the offset of the global offset table entry for a symbol, instead of directly referring to the symbol, compiler-emitted data structures avoid requiring unnecessary relocation at dynamic linking time.
```

These relative pointers make use of int32 types (instead of 8 bytes which would be the traditional pointer!).
As a simple pseudocode, you can think of an offset like this:

```c
dstAddress = ptr_auth(currentAddress + (int32)offset)
```

When analyzing a binary that makes use of the Swift runtime, you will be able to find lots of `swift5_*` segments.
These segments (together with `__const`) provide Swift with all it needs.

Following, you'll see a description of those:

- `__TEXT.__swift5_protos`: Contains a list of relative pointers that each of them point to a **Protocol Descriptor**.
  Each of them consist of what we know as a **Swift Protocol**. These pointers point to `__TEXT.__const`.

  The implementation of each **Protocol Descriptor (Swift Protocol)** can be found at: <https://github.com/swiftlang/swift/blob/main/include/swift/ABI/Metadata.h#L3193-L3241> (more on this later when we dig deep into the Swift Protocols). The structure of a **Protocol Descriptor** is:

  ```swift
  type ProtocolDescriptor struct {
      Flags                      uint32
      Parent                     int32
      Name                       int32
      NumRequirementsInSignature uint32
      NumRequirements            uint32
      AssociatedTypeNames        int32
  }
  ```

  Or, to be more specific with Swift types:

  ```swift
  type ProtocolDescriptor struct {
      Flags                      ContextDescriptorFlags 
      Parent                     TargetRelativeContextPointer 
      Name                       TargetRelativeDirectPointer
      NumRequirementsInSignature uint32
      NumRequirements            uint32
      AssociatedTypeNames        RelativeDirectPointer
  }
  ```

- `__TEXT.__swift5_proto`: This section is a list of relative pointers to **Protocol Conformance Descriptors** (<https://github.com/swiftlang/swift/blob/main/include/swift/ABI/Metadata.h#L2773-L2784>).
  Each of these point to the `__TEXT.__const` section. A script to parse this sectio can be found in: <https://github.com/doronz88/ida-scripts/blob/main/fix_proto_conf_desc.py>.

  ```c
    /// The Protocol Descriptor being conformed to.
    TargetRelativeContextPointer<Runtime, TargetProtocolDescriptor> Protocol; 
  
    // Some description of the type that conforms to the protocol.
    TargetTypeReference<Runtime> TypeRef;

    // The witness table pattern, which may also serve as the witness table.
    RelativeDirectPointer<const TargetWitnessTable<Runtime>> WitnessTablePattern;

    // Various flags, including the kind of conformance.
    ConformanceFlags Flags;
  ```

  Which can be understood as:

  ```swift
  type ProtocolConformanceDescriptor struct {
      ProtocolDescriptor    int32 //relative ptr
      NominalTypeDescriptor int32 //relative ptr
      ProtocolWitnessTable  int32 //relative ptr
      ConformanceFlags      uint32
  }
  ```

  > **NOTE:** Protocol Descriptor is the protocol they **conform** to.

- `__TEXT.__swift5_types`

  Types can take many forms (<https://github.com/swiftlang/swift/blob/main/include/swift/ABI/Metadata.h#L4840-L4872>) that are resolved in runtime.
  Thus, even if the structs are **the same size** they mean different things which means there isn't a unique solution for parsing this segment.

  (Again, thanks Scott Knight for his work, this is directly taken from his research)

  ```swift
  type EnumDescriptor struct {
      Flags                               uint32
      Parent                              int32
      Name                                int32
      AccessFunction                      int32
      FieldDescriptor                     int32
      NumPayloadCasesAndPayloadSizeOffset uint32
      NumEmptyCases                       uint32
  }

  type StructDescriptor struct {
      Flags                   uint32
      Parent                  int32
      Name                    int32
      AccessFunction          int32
      FieldDescriptor         int32
      NumFields               uint32
      FieldOffsetVectorOffset uint32
  }

  type ClassDescriptor struct {
      Flags                       uint32
      Parent                      int32
      Name                        int32
      AccessFunction              int32
      FieldDescriptor             int32
      SuperclassType              int32
      MetadataNegativeSizeInWords uint32
      MetadataPositiveSizeInWords uint32
      NumImmediateMembers         uint32
      NumFields                   uint32
  }
  ```

  The reader is encouraged to find the types of **TargetExtensionContextDescriptor**, **TargetAnonymousContextDescriptor**, **TargetOpaqueTypeDescriptor**.

- `__TEXT.__swift5_fieldmd`

  (Taken from Scott Knight research)

  This section contains an array of field descriptors. A field descriptor contains a collection of field records for a single class, struct or enum declaration. Each field descriptor can be a different length depending on how many field records the type contains.

  ```swift
  type FieldRecord struct {
      Flags           uint32
      MangledTypeName int32
      FieldName       int32
  }

  type FieldDescriptor struct {
      MangledTypeName int32
      Superclass      int32
      Kind            uint16
      FieldRecordSize uint16
      NumFields       uint32
      FieldRecords    []FieldRecord
  }
  ```

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

### Swift_String

The swift strings specifically are one of the most common types to handle. Though they sound as pretty straight forward, their allocation may be a bit tricky to track for newcomers.

In general, depeding on the `_countAndFlagsBits` and the `_object`, we can tell where the string is really allocated.

- If `string->_object >> 60 == 0xE`, then it is stored in-place, inside the two `_countAndFlagsBits` and `_object` members
- If `string->_countAndFlagsBits >> 60 == 0xD`, then the actual object is in: `(string->_object & 0xffffffffffffff) + 0x20`

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

## Swift Protocols

Swift Protocols are mere interfaces that define how a type has to be adapted to **conform** to a protocol.
You can think a protocol like rules that the type has to comply with. As we saw earlier, these can be found in `swift5_protos`.

Apple states that:

```none
A protocol defines a blueprint of methods, properties, and other requirements that suit a particular task or piece of functionality. The protocol can then be adopted by a class, structure, or enumeration to provide an actual implementation of those requirements. Any type that satisfies the requirements of a protocol is said to conform to that protocol.
```

Note that types can have multiple **conforming** protocols. These are marked like this:

```none
struct SomeStructure: FirstProtocol, AnotherProtocol {
    // structure definition goes here
}
```

Once we understood that, we have to understand what can be defined in a protocol. Protocols can have properties and methods.

For instance, here we have a protocol that have only properties:

```swift
protocol SomeProtocol {
    var mustBeSettable: Int { get set }
    var doesNotNeedToBeSettable: Int { get }
}
```

When defining properties for protocols, what we are really doing is establishing the **Property Requirements** for the protocol.
These will be the **type, name and also specify whether each property must be gettable or gettable and settable**.

For example, here we can see a protocol and a class that conforms to that protocol (**note that both have to have the same name and type of the property**):

```swift
protocol FullyNamed {
    var fullName: String { get }
}

struct Person: FullyNamed {
    var fullName: String
}
let john = Person(fullName: "John Appleseed")
// john.fullName is "John Appleseed"
```

Protocols can also define methods. As previously with the properties, we'll also need to define **Method requirements**.
For example, in the following protocol we will be defining a protocol with a single method that has to return a Double type:

```swift
protocol RandomNumberGenerator {
    func random() -> Double
}
```

Note that the class that **conforms** to this protocol has no obligations regarding to how the `random()` is computed, efficiency, how random is that number or whether Double type can be from 0.0 to 1.0 or -50.0 to 50.0. It's a mere specification of the function name and the return type.

As stated earlier, protocols can be found at `swift5_protos` section as a list of **relative pointers** to `__const` section.
Within them, you'll be able to find the raw bytes of what we've just described.

```swift
type TargetProtocolDescriptor struct {
	TargetContextDescriptor
	NameOffset                 RelativeDirectPointer // The name of the protocol.
	NumRequirementsInSignature uint32                // The number of generic requirements in the requirement signature of the protocol.
	NumRequirements            uint32                /* The number of requirements in the protocol. If any requirements beyond MinimumWitnessTableSizeInWords are present
	 * in the witness table template, they will be not be overwritten with defaults. */
	AssociatedTypeNamesOffset RelativeDirectPointer // Associated type names, as a space-separated list in the same order as the requirements.
}
```

After that definition, you'll encounter the list of generic signature requirements (determined by the **NumRequirementsInSignature**) and after that, the **requirement** list of size **NumRequirements**.

Here are the structures that define both of them:

```swift
type TargetGenericRequirementDescriptor struct {
	Flags                                  GenericRequirementFlags
	ParamOff                               RelativeDirectPointer
	TypeOrProtocolOrConformanceOrLayoutOff RelativeIndirectablePointer 
}
```

```swift
type TargetProtocolRequirement struct {
	Flags                 ProtocolRequirementFlags
	DefaultImplementation RelativeDirectPointer // The optional default implementation of the protocol.
}
```

Once protocols are defined, classes can **conform** to them. There may be cases in which default implementations want to be provided. That is why **protocol extensions** exist. We can create a protocol and afterwards, define an extension for it. Following the previous example:

```swift
protocol RandomNumberGenerator {
    func random() -> Double
}

extension RandomNumberGenerator {
  func random() {
    return 1.0
  }
}
```

So, unless if the conforming class provides their own implementation of `random()`, `1.0` will be returned when called.

## Witness tables

Protocols allow developers to add polymorphism to types through composition, even to value types like structs or enums. Protocol methods are dispatched via Protocol Witness Tables.

The mechanism for these is the same as virtual tables: Protocol-conforming types contain metadata (stored in an existential container*), which includes a pointer to their witness table, which is itself a table of function pointers.

When executing a function on a protocol type, Swift inspects the existential container, looks up the witness table, and dispatches to the memory address of the function to execute.

For example, we may see a situation in which we'll iterate over a list of types that conform to a protocol. Because we won't know at compile time which will be the method to be called, this will have to be dispatched via the PWT (Protocol Witness Tables).

## Protocol conformance descriptors

Protocol conformances are the act of a class, struct, or enum adopting and implementing the requirements specified by a protocol.

```swift
protocol MyProtocol {
 // protocol requirements
  func myMethod() 
}

class MyClass: MyProtocol { 
  func myMethod() {
     print("implementation")
  }
}
```

> **NOTE:** Remember that a class, enum or struct can **conform** to more than one Protocol.

So, yes, you are right, we'll find them referenced at `swift5_proto` as a list of relative pointers.

## Type metadata

The swift runtime keeps a record for every used type. This type metatdata is then used for RTTI, template methods, allocate the object's space, etc.
For further information please read:

<https://github.com/apple/swift/blob/main/docs/ABI/TypeMetadata.rst>

Many of the global swift objects are stored globally in the `__common` section. When initializing a global of any type, the following snippet is generated (assuming we allocate the global `globalVar` of type `globalVar_t`)

```c
// repalce TYPE with the actual type
void *typeMetadata = __swift_instantiateConcreteTypeFromMangledName(&demangling cache variable for type metadata for globalVar_t);
__swift_allocate_value_buffer(typeMetadata, &globalVar);
__swift_project_value_buffer(typeMetadata, &globalVar);
```

These two functions, `__swift_allocate_value_buffer` and `__swift_project_value_buffer` are basically to allocate the variable memory space and get a pointer to it, after consulting with the type metadata, if it allows the actual data to be in-place or use a pointer to an external space.

> **NOTE:** Sometimes IDA cannot parse the pointer `__swift_instantiateConcreteTypeFromMangledName` is referring to.
  That is due the fact it's an int32 relative pointer as we discussed earlier, so you'll just have to fix it manually to discover the actual type.

Also, on many occasions, these allocations will be used on the stack dynamically. In that case you'll see a lot of calls to `__chkstk_darwin()`, whereas the spaces between them are the used local variables.

## va_list

When calling a function which receives a variadic length of arguments, such as `print`, the compiler will use `_allocateUninitializedArray<A>(_:)` to create an array of type `Array<Any>` to create this as a single parameter. We represent this datatype as `Swift_ArrayAny`.

Let's examine now a call to `print(_:separator:terminator:)`.

We'll need to make this function signature as:

```c
void __fastcall print___separator_terminator__(Swift_ArrayAny *printString, Swift_String seperator, Swift_String terminator);
```

In addition, if the function receives multiple protocols in the form of: `<A, B, C>`, then multiple type metadata are passed.

### Template functions

Many of the Swift functions often handle tempaltes. This is usually seen in method signature as: `doSomething<A>()`. In order to trigger the correct method to handle such invocations, the compiler adds an additional argument as the last one which acts the "type metadata" - from which the witness table is extracted. While reversing, assuming we are only focused on understanding the code-flow, this parameter is usually not very important.

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

## Error handling

If a method raises an error, it will write its error object into `X21`. It is then raised using `swift_unexpectedError()`.
If the user raised an error explicitly, it will instead use `swift_allocError()` to allocate the error using the corresponding type metadata.

## References

- <https://hex-rays.com/blog/igors-tip-of-the-week-51-custom-calling-conventions/>
- <https://www.swift.org/documentation/>
- <https://github.com/apple/swift/blob/main/docs/ABI/>
- <https://github.com/blacktop/go-macho/blob/master/swift.go/>
- <https://knight.sc/reverse%20engineering/2019/07/17/swift-metadata.html/>
- <https://blog.jacobstechtavern.com/p/compiler-cocaine-the-swift-method>
- <https://docs.swift.org/swift-book/documentation/the-swift-programming-language/protocols/>
- <https://knight.sc/reverse%20engineering/2019/07/17/swift-metadata.html>
