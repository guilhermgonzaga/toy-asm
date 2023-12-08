# toy-asm

A toy assembler for a toy architecture.

## Features

- Support for line comments started by `;`

- Support for labels

	Labels cannot be redefined and there must be at most one per instruction.

- Jump target resolution

- Pseudo-instructions

	+ `not`: Bitwise negate a byte on the stack.
	+ `and`: Bitwise and two bytes on the stack.
	+ `or`: Bitwise or two bytes on the stack.
	+ `push`: Ability to push an 8-bit immediate.
	+ `jmp`: Ability to set a label as a target.
	+ `jeq`: Ability to set a label as a target.

## General Syntax

```
label ":" opcode [immediate|target] ";" comment
```

The immediate may be a signed decimal or a hexadecimal pattern preceded by `0x`. The only restriction is that it fits in 8 bits.

Labels and targets are translated to 16-bit addresses. Also, a label cannot be placed on a line without an instruction.

## Instruction-set description

All instructions are 8 bits wide and there is only one format, which is a 4-bit opcode followed by a 4-bit immediate. Instructions that don't need the immediate must have it set to all zeros.

	0000 hlt:    Stop execution indefinitely.
	0001 in:     Push a byte received from IO.
	0010 out:    Pop a byte and sends it to IO.
	0011 puship: Push the address stored in IP (2 bytes, MSB first).
	0100 push:   Push a byte containing an *immediate* (stored in the 4 least significant bits of the instruction)
	0101 drop:   Pop an element from the stack and discard it.
	0110 dup:    Duplicate the top of the stack.
	0111 swp:    Swap the two bytes on top of the stack.
	1000 add:    Pop Op1 and Op2 and push (Op1 + Op2).
	1001 sub:    Pop Op1 and Op2 and push (Op1 - Op2).
	1010 nand:   Pop Op1 and Op2 and push ~(Op1 & Op2).
	1011 slt:    Pop Op1 and Op2 and push (Op1 < Op2).
	1100 shl:    Pop Op1 and Op2 and push (Op1 << Op2).
	1101 shr:    Pop Op1 and Op2 and push (Op1 >> Op2).
	1110 jeq:    Pop Op1 (1 bytes) and Op2 (1 bytes) and Op3 (2 bytes) and assign IP = Op3 if Op1 == Op2.
	1111 jmp:    Pop Op1 (2 bytes) and assign IP = Op1.
