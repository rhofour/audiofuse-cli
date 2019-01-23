#!/usr/bin/python3
import argparse
import sys

import usb.core
from usb.core import USBError
from usb.util import CTRL_OUT, CTRL_TYPE_CLASS, CTRL_RECIPIENT_INTERFACE

ARTURIA_VENDOR_ID = 0x1c75
AUDIOFUSE_PRODUCT_ID = 0xaf02

class AudioFuse:
    """A class for controlling a single AudioFuse device."""

    def __new__(cls, verbose):
        dev = usb.core.find(idVendor=ARTURIA_VENDOR_ID, idProduct=AUDIOFUSE_PRODUCT_ID)
        if dev is None:
            return(None)
        af = super(AudioFuse, cls).__new__(cls)
        af._dev = dev
        af._reattach_interfaces = set()
        af._verbose = verbose
        return(af)

    def set_digital_in(self, val):
        # bRequest: 3
        # wValue: 0x0005 
        # Data: 
        #  0: S/PDIF (coax/optical) (must be differentiated with something else)
        #  1: ADAT
        #  2: W. Clock
        # TODO: The bits in-between
        self.setup()

    def set_digital_out(self, val):
        if val == "spdif":
            data = 0
        elif val == "adat":
            data = 1
        elif val == "wclock":
            data = 2
        else:
            raise ValueError('Unknown value (%s) is not "spdif", "adat", or "wclock"' % val)

        self.setup()
        request_type = usb.util.build_request_type(CTRL_OUT, CTRL_TYPE_CLASS, CTRL_RECIPIENT_INTERFACE)
        self._dev.ctrl_transfer(request_type, 0x03, 0x0105, 0x4600, [data])

    def setup(self):
        # Detach kernel driver if currently attached
        for i in range(self._dev[0].bNumInterfaces): # Check all interfaces
            if self._dev.is_kernel_driver_active(i):
                if self._verbose:
                    print("Detaching from interface %d" % i)
                self._reattach_interfaces |= {i}
                self._dev.detach_kernel_driver(i)

        # The AudioFuse only has one configuration
        self._dev.set_configuration()

    def __del__(self):
        usb.util.dispose_resources(self._dev)

        # Reattach kernel driver if we detached it
        # TODO: Figure out why reattaching sometimes fails with Resource Busy
        for i in self._reattach_interfaces:
            if self._verbose:
                print("Reattaching kernel driver to interface %d." % i)
            self._dev.attach_kernel_driver(i)

def main():
    parser = argparse.ArgumentParser(description="An unofficial, incomplete CLI for controlling the Arturia AudioFuse.")
    parser.add_argument("--digital_in", "--din", choices=["spdif-coax", "spdif-optical", "adat", "wclock"])
    parser.add_argument("--digital_out", "--dout", choices=["spdif", "adat", "wclock"])
    parser.add_argument("-v", action='store_true')
    args = parser.parse_args()

    af = AudioFuse(args.v)
    if af:
        print("Found an AudioFuse.")
    else:
        print("No AudioFuse found.")
        sys.exit(1)
    
    try:
        if args.digital_out:
            af.set_digital_out(args.digital_out)
        if args.digital_in:
            af.set_digital_in(args.digital_in)
    except USBError as e:
        if e.errno is 13:
            print("Insufficient permission to talk to AudioFuse.")
            sys.exit(1)
        raise


if __name__ == "__main__":
    main()
