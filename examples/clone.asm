; Copy input to output verbatim

	in		; size of array

loop:	dup
	push 0
	jeq end		; zero marks end of input

	push 1		; count -= 1
	swp
	sub

	in		; work
	out

	jmp loop

end:	hlt
