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
      --digital_in {spdif-coax,spdif-optical,adat,wclock}, --din {spdif-coax,spdif-optical,adat,wclock}
      --digital_out {spdif,adat,wclock}, --dout {spdif,adat,wclock}
      -r, --allow_restart

## Capabilities
This software is currently very incomplete. It is limited to the following:
* Detecting how digital I/O is set (ADAT, SPDIF, World Clock)
* Setting digital I/O

## Bugs and Feature Requests
Please use Github issues to report any bugs found or missing features you would like to see implemented.

## License
This code is licensed under the GNU GPLv3 (see COPYING).

## Disclaimer
This is unofficial, reverse-engineered software. It's possible it may damage your AudioFuse or computer. Use at your own risk.
