# pickaxe

My pickle arsenal

- [`crafter.py`](./pickaxe/crafter.py): hand assembler
- [`unpickler.py`](./pickaxe/unpickler.py): custom unpickler to trace information such as
  - opcode
  - stack
  - new elements in the memo

Tested in Python 3.11.8

## Usage

See [examples](./examples/)

## Todo

- add tests (especially custom unpickler)
- examples
  - solution of CTF challenges
  - size optimization ([Run Length Encoding (ja)](https://project-euphoria.dev/blog/pickle-run-length/))

## Related Tools

`crafter.Crafter` is just an assembler. If you want to compile a source code of Python to Pickle, you can use [Pickola (by splitline)](https://github.com/splitline/Pickora).
