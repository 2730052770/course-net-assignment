#-*- coding: UTF-8 -*-
####################################################
# LSrouter.py
# Name: 袁一滔
# JHED ID:
#####################################################

import sys
from collections import defaultdict
from router import Router
from packet import Packet
from json import dumps, loads
import numpy as np
import heapq

class LSrouter(Router):
    """Link state routing protocol implementation."""


    pktadd = 1
    pktrem = 2
    pktupd = 3


    def __init__(self, addr, heartbeatTime):
        """TODO: add your own class fields and initialization code here"""
        Router.__init__(self, addr)  # initialize superclass - don't remove
        self.heartbeatTime = heartbeatTime
        self.last_time = 0
        # Hints: initialize local state

        self.port2edge = {}
        self.addr2shortestport = {}
        self.glbmap = {}  # {u:{v1:c1,v2:c2},...}
        self.rcvid = {addr: 0}
        self.sendid = 1

        pass

    def broadcast(self, pkt, excpt = None):
        for port in self.port2edge.keys():
            if(port == excpt):
                continue
            self.send(port, pkt)

    def handlePacket(self, port, packet):
        """TODO: process incoming packet"""
        if packet.isTraceroute():
            outport = self.addr2shortestport.get(packet.dstAddr)
            if(outport):
                self.send(outport, packet)
        else:
            typ, args = loads(packet.content)
            sender, id = args[0], args[1]
            preid = self.rcvid.get(sender)
            if(preid and ((typ == self.pktupd and id <= preid) or (typ != self.pktupd and id != preid + 1))):
                # 这个改成 id != preid + 1 第二个点会错，因为可能你前几次都没收到（未连通），然后连通之后就再也收不到了
                # 改成 id <= preid 也会错，因为可能会先接受到大的标号的更新而把小的丢了
                # 所以我们折中，认为小变动需要保证标号连续，而大更新只需要标号更大即可
                # 总之这个没有绝对正确，只能说在一定时间后会变得正确
                return
            self.rcvid.update({sender: id})
            self.broadcast(packet, excpt=port)
            if(typ == self.pktadd):
                self.mapadd(*args)
            elif(typ == self.pktrem):
                self.maprem(*args)
            elif(typ == self.pktupd):
                self.mapupd(*args)
            else:
                print("unkown pkt type")
            self.runnetwork()

    def runnetwork(self):
        L = len(self.glbmap)
        toaddr = {i: a for i, a in enumerate(self.glbmap.keys())}
        toindex = {a: i for i, a in toaddr.items()}
        edge = [[(toindex[v], c) for v, c in self.glbmap[toaddr[u]].items()] for u in range(L)]
        dis = np.array([-1] * L, dtype=int)
        first = np.array([-1] * L, dtype=int)
        vis = np.array([0] * L, dtype=int)
        hp = []
        src = toindex[self.addr]
        dis[src] = 0
        for v, c in edge[src]:
            dis[v] = c
            first[v] = v
            heapq.heappush(hp, (c, v))
        while(hp):
            u = heapq.heappop(hp)[1]
            if(vis[u]):
                continue
            vis[u] = 1
            for v,c in edge[u]:
                ndis = dis[u] + c
                if(dis[v] != -1 and ndis >= dis[v]):
                    continue
                dis[v] = ndis
                first[v] = first[u]
                heapq.heappush(hp, (dis[v], v))
        addr2port = {a:p for p, (a, _) in self.port2edge.items()}
        try:
            self.addr2shortestport = {toaddr[v]:addr2port[toaddr[first[v]]] for v in range(L) if (first[v] != -1)}
        except:
            print(self.addr)
            print(addr2port)
            print(self.glbmap)
            exit(-1)


    def mapset(self, a, b, c):
        disca = self.glbmap.get(a)
        if(not disca):
            self.glbmap.update({a:{b:c}})
        else:
            disca.update({b:c})

    def mappop(self, a, b):
        disca = self.glbmap.get(a)
        if(disca and disca.get(b)):
            disca.pop(b)

    def mapadd(self, addru, sendid, addrv, cost):
        self.mapset(addru, addrv, cost)
        self.mapset(addrv, addru, cost)

    def maprem(self, addru, sendid, addrv):
        self.mappop(addru, addrv)
        self.mappop(addrv, addru)

    def mapupd(self, addru, sendid, umap):
        preumap = self.glbmap.get(addru)
        directlinkvalue = None
        if(preumap):
            directlinkvalue = preumap.get(self.addr) # 看addru是否有与我相连的边
            for v in preumap.keys():
                self.glbmap[v].pop(addru)
        self.glbmap.update({addru: umap})
        for v, c in umap.items():
            self.mapset(v, addru, c)

        if(directlinkvalue):  # 非常关键，如果一个人的upd要改我的边，不允许他在我的地图里改（他的信息可能是滞后或超前的）。我的边应该全部由自己管辖，这样才不会导致我的port数组和map数组不匹配
            self.mapadd(self.addr, None, addru, directlinkvalue)
        else:
            self.maprem(self.addr, None, addru)

    def handleNewLink(self, port, endpoint, cost):

        # print("in newlink", self.addr, endpoint, cost)
        # self.handleRemoveLink(port) # is this usable?
        self.port2edge.update({port: (endpoint, cost)})
        self.handlePacket(None, Packet(Packet.ROUTING, self.addr, None, dumps((self.pktadd, (self.addr, self.sendid, endpoint, cost)))))
        self.sendid = self.sendid + 1



    def handleRemoveLink(self, port):
        prelink = self.port2edge.get(port)
        if (prelink):
            endpoint = prelink[0]
            self.port2edge.pop(port)
            self.handlePacket(None, Packet(Packet.ROUTING, self.addr, None, dumps((self.pktrem, (self.addr, self.sendid, endpoint)))))
            self.sendid = self.sendid + 1



    def handleTime(self, timeMillisecs):
        if timeMillisecs - self.last_time >= self.heartbeatTime:
            self.last_time = timeMillisecs
            self.handlePacket(None, Packet(Packet.ROUTING, self.addr, None, dumps((self.pktupd, (self.addr, self.sendid, self.glbmap[self.addr])))))
            self.sendid = self.sendid + 1
            # Hints:
            # broadcast the link state of this router to all neighbors


    def debugString(self):
        """TODO: generate a string for debugging in network visualizer"""
        return ""
