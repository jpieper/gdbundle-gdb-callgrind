import gdb

class Function:
    def __init__(self, name):
        self.name = name
        self.positions = {}
        self.calls = {}


class ObjectFile:
    def __init__(self, filename, object_filename):
        self.filename = filename
        self.object_filename = object_filename

        self.functions = {}


class EmitCallgrind(gdb.Command):
    def __init__(self):
        gdb.Command.__init__(self, "emit_callgrind", gdb.COMMAND_USER)

    def invoke(self, args, from_tty):
        args = gdb.string_to_argv(args)

        final_ip = int(args[0], 0)
        output_file = args[1]

        gdb.write(f"Stepping to {final_ip}, writing output to {output_file}")

        object_files = {}

        while True:
            frame = gdb.newest_frame()
            cur_pc = frame.pc()
            fn_name = frame.name()
            obj_filename = frame.function().symtab.objfile.filename

            sal = frame.find_sal()
            filename = sal.symtab.filename
            line = sal.line

            addrline = (cur_pc, line)

            if obj_filename not in object_files:
                object_files[obj_filename] = ObjectFile(filename, obj_filename)

            object_file = object_files[obj_filename]

            if fn_name not in object_file.functions:
                object_file.functions[fn_name] = Function(fn_name)

            fn = object_file.functions[fn_name]

            if addrline not in fn.positions:
                fn.positions[addrline] = 0

            fn.positions[addrline] += 1

            if cur_pc == final_ip:
                break

            gdb.execute("stepi")

        cg_out = open(output_file, "w")

        print("# callgrind format", file=cg_out)
        print("version: 1", file=cg_out)
        print("creator: gdb_callgrind")
        print("positions: instr line", file=cg_out)
        print("events: Instructions", file=cg_out)
        print(file=cg_out)

        for object_file in object_files.values():
            for function in object_file.functions.values():
                addrcount = sorted(list(function.positions.items()))

                print(f"ob={object_file.object_filename}", file=cg_out)
                print(f"fl={object_file.filename}", file=cg_out)
                print(f"fn={function.name}", file=cg_out)
                for (addr, line), count in sorted(function.positions.items()):
                    print(f"0x{addr:x} {line} {count}", file=cg_out)
                print("", file=cg_out)

        cg_out.close()


if __name__ == '__main__':
    EmitCallgrind()
