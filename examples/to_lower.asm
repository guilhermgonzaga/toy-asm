; Convert input string to lower case.
; End on null byte.

L1:	in		; get char
	dup
	push 0
	jeq end		; null byte is end of input

	dup		; test char < 'A'
	push 65
	slt
	push 1
	jeq L1		; skip if so

	dup		; test if char < '['
	push 91
	slt
	push 0
	jeq L1		; skip if not

	not		; convert char to lower case
	push 0xDF
	nand
	out

	jmp L1		; continue loop

end:	hlt
