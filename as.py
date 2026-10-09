#!/usr/bin/env python3
"""
Assembler for a simple stack-based architecture.
"""

import re
import shutil
import sys

# Regex patterns used for parsing
RE_LABEL = r'([_a-z][_a-z0-9]*)'
RE_IMMED = r'(-?[0-9]+|0x[0-9a-f]+)'
RE_MNEMONIC = r'(hlt|in|out|puship|push|drop|dup|add|sub|inc|dec|not|nand|and|or|slt|shl|shr|swp|beq|jmp)'
RE_INSTR = rf'{RE_MNEMONIC}(?:(?<=push) {RE_IMMED}|(?<=beq|jmp)(?: {RE_LABEL})?|(?<!beq|jmp)(?<!push))'
RE_LINE = rf'^(?:{RE_LABEL} ?: ?)?{RE_INSTR}$'
RE_PATTERN = re.compile(RE_LINE, re.ASCII | re.IGNORECASE)

"""
Mapping of instruction mnemonics to encoded opcode.
"""
ENCODING_LUT: dict[str, int] = {
	'hlt':    0x0,
	'in':     0x1,
	'out':    0x2,
	'puship': 0x3,
	'push':   0x4,
	'drop':   0x5,
	'dup':    0x6,
	'swp':    0x7,
	'add':    0x8,
	'sub':    0x9,
	'nand':   0xA,
	'slt':    0xB,
	'shl':    0xC,
	'shr':    0xD,
	'beq':    0xE,
	'jmp':    0xF,
}

"""
Mapping of pseudoinstructions to expanded sequence of native instructions.

Each entry maps a pseudoinstruction mnemonic to an expansion function.
The functions return a list of instructions, where each entry contains
the fields label, opcode, argument, and target.

The label must always be placed on the first instruction of the sequence.
Some fields have placeholders that should be set in later assembly steps.
"""
PSEUDO_LUT = {
	'inc': lambda labl, imm, tget: [
		[labl, 'push', 1, None],
		[None, 'add',  0, None]
	],
	'dec': lambda labl, imm, tget: [
		[labl, 'push', 1, None],
		[None, 'swp',  0, None],
		[None, 'sub',  0, None]
	],
	'not': lambda labl, imm, tget: [
		[labl, 'dup',  0, None],
		[None, 'nand', 0, None]
	],
	'and': lambda labl, imm, tget: [
		[labl, 'nand', 0, None],
		[None, 'dup',  0, None],
		[None, 'nand', 0, None]
	],
	'or': lambda labl, imm, tget: [
		[labl, 'dup',  0, None],
		[None, 'nand', 0, None],
		[None, 'swp',  0, None],
		[None, 'dup',  0, None],
		[None, 'nand', 0, None],
		[None, 'nand', 0, None]
	],
	'push': lambda labl, imm, tget: [
		[labl, 'push', 4,      None],
		[None, 'push', imm>>4, None],  # Upper nibble
		[None, 'shl',  0,      None],
		[None, 'push', imm&15, None],  # Lower nibble
		[None, 'add',  0,      None]
	],
	'beq': lambda labl, imm, tget:
		PSEUDO_LUT['push'](labl, 0, None) +  # Placeholder immediate (upper byte)
		PSEUDO_LUT['push'](None, 0, None) +  # Placeholder immediate (lower byte)
		[[None, 'beq',  0, tget]]            # Keep target to resolve later
	,
	'jmp': lambda labl, imm, tget:
		PSEUDO_LUT['push'](labl, 0, None) +  # Placeholder immediate (upper byte)
		PSEUDO_LUT['push'](None, 0, None) +  # Placeholder immediate (lower byte)
		[[None, 'jmp',  0, tget]]            # Keep target to resolve later
	,
}


def imm2int(imm_s: str):
	if imm_s is None:
		return 0

	# Accept hex and decimal
	imm_i = int(imm_s, 16) if '0x' in imm_s else int(imm_s)

	# Validate range
	if not -128 <= imm_i <= 255:
		return None

	# Reset sign bits
	return imm_i & 0xff


def truncate_line(line: str):
	"""Truncate a line to ensure it fits within the terminal window."""
	max_width = min(80, shutil.get_terminal_size()[0])
	line = line.lstrip().expandtabs(4)
	if len(line) > max_width:
		line = line[:max_width-3] + '...'
	return line


def reconstruct_line(line: str):
	line = line.partition(';')[0]  # Remove comment if present
	line = ' '.join(line.split())  # Minimize whitespace between tokens
	return line


def tokenize(line: str):
	# Tokenize with regex
	match = re.fullmatch(RE_PATTERN, line)

	# [label, mnemonic, immediate, target]
	return list(match.groups()) if match else None


