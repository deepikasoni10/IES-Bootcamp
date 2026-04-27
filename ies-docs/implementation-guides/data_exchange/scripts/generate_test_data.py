import json
import os
import random
from datetime import datetime, timedelta, timezone
import math

# --- Configuration ---
START_DATE = datetime(2024, 4, 15, tzinfo=timezone.utc)
DAYS = 60
INTERVAL_MINS = 15
TOTAL_RESOURCES = 100
RES_COUNT = 80
COM_COUNT = 20
SOLAR_PCT = 0.10 # 10% of Residential
CHUNKS = 10

ESTIMATED_PCT = 0.05
MISSING_PCT = 0.05

BOOTCAMP_DIR = os.path.join(os.path.dirname(__file__), "..", "bootcamp")
CONTEXT_URL = "https://raw.githubusercontent.com/beckn/DEG/ies-specs/specification/external/schema/ies/core/context.jsonld"

# Use a fixed seed for reproducible bootcamp data
random.seed(42)

def generate_timestamp(dt):
    return dt.isoformat().replace("+00:00", "Z")

def get_residential_load(hour):
    # Bi-modal peak (morning and evening)
    # Peak 1: 8:00 (index 8), Peak 2: 20:00 (index 20)
    base = 0.2
    v1 = 0.8 * math.exp(-((hour - 8)**2) / 4)
    v2 = 1.2 * math.exp(-((hour - 20)**2) / 6)
    return base + v1 + v2 + random.uniform(-0.1, 0.1)

def get_commercial_load(hour):
    # Plateau between 9 and 18
    if 9 <= hour <= 18:
        return 2.5 + random.uniform(-0.3, 0.3)
    return 0.5 + random.uniform(-0.1, 0.1)

def get_solar_gen(hour):
    # Bell curve centered at 13:00
    if 7 <= hour <= 18:
        return 3.0 * math.exp(-((hour - 13)**2) / 4)
    return 0.0

# --- Generator ---

