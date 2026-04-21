#!/usr/bin/env python3
"""
Detektor steganografii RTP.
Analizuje pliki .pcap i stwierdza czy zawieraja ukryte dane
w polu Timestamp pakietow RTP (4 najnizsze bity).

Uzycie:
    python detector.py <plik.pcap>
    python detector.py <katalog_z_pcapami>
"""

import sys
import struct
import os
import math
from collections import Counter

PREAMBLE = b"DEADBEEF"
EPILOGUE = b"FEEBDAED"

# --- PCAP parser (zero dependencies) ---

def parse_pcap(filepath):
    with open(filepath, 'rb') as f:
        magic = f.read(4)
        if len(magic) < 4:
            return

        if magic == b'\xd4\xc3\xb2\xa1':
            endian = '<'
        elif magic == b'\xa1\xb2\xc3\xd4':
            endian = '>'
        elif magic in (b'\x0a\x0d\x0d\x0a',):
            yield from _parse_pcapng(filepath)
            return
        else:
            print(f"  [!] Nierozpoznany format pliku")
            return

        hdr = f.read(20)
        if len(hdr) < 20:
            return
        _, _, _, _, _, network = struct.unpack(endian + 'HHiIII', hdr)

        while True:
            pkt_hdr = f.read(16)
            if len(pkt_hdr) < 16:
                break
            _, _, incl_len, _ = struct.unpack(endian + 'IIII', pkt_hdr)
            pkt_data = f.read(incl_len)
            if len(pkt_data) < incl_len:
                break

            udp = _extract_udp(pkt_data, network)
            if udp:
                yield udp


