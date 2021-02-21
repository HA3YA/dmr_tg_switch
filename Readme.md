# DMR Talkgroup Switch Home Assistant component

Custom component for [Home Assistant](https://homeassistant.io) that ADD, DELETE static talkgroups to a hotspot on a Brandmeister Server.
![Screenshot](screenshot.png?raw=true)

## Installation

1. Copy the folder `dmr_tg_switch` to `custom_components` inside your Home Assistant config folder.
2. Restart Home Assistant (this installs the component's dependencies)
3. Add your config to `configuration.yaml` (see options below)
4. Restart Home Assistant again

## Configuration

``` yaml
switch:
  - platform: dmr_tg_switch
    dmr_id: 216999901                       
    bm_api_key: !secret your_bm_api_key     
    tg: 216                                 
    tslot: 1                                  
    scan_interval:                                
      hours: 1
```
`dmr_id`:        Your 7 chars DMR ID + 01..99 (more hotspots) ie. 216999901
`bm_api_key`:    Your Bramdmeister API Key 
`tg`:            Talkgroup to ADD/DEL
`tslot`:         TimeSlot [0/1/2], Simplex Hotspot=0, Duplex Hospot = 1/2
`scan_interval`: Updating every hour (instead of the default 30 seconds) seems to be OK though.
