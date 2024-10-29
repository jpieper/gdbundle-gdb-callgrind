# Copyright 2024 Josh Pieper.  jjp@pobox.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import gdb

class Frame:
    '''Simple wrapper around a gdb frame that makes it easier to access
    all the fields we want.'''
    def __init__(self, gdb_frame=None):
        if gdb_frame is None:
            gdb_frame = gdb.newest_frame()

        f = gdb_frame
        self.gdb_frame = f
        self.cur_pc = f.pc()
        self.fn_name = f.name()
        self.obj_filename = f.function().symtab.objfile.filename
        self.sal = f.find_sal()
        self.filename = self.sal.symtab.filename
        self.line = self.sal.line
        self.addrline = (self.cur_pc, self.line)
        self.obj_file_pair = (self.obj_filename, self.filename)


    def parent(self):
        parent_gdb = self.gdb_frame.older()
        if parent_gdb.function() is None:
            return None
        return Frame(gdb_frame=parent_gdb)


class Call:
    '''A single callgrind call site.  Not being instrumented, we won't be
    able to track the actual number of calls, but we can track the
    total inclusive cost.
    '''
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

        # This keeps track of our "self" time.  It is a dictionary with
        #
        #  key: (addr, line)
        # and
        #  value: count
        self.positions = {}

        # Indexed by (obj_filename, fn_name), each value is a Call
        # instance.
        self.calls = {}


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

        i = 1
        while True:
            output_file = f"callgrind.out.{i}"
            if not os.path.exists(output_file):
                break
            i += 1

        gdb.write(f"Stepping to {final_ip}, writing output to {output_file}")

        object_files = {}
        total_instr_count = 0

        while True:
            f = Frame()

            if f.obj_file_pair not in object_files:
                object_files[f.obj_file_pair] = ObjectFile(
                    f.filename, f.obj_filename)

            object_file = object_files[f.obj_file_pair]

            if f.fn_name not in object_file.functions:
                object_file.functions[f.fn_name] = Function(f.fn_name)

            fn = object_file.functions[f.fn_name]

            if f.addrline not in fn.positions:
                fn.positions[f.addrline] = 0

            fn.positions[f.addrline] += 1
            total_instr_count += 1

            # Try to record call-stack information.
            old_parent = f
            parent = f.parent()
            while parent is not None:
                if parent.obj_file_pair not in object_files:
                    object_files[parent.obj_file_pair] = \
                        ObjectFile(parent.filename, parent.obj_filename)

                this_object_file = object_files[parent.obj_file_pair]

                if parent.fn_name not in this_object_file.functions:
                    this_object_file.functions[parent.fn_name] = \
                        Function(parent.fn_name)

                this_fn = this_object_file.functions[parent.fn_name]

                call_obj_fn = (old_parent.obj_filename, old_parent.fn_name)
                if call_obj_fn not in this_fn.calls:
                    this_fn.calls[call_obj_fn] = Call()

                this_call = this_fn.calls[call_obj_fn]
                this_call.filename = parent.filename

                if (this_call.destination_position is None or
                    parent.cur_pc < this_call.destination_position):
                    this_call.destination_position = parent.cur_pc

                this_call.source_line = old_parent.line

                this_call.source_position = old_parent.cur_pc
                this_call.inclusive_cost += 1

                old_parent = parent
                parent = parent.parent()

            if f.cur_pc == final_ip:
                break

            gdb.execute("stepi")

        cg_out = open(output_file, "w")

        print("# callgrind format", file=cg_out)
        print("version: 1", file=cg_out)
        print("creator: gdb_callgrind", file=cg_out)
        print("positions: instr line", file=cg_out)
        print("events: Instructions", file=cg_out)
        print(f"summary: {total_instr_count}", file=cg_out)
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
