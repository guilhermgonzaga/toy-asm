; Validate a sequence as a palindrome.
; The pattern must be marked with a zero in the middle and the end.
; No other byte may be zero. General format: "xx..xx0xx..xx0".

loop1:	in		; get char
	dup
	push 0
	jeq loop2	; byte 0 marks half of input

	jmp loop1	; continue loop

loop2:	in		; get char
	dup
	push 0
	jeq valid	; byte 0 marks end of input

	jeq loop2	; continue loop if chars match

	push 0		; it is not a palindrome
	jmp end
valid:	push 1		; it is a palindrome

end:	out		; 1 if palindrome, 0 if not
	hlt