def parse(asm_file, symtab: dict[str, int]):
	# [label, mnemonic, immediate, target]
	pseudo_asm: list([str, str, int, str]) = []

	# First pass

	for lnum, raw_line in enumerate(asm_file, start=1):
		line = reconstruct_line(raw_line)

		# Skip empty lines
		if not line:
			continue

		if not line.isascii() or not line.isprintable():
			raise Exception(
				f'{asm_file.name}:{lnum}: '
				'illegal characters in code; only printable ASCII characters are allowed outside of comments.\n'
				f'{truncate_line(raw_line)}')

		tokens = tokenize(line)
		if tokens is None:
			raise Exception(
				f'{asm_file.name}:{lnum}: invalid syntax.\n'
				f'{truncate_line(raw_line)}')

		# Validate label
		if label := tokens[0]:
			if label in symtab:
				raise Exception(
					f'{asm_file.name}:{lnum}: '
					f'label already in use (first defined on line {symtab[label]}).\n'
					f'{truncate_line(raw_line)}')
			symtab[label] = lnum  # Not the definitive value

		# Validate immediate
		tokens[2] = imm2int(tokens[2])
		if tokens[2] is None:
			raise Exception(
				f'{asm_file.name}:{lnum}: immediate does not fit in 8 bits.\n'
				f'{truncate_line(raw_line)}')

		pseudo_asm.append(tokens)

	# Second pass

	# Validate symbolic targets
	for lnum, tokens in enumerate(pseudo_asm, start=1):
		target = tokens[3]
		if target and target not in symtab:
			raise Exception(
				f'{asm_file.name}:{lnum}: undefined label "{target}".')

	return pseudo_asm


def expand_pseudo(pseudo_asm, symtab: dict[str, int]):
	label_asm = []
	addr_offset = 0  # Address offset accumulated from expansions

	for addr, tokens in enumerate(pseudo_asm):
		label, mnemonic, immed, target = tokens

		# Set definitive label address
		if label:
			symtab[label] = addr + addr_offset

		# Expand pseudoinstructions, leave the rest
		# 'beq' and 'jmp' are pseudoinstructions iff symbolic targets are given
		if (mnemonic in ('inc', 'dec', 'not', 'and', 'or')) or \
		   (mnemonic == 'push' and immed > 15) or \
		   (mnemonic == 'beq' and target) or \
		   (mnemonic == 'jmp' and target):
			# Pseudoinstructions
			expanded = PSEUDO_LUT[mnemonic](label, immed, target)
			label_asm.extend(expanded)
			addr_offset += len(expanded) - 1  # Minus the one pseudoinstruction
		else:
			# Native instructions
			label_asm.append(tokens)

	return label_asm


def resolve_targets(label_asm: list([str, str, int, str]), symtab: dict[str, int]):
	for addr, [_, mnemonic, _, target] in enumerate(label_asm):

		if target:
			target_addr = symtab[target]

			if mnemonic == 'beq':
				# Relative offsets are used instead of addresses
				target_addr -= addr

			imm_nibble3 = 0xf & (target_addr >> 12)
			imm_nibble2 = 0xf & (target_addr >> 8)
			imm_nibble1 = 0xf & (target_addr >> 4)
			imm_nibble0 = 0xf & target_addr

			# Update immediates in the related data-loading instructions
			# Indices work for 'beq' and 'jmp', as only these set targets
			label_asm[addr-9][2] = imm_nibble3
			label_asm[addr-7][2] = imm_nibble2
			label_asm[addr-4][2] = imm_nibble1
			label_asm[addr-2][2] = imm_nibble0


def gen_binary(bin_file, label_asm: list([str, str, int, str])):
	for addr, [_, mnemonic, immed, _] in enumerate(label_asm):
		opcode = ENCODING_LUT[mnemonic]
		print(f'{opcode:04b}{immed:04b}', file=bin_file)


def print_asm(label_asm):
	# Print instruction records in table format
	print('---------------------------------------------')
	print('ADDRESS  LABEL    MNEMONIC  IMMEDIATE  TARGET')
	print('---------------------------------------------')

	for a, tokens in enumerate(label_asm):
		l, m, i, t = ('-' if x is None else x for x in tokens)
		print(f'{a:>7}  {l:<8} {m:<8}  0x{i:1x}  {i:04b}  {t:<8}')

	print('---------------------------------------------')


def main():
	input_fname  = sys.argv[1] if len(sys.argv) > 1 else 'firmware.asm'
	output_fname = sys.argv[2] if len(sys.argv) > 2 else 'firmware.bin'

	symtab: dict[str, int] = {}  # (label -> address)

	# Source analysis

	try:
		with open(input_fname, 'r') as asm_file:
			pseudo_asm = parse(asm_file, symtab)
	except Exception as e:
		sys.exit(e)

	# Pseudoinstruction expansion and address resolution

	label_asm = expand_pseudo(pseudo_asm, symtab)
	resolve_targets(label_asm, symtab)
	print_asm(label_asm)

	# Binary generation

	try:
		with open(output_fname, 'w') as bin_file:
			gen_binary(bin_file, label_asm)
	except Exception as e:
		sys.exit(e)


if __name__ == '__main__':
	main()
