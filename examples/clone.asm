; Copy input to output verbatim

	in		; size of array

loop:	dup
	push 0
	beq end		; zero marks end of input

	dec		; count -= 1

	in		; work
	out

	jmp loop

end:	hlt
