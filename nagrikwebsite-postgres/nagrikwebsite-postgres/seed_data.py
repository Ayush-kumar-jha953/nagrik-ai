"""
NAGRIK AI - 1,000 High-Fidelity Delhi Civic Complaints Generator
200 complaints in each category:
- Infrastructure (200)
- Sanitation (200)
- Education (200)
- Healthcare (200)
- Climate (200)

All locations are strictly concentric to Delhi with accurate latitude/longitude coordinates,
zone classifications (Red, Yellow, Green), and legal/municipal AI solutions under Delhi laws.
"""

import random
from datetime import datetime, timedelta

from psycopg2.extras import execute_values
from werkzeug.security import generate_password_hash

import database   # PostgreSQL layer (DATABASE_URL from .env)

# ---- DELHI LOCALITIES & COORDINATES (Strictly Concentric to Delhi) ----
# Categorized into challenge zones based on municipal density and historical civic strain:
DELHI_LOCALITIES = [
    # RED ZONES (High Challenge: high population density, aging civic network, industrial/peri-urban strain)
    {"name": "Okhla Phase 3, South Delhi", "lat": 28.5307, "lng": 77.2713, "zone": "red"},
    {"name": "Seelampur, North East Delhi", "lat": 28.6692, "lng": 77.2673, "zone": "red"},
    {"name": "Uttam Nagar, West Delhi", "lat": 28.6219, "lng": 77.0607, "zone": "red"},
    {"name": "Jahangirpuri, North Delhi", "lat": 28.7259, "lng": 77.1627, "zone": "red"},
    {"name": "Shahdara, East Delhi", "lat": 28.6738, "lng": 77.2917, "zone": "red"},
    {"name": "Sadar Bazar, Central Delhi", "lat": 28.6562, "lng": 77.2140, "zone": "red"},
    {"name": "Burari, North Delhi", "lat": 28.7539, "lng": 77.2018, "zone": "red"},
    {"name": "Najafgarh, South West Delhi", "lat": 28.6092, "lng": 76.9798, "zone": "red"},
    {"name": "Sangam Vihar, South Delhi", "lat": 28.5020, "lng": 77.2472, "zone": "red"},
    {"name": "Mustafabad, North East Delhi", "lat": 28.7112, "lng": 77.2785, "zone": "red"},

    # YELLOW ZONES (Moderate Challenge: established residential / commercial sectors with periodic maintenance needs)
    {"name": "Lajpat Nagar, South Delhi", "lat": 28.5677, "lng": 77.2433, "zone": "yellow"},
    {"name": "Rohini Sector 16, North West Delhi", "lat": 28.7325, "lng": 77.1200, "zone": "yellow"},
    {"name": "Karol Bagh, Central Delhi", "lat": 28.6514, "lng": 77.1907, "zone": "yellow"},
    {"name": "Mayur Vihar Phase 1, East Delhi", "lat": 28.6080, "lng": 77.2930, "zone": "yellow"},
    {"name": "Dwarka Sector 10, South West Delhi", "lat": 28.5823, "lng": 77.0500, "zone": "yellow"},
    {"name": "Janakpuri, West Delhi", "lat": 28.6219, "lng": 77.0878, "zone": "yellow"},
    {"name": "Laxmi Nagar, East Delhi", "lat": 28.6312, "lng": 77.2773, "zone": "yellow"},
    {"name": "Pitampura, North West Delhi", "lat": 28.6990, "lng": 77.1384, "zone": "yellow"},
    {"name": "Malviya Nagar, South Delhi", "lat": 28.5356, "lng": 77.2084, "zone": "yellow"},
    {"name": "Chandni Chowk, Central Delhi", "lat": 28.6560, "lng": 77.2300, "zone": "yellow"},
    {"name": "Sarita Vihar, South East Delhi", "lat": 28.5286, "lng": 77.2946, "zone": "yellow"},
    {"name": "Tilak Nagar, West Delhi", "lat": 28.6366, "lng": 77.0963, "zone": "yellow"},
    {"name": "Preet Vihar, East Delhi", "lat": 28.6415, "lng": 77.2961, "zone": "yellow"},

    # GREEN ZONES (Low Challenge: well-planned institutional / diplomatic / premium residential sectors)
    {"name": "Connaught Place, New Delhi", "lat": 28.6315, "lng": 77.2167, "zone": "green"},
    {"name": "Chanakyapuri, New Delhi", "lat": 28.5983, "lng": 77.1972, "zone": "green"},
    {"name": "Vasant Vihar, South West Delhi", "lat": 28.5583, "lng": 77.1583, "zone": "green"},
    {"name": "Civil Lines, Central Delhi", "lat": 28.6814, "lng": 77.2227, "zone": "green"},
    {"name": "Greater Kailash 1, South Delhi", "lat": 28.5482, "lng": 77.2343, "zone": "green"},
    {"name": "Hauz Khas Enclave, South Delhi", "lat": 28.5494, "lng": 77.2001, "zone": "green"},
    {"name": "Model Town, North Delhi", "lat": 28.7027, "lng": 77.1925, "zone": "green"},
    {"name": "Defence Colony, South Delhi", "lat": 28.5727, "lng": 77.2323, "zone": "green"},
    {"name": "Barakhamba Road, New Delhi", "lat": 28.6288, "lng": 77.2285, "zone": "green"}
]