def _parse_pcapng(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()

    pos = 0
    endian = '<'
    link_types = {}
    current_iface = 0

    while pos + 12 <= len(data):
        block_type = struct.unpack_from(endian + 'I', data, pos)[0]
        block_len = struct.unpack_from(endian + 'I', data, pos + 4)[0]

        if block_type == 0x0A0D0D0A:
            if block_len >= 16:
                bom = struct.unpack_from('<I', data, pos + 8)[0]
                if bom == 0x1A2B3C4D:
                    endian = '<'
                elif bom == 0x4D3C2B1A:
                    endian = '>'
                block_len = struct.unpack_from(endian + 'I', data, pos + 4)[0]

        if block_len < 12:
            break
        pad_len = (4 - (block_len % 4)) % 4

        if block_type == 0x00000001:
            if block_len >= 20:
                lt = struct.unpack_from(endian + 'H', data, pos + 8)[0]
                link_types[current_iface] = lt
                current_iface += 1

        elif block_type == 0x00000006:
            if block_len >= 32:
                iface_id = struct.unpack_from(endian + 'I', data, pos + 8)[0]
                cap_len = struct.unpack_from(endian + 'I', data, pos + 20)[0]
                pkt_start = pos + 28
                pkt_data = data[pkt_start:pkt_start + cap_len]
                lt = link_types.get(iface_id, 1)
                udp = _extract_udp(pkt_data, lt)
                if udp:
                    yield udp

        elif block_type == 0x00000003:
            if block_len >= 20:
                cap_len = struct.unpack_from(endian + 'I', data, pos + 12)[0]
                pkt_start = pos + 20
                pkt_data = data[pkt_start:pkt_start + cap_len]
                lt = link_types.get(0, 1)
                udp = _extract_udp(pkt_data, lt)
                if udp:
                    yield udp

        pos += block_len + pad_len
        if pos <= 0:
            break


def _extract_udp(pkt_data, network):
    try:
        if network == 1:
            if len(pkt_data) < 14:
                return None
            eth_type = struct.unpack('!H', pkt_data[12:14])[0]
            ip_start = 14
            if eth_type == 0x8100:
                eth_type = struct.unpack('!H', pkt_data[16:18])[0]
                ip_start = 18
            if eth_type != 0x0800:
                return None
        elif network == 101:
            ip_start = 0
        elif network == 113:
            ip_start = 16
        else:
            return None

        ip_data = pkt_data[ip_start:]
        if len(ip_data) < 20:
            return None
        if (ip_data[0] >> 4) != 4:
            return None
        ip_hdr_len = (ip_data[0] & 0xF) * 4
        if ip_data[9] != 17:
            return None

        udp_data = ip_data[ip_hdr_len:]
        if len(udp_data) < 8:
            return None

        src_port, dst_port = struct.unpack('!HH', udp_data[0:4])
        payload = udp_data[8:]
        return (src_port, dst_port, payload)
    except Exception:
        return None


# --- RTP extraction ---

def extract_rtp_streams(pcap_path):
    streams = {}
    for src_port, dst_port, payload in parse_pcap(pcap_path):
        if len(payload) < 12:
            continue
        version = (payload[0] >> 6) & 0x3
        if version != 2:
            continue
        pt = payload[1] & 0x7F
        if pt not in (0, 8, 3, 4, 9, 18, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111):
            continue
        ssrc = struct.unpack("!I", payload[8:12])[0]
        timestamp = struct.unpack("!I", payload[4:8])[0]
        seq = struct.unpack("!H", payload[2:4])[0]
        streams.setdefault(ssrc, []).append((seq, timestamp))

    for ssrc in streams:
        streams[ssrc].sort(key=lambda x: x[0])

    return streams


# --- Detekcja sygnaturowa ---

def detect_signature(timestamps):
    nibbles = [ts & 0x0F for ts in timestamps]
    data = bytearray()
    for i in range(0, len(nibbles) - 1, 2):
        data.append((nibbles[i] << 4) | nibbles[i + 1])

    preamble_pos = data.find(PREAMBLE)
    if preamble_pos != -1:
        epilogue_pos = data.find(EPILOGUE, preamble_pos + len(PREAMBLE))
        if epilogue_pos != -1:
            hidden_len = epilogue_pos - preamble_pos - len(PREAMBLE)
            return True, f"Znaleziono PREAMBLE + EPILOGUE, ukryte dane: {hidden_len} bajtow"
        return True, f"Znaleziono PREAMBLE (DEADBEEF) na pozycji {preamble_pos}"
    return False, None


# --- Detekcja statystyczna ---

def detect_statistical(timestamps):
    if len(timestamps) < 20:
        return False, "Za malo pakietow do analizy", {}

    nibbles = [ts & 0x0F for ts in timestamps]

    counts = Counter(nibbles)
    total = len(nibbles)
    entropy = 0.0
    for c in counts.values():
        p = c / total
        if p > 0:
            entropy -= p * math.log2(p)

    unique_count = len(counts)

    diffs = []
    for i in range(1, len(timestamps)):
        d = timestamps[i] - timestamps[i - 1]
        if 0 < d < 100000:
            diffs.append(d)

    if diffs:
        diff_nibbles = [d & 0x0F for d in diffs]
        diff_unique = len(set(diff_nibbles))
    else:
        diff_unique = 0

    nibble_changes = sum(1 for i in range(1, len(nibbles)) if nibbles[i] != nibbles[i - 1])
    change_rate = nibble_changes / (len(nibbles) - 1) if len(nibbles) > 1 else 0

    # W normalnym RTP (G.711, increment 160=0xA0), najnizszy nibble
    # timestampa jest STALY (bo 160 mod 16 = 0).
    # Przy steganografii nibble zmienia sie w kazdym pakiecie.
    score = 0
    reasons = []

    if change_rate > 0.8:
        score += 40
        reasons.append(f"Wysoki wskaznik zmian nibble: {change_rate:.2f}")
    elif change_rate > 0.5:
        score += 20
        reasons.append(f"Podejrzany wskaznik zmian nibble: {change_rate:.2f}")

    if entropy > 3.5:
        score += 30
        reasons.append(f"Wysoka entropia LSB: {entropy:.2f} bit")
    elif entropy > 2.5:
        score += 15
        reasons.append(f"Podejrzana entropia LSB: {entropy:.2f} bit")

    if unique_count >= 14:
        score += 20
        reasons.append(f"Duza liczba unikalnych nibble: {unique_count}/16")
    elif unique_count >= 10:
        score += 10
        reasons.append(f"Podejrzana liczba unikalnych nibble: {unique_count}/16")

    if diff_unique <= 3 and change_rate > 0.7:
        score += 10
        reasons.append("Stale przyrosty TS ale zmienne LSB — typowe dla modyfikacji")

    stats = {
        'entropy': entropy,
        'unique_nibbles': unique_count,
        'change_rate': change_rate,
        'score': score,
        'total_packets': total,
    }

    return score >= 50, "; ".join(reasons) if reasons else "Brak anomalii", stats


# --- Glowna analiza ---

def analyze_pcap(pcap_path):
    print(f"\n{'='*60}")
    print(f"  Analiza: {os.path.basename(pcap_path)}")
    print(f"{'='*60}")

    streams = extract_rtp_streams(pcap_path)

    if not streams:
        print("  [?] Nie znaleziono pakietow RTP.")
        return None

    print(f"  Znaleziono {len(streams)} strumieni RTP:")

    detected = False

    for ssrc, packets in streams.items():
        timestamps = [ts for _, ts in packets]
        print(f"\n  --- Strumien SSRC: {hex(ssrc)} ({len(packets)} pakietow) ---")

        sig_found, sig_msg = detect_signature(timestamps)
        stat_found, stat_msg, stats = detect_statistical(timestamps)

        if sig_found:
            print(f"  [!!!] SYGNATURA: {sig_msg}")
            detected = True

        if stats:
            print(f"  [STAT] Entropia LSB: {stats['entropy']:.2f} bit | "
                  f"Unikalne nibble: {stats['unique_nibbles']}/16 | "
                  f"Zmiennosc: {stats['change_rate']:.2%}")
            print(f"  [STAT] Wynik punktowy: {stats['score']}/100")

        if stat_found and not sig_found:
            print(f"  [!!]  ANOMALIA STATYSTYCZNA: {stat_msg}")
            detected = True

        if not sig_found and not stat_found:
            print(f"  [OK]  Brak anomalii w tym strumieniu.")

    print(f"\n  {'='*56}")
    if detected:
        print(f"  >>> WYKRYTO STEGANOGRAFIE w pliku {os.path.basename(pcap_path)}")
    else:
        print(f"  >>> BRAK steganografii w pliku {os.path.basename(pcap_path)}")
    print(f"  {'='*56}")

    return detected


def main():
    if len(sys.argv) < 2:
        print("Uzycie: detector.exe <plik.pcap | katalog>")
        print("Przyklad: detector.exe capture1.pcap")
        print("          detector.exe ./pcapy/")
        sys.exit(1)

    target = sys.argv[1]

    if os.path.isdir(target):
        files = sorted(
            os.path.join(target, f)
            for f in os.listdir(target)
            if f.lower().endswith(('.pcap', '.pcapng', '.cap'))
        )
        if not files:
            print(f"Brak plikow .pcap w katalogu {target}")
            sys.exit(1)
    else:
        files = [target]

    results = {}
    for fpath in files:
        result = analyze_pcap(fpath)
        results[os.path.basename(fpath)] = result

    if len(files) > 1:
        print(f"\n\n{'#'*60}")
        print(f"  PODSUMOWANIE")
        print(f"{'#'*60}")
        for name, r in results.items():
            if r is True:
                status = "STEGANOGRAFIA"
            elif r is False:
                status = "CZYSTO"
            else:
                status = "BRAK RTP"
            print(f"  {name:40s} -> {status}")

    stego_count = sum(1 for r in results.values() if r is True)
    clean_count = sum(1 for r in results.values() if r is False)
    print(f"\n  Steganografia: {stego_count} | Czyste: {clean_count} | "
          f"Brak RTP: {len(results) - stego_count - clean_count}")


if __name__ == "__main__":
    main()
