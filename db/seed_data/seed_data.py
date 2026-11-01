#!/usr/bin/env python3
"""
Jaskr GymGrid - deterministic seed dataset generator.
ALL DATA IS FICTIONAL (names, phones, emails, businesses, transactions).
Usage:  python seed_data.py [output_dir]
Re-running with the same SEED always produces identical CSV files.
"""
import csv
import calendar
import datetime as dt
import json
import os
import random
import sys
import zipfile
from collections import defaultdict, Counter

SEED = 20261030
random.seed(SEED)
TODAY = dt.date(2026, 10, 30)
NOW = dt.datetime(2026, 10, 30, 10, 0, 0)       # dataset snapshot time
ATT_START = dt.date(2026, 8, 3)                  # attendance history window start
N_MEMBERS = 760
GST_RATE = 0.18
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "data")
os.makedirs(OUT, exist_ok=True)
PLACEHOLDER_HASH = "{{HASH_ON_LOAD}}"
DEMO_PASSWORD = "Demo@1234"
DEMO_DOMAIN = "jaskrgymgrid.example"


# ----------------------------------------------------------------- helpers
def add_months(d, m):
    y = d.year + (d.month - 1 + m) // 12
    mo = (d.month - 1 + m) % 12 + 1
    return dt.date(y, mo, min(d.day, calendar.monthrange(y, mo)[1]))


def fdt(x):
    return x.strftime("%Y-%m-%d %H:%M:%S")


def fd(x):
    return x.strftime("%Y-%m-%d") if x else ""


def money(x):
    return f"{x:.2f}"


def wchoice(items, weights):
    return random.choices(items, weights=weights, k=1)[0]


def rdate(a, b):
    return a + dt.timedelta(days=random.randint(0, (b - a).days))


def phone():
    first = random.choice("6789") + "".join(random.choice("0123456789") for _ in range(4))
    last = "".join(random.choice("0123456789") for _ in range(5))
    return f"+91 {first} {last}"


# ------------------------------------------------------------- name pools
def L(s):
    return [x.strip() for x in s.split(",")]


POOLS = {
    "north": {
        "M": L("Aarav,Vivaan,Arjun,Rohan,Karan,Rahul,Amit,Vikram,Nikhil,Sandeep,Harpreet,Gurpreet,Manpreet,Jaspreet,Tejinder,Ankit,Pankaj,Deepak,Mohit,Sahil,Yash,Kunal,Varun,Harsh,Ishaan,Lakshay,Ravi,Sumit,Naveen,Gaurav,Imran,Faisal,Aman,Shivam"),
        "F": L("Ananya,Priya,Neha,Pooja,Simran,Harleen,Kiran,Riya,Sneha,Kavya,Isha,Aditi,Shreya,Nisha,Meera,Divya,Anjali,Komal,Tanvi,Muskan,Jasleen,Manisha,Ritu,Swati,Payal,Sakshi,Bhavna,Preeti,Ayesha,Zoya,Sana,Nargis"),
        "S": L("Sharma,Verma,Gupta,Singh,Kapoor,Malhotra,Chopra,Arora,Bansal,Mehta,Khanna,Bhatia,Sethi,Grewal,Sandhu,Gill,Dhillon,Joshi,Tiwari,Yadav,Chauhan,Rawat,Saxena,Agarwal,Khan,Ahmed,Kohli,Mathur,Pandey,Mishra,Rathore,Shekhawat,Meena,Purohit,Bhati,Qureshi,Ansari,Siddiqui"),
    },
    "west": {
        "M": L("Aditya,Omkar,Sanket,Prathamesh,Swapnil,Rushikesh,Chinmay,Tejas,Hemant,Jay,Dhruv,Parth,Kunj,Mihir,Chirag,Nilesh,Rajesh,Sagar,Pranav,Siddharth,Atharv,Ketan,Bhavesh,Hardik,Jignesh,Viraj,Shubham,Akshay,Mayur,Vedant"),
        "F": L("Sayali,Pooja,Rutuja,Madhuri,Shruti,Gauri,Apurva,Neha,Komal,Ketki,Mansi,Bhakti,Dhara,Krupa,Hetal,Khushi,Riddhi,Janvi,Nidhi,Pallavi,Prerna,Snehal,Tanvi,Vaishnavi,Anushka,Ira,Mitali,Falguni,Nandini,Sakshi"),
        "S": L("Patil,Deshmukh,Kulkarni,Joshi,Shinde,Pawar,Jadhav,More,Gaikwad,Kadam,Chavan,Bhosale,Patel,Shah,Desai,Mehta,Parekh,Trivedi,Thakkar,Modi,Naik,Sawant,Gokhale,Apte,Kamat,Mhatre,Bhatt,Dave,Vyas,Fernandes,D'Souza"),
    },
    "south": {
        "M": L("Arvind,Karthik,Suresh,Vignesh,Harish,Praveen,Naveen,Sai,Venkat,Ramesh,Srinivas,Manoj,Rajesh,Anil,Kiran,Ashwin,Balaji,Dinesh,Gopal,Mahesh,Nithin,Pranav,Rakesh,Sandeep,Santhosh,Tarun,Vijay,Akhil,Anirudh,Jithin"),
        "F": L("Lakshmi,Divya,Keerthi,Meenakshi,Priyanka,Swathi,Deepika,Harini,Kavitha,Madhavi,Nandini,Pavithra,Ramya,Sowmya,Sruthi,Anitha,Bhavana,Geetha,Aishwarya,Archana,Sindhu,Varsha,Vaishnavi,Neha,Anusha,Chaitra,Manasa,Soumya,Athira,Revathi"),
        "S": L("Iyer,Iyengar,Nair,Menon,Pillai,Reddy,Naidu,Rao,Krishnan,Subramanian,Venkatesh,Murthy,Gowda,Shetty,Hegde,Kamath,Prasad,Raman,Sundaram,Chandran,Varma,Kurian,Thomas,George,Babu,Raju,Chowdary,Srinivasan,Natarajan,Narayanan"),
    },
    "east": {
        "M": L("Arnab,Subhajit,Debashis,Sourav,Abhishek,Tanmoy,Rajib,Anirban,Partha,Sayan,Rishav,Ayan,Biswajit,Kaushik,Dipankar,Pritam,Sumanta,Joydeep,Aniket,Souvik,Indranil,Prasenjit,Rana,Amit,Subrata,Ritwik,Koushik,Debjit,Nilanjan,Samir"),
        "F": L("Ananya,Debjani,Madhumita,Moumita,Pritha,Rituparna,Sohini,Sreya,Susmita,Tanushree,Ishita,Mitali,Piyali,Rupsa,Shreya,Aparna,Barnali,Chandrima,Dipti,Jhilik,Mousumi,Payel,Poulami,Riya,Sagarika,Swagata,Trisha,Anwesha,Sharmistha,Srijita"),
        "S": L("Banerjee,Chatterjee,Mukherjee,Bose,Ghosh,Das,Dutta,Sen,Sengupta,Roy,Chakraborty,Bhattacharya,Majumdar,Mitra,Saha,Basu,Biswas,Dey,Paul,Pal,Nandi,Mondal,Halder,Sarkar,Ganguly,Lahiri,Mallick,Guha,Kundu,Datta"),
    },
}

# city -> (primary name region, probability a person from another region lives there)
CITY_REGION = {
    "Delhi": ("north", 0.25), "Gurugram": ("north", 0.30), "Noida": ("north", 0.28),
    "Mumbai": ("west", 0.35), "Pune": ("west", 0.30), "Bengaluru": ("south", 0.45),
    "Hyderabad": ("south", 0.30), "Chennai": ("south", 0.12), "Jaipur": ("north", 0.08),
    "Kolkata": ("east", 0.12), "Chandigarh": ("north", 0.10),
}


def make_name(city, gender=None):
    region, mix = CITY_REGION[city]
    if random.random() < mix:
        region = random.choice([r for r in POOLS if r != region])
    g = gender or wchoice(["M", "F"], [56, 44])
    return f"{random.choice(POOLS[region][g])} {random.choice(POOLS[region]['S'])}", g


used_emails = set()


def make_email(full_name, domain):
    parts = full_name.lower().replace("'", "").split()
    base = f"{parts[0]}.{parts[-1]}"
    e = f"{base}@{domain}"
    n = 1
    while e in used_emails:
        n += 1
        e = f"{base}{n}@{domain}"
    used_emails.add(e)
    return e


def fixed_email(e):
    used_emails.add(e)
    return e


