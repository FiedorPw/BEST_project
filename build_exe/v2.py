import pydivert
import struct
import sys

SECRET_FILE = "antygona.txt"

def get_secret_bits(filepath):
    # nasze identyfikatory, że to stegano
    PREAMBLE = b"DEADBEEF"
    EPILOGUE = b"FEEBDAED"
    
    bits = []
    with open(filepath, 'rb') as f:
        file_data = f.read()
        
    # Sklejamy znaczniki z prawdziwym plikiem
    full_data = PREAMBLE + file_data + EPILOGUE
    
    # Zamieniamy całość na bity
    for byte in full_data:
        bits.extend(f"{byte:08b}")
        
    return bits


def start_interceptor():
    try:
        secret_bits = get_secret_bits(SECRET_FILE)
    except FileNotFoundError:
        print(f"Błąd: Utwórz plik {SECRET_FILE}!")
        sys.exit(1)

    total_bits = len(secret_bits)
    print(f"Wczytano {total_bits} bitów do ukrycia.")
    
    print(secret_bits)
    bit_index = 0
    target_ssrc = None 
    
    filtr = "udp.DstPort >= 4000 and udp.DstPort <= 4050"
    print(f"Nasłuchuje na porcie (filtr: {filtr})...")

    with pydivert.WinDivert(filtr) as w:
        for packet in w:
            if packet.ipv4 and packet.payload and len(packet.payload) >= 12:
                
                payload_type = packet.payload[1] & 0x7F
                
                # Upewniamy się, że to na pewno pakiet RTP (v2) i odpowiedni kodek
                if packet.payload[0] == 0x80 and payload_type in [0, 8]:
                    
                    rtp_header = bytearray(packet.payload)
                    # ósmy bajt to ostatni bajt timestamp a kolejne 4 bajty to ssrc
                    current_ssrc = struct.unpack("!I", rtp_header[8:12])[0]
                    
                    if target_ssrc is None:
                        target_ssrc = current_ssrc
                        print(f"Zablokowano na strumieniu kierunkowym SSRC: {hex(target_ssrc)}")
                        print("Rozpoczynam wysyłanie ukrytych danych...")

                    if current_ssrc == target_ssrc:
                        if bit_index < total_bits:
                            
                            # bierzemy 4 bity do zakodowania ; ljust, żeby na koniec się nie rozjechało
                            bits_str = "".join(secret_bits[bit_index : bit_index+4]).ljust(4, '0')
                            print(f"Zakodowano bity: {bits_str}")
                            
                            bits_val = int(bits_str, 2)
                            
                            # Modyfikujemy RTP Timestamp, 4:8 - odpakowujemy cały timestamp
                            ts = struct.unpack("!I", rtp_header[4:8])[0]
                            # zerujemy ostatnie 4 bity i wklejamy w to miejsce nasze
                            ts = (ts & 0xFFFFFFF0) | bits_val
                            #pakujemy
                            rtp_header[4:8] = struct.pack("!I", ts)
                            
                            packet.payload = bytes(rtp_header)
                            bit_index += 4
            
            # Wypuszczamy pakiet do sieci
            w.send(packet)
            
            # koniec działania
            if bit_index >= total_bits:
                print("\n[SUKCES] Cała Antygona została wysłana i ukryta w ruchu!")
                print("Wyłączam skrypt, przywracam normalny ruch sieciowy...")
                break # Przerwanie pętli kończy działanie WinDiverta i całego programu

if __name__ == "__main__":
    start_interceptor()