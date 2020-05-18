#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-

import datetime;
import json;
import sys;


class CodeStream:
    def __init__(self):
        self.code = ""
        self.spaces = 0
        
    def get(self): return self.code
    
    def indent(self): self.spaces += 4
    def unindent(self): self.spaces -= 4
    
    def write(self, text):
        self.code += text
        
    def begin_line(self):
        self.write(" " * self.spaces)
        
    def write_line(self, line=""):
        self.begin_line()
        self.write(line + "\n")

class MethodInfo:
    def fix_possible_argument_conflicts(self, name):
        conflict_count = -1
        
        for (argument_name, argument_type) in self.arguments:
            if argument_name == name:
                conflict_count += 1
        
        if conflict_count > 0:
            index = 0
            for i in range(len(self.arguments)):
                (argument_name, argument_type) = self.arguments[i]

                if (argument_name == name):
                    self.arguments[i] = ('{0}{1}'.format(argument_name, index), argument_type)
                    index += 1

    def __init__(self, instruction):
        self.bound_increment_needed = False
        self.result_type_index = -1
        self.name = instruction['opname'][2:]
        self.arguments = []
        self.cl = instruction['class']

        i = 0

        if 'operands' in instruction:
            for data in instruction['operands']:
                if data['kind'] != 'IdResult':
                    if data['kind'] == 'IdResultType':
                        self.result_type_index = i
                    self.arguments.append((get_argument_name(data, i), get_type_by_operand(data)))
                    i += 1
                else:
                    self.bound_increment_needed = True
        
        for (argument_name, _) in self.arguments:
            self.fix_possible_argument_conflicts(argument_name)


def get_instructions_by_class(spec_data, cl):
    result = []
    for instruction in spec_data['instructions']:
        if instruction['class'] == cl:
            result.append(instruction)
    return result

def get_instruction_by_name(spec_data, opname):
    for instruction in spec_data['instructions']:
        if instruction['opname'] == opname:
            return instruction
    return None

def get_argument_name(operand, position):
    if operand['kind'] == 'IdResultType':
        return 'resultType'
    
    if 'name' in operand and not '\n' in operand['name'] and not '~' in operand['name'] and not ',' in operand['name'] and operand['name'].isascii():
        
        i = 0

        name = operand['name'].replace('\'', '').replace(' ', '').replace('.', '')

        name = name[0].lower() + name[1:]

        # replace reserved words
        if name == 'object':
            return 'obj'
        elif name == 'base':
            return 'baseObj'
        elif name == 'default':
            return 'defaultObj'
        elif name == 'event':
            return 'eventObj'

        return name

    # the name wasn't derived from the description, try to match some common types that are allowed.
    namemapping = [
        'Dim',
        'ImageFormat',
        'AccessQualifier',
        'AccessQualifier',
        'StorageClass',
        'SamplerAddressingMode',
        'SamplerFilterMode',
        'FunctionControl',
        'ImageOperands',
        'LoopControl',
        'SelectionControl',
        'MemoryAccess'
    ]

    if operand['kind'] in namemapping:
        return operand['kind'][0].lower() + operand['kind'][1:]

    # Dref case
    if 'name' in operand and operand['name'] == '\'D~ref~\'':
        return 'dRef'

    # this case is a pain to handle, let's just give up in this case
    if operand['kind'] in ['IdRef', 'PairIdRefIdRef'] and 'quantifier' in operand and operand['quantifier'] == '*':
        return 'parameters'
    

    print('// Unmanaged argument name: {0}'.format(operand))


    return 'arg{0}'.format(position)

def get_type_by_operand(operand):
    enum_masks = ['MemoryAccess', 'ImageOperands', 'LoopControl', 'SelectionControl', 'FunctionControl']

    typemapping = {
        'LiteralString': 'string',
        'IdRef': 'Instruction',
        'IdResultType': 'Instruction',
        'IdScope': 'Instruction',
        'IdMemorySemantics': 'Instruction',
        'PairIdRefIdRef': 'Instruction',
        'LiteralContextDependentNumber': 'LiteralInteger',
        'LiteralSpecConstantOpInteger': 'LiteralInteger',
        'PairLiteralIntegerIdRef': 'Operand'
    }

    kind = operand['kind']

    result = kind

    if kind in typemapping:
        result = typemapping[kind]
    if kind in enum_masks:
        result = kind + 'Mask'

    if 'quantifier' in operand and operand['quantifier'] == '*':
        result = 'params {0}[]'.format(result)


    return result

def generate_method_for_instruction(stream, instruction):
    method_info = MethodInfo(instruction)

    stream.indent()
    generate_method_prototye(stream, method_info)
    generate_method_definition(stream, method_info)
    stream.unindent()

