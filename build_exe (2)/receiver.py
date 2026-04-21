import pydivert
import struct
import os

OUTPUT_FILE = os.path.join(os.environ.get("USERPROFILE", "."), "received.bin")

PREAMBLE = b"DEADBEEF"
EPILOGUE = b"FEEBDAED"

def start_receiver():
    target_ssrc = None
    nibble_count = 0
    high_nibble = 0
    data = bytearray()
    found_preamble = False

    filtr = "udp.DstPort >= 4000 and udp.DstPort <= 4050"

    with pydivert.WinDivert(filtr) as w:
        for packet in w:
            if packet.ipv4 and packet.payload and len(packet.payload) >= 12:
                if packet.payload[0] == 0x80 and (packet.payload[1] & 0x7F) in (0, 8):
                    current_ssrc = struct.unpack("!I", packet.payload[8:12])[0]

                    if target_ssrc is None:
                        target_ssrc = current_ssrc

                    if current_ssrc == target_ssrc:
                        timestamp = struct.unpack("!I", packet.payload[4:8])[0]
                        nibble = timestamp & 0x0F

                        if nibble_count % 2 == 0:
                            high_nibble = nibble
                        else:
                            byte_val = (high_nibble << 4) | nibble
                            data.append(byte_val)

                            if not found_preamble:
                                if len(data) >= 8 and bytes(data[-8:]) == PREAMBLE:
                                    found_preamble = True
                                    data = bytearray()
                            else:
                                if len(data) >= 8 and bytes(data[-8:]) == EPILOGUE:
                                    result = bytes(data[:-8])
                                    with open(OUTPUT_FILE, 'wb') as f:
                                        f.write(result)
                                    w.send(packet)
                                    return

                        nibble_count += 1

            w.send(packet)

if __name__ == "__main__":
    start_receiver()
