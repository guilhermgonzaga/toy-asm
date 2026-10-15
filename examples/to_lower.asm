; Convert input string to lower case.
; End on null byte.

L1:	in		; get char
	dup 0
	push 0
	beq end		; null byte is end of input

	dup 0		; test char < 'A'
	pushb 65
	slt
	push 1
	beq L1		; skip if so

	dup 0		; test if char < '['
	pushb 91
	slt
	push 0
	beq L1		; skip if not

	not		; convert char to lower case
	pushb 0xDF
	nand
	out

	jmp L1		; continue loop

end:	hlt
