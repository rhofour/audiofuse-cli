#!/usr/bin/python3
import argparse
from enum import Enum, unique
import sys

import usb.core
from usb.core import USBError
from usb.util import CTRL_IN, CTRL_OUT, CTRL_TYPE_CLASS, CTRL_RECIPIENT_INTERFACE

ARTURIA_VENDOR_ID = 0x1c75
AUDIOFUSE_PRODUCT_ID = 0xaf02

Input = Enum(value='Input', names=[
    ('Unknown', 0),
    ('SPDIF_coax', 1),
    ('spdif-coax', 1),
    ('SPDIF_optical', 2),
    ('SPDIF-optical', 2),
    ('ADAT', 3),
    ('adat', 3),
    ('WClock', 4),
    ('wclock', 4),
    ])
Output = Enum(value='Output', names=[
    ('Unknown', 0),
    ('SPDIF', 1),
    ('spdif', 1),
    ('ADAT', 2),
    ('adat', 2),
    ('WClock', 3),
    ('wclock', 3),
    ])

class RequiresAllowRestart(Exception):
    "Thrown when a restart is attempted without the allow_restart flag."
    pass

class AudioFuse:
    """A class for controlling a single AudioFuse device."""

    input = Input.Unknown
    output = Output.Unknown

    def __new__(cls, verbose, allow_restart):
        dev = usb.core.find(idVendor=ARTURIA_VENDOR_ID, idProduct=AUDIOFUSE_PRODUCT_ID)
        if dev is None:
            return(None)
        af = super(AudioFuse, cls).__new__(cls)
        af._dev = dev
        af._reattach_interfaces = set()
        af._verbose = verbose
        af._allow_restart = allow_restart
        af.attach()
        af.get_initial_status()
        return(af)

    def _change_digital_in(self, val):
        "Send the actual USB packets to the Audiofuse to change the digital in setting."
        if val == Input.SPDIF_coax:
            data = 0
            data2 = 0
        if val == Input.SPDIF_optical:
            data = 0
            data2 = 1
        elif val == Input.ADAT:
            data = 1
            data2 = 1
            # 0x0105 = 2 at the end when restart needed
        elif val == Input.WClock:
            data = 2
            data2 = 0
        else:
            raise ValueError('Unknown value (%s) is not "spdif-coax", "spdif-optical", "adat", or "wclock"' % val)

        request_type = usb.util.build_request_type(CTRL_OUT, CTRL_TYPE_CLASS, CTRL_RECIPIENT_INTERFACE)
        self._dev.ctrl_transfer(request_type, 0x03, 0x0005, 0x4600, [data])
        self._dev.ctrl_transfer(request_type, 0x03, 0x0305, 0x4600, [data2])
        self._dev.ctrl_transfer(request_type, 0x03, 0x0c05, 0x4600, [0])
        self._dev.ctrl_transfer(request_type, 0x03, 0x0300, 0x4c00, [0, 0])
        self._dev.ctrl_transfer(request_type, 0x03, 0x0200, 0x4c00, [0, 0])

    def set_digital_in(self, val):
        if self._verbose:
            print("Attempting to set digital in to: %s" % val)
        if val == self.input:
            if self._verbose:
                print("Input already set correctly. Skipping.")
                return

        restart = False
        # Restart when we would be switching from no ADAT I/O to some ADAT I/O
        # or from some ADAT I/O to no ADAT I/O.
        if (val == Input.ADAT and self.input != Input.ADAT and self.output != Output.ADAT) or (
                val != Input.ADAT and self.input == Input.ADAT and self.output != Output.ADAT):
            restart = True
            if not self._allow_restart:
                raise RequiresAllowRestart

        self._change_digital_in(val)
        if restart:
            self._change_digital_out(self.output)

    def _change_digital_out(self, val):
        "Send the actual USB packets to the Audiofuse to change the digital out setting."
        if val == Output.SPDIF:
            data = 0
        elif val == Output.ADAT:
            data = 1
        elif val == Output.WClock:
            data = 2
        else:
            raise ValueError('Unknown value (%s) is not "spdif", "adat", or "wclock"' % val)

        request_type = usb.util.build_request_type(CTRL_OUT, CTRL_TYPE_CLASS, CTRL_RECIPIENT_INTERFACE)
        self._dev.ctrl_transfer(request_type, 0x03, 0x0105, 0x4600, [data])

    def set_digital_out(self, val):
        if self._verbose:
            print("Attempting to set digital out to: %s" % val)
        if val == self.output:
            if self._verbose:
                print("Output already set correctly. Skipping.")
                return

        restart = False
        # Restart when we would be switching from no ADAT I/O to some ADAT I/O
        # or from some ADAT I/O to no ADAT I/O.
        if (val == Output.ADAT and self.output != Output.ADAT and self.input != Input.ADAT) or (
                val != Output.ADAT and self.output == Output.ADAT and self.input != Input.ADAT):
            restart = True
            if not self._allow_restart:
                raise RequiresAllowRestart

        self._change_digital_out(val)
        if restart:
            self._change_digital_in(self.input)
            # TODO: Wait and reconnect after restart. Otherwise a subsequent
            # set_digital_in will fail.

    def attach(self):
        # Detach kernel driver if currently attached
        for i in range(self._dev[0].bNumInterfaces): # Check all interfaces
            if self._dev.is_kernel_driver_active(i):
                if self._verbose:
                    print("Detaching from interface %d" % i)
                self._reattach_interfaces |= {i}
                self._dev.detach_kernel_driver(i)

        # The AudioFuse only has one configuration
        self._dev.set_configuration()

    def get_initial_status(self):
        class TemplateMatchError(Exception):
            "Thrown when we're unable to match any of the given templates."
            pass
        def match_template(arr, templates):
            checked_bytes = {}
            for (tmpl_val, tmpl_bytes) in templates:
                bad_match = False
                for (byte_num, val) in tmpl_bytes:
                    b = arr[byte_num]
                    if b != val:
                        checked_bytes[byte_num] = b
                        bad_match = True
                        break
                if bad_match:
                    continue
                return(tmpl_val)
            raise TemplateMatchError(checked_bytes)

        input_templates = [
            (Input.SPDIF_coax,    [(22, 0), (28, 0)]),
            (Input.SPDIF_optical, [(22, 1), (28, 0)]),
            (Input.ADAT,          [(22, 1), (28, 1)]),
            (Input.WClock,        [(22, 0), (28, 2)]),
        ]
        output_templates = [
            (Output.SPDIF,  [(27, 0), (29, 0)]),
            (Output.ADAT,   [(27, 0), (29, 1)]),
            (Output.WClock, [(27, 1), (29, 2)]),
        ]

        # Request the status of the Audiofuse
        request_type = usb.util.build_request_type(CTRL_IN, CTRL_TYPE_CLASS, CTRL_RECIPIENT_INTERFACE)
        status_bytes = bytearray(self._dev.ctrl_transfer(request_type, 0x03, 0, 0x4700, 178))
        if self._verbose:
            print("Initial Status data:", status_bytes.hex())

        # Interpret the status bytes and set class members accordingly
        try:
            self.input = match_template(status_bytes, input_templates)
        except TemplateMatchError as e:
            print("Could not identify input: %s" % e)
        try:
            self.output = match_template(status_bytes, output_templates)
        except TemplateMatchError as e:
            print("Could not identify output: %s" % e)
        print("AudioFuse Digital I/O set to %s and %s" % (self.input, self.output))

    def __del__(self):
        usb.util.dispose_resources(self._dev)

        # Reattach kernel driver if we detached it
        for i in self._reattach_interfaces:
            if self._verbose:
                print("Reattaching kernel driver to interface %d." % i)
            try:
                self._dev.attach_kernel_driver(i)
            except USBError as e:
                if e.errno is 16:
                    print("TODO: Figure out why we get resource busy errors here.")
                else:
                    raise

