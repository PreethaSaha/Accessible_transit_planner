# Accessible_transit_planner
Accessibility-first, user-controlled routing

Accessible Transit Planner is a Python tool designed to help users find the most accessible paths through Chicago's CTA 'L' train system. It can be extended for other transit services like Metra. Unlike Google Maps where accessibility is a side-layer, this tool puts accessibility at the center of the transit experience.
It incorporates:

- Real-time service alerts (like elevator outages)

- Station accessibility data

- Color-coded route mapping

- Duplicate/shared station handling

to plan the most efficient, disability-friendly routes across the city.

It's not just useful for wheelchair users — people with strollers, seniors, or even travelers with heavy luggage benefit too.

# How it works?
 
 ### Load GTFS data
  - Reads stops.txt, routes.txt, trips.txt, stop_times.txt from CTA's official GTFS feed.

### Filter for rail services and find accessible stations

- Selects only subway/metro services (route_type == 1) and filters stations with wheelchair_boarding == 1.

### Color-code by Line

- Displays stations and routes in classic CTA colors (Red, Blue, Green, etc.). Shared stations are highlighted in black.

### Map generation

 - Creates an interactive Folium map, displayed directly in Jupyter notebooks or other Python environments.

### Real-time alerts
 
 - Parse CTA API feeds to adjust suggested routes dynamically.

# Results

## Accessible CTA L stations map
This map generated using Folium shows accessible CTA L stations, color-coded by their respective routes. Black markers indicate stations that are common across multiple routes. 

You can view the map by clicking the link below:

[View the interactive CTA L Stations Map](cta_accessible_stations_map.html)