USERS = [
    {"name": "Sneha Kumar", "username": "sneha_kumar"},
    {"name": "Rohit Sharma", "username": "rohit_sharma"},
    {"name": "Priya Sharma", "username": "priya.22"},
    {"name": "Amit Verma", "username": "amit_delhi"},
    {"name": "Neha Gupta", "username": "neha_g"},
    {"name": "Vikas Yadav", "username": "vikas_yadav"},
    {"name": "Pooja Singh", "username": "pooja_singh"},
    {"name": "Rajesh Mehta", "username": "rajesh_m"},
    {"name": "Ananya Roy", "username": "ananya_r"},
    {"name": "Kunal Bansal", "username": "kunal_b"},
    {"name": "Sunita Devi", "username": "sunita_d"},
    {"name": "Tarun Kapoor", "username": "tarun_k"},
    {"name": "Deepak Malhotra", "username": "deepak_m"},
    {"name": "Meenakshi Joshi", "username": "meenu_j"},
    {"name": "Gaurav Chawla", "username": "gaurav_c"},
    {"name": "Anju Saxena", "username": "anju123@a"},
    {"name": "Narendra Jain", "username": "Narendra123@a"},
    {"name": "Navneeta Sen", "username": "Navneeta123@a"}
]

IMAGES_POOL = {
    "Infrastructure": [
        "/static/assets/post_pothole.png",
        "/static/assets/post_abandoned_building.png",
        "/static/assets/post_streetlight.jpg",
        "https://images.unsplash.com/photo-1515162816999-a0c47dc192f7?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1584467541268-b040f83be3fd?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=600&q=80"
    ],
    "Sanitation": [
        "/static/assets/post_garbage.png",
        "https://images.unsplash.com/photo-1605600659908-0ef719419d41?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1530587191325-3db32d826c18?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1532996122724-e3c354a0b15b?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1528323273322-d81458248d40?auto=format&fit=crop&w=600&q=80"
    ],
    "Education": [
        "/static/assets/post_education.jpg",
        "https://images.unsplash.com/photo-1509062522246-3755977927d7?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1497633762265-9d179a990aa6?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1580582932707-520aed937b7b?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1577896851231-70ef18881754?auto=format&fit=crop&w=600&q=80"
    ],
    "Healthcare": [
        "/static/assets/post_healthcare.jpg",
        "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1584515979956-d9f6e5d09982?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1538108149393-fbbd81895907?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1516549655169-df83a0774514?auto=format&fit=crop&w=600&q=80"
    ],
    "Climate": [
        "/static/assets/post_climate.jpg",
        "https://images.unsplash.com/photo-1611273426858-450d8e3c9fce?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1513836279014-a89f7a76ae86?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1448375240586-882707db888b?auto=format&fit=crop&w=600&q=80"
    ]
}