# ---------------------------------------------------------- organisations
ORGS = [  # id, name, contact_email, status, brand_type, hq_city, email_domain, created
    (1, "IronPulse Fitness", "hello@ironpulsefit.example", "active", "chain", "Delhi", "ironpulsefit.example", dt.date(2019, 4, 12)),
    (2, "FlexNation Gyms", "care@flexnation.example", "active", "chain", "Mumbai", "flexnation.example", dt.date(2020, 1, 20)),
    (3, "Aarogya Active Club", "contact@aarogyaactive.example", "active", "independent", "Jaipur", "aarogyaactive.example", dt.date(2018, 8, 5)),
    (4, "Sundarban Strength House", "desk@sundarbanstrength.example", "active", "independent", "Kolkata", "sundarbanstrength.example", dt.date(2021, 3, 15)),
    (5, "Zenith Strength Lab", "info@zenithlab.example", "pending", "independent", "Chandigarh", "zenithlab.example", dt.date(2026, 10, 18)),
]
ORG = {o[0]: o for o in ORGS}
OWNERS = {
    1: ("Sanjay Khanna", "M", "owner.ironpulse.demo@" + DEMO_DOMAIN),
    2: ("Meera Krishnamurthy", "F", "owner.flexnation.demo@" + DEMO_DOMAIN),
    3: ("Devendra Singh Rathore", "M", "owner.aarogya.demo@" + DEMO_DOMAIN),
    4: ("Subhasish Bose", "M", "owner.sundarban.demo@" + DEMO_DOMAIN),
    5: ("Amandeep Kaur Gill", "F", "owner.zenith.demo@" + DEMO_DOMAIN),
}

# id, org, name, address, city, state, pincode, lat, lon, capacity
BRANCH_DEFS = [
    (1, 1, "IronPulse Saket", "Plot 14, Press Enclave Road, Saket", "Delhi", "Delhi", "110017", 28.5245, 77.2066, 140),
    (2, 1, "IronPulse Dwarka", "Sector 12 Market Complex, Dwarka", "Delhi", "Delhi", "110075", 28.5921, 77.0460, 120),
    (3, 1, "IronPulse Gurugram Sector 29", "Leisure Valley Road, Sector 29", "Gurugram", "Haryana", "122001", 28.4685, 77.0690, 150),
    (4, 1, "IronPulse Andheri West", "Veera Desai Road, Andheri West", "Mumbai", "Maharashtra", "400053", 19.1363, 72.8277, 130),
    (5, 1, "IronPulse Indiranagar", "100 Feet Road, Indiranagar", "Bengaluru", "Karnataka", "560038", 12.9784, 77.6408, 135),
    (6, 1, "IronPulse Gachibowli", "Financial District Road, Gachibowli", "Hyderabad", "Telangana", "500032", 17.4401, 78.3489, 160),
    (7, 2, "FlexNation Rohini", "Sector 7 Community Centre, Rohini", "Delhi", "Delhi", "110085", 28.7160, 77.1130, 110),
    (8, 2, "FlexNation Noida Sector 18", "Atta Market Road, Sector 18", "Noida", "Uttar Pradesh", "201301", 28.5708, 77.3260, 145),
    (9, 2, "FlexNation Bandra West", "Hill Road, Bandra West", "Mumbai", "Maharashtra", "400050", 19.0596, 72.8295, 110),
    (10, 2, "FlexNation Baner", "Baner Road, near Balewadi Phata", "Pune", "Maharashtra", "411045", 18.5590, 73.7868, 125),
    (11, 2, "FlexNation Kothrud", "Paud Road, Kothrud", "Pune", "Maharashtra", "411038", 18.5074, 73.8077, 115),
    (12, 2, "FlexNation Koramangala", "80 Feet Road, 4th Block, Koramangala", "Bengaluru", "Karnataka", "560034", 12.9352, 77.6245, 130),
    (13, 2, "FlexNation Adyar", "Lattice Bridge Road, Adyar", "Chennai", "Tamil Nadu", "600020", 13.0067, 80.2570, 120),
    (14, 3, "Aarogya Active Club C-Scheme", "Ashok Marg, C-Scheme", "Jaipur", "Rajasthan", "302001", 26.9100, 75.8000, 100),
    (15, 3, "Aarogya Active Club Vaishali Nagar", "Gandhi Path West, Vaishali Nagar", "Jaipur", "Rajasthan", "302021", 26.9124, 75.7270, 90),
    (16, 4, "Sundarban Strength House", "Sector V, Salt Lake City", "Kolkata", "West Bengal", "700091", 22.5736, 88.4330, 110),
    (17, 5, "Zenith Strength Lab Sector 17", "Sector 17 Plaza", "Chandigarh", "Chandigarh", "160017", 30.7398, 76.7827, 100),
]
LIVE_BRANCHES = [b for b in BRANCH_DEFS if b[1] != 5]
BR = {b[0]: b for b in BRANCH_DEFS}
BR_CITY = {b[0]: b[4] for b in BRANCH_DEFS}
BR_ORG = {b[0]: b[1] for b in BRANCH_DEFS}
BRANCHES_OF_ORG = defaultdict(list)
for b in BRANCH_DEFS:
    BRANCHES_OF_ORG[b[1]].append(b[0])

# opening hours styles: list of (open, close) for Mon..Sun
T = dt.time
HOURS_STYLES = [
    [(T(5, 30), T(22, 30))] * 6 + [(T(7, 0), T(20, 0))],
    [(T(6, 0), T(23, 0))] * 7,
    [(T(5, 0), T(23, 0))] * 5 + [(T(6, 0), T(22, 0)), (T(7, 0), T(14, 0))],
    [(T(5, 30), T(22, 30))] * 7,
]
BH = {b[0]: HOURS_STYLES[b[0] % 4] for b in BRANCH_DEFS}

FACILITIES = [
    ("Cardio Zone", "Treadmills, cross-trainers, cycles and rowers"),
    ("Free Weights Area", "Dumbbells, barbells, racks and benches"),
    ("Strength Machines", "Selectorised and plate-loaded machines"),
    ("Functional Training Zone", "Turf, sleds, ropes and kettlebells"),
    ("CrossFit Rig", "Pull-up rig, plyo boxes and Olympic lifting platforms"),
    ("Yoga Studio", "Dedicated yoga and mobility studio"),
    ("Zumba and Dance Studio", "Group dance fitness classes"),
    ("Spin Studio", "Indoor cycling classes"),
    ("Boxing Bay", "Heavy bags and a sparring area"),
    ("Steam Room", "Steam bath for recovery"),
    ("Sauna", "Dry sauna for recovery"),
    ("Swimming Pool", "Lap pool, timed sessions"),
    ("Locker Room", "Lockers, showers and changing rooms"),
    ("Personal Training", "One-on-one coaching with certified trainers"),
    ("Nutrition Counselling", "Diet planning with a nutritionist"),
    ("Parking", "Two-wheeler and four-wheeler parking"),
]
CORE_FAC = [1, 2, 3, 13]

# ----------------------------------------------------- membership plans
PLAN_DEFS = {  # org -> list of (name, months, price_inr_ex_gst, access_type, popularity_weight)
    1: [("Monthly Flex", 1, 2800, "HOME_ONLY", 30), ("Quarterly Pro", 3, 7200, "SAME_CITY", 24),
        ("Weekday Saver", 3, 5900, "WEEKDAYS_ONLY", 10), ("Half-Yearly Elite", 6, 12500, "SAME_CITY", 14),
        ("Annual All-Access", 12, 21000, "FULL", 22)],
    2: [("Monthly Flex", 1, 2400, "HOME_ONLY", 30), ("Quarterly Plus", 3, 6300, "SAME_CITY", 25),
        ("Weekday Saver", 3, 5100, "WEEKDAYS_ONLY", 10), ("Half-Yearly Pro", 6, 11000, "SAME_CITY", 13),
        ("Annual Pass", 12, 18500, "FULL", 22)],
    3: [("Monthly Club", 1, 1500, "HOME_ONLY", 35), ("Quarterly Club", 3, 3900, "SAME_CITY", 30),
        ("Annual Club", 12, 12000, "FULL", 35)],
    4: [("Monthly Lift", 1, 1800, "HOME_ONLY", 38), ("Quarterly Lift", 3, 4800, "HOME_ONLY", 32),
        ("Annual Lift", 12, 14500, "FULL", 30)],
}
ACCESS_TEXT = {
    "HOME_ONLY": "Valid only at the member's registered home branch.",
    "SAME_CITY": "Valid at every branch in the member's home city.",
    "WEEKDAYS_ONLY": "Valid at all branches of the organization, Monday to Friday only.",
    "FULL": "Valid at all branches of the organization during opening hours.",
}
PLAN_DESC = {
    "HOME_ONLY": "Single-branch access.", "SAME_CITY": "Multi-branch access within your city.",
    "WEEKDAYS_ONLY": "Budget plan, weekdays only, all branches.", "FULL": "All branches, every day.",
}
plans = []           # dicts
plan_by_org = defaultdict(list)
pid = 0
for org, defs in PLAN_DEFS.items():
    for (name, months, price, acc, w) in defs:
        pid += 1
        p = dict(plan_id=pid, organization_id=org, plan_name=name, duration_months=months, price=price,
                 access=acc, weight=w, description=PLAN_DESC[acc])
        plans.append(p)
        plan_by_org[org].append(p)
