"""Wire-level constants for Delta Tau's PMAC protocol.

Delta Tau defined one packet for both transports. The ACC-54E manual calls it
``ETHERNETCMD``::

    typedef struct tagEthernetCmd {
        BYTE RequestType;
        BYTE Request;
        WORD wValue;
        WORD wIndex;
        WORD wLength;
        BYTE bData[1492];
    } ETHERNETCMD;

That layout is exactly a USB control setup packet, because it began as one. So
over USB these requests are control transfers, and over Ethernet the same
structure is sent to a socket on :data:`PMAC_PORT`.
"""

import struct

#: RequestType: direction of the transfer with respect to the host.
VR_DOWNLOAD = 0x40  # host -> controller
VR_UPLOAD = 0xC0  # controller -> host

#: Request codes, from the ACC-54E manual.
VR_PMAC_SENDLINE = 0xB0
VR_PMAC_GETLINE = 0xB1
VR_PMAC_FLUSH = 0xB3
VR_PMAC_GETMEM = 0xB4
VR_PMAC_SETMEM = 0xB5
VR_PMAC_SETBIT = 0xBA
VR_PMAC_SETBITS = 0xBB
VR_PMAC_PORT = 0xBE
VR_PMAC_GETRESPONSE = 0xBF
VR_PMAC_READREADY = 0xC2
VR_CTRL_RESPONSE = 0xC4
VR_PMAC_GETBUFFER = 0xC5
VR_PMAC_WRITEBUFFER = 0xC6
VR_PMAC_WRITEERROR = 0xC7
VR_FWDOWNLOAD = 0xCB
VR_IPADDRESS = 0xE0

#: The controller listens here for UDP or TCP.
PMAC_PORT = 1025

#: Delta Tau's factory default address.
DEFAULT_IP = "192.6.94.5"

#: USB identity of the ACC-54E / Brick USB interface.
USB_VENDOR_ID = 0x0AA2
USB_PRODUCT_ID = 0x0007

#: Reply framing characters.
ACK = 0x06  # terminates a reply
BEL = 0x07  # introduces an error string
STX = 0x02  # introduces a status string
CR = 0x0D  # separates lines within a reply

#: Header layout. The WORD fields are network byte order -- the manual's
#: sample code passes each through htons().
HEADER = struct.Struct(">BBHHH")


def pack(request_type: int, request: int, value: int = 0, index: int = 0,
         data: bytes = b"") -> bytes:
    """Build one protocol packet."""
    return HEADER.pack(request_type, request, value, index, len(data)) + data


#: Control characters accepted as commands in their own right. <CTRL-A> is
#: deliberately absent from any convenience wrapper: it aborts programs but
#: also "brings any disabled or open loop motors to an enabled zero-velocity
#: closed-loop state", so it re-enables motors rather than stopping them.
CTRL_ABORT_ALL = "\x01"  # <CTRL-A>  aborts *and enables* -- see above
CTRL_DISABLE_PLCS = "\x04"  # <CTRL-D>  disable all PLC programs
CTRL_KILL_ALL = "\x0B"  # <CTRL-K>  kill all motors: open loop, output zero