def run():
    os.makedirs(BOOTCAMP_DIR, exist_ok=True)
    
    # 1. Generate Programs
    programs = [
        {
            "@context": CONTEXT_URL,
            "id": "mera-shehar-res-001",
            "objectType": "PROGRAM",
            "@type": "PROGRAM",
            "createdDateTime": "2024-04-10T10:00:00Z",
            "modificationDateTime": "2024-04-10T10:00:00Z",
            "programName": "MeraShehar Residential",
            "programDescriptions": ["Residential tariff program for MeraShehar municipality."]
        },
        {
            "@context": CONTEXT_URL,
            "id": "mera-shehar-com-001",
            "objectType": "PROGRAM",
            "@type": "PROGRAM",
            "createdDateTime": "2024-04-10T10:00:00Z",
            "modificationDateTime": "2024-04-10T10:00:00Z",
            "programName": "MeraShehar Commercial",
            "programDescriptions": ["Commercial tariff program for MeraShehar business district."]
        }
    ]
    with open(os.path.join(BOOTCAMP_DIR, "programs.jsonld"), "w") as f:
        json.dump(programs, f, indent=2)

    # 2. Generate Policies
    policies = [
        {
            "@context": CONTEXT_URL,
            "id": "policy-res-telescopic-001",
            "objectType": "POLICY",
            "@type": "POLICY",
            "createdDateTime": "2024-04-10T11:00:00Z",
            "modificationDateTime": "2024-04-10T11:00:00Z",
            "programID": "mera-shehar-res-001",
            "policyID": "RES-T1",
            "policyName": "Residential Telescopic Standard",
            "policyType": "TARIFF",
            "samplingInterval": "R/2024-04-10T00:00:00Z/P1M",
            "energySlabs": [
                {"id": "s1", "start": 0, "end": 100, "price": 4.5, "@type": "EnergySlab"},
                {"id": "s2", "start": 101, "end": 300, "price": 7.5, "@type": "EnergySlab"},
                {"id": "s3", "start": 301, "end": None, "price": 10.5, "@type": "EnergySlab"}
            ],
            "surchargeTariffs": [
                {
                    "id": "night-discount",
                    "@type": "SurchargeTariff",
                    "recurrence": "P1D",
                    "interval": {"start": "T23:00:00Z", "duration": "PT6H"},
                    "value": -10,
                    "unit": "PERCENT"
                }
            ]
        },
        {
            "@context": CONTEXT_URL,
            "id": "policy-com-tou-001",
            "objectType": "POLICY",
            "@type": "POLICY",
            "createdDateTime": "2024-04-10T11:00:00Z",
            "modificationDateTime": "2024-04-10T11:00:00Z",
            "programID": "mera-shehar-com-001",
            "policyID": "COM-TOU1",
            "policyName": "Commercial ToD Standard",
            "policyType": "TARIFF",
            "samplingInterval": "R/2024-04-10T00:00:00Z/P1M",
            "energySlabs": [
                {"id": "fixed-base", "start": 0, "end": None, "price": 8.5, "@type": "EnergySlab"}
            ],
            "surchargeTariffs": [
                {
                    "id": "evening-peak",
                    "@type": "SurchargeTariff",
                    "recurrence": "P1D",
                    "interval": {"start": "T18:00:00Z", "duration": "PT4H"},
                    "value": 1.5,
                    "unit": "INR_PER_KWH"
                }
            ]
        }
    ]
    with open(os.path.join(BOOTCAMP_DIR, "policies.jsonld"), "w") as f:
        json.dump(policies, f, indent=2)

    # 3. Generate Resources
    resources = []
    res_ids = []
    # 80 Residential
    for i in range(1, RES_COUNT + 1):
        base_rid = f"RES-{i:03d}"
        has_solar = i <= (RES_COUNT * SOLAR_PCT)
        
        if not has_solar:
            resources.append({
                "@context": CONTEXT_URL,
                "id": base_rid,
                "objectType": "RESOURCE",
                "@type": "RESOURCE",
                "resourceName": base_rid,
                "venID": f"VEN-RES-{i:03d}",
                "attributes": [
                    {"type": "PROGRAM_ID", "values": ["mera-shehar-res-001"]},
                    {"type": "CAPABILITIES", "values": ["CONSUMPTION"]}
                ]
            })
            res_ids.append((base_rid, "RES", False))
        else:
            # Solar Site: Split into IMPORT and EXPORT
            for suffix, is_export in [("_IMPORT", False), ("_EXPORT", True)]:
                rid = f"{base_rid}{suffix}"
                attributes = [
                    {"type": "PROGRAM_ID", "values": ["mera-shehar-res-001"]},
                    {"type": "CAPABILITIES", "values": ["EXPORT" if is_export else "CONSUMPTION"]}
                ]
                if is_export:
                    attributes.append({"type": "EXPORTING", "values": [True]})
                
                resources.append({
                    "@context": CONTEXT_URL,
                    "id": rid,
                    "objectType": "RESOURCE",
                    "@type": "RESOURCE",
                    "resourceName": rid,
                    "venID": f"VEN-RES-{i:03d}",
                    "attributes": attributes
                })
            res_ids.append((base_rid, "RES", True))
    
    # 20 Commercial
    for i in range(1, COM_COUNT + 1):
        rid = f"COM-{i:03d}"
        resources.append({
            "@context": CONTEXT_URL,
            "id": rid,
            "objectType": "RESOURCE",
            "@type": "RESOURCE",
            "resourceName": rid,
            "venID": f"VEN-COM-{i:03d}",
            "attributes": [
                {"type": "PROGRAM_ID", "values": ["mera-shehar-com-001"]},
                {"type": "CAPABILITIES", "values": ["CONSUMPTION"]}
            ]
        })
        res_ids.append((rid, "COM", False))

    with open(os.path.join(BOOTCAMP_DIR, "resources.jsonld"), "w") as f:
        json.dump(resources, f, indent=2)

    # 4. Generate Telemetry (Chunks)
    total_intervals = DAYS * 24 * (60 // INTERVAL_MINS)
    intervals_per_chunk = total_intervals // CHUNKS
    
    current_time = START_DATE
    
    for c in range(1, CHUNKS + 1):
        chunk_file = os.path.join(BOOTCAMP_DIR, f"telemetry_chunk_{c}.jsonld")
        chunk_report = {
            "@context": CONTEXT_URL,
            "objectType": "REPORT",
            "@type": "REPORT",
            "id": f"chunk-{c}",
            "createdDateTime": generate_timestamp(datetime.now(timezone.utc)),
            "modificationDateTime": generate_timestamp(datetime.now(timezone.utc)),
            "clientID": "bootcamp-aggregator-01",
            "reportName": f"Bootcamp Telemetry Chunk {c}",
            "eventID": "none", # Will be filled by participants based on policy linkage
            "clientName": "Aggregator-01",
            "payloadDescriptors": [
                {"objectType": "REPORT_PAYLOAD_DESCRIPTOR", "@type": "REPORT_PAYLOAD_DESCRIPTOR", "payloadType": "USAGE", "units": "KWH", "readingType": "DIRECT_READ"},
                {"objectType": "REPORT_PAYLOAD_DESCRIPTOR", "@type": "REPORT_PAYLOAD_DESCRIPTOR", "payloadType": "DATA_QUALITY", "readingType": "ANNOTATION"}
            ],
            "resources": []
        }
        
        chunk_start_time = current_time
        
        for base_rid, rtype, has_solar in res_ids:
            # Create list of actual resources for this site (1 or 2)
            site_resources = []
            if has_solar:
                site_resources.append((f"{base_rid}_IMPORT", False)) # (rid, is_export)
                site_resources.append((f"{base_rid}_EXPORT", True))
            else:
                site_resources.append((base_rid, False))
            
            # Pre-generate values for the whole chunk to coordinate netting
            site_intervals = [] # list of (val, gen, status, is_missing)
            for i in range(intervals_per_chunk):
                interval_time = chunk_start_time + timedelta(minutes=i * INTERVAL_MINS)
                hour = interval_time.hour + (interval_time.minute / 60.0)
                
                is_missing = random.random() < MISSING_PCT
                is_estimated = False if is_missing else (random.random() < ESTIMATED_PCT)
                status = "MISSING" if is_missing else ("ESTIMATED" if is_estimated else "VALID")
                
                if rtype == "RES":
                    val = get_residential_load(hour) if not is_missing else 0.0
                else:
                    val = get_commercial_load(hour) if not is_missing else 0.0
                    
                gen = get_solar_gen(hour) if (has_solar and not is_missing) else 0.0
                site_intervals.append((val, gen, status, is_missing))

            # Now create entries for each resource in the site
            for rid, is_export in site_resources:
                res_entry = {
                    "resourceName": rid,
                    "intervalPeriod": {
                        "start": generate_timestamp(chunk_start_time),
                        "duration": f"PT{INTERVAL_MINS}M"
                    },
                    "intervals": []
                }
                
                for i, (val, gen, status, is_missing) in enumerate(site_intervals):
                    # Netting Logic
                    net_usage = 0.0
                    if not is_missing:
                        net = gen - val
                        if is_export:
                            net_usage = max(0, net)
                        else:
                            net_usage = max(0, -net)
                    
                    payloads = [{"type": "USAGE", "values": [round(net_usage, 3)]}]
                    if status != "VALID":
                        payloads.append({"type": "DATA_QUALITY", "values": [status]})
                    
                    res_entry["intervals"].append({
                        "id": i,
                        "payloads": payloads
                    })
                chunk_report["resources"].append(res_entry)
            
        # Write chunk
        with open(chunk_file, "w") as f:
            json.dump(chunk_report, f, indent=2)
        print(f"Generated {chunk_file} (Start: {generate_timestamp(chunk_start_time)})")
        
        # Advance current_time for next chunk
        current_time += timedelta(minutes=intervals_per_chunk * INTERVAL_MINS)

if __name__ == "__main__":
    run()