PLAN = {p["plan_id"]: p for p in plans}

access_rules = []
for p in plans:
    for bid in BRANCHES_OF_ORG[p["organization_id"]]:
        access_rules.append(dict(access_rule_id=len(access_rules) + 1, plan_id=p["plan_id"], branch_id=bid,
                                 access_type=p["access"], conditions=ACCESS_TEXT[p["access"]]))

# ---------------------------------------------------------------- users
users = []


def new_user(email, role, created, last_login=None):
    u = dict(user_id=len(users) + 1, email=email, password_hash=PLACEHOLDER_HASH, role=role,
             is_active=1, created_at=created, last_login=last_login)
    users.append(u)
    return u["user_id"]


def rand_login(recent_days=14, p_recent=0.8):
    if random.random() < p_recent:
        d = TODAY - dt.timedelta(days=random.randint(0, recent_days))
    else:
        d = TODAY - dt.timedelta(days=random.randint(15, 90))
    return dt.datetime.combine(d, dt.time(random.randint(5, 22), random.randint(0, 59), random.randint(0, 59)))


admin_uid = new_user(fixed_email("admin.demo@" + DEMO_DOMAIN), "admin", dt.datetime(2026, 1, 5, 9, 0, 0), rand_login())
staff = []

# platform admin as a staff row (no organization)
staff.append(dict(staff_id=1, user_id=admin_uid, organization_id="", branch_id="", job_role="PLATFORM_ADMIN",
                  full_name="Jaskr Platform Admin", phone=phone(), status="active", hired_date=dt.date(2026, 1, 5)))
owner_uid = {}
for org, (nm, g, em) in OWNERS.items():
    created = dt.datetime.combine(ORG[org][7], dt.time(10, 0))
    uid = new_user(fixed_email(em), "owner", created, rand_login())
    owner_uid[org] = uid
    staff.append(dict(staff_id=len(staff) + 1, user_id=uid, organization_id=org, branch_id="", job_role="OWNER",
                      full_name=nm, phone=phone(), status="active", hired_date=ORG[org][7]))

TRAINER_SPECS = ["Strength and Conditioning", "Weight Loss Coaching", "Yoga and Mobility", "Zumba and Dance Fitness",
                 "CrossFit", "Boxing and Combat Fitness", "Functional Training", "Bodybuilding",
                 "Rehabilitation and Mobility", "Pilates"]
trainers, trainer_assign = [], []
SALARY = {}
demo_flags = {"manager": False, "frontdesk": False, "trainer": False}
trainers_by_branch = defaultdict(list)


def add_staff(org, branch, role, city, email_override=None):
    nm, _ = make_name(city)
    domain = ORG[org][6]
    email = fixed_email(email_override) if email_override else make_email(nm, domain)
    hired_lo = max(ORG[org][7], dt.date(2019, 1, 1))
    if role == "BRANCH_MANAGER":
        hired = rdate(hired_lo, dt.date(2024, 12, 31))
        SALARY_VAL = random.randint(55, 70) * 1000
    elif role == "FRONT_DESK":
        hired = rdate(max(hired_lo, dt.date(2021, 1, 1)), dt.date(2026, 8, 31))
        SALARY_VAL = random.randint(20, 26) * 1000
    elif role == "TRAINER":
        hired = rdate(max(hired_lo, dt.date(2020, 1, 1)), dt.date(2026, 8, 31))
        SALARY_VAL = random.randint(28, 45) * 1000
    else:  # FINANCE
        hired = rdate(max(hired_lo, dt.date(2021, 1, 1)), dt.date(2025, 12, 31))
        SALARY_VAL = random.randint(40, 55) * 1000
    uid = new_user(email, "staff", dt.datetime.combine(hired, dt.time(9, 30)), rand_login(7, 0.9))
    sid = len(staff) + 1
    ph = phone()
    staff.append(dict(staff_id=sid, user_id=uid, organization_id=org, branch_id=branch if branch else "",
                      job_role=role, full_name=nm, phone=ph, status="active", hired_date=hired))
    SALARY[sid] = SALARY_VAL
    return sid, uid, nm, ph, hired


finance_user = {}
for org in (1, 2, 3, 4):
    for bid in BRANCHES_OF_ORG[org]:
        city = BR_CITY[bid]
        em = "manager.demo@" + DEMO_DOMAIN if (bid == 1 and not demo_flags["manager"]) else None
        demo_flags["manager"] |= bid == 1
        add_staff(org, bid, "BRANCH_MANAGER", city, em)
        for i in range(2):
            em = "frontdesk.demo@" + DEMO_DOMAIN if (bid == 1 and i == 0) else None
            add_staff(org, bid, "FRONT_DESK", city, em)
        for i in range(3):
            em = "trainer.demo@" + DEMO_DOMAIN if (bid == 1 and i == 0) else None
            sid, uid, nm, ph, hired = add_staff(org, bid, "TRAINER", city, em)
            tid = len(trainers) + 1
            trainers.append(dict(trainer_id=tid, organization_id=org, staff_id=sid, user_id=uid, full_name=nm,
                                 specialization=random.choice(TRAINER_SPECS), phone=ph, hired=hired, branch=bid))
    em = "finance.demo@" + DEMO_DOMAIN if org == 1 else None
    sid, uid, _, _, _ = add_staff(org, None, "FINANCE", ORG[org][5], em)
    finance_user[org] = uid

# trainer assignments (some trainers moved between branches of the same organisation)
for t in trainers:
    org, cur = t["organization_id"], t["branch"]
    others = [b for b in BRANCHES_OF_ORG[org] if b != cur]
    if others and t["hired"] <= dt.date(2025, 6, 1) and random.random() < 0.22:
        prev_end = t["hired"] + dt.timedelta(days=random.randint(120, 400))
        trainer_assign.append(dict(assignment_id=len(trainer_assign) + 1, trainer_id=t["trainer_id"],
                                   branch_id=random.choice(others), start_date=t["hired"], end_date=prev_end))
        trainer_assign.append(dict(assignment_id=len(trainer_assign) + 1, trainer_id=t["trainer_id"],
                                   branch_id=cur, start_date=prev_end + dt.timedelta(days=1), end_date=""))
    else:
        trainer_assign.append(dict(assignment_id=len(trainer_assign) + 1, trainer_id=t["trainer_id"],
                                   branch_id=cur, start_date=t["hired"], end_date=""))
    trainers_by_branch[cur].append(t)

# --------------------------------------------------------------- members
FORCED = {
    1: dict(name="Rohan Malhotra", g="M", home=1, email="member.demo@" + DEMO_DOMAIN,
            chain=[("Half-Yearly Elite", dt.date(2025, 12, 1)), ("Annual All-Access", dt.date(2026, 6, 1))]),
    2: dict(name="Priya Deshmukh", g="F", home=10, email="member.monthly.demo@" + DEMO_DOMAIN,
            chain=[("Monthly Flex", dt.date(2026, 10, 12))]),
    3: dict(name="Imran Qureshi", g="M", home=9, email="member.expired.demo@" + DEMO_DOMAIN,
            chain=[("Monthly Flex", dt.date(2026, 8, 1))]),
}
cap_w = [b[9] for b in LIVE_BRANCHES]
members = []
for i in range(1, N_MEMBERS + 1):
    if i in FORCED:
        f = FORCED[i]
        m = dict(member_id=i, home=f["home"], name=f["name"], gender=f["g"], forced=f)
    else:
        home = random.choices([b[0] for b in LIVE_BRANCHES], weights=cap_w, k=1)[0]
        nm, g = make_name(BR_CITY[home])
        m = dict(member_id=i, home=home, name=nm, gender=g, forced=None)
    m["freq"] = wchoice([1, 2, 3, 4, 5, 6], [8, 20, 27, 22, 15, 8])
    m["profile"] = wchoice(["morning", "evening", "midday", "flex"], [40, 45, 10, 5])
    members.append(m)
MEMBER = {m["member_id"]: m for m in members}

