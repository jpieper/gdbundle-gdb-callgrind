import gdb

class EmitCallgrind(gdb.Command):
    def __init__(self):
        gdb.Command.__init__(self, "emit_callgrind", gdb.COMMAND_USER)

    def invoke(self, args, from_tty):
        args = gdb.string_to_argv(args)

        final_ip = int(args[0], 0)
        output_file = args[1]

        gdb.write(f"Stepping to {final_ip}, writing output to {output_file}")

        # (File, obj): function: {(addr, line): count}
        results = {
        }

        while True:
            frame = gdb.newest_frame()
            cur_pc = frame.pc()
            fn_name = frame.name()
            obj_file = frame.function().symtab.objfile.filename

            sal = frame.find_sal()
            filename = sal.symtab.filename
            line = sal.line

            addrline = (cur_pc, line)

            old_count = (
                results.setdefault(
                    (filename, obj_file), {}).setdefault(
                        fn_name, {}).setdefault(
                            addrline, 0))
            new_count = old_count + 1
            results[(filename, obj_file)][fn_name][addrline] = new_count

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

        for (filename, obj_file), fdata in results.items():
            for fname, fndata in fdata.items():
                addrcount = sorted(list(fndata.items()))

                print(f"ob={obj_file}", file=cg_out)
                print(f"fl={filename}", file=cg_out)
                print(f"fn={fname}", file=cg_out)
                for (addr, line), count in addrcount:
                    print(f"0x{addr:x} {line} {count}", file=cg_out)
                print("", file=cg_out)

        cg_out.close()


if __name__ == '__main__':
    EmitCallgrind()
