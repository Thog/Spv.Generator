﻿using System;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;

namespace Spv.Generator
{
    public class LiteralInteger : Operand, IEquatable<LiteralInteger>
    {
        public OperandType Type => OperandType.Number;

        private byte[] _data;

        public LiteralInteger(byte[] data)
        {
            _data = data;
        }

        public static implicit operator LiteralInteger(int value) => Create(value);
        public static implicit operator LiteralInteger(uint value) => Create(value);
        public static implicit operator LiteralInteger(long value) => Create(value);
        public static implicit operator LiteralInteger(ulong value) => Create(value);
        public static implicit operator LiteralInteger(float value) => Create(value);
        public static implicit operator LiteralInteger(double value) => Create(value);
        public static implicit operator LiteralInteger(Enum value) => Create((int)Convert.ChangeType(value, typeof(int)));

        // NOTE: this is not in the standard, but this is some syntax sugar useful in some instructions (TypeInt ect)
        public static implicit operator LiteralInteger(bool value) => Create(Convert.ToInt32(value));

        public static LiteralInteger Create<T>(T value) where T: struct
        {
            return new LiteralInteger(MemoryMarshal.Cast<T, byte>(MemoryMarshal.CreateSpan(ref value, 1)).ToArray());
        }

        public ushort WordCount => (ushort)(_data.Length / 4);

        public void WriteOperand(Stream stream)
        {
            stream.Write(_data);
        }

        public override bool Equals(object obj)
        {
            return obj is LiteralString literalString && Equals(literalString);
        }

        public bool Equals(LiteralInteger cmpObj)
        {
            return Type == cmpObj.Type && _data.SequenceEqual(cmpObj._data);
        }

        public override int GetHashCode()
        {
            return HashCode.Combine(Type, _data);
        }

        public bool Equals(Operand obj)
        {
            return obj is Instruction instruction && Equals(instruction);
        }
    }
}