def generate_method_definition(stream, method_info):
    stream.write_line('{')
    stream.indent()

    if method_info.bound_increment_needed:
        if method_info.result_type_index != -1:
            (argument_name, _) = method_info.arguments[method_info.result_type_index]
            stream.write_line('Instruction result = new Instruction(Op.Op{0}, GetNewId(), {1});'.format(method_info.name, argument_name))
        else:
            # Optimization: here we explictly don't set the id because it will be set in AddTypeDeclaration/AddLabel.
            # In the end this permit to not reserve id that will be discared.
            if method_info.cl == 'Type-Declaration' or method_info.name == 'Label':
                stream.write_line('Instruction result = new Instruction(Op.Op{0});'.format(method_info.name))
            else:
                stream.write_line('Instruction result = new Instruction(Op.Op{0}, GetNewId());'.format(method_info.name))
    else:
        if method_info.result_type_index != -1:
            raise "TODO"
        stream.write_line('Instruction result = new Instruction(Op.Op{0});'.format(method_info.name))

    stream.write_line()

    for (argument_name, _) in method_info.arguments:
        # skip result type as it's send in the constructor
        if argument_name == 'resultType':
            continue
        stream.write_line('result.AddOperand({0});'.format(argument_name))

    if method_info.cl == 'Type-Declaration':
        stream.write_line('AddTypeDeclaration(result);')
        stream.write_line()
    elif method_info.cl == 'Constant-Creation' and method_info.name.startswith('Constant'):
        stream.write_line('AddGlobalVariable(result);')
        stream.write_line()
    elif not method_info.name == 'Variable' and not method_info.name == 'Label':
        stream.write_line('AddToFunctionDefinitions(result);')
        stream.write_line()


    stream.write_line('return result;')
    stream.unindent()
    stream.write_line('}')
    stream.write_line()

def generate_method_prototye(stream, method_info):
    stream.begin_line()
    stream.write('protected Instruction {0}('.format(method_info.name))

    arguments = []

    i = 0

    for (argument_name, argument_type) in method_info.arguments:
        arguments.append('{0} {1}'.format(argument_type, argument_name))
        i += 1

    stream.write(', '.join(arguments))
    stream.write(')\n')

def generate_methods_by_class(stream, spec_data, cl):
    stream.indent()
    stream.write_line('// {0}'.format(cl))
    stream.write_line()
    stream.unindent()
    for instruction in get_instructions_by_class(spec_data, cl):
        generate_method_for_instruction(stream, instruction)

def main():
    if len(sys.argv) < 3:
        print("usage: %s grammar.json Target.cs" % (sys.argv[0]))
        exit(1)

    spec_filepath = sys.argv[1]
    result_filepath = sys.argv[2]


    with open(spec_filepath, "r") as f:
        spec_data = json.loads(f.read())

    stream = CodeStream()

    stream.write_line("// AUTOGENERATED: DO NOT EDIT")
    stream.write_line("// Last update date: {0}".format(datetime.datetime.now()))

    stream.write_line("#region Grammar License")
    for copyright_line in spec_data['copyright']:
        stream.write_line('// {0}'.format(copyright_line))
    
    stream.write_line("#endregion")
    stream.write_line()


    stream.write_line('using static Spv.Specification;')
    stream.write_line()
    stream.write_line('namespace Spv.Generator')
    stream.write_line('{')
    stream.indent()
    stream.write_line('public partial class Module')
    stream.write_line('{')


    generate_methods_by_class(stream, spec_data, 'Miscellaneous')
    generate_methods_by_class(stream, spec_data, 'Type-Declaration')
    generate_methods_by_class(stream, spec_data, 'Constant-Creation')
    generate_methods_by_class(stream, spec_data, 'Memory')
    generate_methods_by_class(stream, spec_data, 'Function')
    generate_methods_by_class(stream, spec_data, 'Image')
    generate_methods_by_class(stream, spec_data, 'Conversion')
    generate_methods_by_class(stream, spec_data, 'Composite')
    generate_methods_by_class(stream, spec_data, 'Arithmetic')
    generate_methods_by_class(stream, spec_data, 'Bit')
    generate_methods_by_class(stream, spec_data, 'Relational_and_Logical')
    generate_methods_by_class(stream, spec_data, 'Derivative')
    generate_methods_by_class(stream, spec_data, 'Control-Flow')
    generate_methods_by_class(stream, spec_data, 'Atomic')
    generate_methods_by_class(stream, spec_data, 'Primitive')
    generate_methods_by_class(stream, spec_data, 'Barrier')
    generate_methods_by_class(stream, spec_data, 'Group')
    generate_methods_by_class(stream, spec_data, 'Device-Side_Enqueue')
    generate_methods_by_class(stream, spec_data, 'Pipe')
    generate_methods_by_class(stream, spec_data, 'Non-Uniform')
    generate_methods_by_class(stream, spec_data, 'Reserved')

    stream.write_line('}')
    stream.unindent()
    stream.write_line('}')

    with open(result_filepath, "w+") as result_file:
        result_file.write(stream.get())

    return


if __name__ == '__main__':
    main()