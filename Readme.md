# DMR Talkgroup Switch Home Assistant component

Custom component for [Home Assistant](https://homeassistant.io) so you can   
 - ADD, DELETE static talkgroups  
 - Drop Current QSO  
 - Drop All Dynamic Talkgroups 
 
on a Brandmeister DMR Server using BM API v2.   

![Screenshot](screenshot_2.png?raw=true)
![Screenshot](screenshot_1.png?raw=true)

## Installation

1. Copy the folder `dmr_tg_switch` to `custom_components` inside your Home Assistant config folder
2. Restart Home Assistant (this installs the component's dependencies)
3. Add your config to `configuration.yaml` (see options below)
4. Restart Home Assistant again

## Configuration

### Talkgroup switch
``` yaml
switch:
  - platform: dmr_tg_switch
    name: TG216
    dmr_id: 123456701                       
    bm_api_key: !secret your_bm_api_key     
    tg: 216                                 
    tslot: 1                                  
    scan_interval:                                
      hours: 1        
```     

|   |    |   
| :--- | :---- |  
|`name`       | Talkgroup friendly name |
|`dmr_id`     | Your 7-digit personal DMR ID + 01...99 suffix for more than one hotspot (for example: 2169999**01**) |   
|`bm_api_key` | Your Brandmeister API Key |
|`tg`         | Talkgroup to ADD/DEL |
|             | 9998 = Drop Current QSO | 
|             | 9997 = Drop All Dynamic Talkgroups | 
|`tslot` | TimeSlot [0/1/2], simplex hotspot=0, duplex hotspot=1/2 |   
|`scan_interval` | Updating every hour (instead of the default 30 seconds) seems to be OK. |  
    
        
### Drop Current QSO
``` yaml
switch:
  - platform: dmr_tg_switch
    name: Drop Current QSO S1
    dmr_id: 123456701                       
    bm_api_key: !secret your_bm_api_key     
    tg: 9998                                 
    tslot: 1                                  
    scan_interval:                                
      hours: 1        
``` 
Create it as a button in HA Lovelace.   

![Screenshot](drop_current_2.png?raw=true)
![Screenshot](drop_current_1.png?raw=true)



### Drop All Dynamic Talkgroups
``` yaml
switch:
  - platform: dmr_tg_switch
    name: Drop All Dynamic S1
    dmr_id: 123456701                       
    bm_api_key: !secret your_bm_api_key     
    tg: 9997                                 
    tslot: 1                                  
    scan_interval:                                
      hours: 1        
```  
    
Create it as a button in HA Lovelace.   
   
![Screenshot](drop_all_dynamic_2.png?raw=true)
![Screenshot](drop_all_dynamic_1.png?raw=true)

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