# Pre-defined realistic Delhi civic issue templates (20+ per category, parameterized to reach 200)
TEMPLATES = {
    "Infrastructure": [
        {
            "title": "Severe pothole cluster causing vehicle undercarriage damage",
            "desc": "Multiple deep craters on the main bypass corridor stretching over 300 meters. Two wheelers are skidding during late evening hours and vehicular speed is bottlenecked.",
            "solution": "Lodge an emergency road maintenance ticket under Delhi Right to Service (e-SLA) Act 2011 with PWD Division. Road maintenance engineers are mandated to execute cold-mix patching within 72 hours under IRC:82 guidelines.",
            "authority": "Public Works Department (PWD Delhi) / MCD Road Maintenance Wing",
            "rules": "Delhi Right to Service Act 2011 (Road Repairs SLA 72 hrs), IRC:82 Specifications"
        },
        {
            "title": "Broken storm water drain slab posing pedestrian death trap",
            "desc": "A reinforced concrete drain slab has collapsed into the open nala right in front of the local market entrance. Pedestrians, especially children and senior citizens, are at severe risk.",
            "solution": "Issue emergency rectification notice under Section 317 of Delhi Municipal Corporation (DMC) Act 1957. The Zonal Executive Engineer must barricade the opening with retro-reflective warnings within 6 hours and replace the slab within 48 hours.",
            "authority": "MCD Civil Engineering Dept / Zonal Executive Engineer",
            "rules": "DMC Act 1957 Section 317 (Public Safety on Ways), PWD Safety Norms"
        },
        {
            "title": "Dark stretch due to continuous street light circuit fault",
            "desc": "Over 12 consecutive LED light poles have been unlit for the past 6 days. The entire colony road has turned pitch dark after 7 PM, creating safety hazards for female commuters.",
            "solution": "File complaint directly via MCD 311 app or BSES/TPDDL Streetlight Redressal portal. Standard operating procedure under GNCTD DISCOM framework mandates restoration of street light feeder lines within 24 to 48 hours.",
            "authority": "MCD Electrical Wing & Power DISCOM (BSES/TPDDL)",
            "rules": "Delhi Electricity Regulatory Commission (DERC) Standards of Performance"
        },
        {
            "title": "Major potable water supply pipeline rupture flooding road",
            "desc": "High-pressure freshwater pipeline has ruptured under the sidewalk, wasting thousands of liters of clean treated drinking water and creating a waterlogged crater across the intersection.",
            "solution": "Trigger emergency pipeline intervention via Delhi Jal Board (DJB) Central Control Room (1916). As per Delhi Water Board Act 1998, emergency valve throttling and repair teams must deploy within 6 to 12 hours.",
            "authority": "Delhi Jal Board (DJB) - Zonal Maintenance Division",
            "rules": "Delhi Water Board Act 1998 Section 34 (Repair of Mains & Waste Prevention)"
        },
        {
            "title": "Missing manhole cover on unlit residential avenue",
            "desc": "A heavy cast-iron manhole cover is completely missing on the inner colony road without any protective barricade or danger indicator.",
            "solution": "Report instantly via MCD Toll-Free helpline 155304 or DJB Sewerage Helpline. Under Delhi High Court strict civic safety guidelines, open manholes must be cordoned off within 2 hours and fitted with FRP covers within 24 hours.",
            "authority": "Delhi Jal Board (DJB) Sewerage Maintenance / MCD",
            "rules": "Delhi High Court Mandate on Open Manholes (W.P.(C) 6932/2012) & DMC Act 1957"
        },
        {
            "title": "Damaged expansion joint on major flyover bridge",
            "desc": "Visible gap and rattling iron plates on the flyover expansion joint causing sudden vehicle braking and structural vibration concerns.",
            "solution": "Submit structural inspection report to Delhi PWD Bridge Maintenance Division. Protocol mandates acoustic sensor testing and elastomeric joint restoration under Delhi PWD Works Manual.",
            "authority": "Delhi PWD Bridge Maintenance Cell",
            "rules": "Ministry of Road Transport & Highways (MoRTH) Bridge Inspection Guidelines"
        },
        {
            "title": "Broken pedestrian pavement tiles and encroached walkway",
            "desc": "Footpath paving blocks are shattered with exposed steel rods and debris, forcing pedestrians to walk into oncoming vehicular traffic on the arterial road.",
            "solution": "Notice to MCD Ward Councilor and PWD Road Division under Delhi Urban Shelter & Pedestrian Rights Charter. Re-tiling and obstruction clearance required within 5 working days.",
            "authority": "MCD Works Department / PWD Road Infrastructure",
            "rules": "Unified Traffic and Transportation Infrastructure (UTTIPEC) Pedestrian Guidelines"
        },
        {
            "title": "Non-functional automated traffic signal causing daily gridlock",
            "desc": "The 4-way traffic junction signal has been blinking amber erratically, resulting in chaotic intersections and near-collision incidents during peak morning hours.",
            "solution": "Notify Delhi Traffic Police Modernisation Cell and MCD Electrical Division. Standard SLA for electronic signal controller repairs is 12 hours via Traffic Control Room (1095).",
            "authority": "Delhi Traffic Police & GNCTD Transport Department",
            "rules": "Motor Vehicles Act 1988 & Delhi Police Traffic Regulation Guidelines"
        }
    ],

    "Sanitation": [
        {
            "title": "Community dhalao overflowing onto carriageway for 4 days",
            "desc": "MCD secondary waste collection dhalao has not been cleared for over 96 hours. Putrid organic waste has spilled over 50 meters of the road, breeding swarms of flies and stray cows.",
            "solution": "Log urgent escalation on MCD 311 App with geo-tagged photograph under Section 353 of DMC Act 1957. The concessionaire is subject to liquidated damages of ₹5,000/day for failure to operate compactors within 24 hours.",
            "authority": "MCD Solid Waste Management (SWM) Department",
            "rules": "Delhi Municipal Corporation Act 1957 Sec 353 & Solid Waste Management Rules 2016"
        },
        {
            "title": "Clogged open drain discharging foul blackwater into residential lane",
            "desc": "Colony storm drain is choked with single-use plastic and heavy silt. Stagnant sewage is backing up into house driveways, releasing foul gases and severe mosquito hazard.",
            "solution": "Request suction jetting deployment from MCD Sanitation Wing. Under Swachh Bharat Mission (Urban) guidelines, mechanical desilting and disinfectant spraying must be completed within 48 hours.",
            "authority": "MCD Ward Sanitary Inspector & DJB Drainage Wing",
            "rules": "SWM Rules 2016 & National Green Tribunal Drainage Maintenance Directives"
        },
        {
            "title": "Illegal dumping of construction and demolition (C&D) debris",
            "desc": "Tractor-trolleys have dumped tons of concrete chunks, plaster dust, and broken masonry alongside the colony boundary wall overnight.",
            "solution": "Lodge complaint on Green Delhi App / MCD C&D portal. Under Delhi C&D Waste Management Rules, violators face a mandatory ₹50,000 penalty and MCD must transport debris to the Burari/Shastri Park recycling plant.",
            "authority": "Delhi Pollution Control Committee (DPCC) & MCD Enforcement",
            "rules": "Construction and Demolition Waste Management Rules 2016 & DPCC Guidelines"
        },
        {
            "title": "Dysfunctional and filthy public toilet complex in market area",
            "desc": "Public toilet seats are broken, taps are running dry, and doors are missing latches. Market shoppers and daily wage workers are forced into open defecation nearby.",
            "solution": "Issue remediation summons to DUSIB / MCD under Swachh Bharat Mission Public Toilet Protocol. Contractor contract termination clause applies if running water and cleanliness are not restored within 24 hours.",
            "authority": "Delhi Urban Shelter Improvement Board (DUSIB) / MCD Toilet Wing",
            "rules": "SBM-Urban ODF+ Protocol & DUSIB Toilet Maintenance Regulations"
        },
        {
            "title": "Stagnant storm water pool breeding high density mosquito larvae",
            "desc": "A vast pool of green stagnant water in an abandoned vacant plot has become a major vector breeding site. Multiple dengue and chikungunya cases reported in adjacent blocks.",
            "solution": "Submit notice to MCD Public Health Department for anti-larval chemical spraying (Temephos/Bti). Under Delhi Municipal Health Bye-laws, the plot owner is liable for legal notice and summary fines within 48 hours.",
            "authority": "MCD Malaria and Vector Borne Disease Control Cell",
            "rules": "Delhi Municipal Corporation Epidemic Diseases Regulations & DMC Health Bye-laws"
        },
        {
            "title": "Dead animal carcass left unattended near residential gate",
            "desc": "A stray animal carcass has been lying on the sidewalk for over 24 hours, emitting intolerable odor and posing biological contamination.",
            "solution": "Call MCD Animal Carcass Disposal Helpline (011-23225204). The dedicated hydraulic lifting van is mandated to clear and disinfect the site within 4 hours of notification.",
            "authority": "MCD Veterinary Services Department",
            "rules": "DMC Act 1957 Section 361 (Disposal of Dead Animals SLA 4-6 hours)"
        },
        {
            "title": "Unsegregated garbage burning in open municipal dustbin",
            "desc": "Sanitation sweepers or scrap collectors are burning dried leaves and plastic waste inside the dustbin, creating thick acrid smoke engulfing nearby balconies.",
            "solution": "Report immediately on Green Delhi App with live location. Open burning is strictly prohibited under CAQM GRAP Stage 1-4 with a direct fine of ₹5,000 on responsible individuals.",
            "authority": "Commission for Air Quality Management (CAQM) & MCD Sanitary Squad",
            "rules": "NGT Order in Vardhaman Kaushik Case & CAQM Statutory Regulations"
        }
    ],

    "Education": [
        {
            "title": "Dilapidated boundary wall and crumbling ceiling plaster in school",
            "desc": "Primary section classroom roof has active seepage and exposed reinforcement bars. The rear perimeter wall has tilted dangerously after recent rains.",
            "solution": "Register grievance with School Management Committee (SMC) and DoE Civil Works Division. Emergency audit required under Directorate of Education (DoE Delhi) School Safety Standards with 7-day repair timeline.",
            "authority": "Directorate of Education (DoE Delhi) & PWD Education Building Cell",
            "rules": "Delhi School Education Act & Rules 1973 (DSEAR) & National Disaster Management Guidelines for Schools"
        },
        {
            "title": "Severe shortage of student desks in primary section",
            "desc": "Over 80 students in classes 3 and 4 are sitting on bare cold concrete floors due to missing dual-desks, affecting student posture and handwriting.",
            "solution": "Escalate to the Block Education Officer (BEO) under Samagra Shiksha Delhi procurement schedule. Buffer furniture reserves from central warehouse must be dispatched within 5 working days.",
            "authority": "Directorate of Education (DoE) - District North/South/East Education Office",
            "rules": "Right of Children to Free and Compulsory Education (RTE) Act 2009 Section 19"
        },
        {
            "title": "Defective commercial RO drinking water plant in government school",
            "desc": "The central drinking water cooler and filtration unit has broken cooling coils and dirty filters. Children are bringing water bottles from home or drinking untreated tap water.",
            "solution": "Invoke Comprehensive Annual Maintenance Contract (CAMC) with DJB / DoE Water Quality Division. Mandatory microbial testing and filter element replacement must be certified within 48 hours.",
            "authority": "DoE Delhi School Infrastructure Branch / Delhi Jal Board Quality Wing",
            "rules": "Delhi School Health Norms & BIS 10500 Drinking Water Standards"
        },
        {
            "title": "Dysfunctional student washrooms lacking running water supply",
            "desc": "Girls' washrooms on the ground floor have non-functional flush cisterns and cracked door locks, causing severe embarrassment and absentee rates among teenage students.",
            "solution": "Immediate directive to School Head and Estate Manager under Swachh Vidyalaya Guidelines. PWD Electrical/Civil sub-division must rectify sanitary fittings within 24 hours.",
            "authority": "Directorate of Education (DoE) & PWD Civil Maintenance",
            "rules": "Swachh Vidyalaya Swachh Bharat Norms & RTE Act Schedule"
        },
        {
            "title": "Non-functional computers and internet in ICT smart classroom",
            "desc": "Computer lab has 18 out of 25 systems suffering from power supply failure and operating system crashes, stalling weekly computer science curriculum.",
            "solution": "Log hardware service incident on Delhi IT Project Cell (DGS&D) SLA tracker. Vendor contract guarantees 48-hour hardware replacement or penalty clause.",
            "authority": "DoE Delhi Information & Communication Technology (ICT) Branch",
            "rules": "GNCTD IT Policy for Smart Classrooms & Service Level Agreement 2024"
        },
        {
            "title": "Inadequate security and broken streetlights outside girls school gate",
            "desc": "Street lights outside the primary entrance gate are broken, and unauthorized vendors gather around dismissal time, causing safety anxieties for female students.",
            "solution": "Joint request for Delhi Police PCR van stationed at school dispersal hours and expedited MCD lighting fix under Delhi Nirbhaya Safety Fund program.",
            "authority": "Delhi Police Ward Beat Officer & MCD Electrical Wing",
            "rules": "Delhi Protection of Children from Harassment Protocols & DMC Lighting Norms"
        }
    ],

    "Healthcare": [
        {
            "title": "Stockout of essential diabetes and hypertension medications at clinic",
            "desc": "Mohalla Clinic has had zero inventory of Metformin, Amlodipine, and basic paracetamol syrups for 10 straight days, turning away elderly chronic illness patients.",
            "solution": "Trigger emergency drug replenishment requisition to Central Procurement Agency (CPA), GNCTD. Under Delhi Health Services charter, critical medicine stockout must be re-stocked via buffer inventory within 48 hours.",
            "authority": "Directorate General of Health Services (DGHS Delhi) / Mohalla Clinic Cell",
            "rules": "Delhi Free Medicine Scheme Protocol & Essential Medicines List (DEL-NLEM)"
        },
        {
            "title": "Broken ultrasound and X-Ray machine at sub-district hospital",
            "desc": "The primary digital X-Ray imaging unit has been displaying error codes for over two weeks. Trauma and fracture patients are being referred to far-away tertiary centers.",
            "solution": "Escalate equipment downtime notice to Medical Superintendent under GNCTD Biomedical Equipment Management Maintenance (BEMM) policy. Vendor SLA enforces technician visit within 24 hours.",
            "authority": "Hospital Administration & DGHS Delhi Health Infrastructure Cell",
            "rules": "Delhi Health Infrastructure Maintenance Standards & Clinical Establishments Act"
        },
        {
            "title": "Missing wheelchair access and damaged entrance ramp at dispensary",
            "desc": "The wheelchair ramp at the dispensary entrance is broken and obstructed by debris, preventing physically challenged and elderly patients from entering safely.",
            "solution": "Issue accessibility violation notice under Rights of Persons with Disabilities (RPwD) Act 2016. PWD Health Maintenance wing must reconstruct compliant ramp with railings within 7 days.",
            "authority": "Chief Medical Officer (CMO) & PWD Health Civil Division",
            "rules": "Rights of Persons with Disabilities Act 2016 Section 44 & Accessible India Campaign"
        },
        {
            "title": "Extreme wait times and crashed electronic OPD registration queue",
            "desc": "Server downtime in the cloud hospital management software has caused hundreds of patients to wait in sweltering heat for manual paper slips for over 3 hours.",
            "solution": "Deploy manual token backup protocol and report NIC Delhi E-Hospital technical failure. Hospital admin must open 3 extra manual registration counters within 15 minutes of server outage.",
            "authority": "Delhi Health & Family Welfare Department & NIC Delhi",
            "rules": "GNCTD Citizen Hospital Charter & National Digital Health Mission Protocols"
        },
        {
            "title": "Overflowing biomedical waste bins left exposed in clinic courtyard",
            "desc": "Red and yellow biomedical waste bins containing used syringes, bandages, and IV sets are overfilled and left open to rain and stray animals behind the clinic.",
            "solution": "Serve immediate penalty notice to Common Biomedical Waste Treatment Facility (CBWTF) operator. Under Bio-Medical Waste Management Rules 2016, failure to collect within 48 hours attracts DPCC prosecution.",
            "authority": "Delhi Pollution Control Committee (DPCC) & DGHS Bio-Safety Cell",
            "rules": "Bio-Medical Waste Management Rules 2016 & DPCC Inspection Guidelines"
        },
        {
            "title": "Delayed CATS ambulance response due to colony access blockage",
            "desc": "Centralized Accident & Trauma Services (CATS) ambulance took 55 minutes to reach patient due to illegal parking and broken speed bumps inside the colony.",
            "solution": "Submit joint petition to Traffic Police and MCD for emergency green corridor lane clearance and removal of unauthorized speed breakers under Delhi High Court road safety directives.",
            "authority": "Delhi Traffic Police & CATS Ambulance Control Room",
            "rules": "Motor Vehicles (Driving) Regulations 2017 & Delhi Ambulance Access Norms"
        }
    ],

    "Climate": [
        {
            "title": "Severe road dust emission from unpaved road shoulders under dry sweep",
            "desc": "Heavy vehicular movement is throwing up clouds of fine PM2.5 and PM10 silica dust from unpaved mud shoulders. Nearby residents are reporting chronic throat irritation.",
            "solution": "Invoke CAQM GRAP Stage-2 statutory regulations. PWD/MCD must deploy mechanical sweeping machines and water mist sprinklers using treated sewage effluent daily on this stretch.",
            "authority": "Commission for Air Quality Management (CAQM) & Delhi PWD Dust Cell",
            "rules": "CAQM Statutory Directions on Fugitive Dust & National Clean Air Programme (NCAP)"
        },
        {
            "title": "Illegal biomass and fallen dry leaves burning in public park",
            "desc": "Garden waste and pruned branches are being burnt inside the municipal park, producing dense gray toxic smoke that settles across the neighboring apartment blocks.",
            "solution": "Lodge complaint on Green Delhi App with live GPS. Under NGT directives and DMC Act, a summary spot fine of ₹5,000 must be levied on violators, and organic waste redirected to composting pits.",
            "authority": "MCD Horticulture Department & DPCC Air Vigilance Squad",
            "rules": "National Green Tribunal (NGT) Order in OA No. 21/2014 & DMC Act 1957"
        },
        {
            "title": "Untreated chemical industrial discharge into open stormwater drain",
            "desc": "A chemical washing unit is discharging foaming colored effluent with pungent solvent fumes into the natural storm channel feeding into Najafgarh/Yamuna drain.",
            "solution": "Report urgent industrial violation to DPCC Inspection Wing. The factory is subject to immediate power and water disconnection under Water (Prevention and Control of Pollution) Act 1974 Section 33A.",
            "authority": "Delhi Pollution Control Committee (DPCC) Industrial Cell",
            "rules": "Water (Prevention and Control of Pollution) Act 1974 Sec 33A & NGT Yamuna Rejuvenation Orders"
        },
        {
            "title": "Illegal concretization of urban tree bases suffocating roots",
            "desc": "Contractors have poured dense concrete right up to the tree trunks on both sides of the road, leaving zero soil basin and causing healthy neem and peepal trees to dry up.",
            "solution": "Lodge complaint with Delhi Tree Officer under Delhi Preservation of Trees Act (DPTA) 1994. Under Delhi High Court orders, a mandatory 1-meter unpaved green radius around tree bases must be cleared within 3 days.",
            "authority": "Department of Forests & Wildlife (GNCTD) / Tree Officer",
            "rules": "Delhi Preservation of Trees Act 1994 & Delhi High Court Concretization Judgement"
        },
        {
            "title": "Uncovered sand and gravel transit creating hazardous PM10 plumes",
            "desc": "Overloaded dump trucks without tarpaulin covers are dropping construction sand and fine stone dust continuously along the highway corridor.",
            "solution": "Report vehicle registration number on Green Delhi App. Delhi Traffic Police and DPCC are empowered to impound vehicle and impose a mandatory ₹20,000 environmental compensation fine.",
            "authority": "Delhi Traffic Police & DPCC Flying Squad",
            "rules": "Environment (Protection) Act 1986 & CAQM Construction Dust Guidelines"
        },
        {
            "title": "Dying street canopy and dried branches threatening overhead power lines",
            "desc": "Large desiccated branches of aged eucalyptus trees have tilted directly against 11kV overhead electrical conductors, posing severe fire and electrocution danger in wind gusts.",
            "solution": "Apply for emergency trimming clearance via Tree Officer GNCTD and BSES/TPDDL safety cell. Tree pruning under safety exigency must be executed with forest observer supervision within 48 hours.",
            "authority": "Delhi Forest Department & Power DISCOM Safety Cell",
            "rules": "Delhi Preservation of Trees Rules & Central Electricity Authority Safety Regulations"
        }
    ]
}


