# toy-asm

A toy assembler for a toy architecture.

## Features

- Line comments started by `;`. Text inside comments is not restricted to the ASCII character set.

- Symbolic addressing for branching instructions. Symbols follow the same naming rules as identifiers in C. Each symbol must have only one definition in the source, though there is no restriction on use before definition.

- Pseudo-instructions. The original ISA is quite small at 20 instructions, so these are very appealing for practical programming.

### General Syntax

```
label ":" mnemonic [immediate|target] ";" comment
```

The immediate may be a signed decimal or an unsigned hexadecimal pattern preceded by `0x`. For native instructions, the immediate must fit within 4 bits. For PUSH, immediate values can be up to 8 bits wide.

Labels and targets are translated to 16-bit addresses and placed in code during pseudoinstruction expansion. Currently, a label cannot be placed on a line without an instruction.

## Instruction-set Architecture

The ISA is designed for the model of a stack machine with two stacks:

- a main stack to hold data and, for most instructions, all operands;
- a secondary stack to hold return addresses.

There are no general-purpose registers, only an instruction pointer (IP) and stack pointer (SP), which are only accessible by special control flow instructions.

There is one IO device that reads in or puts out one byte at a time. There are special instructions IN and OUT to do these operations.

All instructions are 8 bits wide, with a 4-bit *opcode* followed by a 4-bit segment that may be an opcode extension (*opext*) or an *immediate*, depending on the instruction's format. Hence, there are two formats, called **extended** and **immediate**.

Native instructions and their encodings.

|Mnemonic|Format   |Encoding  |
|:-------|:-------:|:--------:|
|HLT     |extended |`00000000`|
|PUSHIP  |extended |`00000001`|
|IN      |extended |`00000010`|
|OUT     |extended |`00000011`|
|SWP     |extended |`00000100`|
|NAND    |extended |`00000101`|
|ADD     |extended |`00000110`|
|SUB     |extended |`00000111`|
|SLT     |extended |`00001000`|
|SLTU    |extended |`00001001`|
|SHL     |extended |`00001010`|
|SHR     |extended |`00001011`|
|BEQ     |extended |`00001100`|
|JMP     |extended |`00001101`|
|JAL     |extended |`00001110`|
|RET     |extended |`00001111`|
|PUSH    |immediate|`1000iiii`|
|ADDUI   |immediate|`1001iiii`|
|DROP    |immediate|`1010iiii`|
|DUP     |immediate|`1011iiii`|

### Description of the Instructions

#### Native instructions

- **HLT (_halt_)**: Stop execution indefinitely.

- **PUSHIP (_push ip_)**: Push IP to the data stack.

- **IN**: Push a byte to the data stack received from the IO device.

- **OUT**: Pop a byte to the data stack and send it to the IO device.

- **SWP (_swap_)**: Swap the two topmost bytes on the stack.

- **NAND**: Pop two bytes on the data stack, bitwise nand them, and push the resulting byte.

- **ADD**: Pop two bytes on the data stack, add them, and push the resulting byte.

- **SUB (_subtract_)**: Pop two bytes on the data stack, subtract them, and push the resulting byte.

- **SLT (_set if less than_)**: Pop two bytes on the data stack, and push a byte 1 if the topmost is smaller, 0 otherwise. Example: "-1 < 1" is 1 (true).

- **SLTU (_set if less than, unsigned_)**: Same as SLT, except the comparison takes operands as unsigned. Example: "-1 < 1" is 0 (false).

- **SHL (_shift left_)**: Pop two bytes on the data stack, and push the topmost shifted left by the next one.

- **SHR (_shift right_)**: Pop two bytes on the data stack, and push the topmost shifted right by the next one.

- **BEQ (_branch if equal_)**: Pop 4 bytes on the data stack and, if the lower ones are equal, assign the address made up of the topmost bytes to IP.

- **JMP (_jump_)**: Pop an address from the data stack and assign it to IP.

- **JAL (_jump and link_)**: Push IP to the top of the address stack, pop an address from the data stack and assign it to IP.

- **RET (_return_)**: Pop the top of the address stack and assign it to IP.

- **PUSH**: Push a byte with its 4 least significant bits containing the immediate.

- **ADDUI (_add upper immediate_)**: Add the immediate to the 4 most significant bits of the top of the stack.

- **DROP**: Pop and discard up to 16 elements from the stack, the number given in the immediate.

- **DUP (_duplicate_)**: Copy one of the 4 topmost bytes on the data stack and push it on top. The immediate indicates which one as a value to be subtracted from SP. Hence, only the two lowest bits are relevant.

#### Pseudoinstructions

- **INC (_increment_)**: Increment the topmost byte on the data stack.

- **DEC (_decrement_)**: Decrement the topmost byte on the data stack.

- **NOT**: Bitwise negate the topmost byte on the data stack.

- **AND**: Bitwise AND the two topmost bytes on the data stack.

- **OR**: Bitwise OR the two topmost bytes on the data stack.

For some native instructions, syntactic sugar was added:

- Ability to use labels as branch targets with JMP, BEQ, or JAL.

- Ability to PUSH values up to 8 bits wide to the data stack transparently; the assembler substitutes in a longer sequence of instructions if needed.
