# RasPi-Discord-Bot-Server-Manager
Every Feel like you want to remotely turn on and off your computer with a Raspberry Pi 3B and you front IO header pins well do I have the repo for you...

Im using a 3 pin in Relay (5v, gnd, in [3.3-5v]), but online people want you to use octocouplers this would be roughly the same as that but no Vin. If you decide to use transitors or mosfets this repo would still work (if someone wants I could make it work with a cheap servo too.) 

Hardcoded Varibles Needed:
SERVER_IP
SERVER_MAC
DISCORD_TOKEN
CHANEL_ID 

Limitations:
Only works for one server channel curently
CHEAP
Hardcoded Macadresse and IPs
Not reading front header led 
Dumb hardware device
