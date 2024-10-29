# gdbundle-gdb-callgrind

This is a gdb plugin, packaged using gdbundle, which can emit
callgrind style call tree information using gdb single instruction
stepping.  This makes it possible to generate call tree profiling
information on arbitrary remote targets, like microcontrollers, at the
expense of the process being quite slow.

# Installation

```
$ pip install gdbundle-gdb-callgrind
```

# Usage

```
(gdb) emit_callgrind
```

Optionally, a terminal program counter can be specified as an argument
to emit_callgrind.  If omitted, then profiling proceeds until the end
of the current function.
