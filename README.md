# dyndns-ventraip

Simple Dynamic DNS on VentraIP

Requires Python 3 and `python3-requests` (ie. `pip install requests`)

Updates a single DNS record with your current public IPv4 address (retrieved via https://api.ipify.org/)

Usage:

0. Configure a DNS record in the control panel with some temporary values (just set the hostname and type as desired for now)
1. Run `ventraip-dns.py` once to generate an empty config file
2. Enter your VentraIP login details into the config, and enter the info for the DNS record you just created
3. Run the script to update the DNS record
