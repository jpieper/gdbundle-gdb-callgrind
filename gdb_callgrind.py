import gdb

class Call:
    def __init__(self):
        self.count = 0
        self.filename = None
        self.destination_position = None
        self.source_line = None
        self.source_position = None
        self.inclusive_cost = 0


class Function:
    def __init__(self, name):
        self.name = name

        # Indexed by (addr, line)
        self.positions = {}

        # Indexed by (obj_filename, fn_name)
        self.calls = {}


# TODO: One object file can have multiple filenames inside it.  Need
# to separate them!
class ObjectFile:
    def __init__(self, filename, object_filename):
        self.filename = filename
        self.object_filename = object_filename

        # Indexed by 'name'
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
            obj_file_pair = (obj_filename, filename)

            if obj_file_pair not in object_files:
                object_files[obj_file_pair] = ObjectFile(filename, obj_filename)

            object_file = object_files[obj_file_pair]

            if fn_name not in object_file.functions:
                object_file.functions[fn_name] = Function(fn_name)

            fn = object_file.functions[fn_name]

            if addrline not in fn.positions:
                fn.positions[addrline] = 0

            fn.positions[addrline] += 1

            # Try to record call-stack information.
            old_parent = frame
            parent = frame.older()
            while parent and parent.function() is not None:
                this_fn_name = parent.name()
                this_cur_pc = parent.pc()
                this_obj_filename = parent.function().symtab.objfile.filename
                this_sal = parent.find_sal()
                this_filename = sal.symtab.filename
                this_line = sal.line
                this_obj_file_pair = (this_obj_filename, this_filename)

                if this_obj_file_pair not in object_files:
                    object_files[this_obj_file_pair] = ObjectFile(this_filename, this_obj_filename)

                this_object_file = object_files[this_obj_file_pair]

                if this_fn_name not in this_object_file.functions:
                    this_object_file.functions[this_fn_name] = Function(this_fn_name)

                this_fn = this_object_file.functions[this_fn_name]

                call_obj_fn = (obj_filename, fn_name)
                if call_obj_fn not in this_fn.calls:
                    this_fn.calls[call_obj_fn] = Call()

                this_call = this_fn.calls[call_obj_fn]
                this_call.filename = this_filename

                if (this_call.destination_position is None or
                    this_cur_pc < this_call.destination_position):
                    this_call.destination_position = this_cur_pc

                this_call.source_line = line

                this_call.source_position = cur_pc
                this_call.inclusive_cost += 1


                old_parent = parent
                fn_name = this_fn_name
                obj_filename = this_obj_filename
                sal = this_sal
                filename = this_filename
                line = this_line
                cur_pc = this_cur_pc

                parent = parent.older()

            if cur_pc == final_ip:
                break

            gdb.execute("stepi")

        cg_out = open(output_file, "w")

        print("# callgrind format", file=cg_out)
        print("version: 1", file=cg_out)
        print("creator: gdb_callgrind", file=cg_out)
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

                for (obj_filename, fn_name), call in function.calls.items():
                    print(f"cfi={call.filename}", file=cg_out)
                    print(f"cfn={fn_name}", file=cg_out)
                    print(f"cob={obj_filename}", file=cg_out)
                    print(f"calls=1 0x{call.destination_position:x}", file=cg_out)
                    print(f"0x{call.source_position:x} {call.source_line} {call.inclusive_cost}", file=cg_out)

                print("", file=cg_out)


        cg_out.close()


if __name__ == '__main__':
    EmitCallgrind()
