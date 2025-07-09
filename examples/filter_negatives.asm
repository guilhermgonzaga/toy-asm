; Remove all negatives from input.
; Zero marks end of input.

L1:	in		; Get next element

	dup		; Copy element
	jz end		; (pseudo) push address, then jmp if zero

	dup		; Copy element
	push 0
	slt
	jz L1		; If negative, continue loop

	out		; Output positive element

	jmp L1

end:	hlt