memberships = []


def plan_named(org, name):
    return next(p for p in plan_by_org[org] if p["plan_name"] == name)


def add_ms(m, plan, start, idx, locked=False):
    end = add_months(start, plan["duration_months"]) - dt.timedelta(days=1)
    ms = dict(membership_id=len(memberships) + 1, member_id=m["member_id"], plan_id=plan["plan_id"], start_date=start,
              end_date=end, status="expired" if end < TODAY else "active", locked=locked, idx=idx)
    memberships.append(ms)
    return ms


for m in members:
    org = BR_ORG[m["home"]]
    if m["forced"]:
        for k, (pn, st) in enumerate(m["forced"]["chain"]):
            add_ms(m, plan_named(org, pn), st, k, locked=True)
        continue
    plist = plan_by_org[org]
    start = dt.date(2025, 4, 1) + dt.timedelta(days=int(random.triangular(0, 575, 520)))
    k = 0
    while True:
        plan = random.choices(plist, weights=[p["weight"] for p in plist], k=1)[0]
        ms = add_ms(m, plan, start, k)
        if ms["end_date"] >= TODAY:
            break
        if random.random() < 0.72:
            nxt = ms["end_date"] + dt.timedelta(days=1 + (0 if random.random() < 0.7 else random.randint(1, 25)))
            if nxt > TODAY:
                break
            start, k = nxt, k + 1
        else:
            break

ms_by_member = defaultdict(list)
for ms in memberships:
    ms_by_member[ms["member_id"]].append(ms)
last_ms = {mid: lst[-1] for mid, lst in ms_by_member.items()}

# some latest memberships were never paid (pending / overdue); a few members cancelled
for mid, ms in last_ms.items():
    if ms["locked"]:
        continue
    if ms["start_date"] >= TODAY - dt.timedelta(days=25) and random.random() < 0.18:
        ms["status"] = "pending"
        ms["unpaid"] = True
for ms in memberships:
    if (not ms["locked"] and ms["status"] == "active" and ms["start_date"] < TODAY - dt.timedelta(days=14)
            and random.random() < 0.03):
        ms["status"] = "cancelled"

# create member users + member rows
member_rows = []
for m in members:
    first = ms_by_member[m["member_id"]][0]["start_date"]
    reg = first - dt.timedelta(days=random.randint(0, 4))
    if m["forced"]:
        email = fixed_email(m["forced"]["email"])
    else:
        email = make_email(m["name"], random.choice(["mailbox.example", "inbox.example", "demo-mail.example"]))
    uid = new_user(email, "member", dt.datetime.combine(reg, dt.time(11, 0)),
                   rand_login(10, 0.7) if ms_by_member[m["member_id"]][-1]["status"] == "active" else rand_login(5, 0.1))
    m["user_id"], m["reg"] = uid, reg
    member_rows.append(dict(member_id=m["member_id"], user_id=uid, home_branch_id=m["home"], full_name=m["name"],
                            phone=phone(), registration_date=reg))

# ------------------------------------------------ invoices / payments
invoices, items, payments = [], [], []
fail_methods = ["UPI", "Credit Card", "Debit Card", "Net Banking"]
PAY_METHODS = ["UPI", "Credit Card", "Debit Card", "Net Banking", "Cash"]
PAY_W = [55, 14, 11, 10, 10]
for ms in memberships:
    m, plan = MEMBER[ms["member_id"]], PLAN[ms["plan_id"]]
    inv_date = ms["start_date"] - dt.timedelta(days=random.randint(0, 2)) if not ms["locked"] else ms["start_date"]
    if inv_date > TODAY:
        inv_date = TODAY
    iid = len(invoices) + 1
    lines = [(f"{plan['plan_name']} - {plan['duration_months']} month{'s' if plan['duration_months'] > 1 else ''}", 1, plan["price"])]
    if ms["idx"] == 0 and (ms["locked"] or random.random() < 0.7):
        lines.append(("Joining fee", 1, random.choice([500, 750, 1000])))
    if random.random() < 0.10:
        lines.append((f"Locker rental ({min(plan['duration_months'], 3)} months)", 1, 200 * min(plan["duration_months"], 3)))
    if not ms["locked"] and random.random() < 0.08:
        lines.append(("Personal training starter pack (4 sessions)", 1, 2400))
    subtotal = sum(q * u for _, q, u in lines)
    gst = round(subtotal * GST_RATE, 2)
    lines.append((f"GST @ {int(GST_RATE * 100)}%", 1, gst))
    total = round(subtotal + gst, 2)
    for desc, q, u in lines:
        items.append(dict(invoice_item_id=len(items) + 1, invoice_id=iid, description=desc, quantity=q,
                          unit_price=money(u), line_total=money(q * u)))
    due = inv_date + dt.timedelta(days=7)
    inv = dict(invoice_id=iid, invoice_number=f"JGG/{inv_date.year}/{iid:06d}", member_id=m["member_id"],
               membership_id=ms["membership_id"], invoice_date=inv_date, due_date=due, total=total, status="paid")
    invoices.append(inv)
    ms["invoice"] = inv
    if ms.get("unpaid"):
        inv["status"] = "pending" if due >= TODAY else "overdue"
        if random.random() < 0.5:
            payments.append(dict(payment_id=len(payments) + 1, membership_id=ms["membership_id"], invoice_id=iid,
                                 branch_id=m["home"], amount=total, payment_date=min(NOW, dt.datetime.combine(inv_date, dt.time(12, 0))),
                                 payment_method=random.choice(fail_methods), payment_status=random.choice(["failed", "pending"]),
                                 ref=""))
        continue
    pdate = dt.datetime.combine(inv_date + dt.timedelta(days=random.randint(0, 1)),
                                dt.time(random.randint(7, 21), random.randint(0, 59), random.randint(0, 59)))
    if pdate > NOW:
        pdate = NOW - dt.timedelta(hours=1)
    if not ms["locked"] and random.random() < 0.04:  # an earlier failed attempt
        payments.append(dict(payment_id=len(payments) + 1, membership_id=ms["membership_id"], invoice_id=iid,
                             branch_id=m["home"], amount=total, payment_date=pdate - dt.timedelta(hours=random.randint(2, 20)),
                             payment_method=random.choice(fail_methods), payment_status="failed", ref=""))
    method = wchoice(PAY_METHODS, PAY_W)
    payments.append(dict(payment_id=len(payments) + 1, membership_id=ms["membership_id"], invoice_id=iid,
                         branch_id=m["home"], amount=total, payment_date=pdate, payment_method=method,
                         payment_status="successful", ref=""))
    ms["payment"] = payments[-1]
for p in payments:
    p["ref"] = f"GGTXN2026{p['payment_id']:07d}" if p["payment_status"] != "failed" or True else ""

# ------------------------------------------------------------- refunds
refunds = []
REASONS = ["Relocated to another city", "Medical reasons", "Duplicate payment", "Plan changed to a different tier",
           "Dissatisfied with facilities", "Cancelled within cooling-off period", "Work travel commitments"]
succ = [p for p in payments if p["payment_status"] == "successful"]
ms_by_id = {ms["membership_id"]: ms for ms in memberships}
refund_cands = [p for p in succ if not ms_by_id[p["membership_id"]]["locked"]]
random.shuffle(refund_cands)
for p in refund_cands[: int(len(refund_cands) * 0.055)]:
    ms = ms_by_id[p["membership_id"]]
    full = random.random() < 0.35
    amt = p["amount"] if full else round(p["amount"] * random.choice([0.25, 0.4, 0.5, 0.6]), 2)
    pd = p["payment_date"].date()
    delta = random.randint(2, 20)
    rdate_ = min(pd + dt.timedelta(days=delta), TODAY)
    status = wchoice(["completed", "approved", "requested", "rejected"], [65, 12, 15, 8])
    if rdate_ >= TODAY - dt.timedelta(days=4) and status == "completed":
        status = "approved"
    refunds.append(dict(refund_id=len(refunds) + 1, payment_id=p["payment_id"], refund_amount=amt,
                        refund_date=rdate_, reason=random.choice(REASONS), status=status, full=full))
    if full and status == "completed":
        ms["status"] = "cancelled"
        ms["invoice"]["status"] = "refunded"
# two partial refunds on a few payments (tests that SUM(refunds) <= payment)
for p in refund_cands[int(len(refund_cands) * 0.055): int(len(refund_cands) * 0.055) + 6]:
    pd = p["payment_date"].date()
    d1 = min(pd + dt.timedelta(days=3), TODAY)
    d2 = min(pd + dt.timedelta(days=12), TODAY)
    for k, dd in enumerate((d1, d2)):
        refunds.append(dict(refund_id=len(refunds) + 1, payment_id=p["payment_id"],
                            refund_amount=round(p["amount"] * 0.3, 2), refund_date=dd,
                            reason=random.choice(REASONS), status="completed", full=False))

