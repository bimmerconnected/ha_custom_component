# HA Custom Component
Home Assistant Custom Component of BMW Connected Drive

### This is for testing purposes only
With this version you can use the following new options:
* Send notifications to your car
* Send Point of Interest (POI) to your car

You can test this by using Developer Tools - Services and select `notify.bmw_connected_drive_<car>`
and for a message use these service data:
```
title: Your title here (if left empty it will be Home Assistant)
message: Your message here
```

for a POI:
```
title: Send location
message: POI
data:
  location:
    latitude: 48.177024
    longitude: 11.559107
    name: The name of the location
```

#### Installation
Place the folder `bmw_connected_drive` and all it's files in the folder `custom_components` in the config folder of HA (where configuration.yaml is).

#### Pictures
Here are some pictures, not too sharp and yeah it's a touch screen, but they give a good impression

Overview of messages
![Example 1](/pictures/example_1.jpg)

Example of message
![Example 2](/pictures/example_2.jpg)

Example of POI
![Example 3](/pictures/example_3.jpg)
