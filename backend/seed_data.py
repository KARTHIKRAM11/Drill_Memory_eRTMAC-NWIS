"""
Generates synthetic-but-realistic wells + historical drilling events for the
NWIS prototype demo. Coordinates are clustered around Oil India Limited's
actual operating area in Upper Assam (Duliajan / Naharkatiya / Moran / Lakwa
fields) so the map looks geographically plausible. All well names, events and
dates are fabricated for demo purposes only.
"""
import random
import datetime
from database import SessionLocal, Well, DrillingEvent, init_db

random.seed(42)

FIELDS = {
    "Duliajan":     (27.373, 95.334),
    "Naharkatiya":  (27.293, 95.328),
    "Moran":        (27.283, 95.128),
    "Lakwa":        (27.113, 94.783),
    "Kumchai":      (27.230, 95.230),
    "Jorajan":      (27.350, 95.450),
}

FORMATIONS = [
    ("Alluvium", 0, 150),
    ("Girujan Clay", 150, 800),
    ("Tipam Sandstone", 800, 1600),
    ("Barail Group", 1600, 2400),
    ("Basement (Pre-Tertiary)", 2400, 3200),
]

EVENT_TYPES = {
    "mud_loss": [
        "Partial mud loss observed while drilling through fractured {formation}; losses of {rate} bbl/hr recorded.",
        "Total mud loss encountered on entering vugular zone in {formation}; circulation lost within {mins} minutes.",
    ],
    "kick": [
        "Well kick detected in {formation} zone; pit gain of {gain} bbls, shut-in and circulated out using driller's method.",
        "Gas influx observed while drilling {formation}; SIDPP {pressure} psi recorded, well controlled per BOP procedure.",
    ],
    "stuck_pipe": [
        "Differential sticking encountered in {formation} at {depth}m; freed after {hours} hrs of jarring and spotting pill.",
        "Mechanical stuck pipe due to hole pack-off in {formation}; string parted, fishing operation initiated.",
    ],
    "cementing_issue": [
        "Poor cement bond observed at casing shoe in {formation}; squeeze cementing job performed to isolate zone.",
        "Cement channeling detected post-WOC in {formation} interval; remedial cement plug set.",
    ],
    "torque_spike": [
        "Abnormal torque spike observed while drilling {formation}, attributed to tight hole/ledging; reamed and continued.",
        "Erratic torque and drag noted in {formation} section; mud properties adjusted, ROP reduced as mitigation.",
    ],
}

MITIGATIONS = {
    "mud_loss": "Increased LCM concentration, reduced mud weight incrementally, monitored ECD closely.",
    "kick": "Well shut in immediately, driller's method used to circulate out kick, mud weight increased per kill sheet.",
    "stuck_pipe": "Spotted pipe-freeing pill, applied jarring, reduced overbalance on subsequent wells in this formation.",
    "cementing_issue": "Ran cement bond log, performed remedial squeeze, revised slurry design for offset wells.",
    "torque_spike": "Increased mud lubricity, adjusted BHA, reduced WOB through the ledged interval.",
}


def make_formation_sequence():
    return ",".join(f"{name}:{top}-{base}" for name, top, base in FORMATIONS)


def random_point_near(lat, lon, max_km=6):
    # ~1 deg lat = 111km; rough jitter, fine for demo visualization
    dlat = random.uniform(-max_km, max_km) / 111.0
    dlon = random.uniform(-max_km, max_km) / (111.0 * 0.89)  # approx cos(lat) at ~27N
    return round(lat + dlat, 5), round(lon + dlon, 5)


def gen_events_for_well(well_id, n_events):
    events = []
    for _ in range(n_events):
        etype = random.choice(list(EVENT_TYPES.keys()))
        formation, top, base = random.choice(FORMATIONS)
        depth = round(random.uniform(top + 20, base - 20), 1) if base > top + 40 else round((top + base) / 2, 1)
        template = random.choice(EVENT_TYPES[etype])
        desc = template.format(
            formation=formation,
            rate=random.randint(5, 80),
            mins=random.randint(10, 90),
            gain=random.randint(5, 40),
            pressure=random.randint(200, 1500),
            depth=depth,
            hours=random.randint(2, 30),
        )
        severity = random.choices(["low", "medium", "high"], weights=[0.4, 0.4, 0.2])[0]
        date = (datetime.date(2015, 1, 1) + datetime.timedelta(days=random.randint(0, 3800))).isoformat()
        events.append(DrillingEvent(
            well_id=well_id,
            event_type=etype,
            depth_m=depth,
            formation=formation,
            severity=severity,
            description=desc,
            mitigation=MITIGATIONS[etype],
            date=date,
        ))
    return events


def seed():
    init_db()
    db = SessionLocal()
    db.query(DrillingEvent).delete()
    db.query(Well).delete()
    db.commit()

    well_counter = 1
    for field, (lat, lon) in FIELDS.items():
        n_wells = random.randint(3, 5)
        for i in range(n_wells):
            wlat, wlon = random_point_near(lat, lon)
            td = round(random.uniform(2200, 3100), 0)
            status = random.choices(["producing", "abandoned", "drilling"], weights=[0.6, 0.25, 0.15])[0]
            spud = (datetime.date(2010, 1, 1) + datetime.timedelta(days=random.randint(0, 5500))).isoformat()
            well = Well(
                name=f"{field[:3].upper()}-{well_counter:03d}",
                field_name=field,
                latitude=wlat,
                longitude=wlon,
                total_depth_m=td,
                spud_date=spud,
                status=status,
                formation_sequence=make_formation_sequence(),
            )
            db.add(well)
            db.flush()  # get well.id
            n_events = random.randint(2, 6)
            for ev in gen_events_for_well(well.id, n_events):
                db.add(ev)
            well_counter += 1

    db.commit()
    total_wells = db.query(Well).count()
    total_events = db.query(DrillingEvent).count()
    db.close()
    print(f"Seeded {total_wells} wells and {total_events} historical drilling events.")


if __name__ == "__main__":
    seed()