# --------------------------------------------------------- attendance
attendance = []
DOWW = [1.1, 1.0, 1.0, 1.0, 0.95, 0.9, 0.55]


def pick_minutes(profile, dow, bid):
    o, c = BH[bid][dow]
    weekend = dow >= 5
    if profile == "morning":
        mu, sd = 6.9 + (1.4 if weekend else 0), 0.8
    elif profile == "evening":
        mu, sd = 18.9 - (0.4 if weekend else 0), 1.0
    elif profile == "midday":
        mu, sd = 12.8, 1.5
    else:
        mu, sd = random.choice([7.2, 13.0, 19.5]), 1.0
    lo = o.hour + o.minute / 60
    hi = c.hour + c.minute / 60 - 0.75
    h = min(max(random.gauss(mu, sd), lo), hi)
    return int(h * 60)


def eligible_branches(home, plan):
    org = plan["organization_id"]
    a = plan["access"]
    if a == "HOME_ONLY":
        return [home]
    if a == "SAME_CITY":
        return [b for b in BRANCHES_OF_ORG[org] if BR_CITY[b] == BR_CITY[home]]
    return list(BRANCHES_OF_ORG[org])


for ms in memberships:
    if ms["status"] not in ("active", "expired"):
        continue
    m, plan = MEMBER[ms["member_id"]], PLAN[ms["plan_id"]]
    d0, d1 = max(ms["start_date"], ATT_START), min(ms["end_date"], TODAY)
    elig = eligible_branches(m["home"], plan)
    day = d0
    while day <= d1:
        dow = day.weekday()
        if not (plan["access"] == "WEEKDAYS_ONLY" and dow >= 5) and random.random() < m["freq"] / 7 * DOWW[dow]:
            bid = m["home"]
            if len(elig) > 1 and random.random() < 0.12:
                bid = random.choice(elig)
            mins = pick_minutes(m["profile"], dow, bid)
            cin = dt.datetime.combine(day, dt.time(0, 0)) + dt.timedelta(minutes=mins)
            close = dt.datetime.combine(day, BH[bid][dow][1])
            cout = min(cin + dt.timedelta(minutes=random.randint(40, 110)), close)
            ok = True
            if day == TODAY:
                if cin > NOW - dt.timedelta(minutes=10):
                    ok = False
                elif cout > NOW:
                    cout = None  # still inside
            if ok:
                attendance.append(dict(attendance_id=0, member_id=m["member_id"], branch_id=bid, check_in=cin, check_out=cout))
        day += dt.timedelta(days=1)
attendance.sort(key=lambda a: (a["check_in"], a["member_id"]))
for i, a in enumerate(attendance, 1):
    a["attendance_id"] = i

# ----------------------------------------------------- training sessions
sessions = []
valid_ms = defaultdict(list)
for ms in memberships:
    if ms["status"] in ("active", "expired"):
        valid_ms[ms["member_id"]].append(ms)
