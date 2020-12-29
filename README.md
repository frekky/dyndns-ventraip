# dyndns-ventraip

Simple Dynamic DNS on VentraIP

Requires Python 3 and `python3-requests` (ie. `pip install requests`)

Updates a single DNS record with your current public IPv4 address (retrieved via https://api.ipify.org/)

## Usage

0. Configure a DNS record in the control panel with some temporary values (just set the hostname and type as desired for now)
1. Run `ventraip-dns.py` once to generate an empty config file
2. Enter your VentraIP login details into the config, and enter the info for the DNS record you just created
3. Run the script to update the DNS record

## Installation

Some suggestions for running this using a systemd timer on most Linux distros:

```
# make a user for the service to run under
sudo useradd -r -M -s /bin/false -d /etc/dyndns dyndns
sudo mkdir -p /etc/dyndns

# make and edit a config file
sudo ./ventraip-dns.py --config /etc/dyndns/ventraip.conf
sudo vim /etc/dyndns/ventraip.conf

# don't let everyone read your password
sudo chown -R dyndns:root /etc/dyndns
sudo chmod 640 /etc/dyndns/ventraip.conf

# install all the things
sudo cp ventraip-dns.timer ventraip-dns.service /usr/lib/systemd/system/
sudo cp ventraip-dns.py /usr/local/bin/

# enable the timer
sudo systemctl enable ventraip-dns.timer
```