#!/usr/bin/env python3
"""
Assembler for a simple stack-based architecture.
"""

import re
import shutil
import sys

# Regex patterns used for parsing
RE_IMMED = r'(-?[0-9]+|0x[0-9a-f]+)'
RE_LABEL = r'([_a-z][_a-z0-9]*)'
RE_MNEM_IMMED = r'(push|addui|drop|dup)'
RE_MNEM_LABEL = r'(beq|jmp|jal)'
RE_MNEM_PLAIN = r'(hlt|puship|in|out|swp|nand|not|and|or|inc|dec|add|sub|slt|sltu|shl|shr|beq|jmp|jal|ret)'
RE_INSTR = rf'(?:{RE_MNEM_IMMED} {RE_IMMED}|{RE_MNEM_LABEL} {RE_LABEL}|{RE_MNEM_PLAIN})'
RE_LINE = rf'^(?:{RE_LABEL} ?: ?)?{RE_INSTR}$'
RE_PATTERN = re.compile(RE_LINE, re.ASCII | re.IGNORECASE)

"""
Mapping of instruction mnemonics to encoded fields (opcode and opext).
Opext is defined only for instructions of the extended format.
"""
ENCODING_LUT: dict[str, tuple[int, int|None]] = {
	# Extended format
	'hlt':    (0x0, 0x0),
	'puship': (0x0, 0x1),
	'in':     (0x0, 0x2),
	'out':    (0x0, 0x3),
	'swp':    (0x0, 0x4),
	'nand':   (0x0, 0x5),
	'add':    (0x0, 0x6),
	'sub':    (0x0, 0x7),
	'slt':    (0x0, 0x8),
	'sltu':   (0x0, 0x9),
	'shl':    (0x0, 0xA),
	'shr':    (0x0, 0xB),
	'beq':    (0x0, 0xC),
	'jmp':    (0x0, 0xD),
	'jal':    (0x0, 0xE),
	'ret':    (0x0, 0xF),
	# Immediate format
	'push':   (0x8, None),
	'addui':  (0x9, None),
	'drop':   (0xA, None),
	'dup':    (0xB, None),
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
		[labl, 'push', 1,    None],
		[None, 'add',  None, None]
	],
	'dec': lambda labl, imm, tget: [
		[labl, 'push', 1,    None],
		[None, 'swp',  None, None],
		[None, 'sub',  None, None]
	],
	'not': lambda labl, imm, tget: [
		[labl, 'dup',  0,    None],
		[None, 'nand', None, None]
	],
	'and': lambda labl, imm, tget: [
		[labl, 'nand', None, None],
		[None, 'dup',  0,    None],
		[None, 'nand', None, None]
	],
	'or': lambda labl, imm, tget: [
		[labl, 'dup',  0,    None],
		[None, 'nand', None, None],
		[None, 'swp',  None, None],
		[None, 'dup',  0,    None],
		[None, 'nand', None, None],
		[None, 'nand', None, None]
	],
	'push': lambda labl, imm, tget: [
		[labl, 'push',  imm&15, None],  # Lower nibble
		[None, 'addui', imm>>4, None]   # Upper nibble
	] if imm>>4 != 0 else [
		[labl, 'push',  imm,    None],  # Just a nibble
	],
	'beq': lambda labl, imm, tget: [
		[labl, 'push',  0,    None],  # Placeholder for upper byte of target
		[None, 'addui', 0,    None],  # Placeholder for upper byte of target
		[None, 'push',  0,    None],  # Placeholder for lower byte of target
		[None, 'addui', 0,    None],  # Placeholder for lower byte of target
		[None, 'beq',   None, tget]   # Keep target to resolve later
	],
	'jmp': lambda labl, imm, tget: [
		[labl, 'push',  0,    None],  # Placeholder for upper byte of target
		[None, 'addui', 0,    None],  # Placeholder for upper byte of target
		[None, 'push',  0,    None],  # Placeholder for lower byte of target
		[None, 'addui', 0,    None],  # Placeholder for lower byte of target
		[None, 'jmp',   None, tget]   # Keep target to resolve later
	],
	'jal': lambda labl, imm, tget: [
		[labl, 'push',  0,    None],  # Placeholder for upper byte of target
		[None, 'addui', 0,    None],  # Placeholder for upper byte of target
		[None, 'push',  0,    None],  # Placeholder for lower byte of target
		[None, 'addui', 0,    None],  # Placeholder for lower byte of target
		[None, 'jal',   None, tget]   # Keep target to resolve later
	],
}


def imm2int(imm_s: str):
	if imm_s is None:
		return None

	if '0x' in imm_s:  # Unsigned hexadecimal literal
		return int(imm_s, 16)

	return int(imm_s)  # Signed decimal literal


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
	if match is None:
		return None

	# [label, mnemonic_immed, immediate, mnemonic_label, target, mnemonic_plain]
	groups = list(match.groups())

	# Concentrate mnemonics, discard unused places
	groups[1] = groups[1] or groups[3] or groups[5]  # Two out of three are None
	groups.pop(5)
	groups.pop(3)

	# [label, mnemonic, immediate, target]
	return groups


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

		# Parse immediate
		tokens[2] = imm2int(tokens[2])

		# Validate immediate
		if immediate := tokens[2]:
			if tokens[1].casefold() == 'push':
				lowerbound, upperbound, width = -128, 255, 8
			else:
				lowerbound, upperbound, width = -8, 15, 4
			# Immediate must fit within range
			if not lowerbound <= immediate <= upperbound:
				raise Exception(
					f'{asm_file.name}:{lnum}: immediate for "{tokens[1]}" exceeds {width}-bit width.\n'
					f'{truncate_line(raw_line)}')
			# Reinterpret value as unsigned
			immediate &= (1 << width) - 1
			tokens[2] = immediate

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
		mnemonic = mnemonic.casefold()  # Case-insensitive

		# Set definitive label address
		if label:
			symtab[label] = addr + addr_offset

		# Expand pseudoinstructions, leave the rest
		# 'beq', 'jmp', 'jal' are pseudoinstructions iff symbolic targets are given
		if mnemonic not in ENCODING_LUT or mnemonic == 'push' or target:
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
			# Indices work for 'beq', 'jmp' and 'jal', as only these set targets
			label_asm[addr-4][2] = imm_nibble2
			label_asm[addr-3][2] = imm_nibble3
			label_asm[addr-2][2] = imm_nibble0
			label_asm[addr-1][2] = imm_nibble1


def gen_binary(bin_file, label_asm: list([str, str, int, str])):
	for addr, [_, mnemonic, immed, _] in enumerate(label_asm):
		opcode, opext = ENCODING_LUT[mnemonic]
		other = immed if opext is None else opext
		print(f'{opcode:04b}{other:04b}', file=bin_file)


def print_asm(label_asm):
	# Print instruction records in table format
	print('---------------------------------------------')
	print('ADDRESS  LABEL    MNEMONIC  IMMEDIATE  TARGET')
	print('---------------------------------------------')

	for a, tokens in enumerate(label_asm):
		l, m, i, t = tokens
		l, m, t = ('-' if x is None else x for x in (l, m, t))
		i = '-    -' if i is None else f'0x{i:1x}  {i:04b}'  # Special case
		print(f'{a:>7}  {l:<8} {m:<8}  {i:<9}  {t:<8}')

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
