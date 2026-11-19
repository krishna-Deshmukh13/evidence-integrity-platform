"""
Seed realistic GPS coordinates and geographic locations into evidence items in storage/evidence.db
"""
import json
import sqlite3
import random

LOCATIONS = [
    # Mumbai Cluster
    {"city": "Mumbai", "loc": "Bandra Kurla Complex (BKC) Financial District", "lat": 19.0667, "lon": 72.8687},
    {"city": "Mumbai", "loc": "Nariman Point Business Center", "lat": 18.9256, "lon": 72.8242},
    {"city": "Mumbai", "loc": "Chhatrapati Shivaji Maharaj Terminus (CSMT)", "lat": 18.9401, "lon": 72.8354},
    {"city": "Mumbai", "loc": "Fort Banking Reserve & Stock Exchange", "lat": 18.9322, "lon": 72.8336},
    {"city": "Mumbai", "loc": "Bhabha Atomic Research Center (BARC) Perimeter", "lat": 19.0069, "lon": 72.9196},
    {"city": "Mumbai", "loc": "Navi Mumbai Data Center Park", "lat": 19.1663, "lon": 73.0044},
    
    # Delhi NCR Cluster
    {"city": "New Delhi", "loc": "Northern Regional Grid Load Despatch Centre", "lat": 28.5355, "lon": 77.2006},
    {"city": "New Delhi", "loc": "Indira Gandhi International Airport (Terminal 3)", "lat": 28.5562, "lon": 77.1000},
    {"city": "New Delhi", "loc": "Central Secretariat & Ministry Corridor", "lat": 28.6180, "lon": 77.2090},
    {"city": "New Delhi", "loc": "New Delhi Railway Interlocking Signal Tower", "lat": 28.6429, "lon": 77.2195},
    {"city": "New Delhi", "loc": "Cyber Crime Police Station Mandir Marg", "lat": 28.6292, "lon": 77.2001},
    {"city": "Noida", "loc": "Noida Sector 62 Tech Surveillance Hub", "lat": 28.6258, "lon": 77.3686},
    {"city": "Gurugram", "loc": "Cyber Hub Corporate Complex Cyber City", "lat": 28.4986, "lon": 77.0878},
    
    # Bengaluru Cluster
    {"city": "Bengaluru", "loc": "Electronic City Cyber Operations Campus", "lat": 12.8399, "lon": 77.6770},
    {"city": "Bengaluru", "loc": "Whitefield IT Export Zone", "lat": 12.9698, "lon": 77.7499},
    {"city": "Bengaluru", "loc": "Vidhana Soudha State Secretariat", "lat": 12.9797, "lon": 77.5907},
    
    # Hyderabad Cluster
    {"city": "Hyderabad", "loc": "HITEC City Cyber Towers", "lat": 17.4474, "lon": 78.3762},
    {"city": "Hyderabad", "loc": "Financial District Nanakramguda", "lat": 17.4156, "lon": 78.3489},
    
    # International Hubs
    {"city": "San Francisco", "loc": "San Francisco International Airport (SFO Runways)", "lat": 37.6189, "lon": -122.3750},
    {"city": "New York", "loc": "Wall Street Financial District Pier 11", "lat": 40.7071, "lon": -74.0090},
    {"city": "London", "loc": "Canary Wharf Global Bank Center", "lat": 51.5055, "lon": -0.0195},
    {"city": "Singapore", "loc": "Marina Bay Financial Center Tower 3", "lat": 1.2801, "lon": 103.8542},
    {"city": "Dubai", "loc": "DIFC Gate Precinct Financial Centre", "lat": 25.2104, "lon": 55.2818},
]

def seed_gps():
    conn = sqlite3.connect('storage/evidence.db')
    cur = conn.cursor()
    
    cur.execute('SELECT id, case_id, filename, media_type, details FROM evidence')
    rows = cur.fetchall()
    
    updated_count = 0
    # Assign GPS to image, video, and audio items, plus select documents (about 55 items)
    for idx, (ev_id, case_id, filename, media_type, details_raw) in enumerate(rows):
        # Pick 55 items spread out across cases
        if idx % 4 == 0 or media_type in ('image', 'video'):
            loc_data = LOCATIONS[idx % len(LOCATIONS)]
            
            # Add small random jitter so items in the same facility have distinct micro-coords (10-50m)
            jitter_lat = loc_data["lat"] + (random.random() - 0.5) * 0.003
            jitter_lon = loc_data["lon"] + (random.random() - 0.5) * 0.003
            
            details = {}
            if details_raw:
                try:
                    details = json.loads(details_raw)
                except Exception:
                    details = {}
            
            if "exif" not in details or not isinstance(details["exif"], dict):
                details["exif"] = {}
                
            details["exif"]["GPSLatitude"] = round(jitter_lat, 6)
            details["exif"]["GPSLongitude"] = round(jitter_lon, 6)
            details["exif"]["latitude"] = round(jitter_lat, 6)
            details["exif"]["longitude"] = round(jitter_lon, 6)
            details["city"] = loc_data["city"]
            details["location_name"] = loc_data["loc"]
            
            cur.execute(
                'UPDATE evidence SET details = ? WHERE id = ?',
                (json.dumps(details), ev_id)
            )
            updated_count += 1
            
    conn.commit()
    conn.close()
    print(f"Successfully seeded GPS coordinates and geographic tags for {updated_count} evidence items!")

if __name__ == "__main__":
    seed_gps()
