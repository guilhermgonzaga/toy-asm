; Convert input string to upper case.
; End on null byte.

L1:	in		; get char
	dup 0
	push 0
	beq end		; null byte is end of input

	dup 0		; test char < 'a'
	pushb 97
	slt
	push 1
	beq L1		; skip if so

	dup 0		; test if char < '{'
	pushb 123
	slt
	push 0
	beq L1		; skip if not

	pushb 0xDF	; convert char to upper case
	and
	out

	jmp L1		; continue loop

end:	hlt
