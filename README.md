# AudioFuse CLI
An **unofficial**, incomplete CLI for controlling the Arturia AudioFuse.

While made primarily to bring Linux control to the AudioFuse, in theory this should work on Windows or Mac OS X.

## Usage
    usage: audiofuse-cli.py [-h] [-v]
                            [--digital_in {spdif-coax,spdif-optical,adat,wclock}]
                            [--digital_out {spdif,adat,wclock}] [-r]

    An unofficial, incomplete CLI for controlling the Arturia AudioFuse.

    optional arguments:
      -h, --help            show this help message and exit
      -v, --verbose
      -r, --allow_restart
      --digital_in {spdif-coax,spdif-optical,adat,wclock}, --din {spdif-coax,spdif-optical,adat,wclock}
      --digital_out {spdif,adat,wclock}, --dout {spdif,adat,wclock}
      --from-phone-2        Set Speaker B to output the phones 2 mix.
      --not-from-phone-2    Set Speaker B back to normal.
      --reamping            Enable reamping over Speaker B left output.
      --no-reamping         Disable reamping.
      --ground-lift         Disconnect ground from the reamping circuit.
      --no-ground-lift      Reconnect ground to the reamping circuit.

### Permissions
On Linux by default this will require root. You can instead setup a udev rule to allow it to run as your user.

First, create the group audiofuse and add yourself to it:
* `sudo groupadd audiofuse`
* `sudo usermod -a -G audiofuse $USER`

Next, copy the udev rule into /etc/udev/rules.d and make sure root owns it:
* `sudo cp 80-audiofuse.rules /etc/udev/rules.d/`
* `sudo chown root:root /etc/udev/rules.d/80-audiofuse.rules`

Finally, log out and back in to update the groups. You should now be able to run this without root.

## Capabilities
This software is currently very incomplete. It is limited to the following:
* Detecting how digital I/O is set (ADAT, SPDIF, World Clock)
* Setting digital I/O
* Controlling the From Phone 2 section (From Phone 2, Reamping, and Ground Lift)

## Bugs and Feature Requests
Please use Github issues to report any bugs found or missing features you would like to see implemented.

## License
This code is licensed under the GNU GPLv3 (see COPYING).

## Disclaimer
This is unofficial, reverse-engineered software. It's possible it may damage your AudioFuse or computer. Use at your own risk.
