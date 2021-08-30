###############################################################################
# receiver.py
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

def construct_pkt(typ, cnt, data):
    pkt_header = PacketHeader(type=typ, seq_num=cnt, length=len(data))
    pkt_header.checksum = my_checksum_pkt(pkt_header / data)
    pkt = pkt_header / data
    return pkt

def reliable_pkt(pkt):
    return reliable_str(str(pkt))

def reliable_str(s):
    return my_checksum_str(s) == 0

def is_end(pkt):
    return pkt.type == 1

def send_ACK(skt, addr, p):
    myprint("receiver: ACK {}".format(p))
    mysend(str(construct_pkt(ACK, p, "")), skt, addr)
    return

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

def myprint(s):
    sys.stderr.write(s + '\n')

def receiver(receiver_port, window_size):
    """TODO: Listen on socket and print received message to sys.stdout"""
    skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    skt.bind(('127.0.0.1', receiver_port))
    skt.settimeout(0.3)

    l, r, end = 0, window_size, -1
    lst = [None] * window_size
    while(l != end):
        try:
            s, address = skt.recvfrom(2048)
        except:
            continue
        if(not reliable_str(s)):
            myprint("receiver: receive a broken pkt")
            continue
        pkt = decode(s)
        pos = pkt.seq_num
        myprint("receiver: receive a good pkt {}".format(pos))
        if(pos >= r):
            myprint("receiver: pkt {} 's order is too big".format(pos))
            continue

        if(pos == end-1):
            myprint("receiver: receive closed signal")
            break

        send_ACK(skt, address, pos)
        lst[pos] = pkt

        while(lst[l] != None):
            if (is_end(lst[l]) and end==-1):
                end = l + 2
            l = l + 1
            r = r + 1
            lst.append(None)
    #send_ACK(skt, address, end + 1)
    for p in lst[1:end-2]:
        sys.stdout.write(p.load)
    myprint("receiver: closed")

def main():
    """Parse command-line argument and call receiver function """
    if len(sys.argv) != 3:
        sys.exit("Usage: python receiver.py [Receiver Port] [Window Size]")
    receiver_port = int(sys.argv[1])
    window_size = int(sys.argv[2])
    receiver(receiver_port, window_size)

if __name__ == "__main__":
    main()
