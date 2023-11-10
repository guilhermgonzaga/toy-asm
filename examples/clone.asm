; Copy input to output verbatim

	in		; size of array

L1:	dup
	push 0
	jeq end		; (pseudo) push 16-bit address, then jmp
	push 1		; count -= 1
	sub

	in		; work
	out

	jmp L1		; (pseudo) push 16-bit address, then jmp

end:	hlt
