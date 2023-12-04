; Convert input string to upper case.
; End on null byte.

L1:	in		; get char
	dup
	push 0
	jeq end		; null byte is end of input

	dup		; test char < 'a'
	push 97
	slt
	push 1
	jeq L1		; skip if so

	dup		; test if char < '{'
	push 123
	slt
	push 0
	jeq L1		; skip if not

	push 0xDF	; convert char to upper case
	and
	out

	jmp L1		; continue loop

end:	hlt
