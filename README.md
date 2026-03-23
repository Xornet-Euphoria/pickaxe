# pickaxe

My pickle arsenal

- [`crafter.py`](./pickaxe/crafter.py): hand assembler
  - `Crafter`, `AsciiCrafter`, `UnicodeCrafter`
  - Tracks abstract `stack` and `memo` state through high-level helpers via `stack`, `memo`, `stack_is_valid`, and `memo_is_valid`
- [`unpickler.py`](./pickaxe/unpickler.py): custom unpickler
  - Traces opcodes, stack changes, memo updates, frames, and breakpoints
  - Filters by event with `trace_events` and by opcode with `trace_ops`
  - Writes trace output to `stdout`, files, or callbacks via `trace_output`

## Install

`python -m pip install git+https://github.com/Xornet-Euphoria/pickaxe`

## Usage

See [examples](./examples/).

Notable examples:

- [`examples/ascii.py`](./examples/ascii.py)
- [`examples/binsh.py`](./examples/binsh.py)
- [`examples/unipickle.py`](./examples/unipickle.py)
- [`examples/custom_unpickler/custom_unpickler.py`](./examples/custom_unpickler/custom_unpickler.py)
- [`examples/custom_unpickler/trace_filter.py`](./examples/custom_unpickler/trace_filter.py)
- [`examples/custom_unpickler/trace_output_file.py`](./examples/custom_unpickler/trace_output_file.py)

## Notes

- Raw-byte paths such as `Crafter.add_payload()` invalidate the stack/memo tracer for safety.
- `CustomUnpickler` exports its trace event types as `TraceEvent` and `TraceEventKind`.

## Todo

- examples
  - solution of CTF challenges
  - size optimization ([Run Length Encoding (ja)](https://project-euphoria.dev/blog/pickle-run-length/))
- no-arg opcode wrapper methods for `Crafter`
- analysis-oriented custom opcodes for `CustomUnpickler`
- typing-friendly explicit `load_*` overrides in `CustomUnpickler`

## Related Tools

`crafter.Crafter` is just an assembler. If you want to compile a source code of Python to Pickle, you can use [Pickola (by splitline)](https://github.com/splitline/Pickora).
