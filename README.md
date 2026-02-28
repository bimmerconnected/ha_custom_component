# Library not working anymore due to changes at BMW side

On September 29, 2025, BMW has blocked third parties (i.e. this library used for the Home Assistant BMW Connected Drive integration) from executing requests against BMW servers. BMW enforced additional security checks within the MyBMW app to block third parties (not only this library, but also other companies such as energy providers).

BMW has released BMW Cardata for EU users, see these custom integrations which can be used with Home Assistant or via MQTT with other domotica systems.

* https://github.com/kvanbiesen/bmw-cardata-ha
* https://github.com/dj0abr/bmw-mqtt-bridge
* https://github.com/sincze/bmw-cardata-ha-mqtt
* https://github.com/JoaoPedroBelo/bmw-wallbox-ha

# BMW Connected Drive Custom Component for Development
Home Assistant Custom Component of BMW Connected Drive **for development purposes only**!
For details please see [the official component documentation](https://www.home-assistant.io/integrations/bmw_connected_drive/) or [the bimmer_connected library](https://github.com/bimmerconnected/bimmer_connected).

## Installation (HACS)
When using HACS, just add this repository as a [custom repostiory](https://hacs.xyz/docs/navigation/settings#custom-repositories) of category `Integration` with the url `https://github.com/bimmerconnected/ha_custom_component`.

## Installation (manual)
Place the folder `bmw_connected_drive` and all it's files in the folder `custom_components` in the config folder of HA (where configuration.yaml is).

# Release notes
See [Github Releases](https://github.com/bimmerconnected/ha_custom_component/releases/).

# Version
Can be used with Home Assistant >= `2022.2`
