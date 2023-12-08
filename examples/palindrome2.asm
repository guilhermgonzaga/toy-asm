; Validate a sequence as a palindrome.
; The first byte is taken to be the input size, which must be even.
; The input must not contain a null byte.

	push 0		; empty stack marker
	push 1
	in		; get input size
	shr		; halve size

loop1:	dup
	push 0
	jeq brk1	; jump if half of input consumed
	dec		; decrement size

	in		; get char
	swp		; bring size to TOS

	jmp loop1	; continue loop

brk1:	drop		; discard zero

loop2:	dup
	push 0
	jeq valid	; jump if stack is empty

	in
	jeq loop2	; continue loop if chars match

	push 0		; it is not a palindrome
	jmp end
valid:	push 1		; it is a palindrome
end:	out		; 1 if palindrome, 0 if not
	hlt
