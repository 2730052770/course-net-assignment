#-*- coding: UTF-8 -*-
####################################################
# DVrouter.py
# Name: 袁一滔
# JHED ID:
#####################################################

import sys
from collections import defaultdict
from router import Router
from packet import Packet
from json import dumps, loads


class DVrouter(Router):
    """Distance vector routing protocol implementation."""
    INF = 16

    def __init__(self, addr, heartbeatTime):
        """TODO: add your own class fields and initialization code here"""
        Router.__init__(self, addr)  # initialize superclass - don't remove
        self.heartbeatTime = heartbeatTime
        self.last_time = 0
        # Hints: initialize local state

        self.port2edge = {}
        self.addr2port = {}
        self.glbmap = {addr: [0, None]} # 到自己
        # {v1:[d1,fir1], v2:[d2,fir2]}

    def recalculate(self, addri):
        dis = -1
        fir = -1
        for _, (addrv, cost, vmap) in self.port2edge.items():
            hisdis = vmap.get(addri)
            if not hisdis:
                continue
            ndis = hisdis + cost
            if ndis and (dis == -1 or ndis < dis):
                dis = ndis
                fir = addrv
        if dis == -1:
            self.glbmap.pop(addri)
        else:
            self.glbmap.update({addri: [dis, fir]})

    def update(self, port):
        edge = self.port2edge[port]
        vmap = edge[2]
        cost = edge[1]
        addrv = edge[0]
        changed = False
        for i, disi in vmap.items():
            ndis = disi + cost
            path = self.glbmap.get(i) # path[0] is dis, path[1] is the addr to go first
            if not path:
                self.glbmap.update({i: [ndis, addrv]})
                changed = True
                continue
            predis = path[0]
            prefir = path[1]
            if prefir == addrv:
                if ndis < predis:
                    path[0] = ndis
                    changed = True
                elif ndis > predis:
                    self.recalculate(i)
                    changed = True
            else:
                if ndis < predis:
                    path[0] = ndis
                    path[1] = addrv
                    changed = True
        if changed:
            self.broadcast()

    def remove(self, edge):
        vmap = edge[2]
        addrv = edge[0]
        changed = False
        for i, disi in vmap.items():
            path = self.glbmap.get(i)  # path[0] is dis, path[1] is the addr to go first
            prefir = path[1]
            if prefir == addrv:
                self.recalculate(i)
                changed = True
        if changed:
            self.broadcast()

    def handlePacket(self, port, packet):
        """TODO: process incoming packet"""
        if packet.isTraceroute():
            outpath = self.glbmap.get(packet.dstAddr)
            if outpath:
                outport = self.addr2port[outpath[1]]
                self.send(outport, packet)
                #print("pass a pkt")
        else:
            # print("a routing pkt", self.addr, packet.content)
            vmap = loads(packet.content)
            self.port2edge[port][2] = vmap
            self.update(port)
            # print("after receive update", self.glbmap)

    def handleNewLink(self, port, endpoint, cost):
        # print("in new link", self.addr, endpoint, cost)
        self.port2edge.update({port: [endpoint, cost, {endpoint: 0}]})
        self.addr2port.update({endpoint: port})
        self.update(port)
        # print("after new link", self.addr, self.glbmap)

    def handleRemoveLink(self, port):
        # print("in rem link", self.addr, self.port2edge[port][0])
        edge = self.port2edge[port]
        self.addr2port.pop(self.port2edge[port][0])
        self.port2edge.pop(port)
        self.remove(edge)
        # print("after rem link", self.addr, self.glbmap)

    def handleTime(self, timeMillisecs):
        # print("in timeout resent", self.addr)
        if timeMillisecs - self.last_time >= self.heartbeatTime:
            self.last_time = timeMillisecs
            # broadcast the distance vector of this router to neighbors
            self.broadcast()

    def broadcast(self):
        for p, (v, _, _) in self.port2edge.items():
            self.send(p, Packet(Packet.ROUTING, None, None, self.contentto(v)))

    def contentto(self, addrv):
        return dumps({addri: (disi if firi != addrv else self.INF) for addri, (disi, firi) in self.glbmap.items()})

    def debugString(self):
        """TODO: generate a string for debugging in network visualizer"""
        return ""