def populate_complaints():
    database.init_db()          # make sure all tables exist
    conn = database.get_db()
    cursor = conn.cursor()

    # Check count of existing posts per category
    categories = ["Infrastructure", "Sanitation", "Education", "Healthcare", "Climate"]
    
    # We want exactly 200 posts per category = 1,000 posts total!
    # Let's see if we already have some or if we should seed fresh.
    cursor.execute("SELECT category, COUNT(*) AS n FROM posts GROUP BY category")
    existing_counts = {r["category"]: r["n"] for r in cursor.fetchall()}
    print("Existing category counts:", existing_counts)

    # Let's clear and generate a pristine dataset of 200 per category if not complete
    total_existing = sum(existing_counts.values())
    if total_existing < 1000:
        print(f"Current count {total_existing} < 1000. Clearing and generating 200 high-fidelity complaints in each category...")
        cursor.execute("DELETE FROM post_likes")
        cursor.execute("DELETE FROM post_comments")
        cursor.execute("DELETE FROM solution_votes")
        cursor.execute("DELETE FROM posts")
        conn.commit()

        # Seed initial default users
        cursor.execute("SELECT id FROM users")
        user_rows = cursor.fetchall()
        user_ids = [r["id"] for r in user_rows]
        if not user_ids:
            for u in USERS:
                cursor.execute("INSERT INTO users (name, username, password) VALUES (%s, %s, %s) "
                               "ON CONFLICT (username) DO NOTHING",
                               (u["name"], u["username"], generate_password_hash("password123")))
            conn.commit()
            cursor.execute("SELECT id FROM users")
            user_ids = [r["id"] for r in cursor.fetchall()]

        # Generate 200 complaints for each of the 5 categories
        now = datetime.now()
        complaints_batch = []

        # Make sure the top 3 match the user's uploaded screenshot:
        # 1. sneha_kumar - Lajpat Nagar, New Delhi - Garbage not collected for 3 days in our area
        # 2. rohit_sharma - Sector 18, Noida / Rohini - Street light not working
        # 3. priya.22 - Rohini, Delhi - Water leakage in main road

        for category in categories:
            templates_list = TEMPLATES[category]
            images_list = IMAGES_POOL[category]
            print(f"Generating 200 complaints for category: {category}...")

            for i in range(1, 201):
                # Locality selection: distribute across Red, Yellow, Green zones
                # Red zones: 35%, Yellow zones: 45%, Green zones: 20%
                rand_val = random.random()
                if rand_val < 0.35:
                    eligible_locs = [l for l in DELHI_LOCALITIES if l["zone"] == "red"]
                elif rand_val < 0.80:
                    eligible_locs = [l for l in DELHI_LOCALITIES if l["zone"] == "yellow"]
                else:
                    eligible_locs = [l for l in DELHI_LOCALITIES if l["zone"] == "green"]

                loc_data = random.choice(eligible_locs)
                # Small realistic coordinate jitter (+/- 0.005 deg ~ 500m)
                jitter_lat = round(loc_data["lat"] + random.uniform(-0.006, 0.006), 5)
                jitter_lng = round(loc_data["lng"] + random.uniform(-0.006, 0.006), 5)

                tmpl = templates_list[(i - 1) % len(templates_list)]
                user = random.choice(USERS)
                img = images_list[(i - 1) % len(images_list)]

                # Special overrides for the first 3 posts to perfectly match screenshot
                if category == "Sanitation" and i == 1:
                    user = {"name": "Sneha Kumar", "username": "sneha_kumar"}
                    title = "Garbage not collected for 3 days in our area"
                    desc = "The dustbin near the park has been overflowing for the last 3 days. It's causing bad smell and attracting stray animals. Kindly take action."
                    loc_name = "Lajpat Nagar, New Delhi"
                    loc_zone = "yellow"
                    jitter_lat = 28.5677
                    jitter_lng = 77.2433
                    likes = 12
                    comments = 4
                    shares = 2
                    days_ago = 0.08  # ~2 hours ago
                    img = "/static/assets/post_garbage.png"
                elif category == "Infrastructure" and i == 1:
                    user = {"name": "Rohit Sharma", "username": "rohit_sharma"}
                    title = "Street light not working"
                    desc = "The street light near the park gate has been non-functional for the past week. It gets very dark in the evening."
                    loc_name = "Rohini Sector 16, North West Delhi"
                    loc_zone = "yellow"
                    jitter_lat = 28.7325
                    jitter_lng = 77.1200
                    likes = 8
                    comments = 2
                    shares = 1
                    days_ago = 0.2  # ~5 hours ago
                    img = "/static/assets/post_streetlight.jpg"
                elif category == "Infrastructure" and i == 2:
                    user = {"name": "Priya Sharma", "username": "priya.22"}
                    title = "Water leakage in main road"
                    desc = "Main water transmission line has ruptured causing massive water pool and eroding the road asphalt. Needs immediate DJB pipeline isolation."
                    loc_name = "Rohini, Delhi"
                    loc_zone = "yellow"
                    jitter_lat = 28.7200
                    jitter_lng = 77.1150
                    likes = 15
                    comments = 5
                    shares = 3
                    days_ago = 0.3  # ~7 hours ago
                    img = "/static/assets/post_pothole.png"
                else:
                    title = f"{tmpl['title']} (#{i})"
                    desc = f"{tmpl['desc']} Location: {loc_data['name']}."
                    loc_name = loc_data["name"]
                    loc_zone = loc_data["zone"]
                    likes = random.randint(2, 45)
                    comments = random.randint(0, 12)
                    shares = random.randint(0, 8)
                    # Distribute creation dates over past 180 days to create realistic increase/decrease trend curves
                    days_ago = random.uniform(0.1, 180)

                created_time = (now - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")

                # Realistic community AI solution upvotes / downvotes
                upvotes = random.randint(8, 64)
                downvotes = random.randint(0, 7)
                severity = "Critical" if loc_zone == "red" else ("High" if loc_zone == "yellow" else "Medium")
                status = random.choice(["Open", "In Review", "In Progress", "Action Taken", "Resolved"])

                complaints_batch.append((
                    random.choice(user_ids),
                    user["name"],
                    user["username"],
                    category,
                    title,
                    loc_name,
                    jitter_lat,
                    jitter_lng,
                    loc_zone,
                    severity,
                    desc,
                    img,
                    likes,
                    comments,
                    shares,
                    tmpl["solution"],
                    tmpl["authority"],
                    tmpl["rules"],
                    upvotes,
                    downvotes,
                    status,
                    0.0,
                    created_time
                ))

        execute_values(cursor, """
        INSERT INTO posts (
            user_id, author_name, author_username, category, title, location,
            latitude, longitude, zone, severity, description, image_url,
            likes_count, comments_count, shares_count, ai_solution, ai_authority,
            ai_delhi_rules, solution_upvotes, solution_downvotes, resolved_status,
            moderation_score, created_at
        ) VALUES %s
        """, complaints_batch, page_size=250)

        conn.commit()
        print(f"Successfully populated {len(complaints_batch)} complaints across 5 categories into database!")

    # Verify counts
    cursor.execute("SELECT category, COUNT(*) AS n FROM posts GROUP BY category ORDER BY category")
    print("Final category counts in DB:")
    for r in cursor.fetchall():
        print(f"  - {r['category']}: {r['n']}")

    cursor.execute("SELECT zone, COUNT(*) AS n FROM posts GROUP BY zone ORDER BY zone")
    print("Zone distribution:")
    for r in cursor.fetchall():
        print(f"  - {r['zone'].upper()} ZONE: {r['n']}")

    conn.close()


if __name__ == "__main__":
    populate_complaints()