for m in members:
    if not valid_ms[m["member_id"]] or random.random() > 0.42:
        continue
    for _ in range(random.randint(1, 6)):
        ms = random.choice(valid_ms[m["member_id"]])
        lo, hi = max(ms["start_date"], ATT_START), min(ms["end_date"], TODAY + dt.timedelta(days=14))
        if lo > hi:
            continue
        day = rdate(lo, hi)
        bid = m["home"]
        if not trainers_by_branch[bid]:
            continue
        tr = random.choice(trainers_by_branch[bid])
        dow = day.weekday()
        o, c = BH[bid][dow]
        start_min = random.randint(o.hour * 60 + 30, c.hour * 60 - 90)
        start_min = (start_min // 15) * 15
        start = dt.datetime.combine(day, dt.time(0, 0)) + dt.timedelta(minutes=start_min)
        if day < TODAY:
            status = wchoice(["completed", "cancelled", "no_show"], [84, 9, 7])
        elif day == TODAY and start < NOW:
            status = "completed"
        else:
            status = wchoice(["scheduled", "cancelled"], [95, 5])
        sessions.append(dict(session_id=len(sessions) + 1, member_id=m["member_id"], trainer_id=tr["trainer_id"],
                             branch_id=bid, session_start=start, duration_minutes=random.choice([45, 60, 60, 75]),
                             status=status, focus=tr["specialization"]))
sessions.sort(key=lambda s: s["session_start"])
for i, s in enumerate(sessions, 1):
    s["session_id"] = i

# ----------------------------------------------- expenses and budgets
CATS = [
    ("Rent", "Monthly premises rent"), ("Electricity and Utilities", "Power, water and generator fuel"),
    ("Equipment Maintenance", "Servicing and spares for gym equipment"),
    ("Housekeeping and Supplies", "Cleaning, towels, consumables"), ("Staff Salaries", "Monthly payroll"),
    ("Marketing and Promotions", "Ads, local promotions, referral rewards"), ("Software and Internet", "Internet, CCTV and software subscriptions"),
    ("Insurance and Licences", "Insurance premiums, trade and fire licences"),
    ("Repairs and Renovation", "Civil, flooring, air-conditioning repairs"), ("Miscellaneous", "Small unclassified costs"),
]
CAT_ID = {c[0]: i + 1 for i, c in enumerate(CATS)}
VENDORS = {
    "Rent": ["Kapoor Realty and Estates", "Rao Properties LLP", "Gupta Commercial Spaces", "Mehra Holdings", "Nair Estates", "Shah Realty Partners"],
    "Electricity and Utilities": ["State Power Distribution Company", "City Water Board", "Bharat Diesel Supplies"],
    "Equipment Maintenance": ["TechnoFit Services", "Muscle Care Engineers", "Sharma Gym Equipment Repairs", "FitServe India"],
    "Housekeeping and Supplies": ["Kaveri Facility Services", "CleanSweep Housekeeping", "Anand Supplies"],
    "Staff Salaries": ["Payroll Run"],
    "Marketing and Promotions": ["Pixel Print and Media", "LocalReach Ads", "Spark Social Studio", "RedBrick Outdoor"],
    "Software and Internet": ["NetLink Broadband", "SecureEye CCTV Services", "CloudDesk Software"],
    "Insurance and Licences": ["Suraksha General Insurance", "Municipal Corporation Licensing", "Fire Safety Department"],
    "Repairs and Renovation": ["Verma Interiors", "Coolbreeze AC Works", "Floorcraft Contractors"],
    "Miscellaneous": ["Local Vendor", "Office Mart", "Stationery Hub"],
}
RENT = {"Mumbai": (380000, 520000), "Delhi": (260000, 380000), "Gurugram": (300000, 420000), "Bengaluru": (250000, 380000),
        "Hyderabad": (220000, 330000), "Pune": (180000, 280000), "Noida": (180000, 280000), "Chennai": (180000, 280000),
        "Jaipur": (90000, 150000), "Kolkata": (120000, 210000)}
rent_of = {b[0]: random.randint(*RENT[b[4]]) // 1000 * 1000 for b in LIVE_BRANCHES}
payroll_of = defaultdict(int)
for s in staff:
    if s["branch_id"] != "" and s["job_role"] in ("BRANCH_MANAGER", "FRONT_DESK", "TRAINER"):
        payroll_of[s["branch_id"]] += SALARY[s["staff_id"]]
expenses = []


def add_exp(bid, cat, d, amount, vendor_desc=None):
    org = BR_ORG[bid]
    age = (TODAY - d).days
    if age > 20:
        status = wchoice(["paid", "approved", "rejected"], [96, 3, 1])
    else:
        status = wchoice(["paid", "approved", "pending"], [40, 40, 20])
    expenses.append(dict(expense_id=len(expenses) + 1, branch_id=bid, expense_category_id=CAT_ID[cat],
                         recorded_by=finance_user[org], expense_date=d, amount=int(round(amount)),
                         vendor=random.choice(VENDORS[cat]),
                         description=vendor_desc or f"{cat} - {d.strftime('%B %Y')}", status=status))


for b in LIVE_BRANCHES:
    bid, size = b[0], b[9] / 120
    for mth in range(1, 11):
        first = dt.date(2026, mth, 1)
        last = min(dt.date(2026, mth, calendar.monthrange(2026, mth)[1]), TODAY)
        add_exp(bid, "Rent", first + dt.timedelta(days=random.randint(0, 2)), rent_of[bid])
        season = 1.35 if mth in (4, 5, 6, 7, 8, 9) else 1.0
        add_exp(bid, "Electricity and Utilities", first + dt.timedelta(days=random.randint(9, 14)),
                random.randint(45, 105) * 1000 * size * season)
        mt = random.randint(8, 30) * 1000 * (3 if random.random() < 0.10 else 1)
        add_exp(bid, "Equipment Maintenance", first + dt.timedelta(days=random.randint(4, 24)), mt)
        add_exp(bid, "Housekeeping and Supplies", first + dt.timedelta(days=random.randint(5, 9)), random.randint(28, 52) * 1000 * size)
        add_exp(bid, "Staff Salaries", last, payroll_of[bid], "Monthly payroll - " + first.strftime("%B %Y"))
        add_exp(bid, "Marketing and Promotions", first + dt.timedelta(days=random.randint(3, 20)), random.randint(15, 80) * 1000)
        add_exp(bid, "Software and Internet", first + dt.timedelta(days=random.randint(6, 12)), random.randint(6, 14) * 1000)
        if mth in (1, 4, 7, 10):
            add_exp(bid, "Insurance and Licences", first + dt.timedelta(days=random.randint(10, 20)), random.randint(15, 24) * 1000,
                    "Quarterly insurance premium")
        add_exp(bid, "Miscellaneous", first + dt.timedelta(days=random.randint(2, 25)), random.randint(3, 12) * 1000)
    for _ in range(random.randint(2, 3)):
        add_exp(bid, "Repairs and Renovation", rdate(dt.date(2026, 1, 10), dt.date(2026, 10, 15)), random.randint(40, 180) * 1000)
# The dataset only holds ~760 registered members, so absolute city-level rents would dwarf receipts.
# Scale each branch's expenses to its own 2026 net receipts (cost ratio 72%-112%) so reports show a
# realistic mix of profitable and loss-making branches. Relative proportions between categories are kept.
pay_branch = {p["payment_id"]: p["branch_id"] for p in payments}
rev_2026 = defaultdict(float)
for p in payments:
    if p["payment_status"] == "successful" and p["payment_date"].year == 2026:
        rev_2026[p["branch_id"]] += p["amount"]
for r in refunds:
    if r["status"] == "completed" and r["refund_date"].year == 2026:
        rev_2026[pay_branch[r["payment_id"]]] -= r["refund_amount"]
raw_total = defaultdict(float)
for e in expenses:
    raw_total[e["branch_id"]] += e["amount"]
k_branch = {bid: rev_2026[bid] * random.uniform(0.72, 1.12) / raw_total[bid] for bid in raw_total}
for e in expenses:
    e["amount"] = max(500, int(round(e["amount"] * k_branch[e["branch_id"]], -2)))
expenses.sort(key=lambda e: (e["expense_date"], e["branch_id"]))
for i, e in enumerate(expenses, 1):
    e["expense_id"] = i

actual = defaultdict(float)
for e in expenses:
    if e["status"] in ("paid", "approved"):
        actual[(e["branch_id"], e["expense_category_id"], e["expense_date"].strftime("%Y-%m"))] += e["amount"]
budgets = []
for b in LIVE_BRANCHES:
    for mth in range(1, 11):
        period = f"2026-{mth:02d}"
        for cat, _ in CATS:
            cid = CAT_ID[cat]
            a = actual.get((b[0], cid, period), 0)
            if cat == "Repairs and Renovation":
                amount = 40000
            elif cat == "Insurance and Licences":
                if mth not in (1, 4, 7, 10):
                    continue
                amount = a * random.uniform(0.95, 1.15) if a else 20000
            elif a == 0:
                continue
            elif random.random() < 0.18:
                amount = a * random.uniform(0.78, 0.95)  # deliberately under-budgeted -> overspend
            else:
                amount = a * random.uniform(0.98, 1.20)
            budgets.append(dict(budget_id=len(budgets) + 1, branch_id=b[0], expense_category_id=cid,
                                budget_period=period, budget_amount=int(round(amount, -2))))

# -------------------------------------------------------------- equipment
EQUIP = [("Treadmill", 6, 14), ("Elliptical Cross-Trainer", 3, 8), ("Spin Bike", 6, 20), ("Rowing Machine", 2, 5),
         ("Smith Machine", 1, 3), ("Leg Press", 1, 3), ("Lat Pulldown", 1, 3), ("Cable Crossover", 1, 3),
         ("Dumbbell Set (2.5-50 kg)", 1, 2), ("Olympic Barbell", 6, 14), ("Squat Rack", 2, 5), ("Flat Bench", 4, 9),
         ("Kettlebell Set", 1, 3), ("Battle Ropes", 2, 4), ("Punching Bag", 3, 6), ("Yoga Mats", 15, 40),
         ("Medicine Balls", 6, 15), ("Assault Bike", 2, 5)]
equipment = []
for b in LIVE_BRANCHES:
    for name, lo, hi in random.sample(EQUIP, random.randint(13, 17)):
        qty = max(1, int(random.randint(lo, hi) * b[9] / 120))
        cond = wchoice(["good", "needs_service", "out_of_order"], [78, 15, 7])
        equipment.append(dict(equipment_id=len(equipment) + 1, branch_id=b[0], equipment_name=name, quantity=qty,
                              condition_status=cond, last_serviced_on=rdate(dt.date(2026, 3, 1), TODAY - dt.timedelta(days=5))))

# --------------------------------------------- facilities per branch
branch_fac = []
NOTES = {10: "Extra charge Rs 200 per visit on weekdays", 11: "Extra charge Rs 150 per visit on weekdays",
         12: "Booking required, 45-minute slots", 7: "Women-only batch 10:00-12:00", 16: "Parking space limited"}
for b in BRANCH_DEFS:
    fac = set(CORE_FAC)
    extra = random.sample([f for f in range(1, 17) if f not in fac], random.randint(4, 9))
    fac.update(extra)
    for f in sorted(fac):
        note = NOTES.get(f, "") if random.random() < 0.5 else ""
        if f == 7 and random.random() < 0.4:
            note = "Women-only batch 10:00-12:00"
        branch_fac.append(dict(branch_id=b[0], facility_id=f, availability_notes=note))

# ------------------------------------------------------------ audit log
audit = []
for r in refunds:
    if r["status"] in ("approved", "completed", "rejected"):
        org = BR_ORG[next(p for p in payments if p["payment_id"] == r["payment_id"])["branch_id"]]
        audit.append(dict(user_id=owner_uid[org], action="REFUND_" + r["status"].upper(), table_name="REFUNDS",
                          record_id=r["refund_id"], old_value=json.dumps({"status": "requested"}),
                          new_value=json.dumps({"status": r["status"], "amount": money(r["refund_amount"])}),
                          created_at=dt.datetime.combine(r["refund_date"], dt.time(15, 0))))
for e in random.sample([e for e in expenses if e["status"] == "rejected"], min(10, sum(1 for e in expenses if e["status"] == "rejected"))):
    audit.append(dict(user_id=owner_uid[BR_ORG[e["branch_id"]]], action="EXPENSE_REJECTED", table_name="EXPENSES",
                      record_id=e["expense_id"], old_value=json.dumps({"status": "pending"}),
                      new_value=json.dumps({"status": "rejected"}),
                      created_at=dt.datetime.combine(e["expense_date"] + dt.timedelta(days=2), dt.time(11, 0))))
audit.sort(key=lambda a: a["created_at"])
for i, a in enumerate(audit, 1):
    a["audit_id"] = i


# --------------------------------------------------------------- writers
def write(name, header, rows):
    with open(os.path.join(OUT, name + ".csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)
    return len(rows)


counts = {}
counts["organizations"] = write("organizations", ["organization_id", "name", "contact_email", "status", "brand_type", "headquarters_city", "created_at"],
                                [[o[0], o[1], o[2], o[3], o[4], o[5], fd(o[7])] for o in ORGS])
counts["branches"] = write("branches", ["branch_id", "organization_id", "name", "address", "city", "state", "pincode", "latitude", "longitude", "phone", "description", "capacity"],
                           [[b[0], b[1], b[2], b[3], b[4], b[5], b[6], f"{b[7] + random.uniform(-0.001, 0.001):.6f}", f"{b[8] + random.uniform(-0.001, 0.001):.6f}",
                             phone(), f"{b[2]} - a {'flagship ' if b[9] >= 140 else ''}fitness centre in {b[3].split(',')[-1].strip()}, {b[4]}.", b[9]] for b in BRANCH_DEFS])
bh_rows = []
for b in BRANCH_DEFS:
    for dow in range(7):
        o, c = BH[b[0]][dow]
        bh_rows.append([b[0], dow, o.strftime("%H:%M:%S"), c.strftime("%H:%M:%S"), 0])
counts["branch_hours"] = write("branch_hours", ["branch_id", "day_of_week_0_mon", "open_time", "close_time", "is_closed"], bh_rows)
counts["facilities"] = write("facilities", ["facility_id", "facility_name", "description"], [[i + 1, f[0], f[1]] for i, f in enumerate(FACILITIES)])
counts["branch_facilities"] = write("branch_facilities", ["branch_id", "facility_id", "availability_notes"],
                                    [[r["branch_id"], r["facility_id"], r["availability_notes"]] for r in branch_fac])
counts["users"] = write("users", ["user_id", "email", "password_hash", "role", "is_active", "created_at", "last_login"],
                        [[u["user_id"], u["email"], u["password_hash"], u["role"], u["is_active"], fdt(u["created_at"]),
                          fdt(u["last_login"]) if u["last_login"] else ""] for u in users])
counts["staff"] = write("staff", ["staff_id", "user_id", "organization_id", "branch_id", "job_role", "full_name", "phone", "status", "hired_date"],
                        [[s["staff_id"], s["user_id"], s["organization_id"], s["branch_id"], s["job_role"], s["full_name"], s["phone"], s["status"], fd(s["hired_date"])] for s in staff])
counts["members"] = write("members", ["member_id", "user_id", "home_branch_id", "full_name", "phone", "registration_date"],
                          [[r["member_id"], r["user_id"], r["home_branch_id"], r["full_name"], r["phone"], fd(r["registration_date"])] for r in member_rows])
counts["membership_plans"] = write("membership_plans", ["plan_id", "organization_id", "plan_name", "duration_months", "price", "description"],
                                   [[p["plan_id"], p["organization_id"], p["plan_name"], p["duration_months"], money(p["price"]), p["description"]] for p in plans])
counts["branch_access_rules"] = write("branch_access_rules", ["access_rule_id", "plan_id", "branch_id", "access_type", "conditions"],
                                      [[r["access_rule_id"], r["plan_id"], r["branch_id"], r["access_type"], r["conditions"]] for r in access_rules])
counts["memberships"] = write("memberships", ["membership_id", "member_id", "plan_id", "start_date", "end_date", "status"],
                              [[x["membership_id"], x["member_id"], x["plan_id"], fd(x["start_date"]), fd(x["end_date"]), x["status"]] for x in memberships])
counts["invoices"] = write("invoices", ["invoice_id", "invoice_number", "member_id", "membership_id", "invoice_date", "due_date", "total", "status"],
                           [[i["invoice_id"], i["invoice_number"], i["member_id"], i["membership_id"], fd(i["invoice_date"]), fd(i["due_date"]), money(i["total"]), i["status"]] for i in invoices])
counts["invoice_items"] = write("invoice_items", ["invoice_item_id", "invoice_id", "description", "quantity", "unit_price", "line_total"],
                                [[i["invoice_item_id"], i["invoice_id"], i["description"], i["quantity"], i["unit_price"], i["line_total"]] for i in items])
counts["payments"] = write("payments", ["payment_id", "membership_id", "invoice_id", "branch_id", "amount", "payment_date", "payment_method", "payment_status", "transaction_ref"],
                           [[p["payment_id"], p["membership_id"], p["invoice_id"], p["branch_id"], money(p["amount"]), fdt(p["payment_date"]), p["payment_method"], p["payment_status"], p["ref"]] for p in payments])
counts["refunds"] = write("refunds", ["refund_id", "payment_id", "refund_amount", "refund_date", "reason", "status"],
                          [[r["refund_id"], r["payment_id"], money(r["refund_amount"]), fd(r["refund_date"]), r["reason"], r["status"]] for r in refunds])
counts["expense_categories"] = write("expense_categories", ["expense_category_id", "category_name", "description"], [[i + 1, c[0], c[1]] for i, c in enumerate(CATS)])
counts["expenses"] = write("expenses", ["expense_id", "branch_id", "expense_category_id", "recorded_by", "expense_date", "amount", "vendor", "description", "status"],
                           [[e["expense_id"], e["branch_id"], e["expense_category_id"], e["recorded_by"], fd(e["expense_date"]), money(e["amount"]), e["vendor"], e["description"], e["status"]] for e in expenses])
counts["branch_budgets"] = write("branch_budgets", ["budget_id", "branch_id", "expense_category_id", "budget_period", "budget_amount"],
                                 [[b["budget_id"], b["branch_id"], b["expense_category_id"], b["budget_period"], money(b["budget_amount"])] for b in budgets])
counts["attendance"] = write("attendance", ["attendance_id", "member_id", "branch_id", "check_in", "check_out"],
                             [[a["attendance_id"], a["member_id"], a["branch_id"], fdt(a["check_in"]), fdt(a["check_out"]) if a["check_out"] else ""] for a in attendance])
counts["trainers"] = write("trainers", ["trainer_id", "organization_id", "staff_id", "user_id", "full_name", "specialization", "phone"],
                           [[t["trainer_id"], t["organization_id"], t["staff_id"], t["user_id"], t["full_name"], t["specialization"], t["phone"]] for t in trainers])
counts["trainer_assignments"] = write("trainer_assignments", ["assignment_id", "trainer_id", "branch_id", "start_date", "end_date"],
                                      [[a["assignment_id"], a["trainer_id"], a["branch_id"], fd(a["start_date"]), fd(a["end_date"]) if a["end_date"] else ""] for a in trainer_assign])
counts["training_sessions"] = write("training_sessions", ["session_id", "member_id", "trainer_id", "branch_id", "session_start", "duration_minutes", "status", "focus"],
                                    [[s["session_id"], s["member_id"], s["trainer_id"], s["branch_id"], fdt(s["session_start"]), s["duration_minutes"], s["status"], s["focus"]] for s in sessions])
counts["equipment"] = write("equipment", ["equipment_id", "branch_id", "equipment_name", "quantity", "condition_status", "last_serviced_on"],
                            [[e["equipment_id"], e["branch_id"], e["equipment_name"], e["quantity"], e["condition_status"], fd(e["last_serviced_on"])] for e in equipment])
counts["audit_log"] = write("audit_log", ["audit_id", "user_id", "action", "table_name", "record_id", "old_value", "new_value", "created_at"],
                            [[a["audit_id"], a["user_id"], a["action"], a["table_name"], a["record_id"], a["old_value"], a["new_value"], fdt(a["created_at"])] for a in audit])

demo_rows = [
    ["admin.demo@" + DEMO_DOMAIN, "admin", "Platform administrator: approvals, platform stats, DBMS Lab"],
    ["owner.ironpulse.demo@" + DEMO_DOMAIN, "owner", "Owner of IronPulse Fitness (org 1, 6 branches)"],
    ["owner.flexnation.demo@" + DEMO_DOMAIN, "owner", "Owner of FlexNation Gyms (org 2) - use for cross-tenant isolation tests"],
    ["owner.aarogya.demo@" + DEMO_DOMAIN, "owner", "Owner of Aarogya Active Club (org 3, Jaipur)"],
    ["owner.sundarban.demo@" + DEMO_DOMAIN, "owner", "Owner of Sundarban Strength House (org 4, Kolkata)"],
    ["owner.zenith.demo@" + DEMO_DOMAIN, "owner", "Owner of Zenith Strength Lab - organization is PENDING admin approval"],
    ["manager.demo@" + DEMO_DOMAIN, "staff:BRANCH_MANAGER", "Branch manager, IronPulse Saket (branch 1)"],
    ["frontdesk.demo@" + DEMO_DOMAIN, "staff:FRONT_DESK", "Front desk, IronPulse Saket (branch 1)"],
    ["trainer.demo@" + DEMO_DOMAIN, "staff:TRAINER", "Trainer, IronPulse Saket (branch 1)"],
    ["finance.demo@" + DEMO_DOMAIN, "staff:FINANCE", "Finance officer, IronPulse Fitness (org-wide)"],
    ["member.demo@" + DEMO_DOMAIN, "member", "Rohan Malhotra - Annual All-Access (FULL access), home IronPulse Saket"],
    ["member.monthly.demo@" + DEMO_DOMAIN, "member", "Priya Deshmukh - Monthly Flex (HOME_ONLY), home FlexNation Baner - shows DENIED at other branches"],
    ["member.expired.demo@" + DEMO_DOMAIN, "member", "Imran Qureshi - membership EXPIRED 2026-08-31 - shows DENIED everywhere"],
]
write("demo_accounts", ["email", "role", "description"], demo_rows)

# ------------------------------------------------------------ validation
report = []
ok_all = True


def check(label, cond, detail=""):
    global ok_all
    ok_all &= bool(cond)
    report.append(f"[{'PASS' if cond else 'FAIL'}] {label} {detail}")


uids = {u["user_id"] for u in users}
check("User count within 500-1000", 500 <= len(users) <= 1000, f"({len(users)})")
check("Emails unique", len({u["email"] for u in users}) == len(users))
check("members.user_id FK", all(r["user_id"] in uids for r in member_rows))
check("staff.user_id FK", all(s["user_id"] in uids for s in staff))
pids = {p["payment_id"] for p in payments}
check("refunds.payment_id FK", all(r["payment_id"] in pids for r in refunds))
check("memberships.member_id/plan FK", all(x["member_id"] in MEMBER and x["plan_id"] in PLAN for x in memberships))
check("memberships: end >= start", all(x["end_date"] >= x["start_date"] for x in memberships))
ok_overlap = True
for mid, lst in ms_by_member.items():
    lst2 = sorted(lst, key=lambda x: x["start_date"])
    for a, b in zip(lst2, lst2[1:]):
        if b["start_date"] <= a["end_date"]:
            ok_overlap = False
check("No overlapping memberships per member", ok_overlap)
item_sum = defaultdict(float)
for it in items:
    item_sum[it["invoice_id"]] += float(it["line_total"])
check("invoice total = SUM(items)", all(abs(item_sum[i["invoice_id"]] - i["total"]) < 0.011 for i in invoices))
ref_sum = defaultdict(float)
for r in refunds:
    ref_sum[r["payment_id"]] += r["refund_amount"]
pay_amt = {p["payment_id"]: p["amount"] for p in payments}
check("SUM(refunds) <= payment amount", all(ref_sum[k] <= pay_amt[k] + 0.001 for k in ref_sum))
check("amounts > 0", all(p["amount"] > 0 for p in payments) and all(e["amount"] > 0 for e in expenses) and all(b["budget_amount"] > 0 for b in budgets))
ms_ok = True
for a in attendance:
    if a["check_out"] and a["check_out"] <= a["check_in"]:
        ms_ok = False
check("attendance check_out > check_in", ms_ok)
rng_ok = True
for a in attendance[:]:
    lst = [x for x in ms_by_member[a["member_id"]] if x["status"] in ("active", "expired")]
    if not any(x["start_date"] <= a["check_in"].date() <= x["end_date"] for x in lst):
        rng_ok = False
        break
check("attendance only inside an active/expired membership period", rng_ok)
hrs_ok = True
for a in attendance:
    o, c = BH[a["branch_id"]][a["check_in"].weekday()]
    if not (o <= a["check_in"].time() <= c):
        hrs_ok = False
        break
check("attendance inside branch opening hours", hrs_ok)
check("sessions trainer/branch consistent", all(any(t["trainer_id"] == s["trainer_id"] and t["branch"] == s["branch_id"] for t in trainers) for s in sessions))
check("expenses.recorded_by FK", all(e["recorded_by"] in uids for e in expenses))
check("budget (branch, category, period) unique", len({(b["branch_id"], b["expense_category_id"], b["budget_period"]) for b in budgets}) == len(budgets))
check("every live org has a finance user", all(o in finance_user for o in (1, 2, 3, 4)))
st = Counter(x["status"] for x in memberships)
report.append("Membership status mix: " + ", ".join(f"{k}={v}" for k, v in sorted(st.items())))
inside = sum(1 for a in attendance if a["check_out"] is None)
report.append(f"Members currently inside (NULL check_out): {inside}")
over = 0
for b in budgets:
    if actual.get((b["branch_id"], b["expense_category_id"], b["budget_period"]), 0) > b["budget_amount"]:
        over += 1
report.append(f"Budget rows overspent: {over} of {len(budgets)}")
gross = sum(p["amount"] for p in payments if p["payment_status"] == "successful")
refd = sum(r["refund_amount"] for r in refunds if r["status"] == "completed")
report.append(f"Gross receipts Rs {gross:,.0f}; completed refunds Rs {refd:,.0f}; net receipts Rs {gross - refd:,.0f}")
report.append("OVERALL: " + ("ALL CHECKS PASSED" if ok_all else "SOME CHECKS FAILED"))
with open(os.path.join(OUT, "validation_report.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(report) + "\n")

# ---------------------------------------------------------------- README
load_order = ["organizations", "branches", "branch_hours", "facilities", "branch_facilities", "users", "staff", "trainers",
              "trainer_assignments", "members", "membership_plans", "branch_access_rules", "memberships", "invoices",
              "invoice_items", "payments", "refunds", "expense_categories", "expenses", "branch_budgets", "attendance",
              "training_sessions", "equipment", "audit_log"]
readme = f"""# Jaskr GymGrid - Seed Dataset (fictional)

All people, phone numbers, emails, businesses and transactions in this dataset are FICTIONAL and generated by `seed_data.py`
(seed {SEED}). Snapshot date: {TODAY} (10:00). Currency: INR (Rs). GST on membership fees: 18% (shown as an invoice line).

## Size
Users: {len(users)} (1 platform admin, 5 owners, {len(staff) - 6} staff, {len(members)} members) | Branches: {len(BRANCH_DEFS)} in 11 Indian cities |
Organizations: 5 (4 active, 1 pending approval)

| Table | Rows |
|---|---|
""" + "\n".join(f"| {k} | {v:,} |" for k, v in counts.items()) + f"""

## Load order (respects foreign keys)
{" -> ".join(load_order)}
(Nullable circular-free; `staff.organization_id` / `staff.branch_id` are empty for the platform admin, owners and finance officers.)

## Conventions and rules the app must honour
- `users.password_hash` contains the placeholder `{PLACEHOLDER_HASH}`. The loader must replace it with a real hash (bcrypt/argon2) of the
  demo password `{DEMO_PASSWORD}` (all accounts share it; DEMO_MODE only).
- Empty CSV cells = NULL (e.g. `attendance.check_out` empty = member still inside; `trainer_assignments.end_date` empty = current).
- `branch_hours.day_of_week_0_mon`: 0 = Monday ... 6 = Sunday.
- `branch_access_rules.access_type` semantics (the Access Checker must implement them):
  - `HOME_ONLY`: allowed only if the branch equals the member's `home_branch_id`.
  - `SAME_CITY`: allowed at branches whose city equals the city of the member's home branch.
  - `WEEKDAYS_ONLY`: allowed at every branch of the organization, Monday-Friday only.
  - `FULL`: allowed at every branch of the organization during opening hours.
  - A plan can only reach branches of its own organization.
- `memberships.status`: active | expired | cancelled | pending (unpaid). Only active/expired memberships have attendance and sessions.
- `invoices.status`: paid | pending | overdue | refunded. `payments.payment_status`: successful | pending | failed.
  `refunds.status`: requested | approved | completed | rejected. `expenses.status`: paid | approved | pending | rejected.
- Metrics: gross receipts = successful payments; refunds = completed refunds; net receipts = gross - refunds;
  operating expenses = expenses with status paid/approved. Budget variance = budget - actual, per branch/category/`budget_period` (YYYY-MM).
- Owners and the platform admin also appear in `staff` (job_role OWNER / PLATFORM_ADMIN) so organization scoping is uniform.
- `trainers` carries `staff_id`/`user_id` and also `full_name`/`phone` (as in the proposal). For strict 3NF, drop the duplicates and read them via `staff`.
- Extra columns beyond the proposal: `branches.(state,pincode,latitude,longitude,phone,description)`, `payments.(invoice_id,transaction_ref)`,
  `invoices.invoice_number`, `membership_plans.description`, `equipment.last_serviced_on`, `training_sessions.focus`,
  `organizations.(brand_type,headquarters_city,created_at)`, `users.(is_active,created_at,last_login)`.
- Attendance history covers {ATT_START} to {TODAY}; use an 8-week lookback for crowd estimates (shows day/hour peaks).
- Deliberate test cases: a few payments have two partial refunds (sum <= payment), failed payment attempts followed by success, pending/overdue
  invoices, deliberately overspent budgets, equipment needing service, an organization pending approval.

## Demo accounts (password `{DEMO_PASSWORD}`)
""" + "\n".join(f"- `{r[0]}` ({r[1]}): {r[2]}" for r in demo_rows) + """

## Regenerate
`python seed_data.py [output_dir]` (Python 3.8+, no third-party packages). Output is deterministic.
"""
with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8") as f:
    f.write(readme)

print("\n".join(report))
print({k: v for k, v in counts.items()})
