; Validade a sequence as a palindrome.
; The pattern must be marked with a zero in the middle and the end.
; No other byte may be zero. General format: "xx..xx0xx..xx0".

L1:	in		; get char
	dup
	push 0
	jeq L2		; byte 0 marks half of input

	jmp L1		; continue loop

L2:	in		; get char
	dup
	push 0
	jeq L3		; byte 0 marks end of input

	dup
	jeq L2		; skip if equal

	push 0		; it is not a palindrome
	jmp end
L3:	push 1		; it is a palindrome

end:	out		; 1 if palindrome, 0 if not
	hlt
