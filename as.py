#!/usr/bin/env python3
"""
Assembler for a simple stack-based architecture.
"""

import sys
from re import fullmatch

# Regex patterns tokenize and validate syntax
RE_ID = r'([_a-z]\w*)'
# RE_IMM = r'(-[0-8]|[0-9]|1[0-5]|0x[0-9a-f])'
RE_IMM = r'(-?[0-9]+|0x[0-9a-f]+)'
RE_MNEMONIC = r'(hlt|in|out|puship|push|drop|dup|add|sub|not|nand|and|slt|shl|shr|jeq|jmp)'
RE_INSTR = rf'{RE_MNEMONIC}(?:(?<=push) {RE_IMM}|(?<=jmp)(?: {RE_ID})?|(?<!jmp)(?<!push))'
RE_LINE = rf'^(?:{RE_ID} ?: ?)? ?{RE_INSTR}$'

OPCODES_LUT = {
	'hlt':    '0000',
	'in':     '0001',
	'out':    '0010',
	'puship': '0011',
	'push':   '0100',
	'drop':   '0101',
	'dup':    '0110',
	         # 0111 does not exist (reserved)
	'add':    '1000',
	'sub':    '1001',
	'nand':   '1010',
	'slt':    '1011',
	'shl':    '1100',
	'shr':    '1101',
	'jeq':    '1110',
	'jmp':    '1111',
}

# TODO swap; PUSH with label or JEQ with target; shift with immediate
# Always put label on first instruction
PSEUDO_LUT = {
	'not': lambda labl, imm, tget: [
		[labl, 'dup',  0, None],
		[None, 'nand', 0, None]
	],
	'and': lambda labl, imm, tget: [
		[labl, 'nand', 0, None],
		[None, 'dup',  0, None],
		[None, 'nand', 0, None]
	],
	'push': lambda labl, imm, tget: [
		[labl, 'push', 4,      None],
		[None, 'push', imm>>4, None],  # High nibble
		[None, 'shl',  0,      None],
		[None, 'push', imm&15, None],  # Low nibble
		[None, 'add',  0,      None]
	],
	'jmp': lambda labl, imm, tget:
		PSEUDO_LUT['push'](labl, 0, None) +  # Placeholder immediate (high byte)
		PSEUDO_LUT['push'](None, 0, None) +  # Placeholder immediate (low byte)
		[[None, 'jmp',  0, tget]]   # Keep target to resolve later
	,
}


def imm2int(imm_s: str):
	if not imm_s:
		return 0
	# Accept hex and decimal
	return int(imm_s, 16) if '0x' in imm_s else int(imm_s)

def int2nibble(imm_i: int):
	return f'{imm_i & 0xf:04b}'

def preprocess(line: str):
	line = line.lower()            # Lower case
	line = line.partition(';')[0]  # Remove comment if present
	line = ' '.join(line.split())  # Minimize spaces between tokens
	return line

def tokenize(line: str):
	# Tokenize with regex
	match = fullmatch(RE_LINE, line)

	# label, mnemonic, immediate, target
	return list(match.groups()) if match else None

def parse(asm_file, label_lut: dict[str: int]):
	# [label, mnemonic, immediate, target]
	pseudo_asm: list([str, str, int, str]) = []

	# First pass

	for lnum, raw_line in enumerate(asm_file, start=1):
		line = preprocess(raw_line)

		# Skip empty lines
		if not line:
			continue

		tokens = tokenize(line)
		if not tokens:
			raise Exception(
				f'{asm_file.name}:{lnum}: invalid syntax\n'
				f'{raw_line.strip()}')

		# Validate label
		if label := tokens[0]:
			if label in label_lut:
				raise Exception(
					f'{asm_file.name}:{lnum}: '
					f'label already in use (first defined on line {label_lut[label]})\n'
					f'{raw_line.strip()}')
			label_lut[label] = lnum  # Not the definitive value

		# Validate immediate
		tokens[2] = imm2int(tokens[2])
		if not -128 <= tokens[2] <= 255:
			raise Exception(
				f'{asm_file.name}:{lnum}: immediate does not fit in 8 bits\n'
				f'{raw_line.strip()}')

		pseudo_asm.append(tokens)

	# Second pass

	# Validate target
	for lnum, tokens in enumerate(pseudo_asm, start=1):
		target = tokens[3]
		if target and target not in label_lut:
			raise Exception(
				f'{asm_file.name}:{lnum}: jump targets undefined label "{target}"')

	return pseudo_asm

def expand_pseudo(pseudo_asm, label_lut: dict[str: int]):
	label_asm = []
	instr_offset = 0  # Offset of an instruction after expansion

	for addr, tokens in enumerate(pseudo_asm):
		label, mnemonic, imm, target = tokens

		# Update label
		if label:
			label_lut[label] = addr + instr_offset

		# Expand pseudoinstruction, leave the rest
		if (mnemonic == 'not') or \
		   (mnemonic == 'and') or \
		   (mnemonic == 'push' and not -8 <= imm <= 15) or \
		   (mnemonic == 'jmp' and target):
			transl = PSEUDO_LUT[mnemonic](label, imm, target)
			# print(f'Translating:\n{tokens}\n{transl}\n')
			label_asm.extend(transl)
			instr_offset += len(transl) - 1  # minus the pseudoinstruction
		else:
			label_asm.append(tokens)

	return label_asm

def gen_code(label_asm: list([str, str, int, str]), label_lut: dict[str: int]):
	code: list([str, str]) = []   # [opcode, immediate]

	for addr, tokens in enumerate(label_asm):
		label, mnemonic, imm, target = tokens

		# Resolve target
		if target:
			target_addr = label_lut[target]
			imm_nibble3 = int2nibble(target_addr >> 12)
			imm_nibble2 = int2nibble(target_addr >> 8)
			imm_nibble1 = int2nibble(target_addr >> 4)
			imm_nibble0 = int2nibble(target_addr)

			# Update immediate in corresponding push instructions
			code[-9][1] = imm_nibble3
			code[-7][1] = imm_nibble2
			code[-4][1] = imm_nibble1
			code[-2][1] = imm_nibble0

		opcode = OPCODES_LUT[mnemonic]
		imm_bits = int2nibble(imm)
		code.append([opcode, imm_bits])

	return code


def main():
	input_fname  = sys.argv[1] if len(sys.argv) > 1 else 'firmware.asm'
	output_fname = sys.argv[2] if len(sys.argv) > 2 else 'firmware.bin'

	# Source analysis

	label_lut: dict[str: int] = {}  # (label -> address)

	try:
		asm_file = open(input_fname, 'r')
		pseudo_asm = parse(asm_file, label_lut)
		asm_file.close()
	except Exception as e:
		sys.exit(e)

	# Pseudoinstruction translation and address resolution

	try:
		label_asm = expand_pseudo(pseudo_asm, label_lut)
	except Exception as e:
		sys.exit(e)

	print('----------------------------------------')
	for addr, tokens in enumerate(label_asm):
		print(f'{addr:3}  ', end='')
		print(*(f'{"-" if t is None else t:<8}' for t in tokens))
	print('----------------------------------------')

	# Binary generation

	code = gen_code(label_asm, label_lut)
	bin_file = open(output_fname, 'w')
	for op, imm in code:
		print(f'{op}{imm}', file=bin_file)
	bin_file.close()


if __name__ == '__main__':
	main()