def main():
    parser = argparse.ArgumentParser(description="An unofficial, incomplete CLI for controlling the Arturia AudioFuse.")
    parser.add_argument("--digital_in", "--din", choices=["spdif-coax", "spdif-optical", "adat", "wclock"])
    parser.add_argument("--digital_out", "--dout", choices=["spdif", "adat", "wclock"])
    parser.add_argument("-v", action='store_true')
    parser.add_argument("--allow_restart", "-r", action='store_true')
    args = parser.parse_args()

    af = AudioFuse(args.v, args.allow_restart)
    if af:
        print("Found an AudioFuse.")
    else:
        print("No AudioFuse found.")
        sys.exit(1)
    
    try:
        if args.digital_out:
            try:
                af.set_digital_out(Output[args.digital_out])
            except RequiresAllowRestart:
                print("Setting digital out to %s requires a restart. Please re-run with --allow_restart." %
                        args.digital_out)
        if args.digital_in:
            try:
                af.set_digital_in(Input[args.digital_in])
            except RequiresAllowRestart:
                print("Setting digital in to %s requires a restart. Please re-run with --allow_restart." %
                        args.digital_in)
    except USBError as e:
        if e.errno is 13:
            print("Insufficient permission to talk to AudioFuse.")
            sys.exit(1)
        raise


if __name__ == "__main__":
    main()
