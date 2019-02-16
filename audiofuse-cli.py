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
        af.get_status()
        af._send_300_200()
        return(af)

    def _restart(self, to_adat):
        request_type = usb.util.build_request_type(CTRL_OUT, CTRL_TYPE_CLASS, CTRL_RECIPIENT_INTERFACE)
        if to_adat:
            # No idea why we only need this here
            self._dev.ctrl_transfer(request_type, 0x01, 0x0100, 0x2900, [0, 0x77, 1, 0])
            data = 2
        else:
            data = 1
        self._dev.ctrl_transfer(request_type, 0x03, 0, 0x5000, [data, 0])
        # Don't try and reattach interfaces after a restart
        self._reattach_interfaces = set()

    def _send_300_200(self):
        # This is done in several places, but I have no diea why.
        request_type = usb.util.build_request_type(CTRL_OUT, CTRL_TYPE_CLASS, CTRL_RECIPIENT_INTERFACE)
        self._dev.ctrl_transfer(request_type, 0x03, 0x0300, 0x4c00, [0, 0])
        self._dev.ctrl_transfer(request_type, 0x03, 0x0200, 0x4c00, [0, 0])

    def _change_digital_in(self, val, restart, to_adat):
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
        elif val == Input.WClock:
            data = 2
            data2 = 0
        else:
            raise ValueError('Unknown value (%s) is not "spdif-coax", "spdif-optical", "adat", or "wclock"' % val)

        request_type = usb.util.build_request_type(CTRL_OUT, CTRL_TYPE_CLASS, CTRL_RECIPIENT_INTERFACE)
        self._dev.ctrl_transfer(request_type, 0x03, 0x0005, 0x4600, [data])
        self._dev.ctrl_transfer(request_type, 0x03, 0x0305, 0x4600, [data2])
        # My reverse-engineering says we should call restart here, but then we
        # don't have time to finish these transfers first.
        #if restart:
        #    self._restart(to_adat)
        self._dev.ctrl_transfer(request_type, 0x03, 0x0c05, 0x4600, [0])
        self._send_300_200()
        if restart:
            self._change_digital_out(self.output, False, False)
            # Restarting here instead seems to work.
            self._restart(to_adat)

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
        if val == Input.ADAT and self.input != Input.ADAT and self.output != Output.ADAT:
            restart = True
            to_adat = True
        if val != Input.ADAT and self.input == Input.ADAT and self.output != Output.ADAT:
            restart = True
            to_adat = False
        if restart and not self._allow_restart:
            raise RequiresAllowRestart

        self._change_digital_in(val, restart, to_adat)

    def _change_digital_out(self, val, restart, to_adat):
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
        if restart:
            # My reverse-engineering says we should call restart here, but then we
            # don't have time to finish these transfers first.
            # self._restart(to_adat)
            self._change_digital_in(self.input, False, False)
            # Doing it afterwards seems to still work.
            self._restart(to_adat)

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
        if val == Output.ADAT and self.output != Output.ADAT and self.input != Input.ADAT:
            restart = True
            to_adat = True
        if val != Output.ADAT and self.output == Output.ADAT and self.input != Input.ADAT:
            restart = True
            to_adat = False
        if restart and not self._allow_restart:
            raise RequiresAllowRestart

        self._change_digital_out(val, restart, to_adat)

    def _set_binary_option(self, name, usb_val, val):
        if self._verbose:
            print("Attempting to set %s to %d." % (name, val))

        if not (val == 0 or val == 1):
            raise ValueError

        request_type = usb.util.build_request_type(CTRL_OUT, CTRL_TYPE_CLASS, CTRL_RECIPIENT_INTERFACE)
        self._dev.ctrl_transfer(request_type, 0x03, usb_val, 0x4600, [val])

    def set_from_phone_2(self, val): 
        self._set_binary_option("from phones 2", 0x0a00, val)

    def set_reamping(self, val): 
        self._set_binary_option("reamping", 0x0b00, val)

    def set_ground_lift(self, val): 
        self._set_binary_option("ground lift", 0x0c00, val)

    def attach(self):
        if self._dev.is_kernel_driver_active(0):
            if self._verbose:
                print("Detaching from interface %d" % 0)
            self._reattach_interfaces |= {0}
            self._dev.detach_kernel_driver(0)

    def get_status(self):
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
            print("Status data:", status_bytes.hex())

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
                if e.errno is 2:
                    # This seems to happen whenever this is run after a
                    # self-initiated restart.
                    print("TODO: Figure out why we get entity not found here.")
                else:
                    raise

def main():
    parser = argparse.ArgumentParser(description="An unofficial, incomplete CLI for controlling the Arturia AudioFuse.")
    parser.add_argument("-v", "--verbose", action='store_true')
    parser.add_argument("-r", "--allow_restart", action='store_true')
    parser.add_argument("--digital_in", "--din", choices=["spdif-coax", "spdif-optical", "adat", "wclock"])
    parser.add_argument("--digital_out", "--dout", choices=["spdif", "adat", "wclock"])
    parser.add_argument("--from-phone-2", action='store_true', help="Set Speaker B to output the phones 2 mix.")
    parser.add_argument("--not-from-phone-2", action='store_true', help="Set Speaker B back to normal.")
    parser.add_argument("--reamping", action='store_true', help="Enable reamping over Speaker B left output.")
    parser.add_argument("--no-reamping", action='store_true', help="Disable reamping.")
    parser.add_argument("--ground-lift", action='store_true', help="Disconnect ground from the reamping circuit.")
    parser.add_argument("--no-ground-lift", action='store_true', help="Reconnect ground to the reamping circuit.")
    args = parser.parse_args()

    try:
        af = AudioFuse(args.verbose, args.allow_restart)
    except USBError as e:
        if e.errno is 13:
            print("Insufficient permission to talk to AudioFuse.")
            sys.exit(1)
        elif e.errno is 16:
            print("AudioFuse is currently in use by another application.")
            sys.exit(1)
        raise

    if af:
        print("Found an AudioFuse.")
    else:
        print("No AudioFuse found.")
        sys.exit(1)

    # Validate arguments
    if args.from_phone_2 and args.not_from_phone_2:
        print("Cannot simultaneously set --from-phone-2 and --not-from-phone-2.")
        sys.exit(1)

    if args.reamping and args.no_reamping:
        print("Cannot simultaneously set --reamping and --no-reamping.")
        sys.exit(1)

    if args.ground_lift and args.no_ground_lift:
        print("Cannot simultaneously set --ground-lift and --no-ground-lift.")
        sys.exit(1)

    if args.from_phone_2:
        af.set_from_phone_2(1)

    if args.not_from_phone_2:
        af.set_from_phone_2(0)

    if args.reamping:
        af.set_reamping(1)

    if args.no_reamping:
        af.set_reamping(0)

    if args.ground_lift:
        af.set_ground_lift(1)

    if args.no_ground_lift:
        af.set_ground_lift(0)

    # Do these last since they can potentially lead to a restart.
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


if __name__ == "__main__":
    main()
