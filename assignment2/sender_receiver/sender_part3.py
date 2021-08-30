###############################################################################
# sender.py
# Name:
# JHED ID:
###############################################################################

import sys
import socket
from util import *
import random

START = 0
END = 1
DATA = 2
ACK = 3
K = 0.5

def my_checksum_str(s):
    l = len(s)
    if(l & 1):
        s += chr(0)
        l = l + 1
    res = 0
    for i in range(0, l, 2):
        t = (ord(s[i]) << 8) + ord(s[i+1])  # high byte first
        res = res + t
    res = (res >> 16) + (res & 0xffff)
    res = (res >> 16) + (res & 0xffff)
    return res ^ 0xffff

def my_checksum_pkt(pkt):
    return my_checksum_str(str(pkt))

DATAMAX=1024

def read_local_data():
    return sys.stdin.read(DATAMAX)

def construct_pkt(typ, cnt, data):
    pkt_header = PacketHeader(type=typ, seq_num=cnt, length=len(data))
    pkt_header.checksum = my_checksum_pkt(pkt_header / data)
    pkt = pkt_header / data
    return pkt

def read_local_packet(cnt):
    data = read_local_data()
    if(not data):
        return None
    return construct_pkt(2, cnt, data)

def packet_start(cnt):
    return construct_pkt(0, cnt, "")

def packet_end(cnt):
    return construct_pkt(1, cnt, "")

def read_local_packet_list():
    id = 0
    pkt = packet_start(id)
    l = []
    while(pkt):
        l.append(pkt)
        id = id + 1
        pkt = read_local_packet(id)
    l.append(packet_end(id))
    l.append(packet_end(id+1)) # 3-time shake hands
    return l

def send_win_not_ACK(pkt_list, acked, l, r, skt, ip, port):
    lst = []
    strs = []
    for i in range(l, r):
        if(not acked[i]):
            lst.append(i)
            strs.append(str(pkt_list[i]))
    print("sender: send {}".format(lst))
    for s in strs:
        mysend(s, skt, (ip, port))

def reliable_pkt(pkt):
    return reliable_str(str(pkt))

def reliable_str(s):
    return my_checksum_str(s) == 0

def decode_i(s):
    return (ord(s[0])<<24) | (ord(s[1])<<16) | (ord(s[2])<<8) | ord(s[3])

def decode(s):
    return PacketHeader(type = decode_i(s[0:4]), seq_num = decode_i(s[4:8]), length = decode_i(s[8:12]), checksum = decode_i(s[12:16])) / s[16:]

def mysend(s, skt, addr):
    while(random.random() < K):
        pos = int(random.random() * len(s))
        b = int(random.random() * 8)
        c = chr(ord(s[pos]) ^ (((ord(s[pos])>>b)&1)<<b))
        s = s[:pos] + c + s[pos+1:]
    skt.sendto(s, addr)

def send_list(pkt_list, ip, port, win_size):
    skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    skt.settimeout(0.3)

    print("sender: total num of pkt is {}".format(len(pkt_list)))

    tail = len(pkt_list)
    acked = [False] * tail
    l, r = 0, min(win_size, tail-2) # [l,r)
    send_win_not_ACK(pkt_list, acked, l, r, skt, ip, port)
    end_cnt = 0

    while(l < tail):
        try:
            s, address = skt.recvfrom(2048)
            pkt = decode(s)
            if (not reliable_pkt(pkt)):
                print("sender: receive a broken pkt")
                continue
            print("sender: receive a good pkt {}".format(pkt.seq_num))
        except:
            if(l == tail-1): # 2nd FIN_ACK
                end_cnt = end_cnt + 1
                if(end_cnt >= 3):
                    print("sender: closed")
                    break
                continue
            print("sender: receive timeout")
            send_win_not_ACK(pkt_list, acked, l, r, skt, ip, port)
            continue

        seq_num = pkt.seq_num
        if(seq_num < l or seq_num >= r or acked[seq_num]):
            continue
        acked[seq_num] = True
        # useless
        while(acked[l]):
            l = l + 1
        newr = min(l + win_size, tail-2)
        if (l >= tail - 2):  # complete
            newr = l + 1
        send_win_not_ACK(pkt_list, acked, r, newr, skt, ip, port)
        r = newr

def sender(receiver_ip, receiver_port, window_size):
    """TODO: Open socket and send message from sys.stdin"""
    send_list(read_local_packet_list(), receiver_ip, receiver_port, window_size)

def main():
    """Parse command-line arguments and call sender function """
    if len(sys.argv) != 4:
        sys.exit("Usage: python sender.py [Receiver IP] [Receiver Port] [Window Size] < [message]")
    receiver_ip = sys.argv[1]
    receiver_port = int(sys.argv[2])
    window_size = int(sys.argv[3])
    sender(receiver_ip, receiver_port, window_size)

if __name__ == "__main__":
    main()
