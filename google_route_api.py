import os
import requests


def get_transit_route(origin_address: str, destination_address: str):
    """
    Get a public transit route between two addresses using Google Routes API.
    The response includes all available route details.

    Args:
        origin_address (str): The starting point address.
        destination_address (str): The destination address.

    Returns:
        dict: Detailed information including duration, distance, steps, and transit details.
    """
    API_KEY = os.getenv('GOOGLE_API_KEY')

    if not API_KEY:
        raise ValueError("The environment variable 'GOOGLE_API_KEY' is not set.")

    url = 'https://routes.googleapis.com/directions/v2:computeRoutes'

    payload = {
        "origin": {"address": origin_address},
        "destination": {"address": destination_address},
        "travelMode": "TRANSIT",
        "computeAlternativeRoutes": True,
        "polylineEncoding": "ENCODED_POLYLINE",
        "transitPreferences": {
            "routingPreference": "FEWER_TRANSFERS"  #LESS_WALKING|
        }
    }

    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': API_KEY,
        'X-Goog-FieldMask': 'routes.duration,routes.distanceMeters,routes.legs.stepsOverview'  # ,routes.transitDetails Removed steps
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        data = response.json()
        route = data['routes'][0]

        # Collecting all available route details
        result = {
            'duration': route.get('duration'),
            'distance_meters': route.get('distanceMeters'),
            'stepsOverview': route.get('stepsOverview', {}),
            'polyline': route.get('overviewPolyline', {}),  # Polyline for map visualization
            'arrival_time': route.get('arrivalTime', {}),  # Arrival time info
            'departure_time': route.get('departureTime', {}),  # Departure time info
            'warnings': route.get('warnings', []),  # Warnings (e.g., closures, hazards)
        }

        # Extracting steps if available in the legs object
        if 'legs' in route:
            steps = []
            for leg in route['legs']:
                if 'steps' in leg:
                    steps.extend(leg['steps'])  # Add steps for each leg
            result['steps'] = steps

        return result
    else:
        raise Exception(f"Request failed: {response.status_code} - {response.text}")

# Example usage
if __name__ == "__main__":
    origin = input("Enter your starting address: ")
    destination = input("Enter your destination address: ")

    try:
        route_info = get_transit_route(origin, destination)
        print("\nRoute Info:")
        print("Duration:", route_info['duration'])
        print("Distance (meters):", route_info['distance_meters'])
        print("Arrival Time:", route_info['arrival_time'])
        print("Departure Time:", route_info['departure_time'])
        print(route_info)
        # Print each step in the route
        if route_info.get('steps'):
            print("\nSteps:")
            for step in route_info['steps']:
                print(step)

        # Print polyline (for map visualization)
        if route_info['polyline']:
            print("\nPolyline (for visualization):", route_info['polyline'])

        # Print any warnings
        if route_info['warnings']:
            print("\nWarnings:")
            for warning in route_info['warnings']:
                print(warning)

    except Exception as e:
        print("Error:", e)
