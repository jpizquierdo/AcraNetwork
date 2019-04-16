__author__ = 'diarmuid'
import sys
sys.path.append("..")
import os

import unittest
import AcraNetwork.SimpleEthernet as SimpleEthernet
import AcraNetwork.Pcap as pcap
import struct

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

class SimpleEthernetTest(unittest.TestCase):

    ######################
    # Ethernet
    ######################
    def test_DefaultEthernet(self):
        e = SimpleEthernet.Ethernet()
        self.assertEqual(e.dstmac,None)
        self.assertEqual(e.srcmac,None)
        self.assertEqual(e.type,None)
        self.assertEqual(e.payload,None)

    def test_basicEthernet(self):
        '''Create an ethernet frame, then unpack it to a new object'''
        e = SimpleEthernet.Ethernet()
        e.srcmac = 0x001122334455
        e.dstmac = 0x998877665544
        e.type = SimpleEthernet.Ethernet.TYPE_IP
        e.payload = struct.pack("H",0xa)
        ethbuf = e.pack()

        e2  = SimpleEthernet.Ethernet()
        e2.unpack(ethbuf)

        self.assertEqual(e2.dstmac,0x998877665544)
        self.assertEqual(e2.type,SimpleEthernet.Ethernet.TYPE_IP)
        self.assertEqual(e2.srcmac,0x001122334455)

    def test_buildEmptyEthernet(self):
        '''Try and create an empty ethernet frame'''
        e = SimpleEthernet.Ethernet()
        self.assertRaises(ValueError,lambda: e.pack())

    ######################
    # IP
    ######################
    def test_defaultIP(self):
        i = SimpleEthernet.IP()
        self.assertRaises(ValueError, lambda : i.pack())

    def test_basicIP(self):
        i = SimpleEthernet.IP()
        i.dstip = "235.0.0.1"
        i.srcip = "192.168.1.1"
        i.payload = struct.pack(">H",0xa5)
        ippayload = i.pack()

        i2 = SimpleEthernet.IP()
        i2.unpack(ippayload)
        self.assertEqual(i2.srcip,"192.168.1.1")
        self.assertEqual(i2.dstip,"235.0.0.1")
        self.assertEqual(i2.payload,struct.pack(">H",0xa5))

    def test_unpackIPShort(self):
        i = SimpleEthernet.IP()
        dummypayload = struct.pack('H',0xa5)
        self.assertRaises(ValueError, lambda : i.unpack(dummypayload))

    ######################
    # UDP
    ######################

    def test_defaultUDP(self):
        u = SimpleEthernet.UDP()
        self.assertRaises(ValueError,lambda :u.pack())

    def test_basicUDP(self):
        u = SimpleEthernet.UDP()
        u.dstport = 5500
        u.srcport = 4400
        u.payload = struct.pack('B',0x5)
        mypacket = u.pack()
        self.assertEqual(mypacket,struct.pack('>HHHHB',4400,5500,9,0,0x5))
        self.assertEqual(repr(u), "SRCPORT=4400 DSTPORT=5500")

    def test_unpackUDPShort(self):
        u = SimpleEthernet.UDP()
        dymmypayload =  struct.pack('H',0xa5)
        self.assertRaises(ValueError,lambda : u.unpack(dymmypayload))


    ######################
    # ICMP
    ######################

    def test_defICMP(self):
        i = SimpleEthernet.ICMP()
        self.assertRaises(ValueError, lambda: i.pack())

    ######################
    # Read a complete pcap file
    ######################
    def test_readUDP(self):
        p = pcap.Pcap(os.path.join(THIS_DIR, "test_input.pcap"))
        mypcaprecord = p[0]
        p.close()
        e = SimpleEthernet.Ethernet()
        e.unpack(mypcaprecord.packet)
        self.assertEqual(e.srcmac,0x0018f8b84454)
        self.assertEqual(e.dstmac,0xe0f847259336)
        self.assertEqual(e.type,0x0800)
        self.assertEqual(repr(e), "SRCMAC=00:18:F8:B8:44:54 DSTMAC=E0:F8:47:25:93:36 TYPE=0X800")

        # checksum test
        (exp_checksum,) = struct.unpack_from("<H", e.payload, 10)
        ip_hdr_checksum = SimpleEthernet.ip_calc_checksum(e.payload[:10] + e.payload[12:20])
        self.assertEqual(exp_checksum, ip_hdr_checksum)
        i = SimpleEthernet.IP()
        i.unpack(e.payload)
        self.assertEqual(i.dstip, "192.168.1.110")
        self.assertEqual(i.srcip, "213.199.179.165")
        self.assertEqual(i.protocol, 0x6)
        self.assertEqual(i.ttl, 48)
        self.assertEqual(i.flags, 0x2)
        self.assertEqual(i.id, 0x4795)
        self.assertEqual(i.len, 56)
        self.assertEqual(i.version, 4)
        #print i
        self.assertEqual(repr(i), "SRCIP=213.199.179.165 DSTIP=192.168.1.110 PROTOCOL=TCP LEN=56")

    # Write an ICMP
    def test_writeICMP(self):

        p = pcap.Pcap("_icmp.pcap",mode='w')
        p.write_global_header()
        r = pcap.PcapRecord()
        r.setCurrentTime()

        ping_req = SimpleEthernet.ICMP()
        ping_req.type = SimpleEthernet.ICMP.TYPE_REQUEST
        ping_req.code = 0
        ping_req.request_id = 0x100
        ping_req.request_sequence = 123
        ping_req.payload = struct.pack(">32B", *range(32))

        e = SimpleEthernet.Ethernet()
        e.srcmac = 0x001122334455
        e.dstmac = 0x998877665544
        e.type = SimpleEthernet.Ethernet.TYPE_IP

        i = SimpleEthernet.IP()
        i.dstip = "235.0.0.1"
        i.srcip = "192.168.1.1"
        i.protocol = SimpleEthernet.IP.PROTOCOLS["ICMP"]
        i.payload = ping_req.pack()
        e.payload = i.pack()
        r.packet = e.pack()
        p.write(r)
        ping_req.type = SimpleEthernet.ICMP.TYPE_REPLY
        i.payload = ping_req.pack()
        e.payload = i.pack()
        p.close()

        p = pcap.Pcap("_icmp.pcap",mode='w')
        p.write_global_header()
        r = pcap.PcapRecord()
        r.setCurrentTime()
        r.packet = e.pack()
        p.write(r)
        p.close()


    def test_readIPchecksum(self):
        p = pcap.Pcap(os.path.join(THIS_DIR, "inetx_test.pcap"))
        mypcaprecord = p[0]
        e = SimpleEthernet.Ethernet()
        e.unpack(mypcaprecord.packet)
        i = SimpleEthernet.IP()
        self.assertTrue(i.unpack(e.payload))
        p.close()


if __name__ == '__main__':
    unittest.main()
