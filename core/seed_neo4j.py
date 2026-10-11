"""
core/seed_neo4j.py  —  Seeds Neo4j with the FCC Unit MoC + WO dataset.
Run once:  python -m core.seed_neo4j
       or: PYTHONPATH=. python core/seed_neo4j.py
"""
import os
import sys

# Allow `python core/seed_neo4j.py` from repo root
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from neo4j import GraphDatabase
from core.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

PLANT = {"id": "REFINERY_A", "name": "Refinery A"}
PROCESS_UNIT = {"id": "FCC_UNIT", "name": "FCC Unit"}

AREAS = [
    {"id": "FEED_PREP",  "name": "Feed Preparation"},
    {"id": "REACTOR",    "name": "Reactor/Riser System"},
    {"id": "CAT_STRIP",  "name": "Catalyst Stripping"},
    {"id": "CAT_REGEN",  "name": "Catalyst Regeneration"},
    {"id": "PROD_RECOV", "name": "Product Recovery/Fractionation"},
    {"id": "ENTIRE_FCC", "name": "Entire FCC Unit"},
]

ASSETS = [
    {"id": "P-101",   "name": "Feed Pump",             "equipment_type": "Pump",             "area_id": "FEED_PREP",  "criticality": 4, "pid_reference": "PID-FCC-101"},
    {"id": "FV-103",  "name": "Feed Control Valve",    "equipment_type": "Control Valve",    "area_id": "FEED_PREP",  "criticality": 3, "pid_reference": "PID-FCC-103"},
    {"id": "R-201",   "name": "Riser Reactor",         "equipment_type": "Reactor",          "area_id": "REACTOR",    "criticality": 5, "pid_reference": "PID-FCC-201"},
    {"id": "C-203",   "name": "Cyclone Separator",     "equipment_type": "Cyclone Separator","area_id": "REACTOR",    "criticality": 4, "pid_reference": "PID-FCC-203"},
    {"id": "SV-204",  "name": "Catalyst Slide Valve",  "equipment_type": "Control Valve",    "area_id": "REACTOR",    "criticality": 5, "pid_reference": "PID-FCC-204"},
    {"id": "S-301",   "name": "Catalyst Stripper",     "equipment_type": "Control Valve",    "area_id": "CAT_STRIP",  "criticality": 4, "pid_reference": "PID-FCC-301"},
    {"id": "EX-403",  "name": "Flue Gas Expander",     "equipment_type": "Flue gas expander","area_id": "CAT_REGEN",  "criticality": 3, "pid_reference": "PID-FCC-403"},
    {"id": "P-502",   "name": "Reflux Pump",           "equipment_type": "Pump",             "area_id": "PROD_RECOV", "criticality": 4, "pid_reference": "PID-FCC-502"},
    {"id": "ESD",     "name": "ESD System",            "equipment_type": "Procedure",        "area_id": "ENTIRE_FCC", "criticality": 3, "pid_reference": "N/A"},
    {"id": "CTL-205", "name": "Catalyst Transfer Line","equipment_type": "Piping",           "area_id": "REACTOR",    "criticality": 5, "pid_reference": "PID-FCC-LINE"},
    {"id": "RG-401",  "name": "Regenerator",           "equipment_type": "Reactor",          "area_id": "CAT_REGEN",  "criticality": 5, "pid_reference": "PID-FCC-401"},
    {"id": "F-501",   "name": "Main Fractionator",     "equipment_type": "Fractionator",     "area_id": "PROD_RECOV", "criticality": 5, "pid_reference": "PID-FCC-501"},
    {"id": "WGC-401", "name": "Wet Gas Compressor",    "equipment_type": "Compressor",       "area_id": "PROD_RECOV", "criticality": 5, "pid_reference": "PID-FCC-WGC"},
    {"id": "K-402",   "name": "Air Blower",            "equipment_type": "Compressor",       "area_id": "CAT_REGEN",  "criticality": 4, "pid_reference": "PID-FCC-402"},
]

DEPENDENCIES = [
    ("P-101","R-201"), ("FV-103","R-201"), ("R-201","C-203"), ("R-201","SV-204"),
    ("C-203","RG-401"), ("SV-204","RG-401"), ("S-301","RG-401"), ("RG-401","EX-403"),
    ("RG-401","CTL-205"), ("CTL-205","R-201"), ("R-201","F-501"), ("F-501","WGC-401"),
    ("F-501","P-502"), ("WGC-401","R-201"), ("K-402","RG-401"),
]

MOCS = [
    {"id":"MoC-001","title":"Feed Pump (P-101) Replacement",
     "description":"Replace failing feed pump P-101 with upgraded unit to improve reliability and efficiency",
     "reason":"Vibration, performance decline, and need for improved flow stability",
     "change_type":"Mechanical","asset_id":"P-101","risk_level":"High","overall_risk_score":12,
     "risk_people":3,"risk_asset":4,"risk_community":2,"risk_env":2,"risk_likelihood":3,
     "hazop_required":False,"pssr_required":True,"estimated_cost":120000,"actual_cost":118000,
     "estimated_downtime":0,"actual_downtime":0,"incident_occurred":False,"incident_description":"",
     "lessons_learned":"Improved pump reliability and stable operation",
     "hazard_description":"Feed flow instability leading to reactor temperature excursions",
     "approver_role":"Safety Manager","date_initiated":"2025-01-10","work_orders":["WO-001","WO-002"]},
    {"id":"MoC-002","title":"Feed Heater Control Valve (FV-103) Upgrade",
     "description":"Replace FV-103 with smart control valve to improve temperature regulation accuracy and enable remote monitoring",
     "reason":"Inconsistent control performance and need for improved temperature stability",
     "change_type":"Instrumentation","asset_id":"FV-103","risk_level":"Medium","overall_risk_score":8,
     "risk_people":3,"risk_asset":4,"risk_community":2,"risk_env":2,"risk_likelihood":2,
     "hazop_required":True,"pssr_required":True,"estimated_cost":35000,"actual_cost":36500,
     "estimated_downtime":8,"actual_downtime":9,"incident_occurred":False,"incident_description":"",
     "lessons_learned":"Enhanced temperature control after tuning stabilization",
     "hazard_description":"Loss of temperature control causing reactor instability",
     "approver_role":"Safety Manager","date_initiated":"2025-02-03","work_orders":["WO-003","WO-004"]},
    {"id":"MoC-003","title":"Reactor R-201 Temperature Setpoint Adjustment",
     "description":"Adjust reactor temperature setpoint from 510C to 525C to optimise catalyst performance and improve gasoline yield",
     "reason":"Need to improve catalyst activity and process efficiency",
     "change_type":"Process Parameter","asset_id":"R-201","risk_level":"Medium","overall_risk_score":8,
     "risk_people":4,"risk_asset":4,"risk_community":2,"risk_env":2,"risk_likelihood":2,
     "hazop_required":True,"pssr_required":True,"estimated_cost":8000,"actual_cost":7500,
     "estimated_downtime":0,"actual_downtime":0,"incident_occurred":False,"incident_description":"",
     "lessons_learned":"Improved yield with stable thermal control",
     "hazard_description":"Reactor over-temperature and catalyst degradation",
     "approver_role":"Process Safety Manager","date_initiated":"2025-03-05","work_orders":["WO-005","WO-006"]},
    {"id":"MoC-004","title":"Cyclone Separator (C-203) Internal Inspection and Repair",
     "description":"Inspect and repair cyclone internals to restore catalyst separation efficiency after erosion damage",
     "reason":"Erosion damage causing catalyst losses and reduced efficiency",
     "change_type":"Mechanical Maintenance","asset_id":"C-203","risk_level":"High","overall_risk_score":12,
     "risk_people":3,"risk_asset":4,"risk_community":2,"risk_env":3,"risk_likelihood":3,
     "hazop_required":False,"pssr_required":True,"estimated_cost":95000,"actual_cost":102000,
     "estimated_downtime":48,"actual_downtime":52,"incident_occurred":False,"incident_description":"",
     "lessons_learned":"Restored separation efficiency and reduced losses",
     "hazard_description":"Catalyst carryover and loss of separation efficiency",
     "approver_role":"Maintenance Manager","date_initiated":"2025-04-01","work_orders":["WO-007","WO-008"]},
    {"id":"MoC-005","title":"Catalyst Slide Valve (SV-204) Control System Upgrade",
     "description":"Upgrade slide valve actuator from basic pneumatic to advanced actuator with feedback to improve catalyst circulation control",
     "reason":"Need for improved catalyst flow control and reactor-regenerator balance",
     "change_type":"Instrumentation","asset_id":"SV-204","risk_level":"High","overall_risk_score":12,
     "risk_people":4,"risk_asset":4,"risk_community":2,"risk_env":2,"risk_likelihood":3,
     "hazop_required":True,"pssr_required":True,"estimated_cost":65000,"actual_cost":67500,
     "estimated_downtime":24,"actual_downtime":26,"incident_occurred":False,"incident_description":"",
     "lessons_learned":"Improved catalyst circulation and process stability",
     "hazard_description":"Uncontrolled catalyst circulation causing thermal imbalance",
     "approver_role":"Process Safety Manager","date_initiated":"2025-05-06","work_orders":["WO-009","WO-010"]},
    {"id":"MoC-006","title":"Catalyst Stripper Steam Optimization",
     "description":"Install steam control valve and optimise steam injection rate from 12000 to 15000 kg/h to improve stripping efficiency",
     "reason":"Improve stripping efficiency and reduce hydrocarbon carryover",
     "change_type":"Process & Instrumentation","asset_id":"S-301","risk_level":"High","overall_risk_score":12,
     "risk_people":3,"risk_asset":4,"risk_community":2,"risk_env":3,"risk_likelihood":3,
     "hazop_required":True,"pssr_required":True,"estimated_cost":85000,"actual_cost":92000,
     "estimated_downtime":6,"actual_downtime":8,"incident_occurred":True,
     "incident_description":"Steam leakage at flange during commissioning due to improper gasket installation",
     "lessons_learned":"Steam leakage incident required improved flange installation and inspection procedures",
     "hazard_description":"Improper stripping leading to regenerator instability and emissions",
     "approver_role":"Process Safety Manager","date_initiated":"2025-03-03","work_orders":["WO-011","WO-012"]},
    {"id":"MoC-007","title":"Flue Gas Expander (EX-403) Performance Upgrade",
     "description":"Upgrade expander blades and seals to improve energy recovery from 9500kW to 10500kW output",
     "reason":"Low efficiency and opportunity for improved energy recovery",
     "change_type":"Mechanical Efficiency Improvement","asset_id":"EX-403","risk_level":"Medium","overall_risk_score":8,
     "risk_people":3,"risk_asset":4,"risk_community":2,"risk_env":3,"risk_likelihood":2,
     "hazop_required":False,"pssr_required":True,"estimated_cost":60000,"actual_cost":78000,
     "estimated_downtime":24,"actual_downtime":30,"incident_occurred":True,
     "incident_description":"Temporary misalignment caused trip and flaring during commissioning",
     "lessons_learned":"Temporary misalignment caused trip; improved alignment procedures implemented",
     "hazard_description":"Expander trip causing regenerator overpressure",
     "approver_role":"Maintenance Manager","date_initiated":"2025-04-10","work_orders":["WO-013","WO-014"]},
    {"id":"MoC-008","title":"Fractionator Reflux Pump Replacement",
     "description":"Replace reflux pump P-502 to improve reliability and stabilize fractionation process after frequent bearing and seal failures",
     "reason":"Frequent failures affecting separation performance",
     "change_type":"Mechanical","asset_id":"P-502","risk_level":"High","overall_risk_score":12,
     "risk_people":3,"risk_asset":4,"risk_community":2,"risk_env":2,"risk_likelihood":3,
     "hazop_required":True,"pssr_required":True,"estimated_cost":120000,"actual_cost":135000,
     "estimated_downtime":14,"actual_downtime":16,"incident_occurred":True,
     "incident_description":"Alignment issues delayed startup requiring soft-foot adjustment",
     "lessons_learned":"Alignment issues required improved installation and startup procedures",
     "hazard_description":"Reflux instability causing poor separation and temperature excursions",
     "approver_role":"Maintenance Manager","date_initiated":"2025-09-20","work_orders":["WO-015","WO-016"]},
    {"id":"MoC-009","title":"Emergency Shutdown Procedure Update",
     "description":"Revise FCC emergency shutdown procedure and train operators to improve response coordination and communication",
     "reason":"Improve response coordination and communication following safety audit",
     "change_type":"Procedural","asset_id":"ESD","risk_level":"High","overall_risk_score":10,
     "risk_people":5,"risk_asset":3,"risk_community":3,"risk_env":3,"risk_likelihood":2,
     "hazop_required":True,"pssr_required":True,"estimated_cost":20000,"actual_cost":22000,
     "estimated_downtime":0,"actual_downtime":0,"incident_occurred":False,"incident_description":"",
     "lessons_learned":"Improved emergency preparedness and response coordination",
     "hazard_description":"Delayed or incorrect emergency response",
     "approver_role":"HSE Manager","date_initiated":"2024-02-18","work_orders":["WO-017","WO-018"]},
    {"id":"MoC-010","title":"Catalyst Transfer Line Reinforcement",
     "description":"Reinforce catalyst transfer line CTL-205 with high-temperature resistant material to prevent failure from wall thinning",
     "reason":"Material degradation and wall thinning identified from catalyst erosion",
     "change_type":"Mechanical Integrity Improvement","asset_id":"CTL-205","risk_level":"High","overall_risk_score":15,
     "risk_people":4,"risk_asset":5,"risk_community":2,"risk_env":3,"risk_likelihood":3,
     "hazop_required":True,"pssr_required":True,"estimated_cost":150000,"actual_cost":165000,
     "estimated_downtime":22,"actual_downtime":25,"incident_occurred":True,
     "incident_description":"Weld defect detected during radiography inspection required rework",
     "lessons_learned":"Weld defect required rework; improved welding and inspection procedures implemented",
     "hazard_description":"Line failure causing catalyst loss and process shutdown",
     "approver_role":"Maintenance Manager","date_initiated":"2024-11-12","work_orders":["WO-019","WO-020","WO-021"]},
]

WORK_ORDERS = [
    {"id":"WO-001","moc_id":"MoC-001","title":"Remove existing P-101 feed pump for replacement",
     "work_type":"Corrective Maintenance","priority":"Medium","asset_id":"P-101",
     "planned_hrs":8,"actual_hrs":10,"estimated_cost":45000,"actual_cost":47000,
     "status":"Completed","delay_reason":"Isolation valve required additional sealing"},
    {"id":"WO-002","moc_id":"MoC-001","title":"Install replacement P-101 feed pump and reconnect piping",
     "work_type":"Corrective Maintenance","priority":"Medium","asset_id":"P-101",
     "planned_hrs":12,"actual_hrs":14,"estimated_cost":75000,"actual_cost":79000,
     "status":"Completed","delay_reason":"Alignment adjustment required after installation"},
    {"id":"WO-003","moc_id":"MoC-002","title":"Remove existing FV-103 feed heater control valve",
     "work_type":"Corrective Maintenance","priority":"Medium","asset_id":"FV-103",
     "planned_hrs":3,"actual_hrs":4,"estimated_cost":12000,"actual_cost":12400,
     "status":"Completed","delay_reason":"Additional isolation work required"},
    {"id":"WO-004","moc_id":"MoC-002","title":"Install smart control valve FV-103 and calibrate instrumentation",
     "work_type":"Modification","priority":"Medium","asset_id":"FV-103",
     "planned_hrs":5,"actual_hrs":5,"estimated_cost":23000,"actual_cost":24100,
     "status":"Completed","delay_reason":"Loop calibration required additional fine-tuning"},
    {"id":"WO-005","moc_id":"MoC-003","title":"Update R-201 reactor temperature setpoint in control system",
     "work_type":"Modification","priority":"Medium","asset_id":"R-201",
     "planned_hrs":4,"actual_hrs":4,"estimated_cost":3500,"actual_cost":3500,
     "status":"Completed","delay_reason":"No delay"},
    {"id":"WO-006","moc_id":"MoC-003","title":"Verify R-201 reactor operating limits and confirm safe operation",
     "work_type":"Inspection","priority":"Medium","asset_id":"R-201",
     "planned_hrs":8,"actual_hrs":9,"estimated_cost":4500,"actual_cost":4800,
     "status":"Completed","delay_reason":"Extended monitoring period required"},
    {"id":"WO-007","moc_id":"MoC-004","title":"Internal inspection of C-203 cyclone separator and erosion assessment",
     "work_type":"Inspection","priority":"High","asset_id":"C-203",
     "planned_hrs":18,"actual_hrs":20,"estimated_cost":28000,"actual_cost":31000,
     "status":"Completed","delay_reason":"Confined space entry preparation took longer than planned"},
    {"id":"WO-008","moc_id":"MoC-004","title":"Replace damaged cyclone separator C-203 internal components",
     "work_type":"Corrective Maintenance","priority":"High","asset_id":"C-203",
     "planned_hrs":30,"actual_hrs":32,"estimated_cost":67000,"actual_cost":71000,
     "status":"Completed","delay_reason":"Replacement vortex finder required custom fabrication"},
    {"id":"WO-009","moc_id":"MoC-005","title":"Remove existing pneumatic actuator from catalyst slide valve SV-204",
     "work_type":"Corrective Maintenance","priority":"High","asset_id":"SV-204",
     "planned_hrs":10,"actual_hrs":11,"estimated_cost":25000,"actual_cost":26000,
     "status":"Completed","delay_reason":"High-temperature component cooling required"},
    {"id":"WO-010","moc_id":"MoC-005","title":"Install advanced actuator on SV-204 and configure catalyst flow control",
     "work_type":"Modification","priority":"High","asset_id":"SV-204",
     "planned_hrs":14,"actual_hrs":15,"estimated_cost":40000,"actual_cost":41500,
     "status":"Completed","delay_reason":"DCS integration required additional loop testing"},
    {"id":"WO-011","moc_id":"MoC-006","title":"Install steam flow control valve on catalyst stripper S-301",
     "work_type":"Modification","priority":"Medium","asset_id":"S-301",
     "planned_hrs":2,"actual_hrs":3,"estimated_cost":35000,"actual_cost":38000,
     "status":"Completed","delay_reason":"Steam leakage at flange requiring gasket replacement"},
    {"id":"WO-012","moc_id":"MoC-006","title":"Commission and optimize steam flow control for catalyst stripper S-301",
     "work_type":"Modification","priority":"Medium","asset_id":"S-301",
     "planned_hrs":4,"actual_hrs":5,"estimated_cost":50000,"actual_cost":54000,
     "status":"Completed","delay_reason":"Suboptimal steam flow causing inefficient hydrocarbon stripping"},
    {"id":"WO-013","moc_id":"MoC-007","title":"EX-403 mechanical upgrade - blades and seals",
     "work_type":"Planned mechanical upgrade","priority":"Medium","asset_id":"EX-403",
     "planned_hrs":12,"actual_hrs":15,"estimated_cost":30000,"actual_cost":39000,
     "status":"Completed","delay_reason":"Rework after trip and extra alignment checks"},
    {"id":"WO-014","moc_id":"MoC-007","title":"EX-403 post-upgrade performance test and control tuning",
     "work_type":"Performance test","priority":"Medium","asset_id":"EX-403",
     "planned_hrs":12,"actual_hrs":15,"estimated_cost":30000,"actual_cost":39000,
     "status":"Completed","delay_reason":"Additional tuning and re-run after trip event"},
    {"id":"WO-015","moc_id":"MoC-008","title":"Remove failed reflux pump P-502",
     "work_type":"Corrective Maintenance","priority":"High","asset_id":"P-502",
     "planned_hrs":6,"actual_hrs":7,"estimated_cost":50000,"actual_cost":56000,
     "status":"Completed","delay_reason":"Stuck flange bolts increased removal time"},
    {"id":"WO-016","moc_id":"MoC-008","title":"Install replacement reflux pump and complete testing",
     "work_type":"Modification","priority":"High","asset_id":"P-502",
     "planned_hrs":8,"actual_hrs":9,"estimated_cost":70000,"actual_cost":79000,
     "status":"Completed","delay_reason":"Alignment correction and soft-foot adjustment required"},
    {"id":"WO-017","moc_id":"MoC-009","title":"Revise FCC emergency shutdown documentation",
     "work_type":"Administrative","priority":"High","asset_id":"ESD",
     "planned_hrs":4,"actual_hrs":4,"estimated_cost":9000,"actual_cost":10000,
     "status":"Completed","delay_reason":"Additional review comments incorporated before issue"},
    {"id":"WO-018","moc_id":"MoC-009","title":"Conduct operator training and emergency drill on revised ESD procedure",
     "work_type":"Administrative","priority":"High","asset_id":"ESD",
     "planned_hrs":6,"actual_hrs":6,"estimated_cost":11000,"actual_cost":12000,
     "status":"Completed","delay_reason":"Shift handover delayed final training session start"},
    {"id":"WO-019","moc_id":"MoC-010","title":"Remove worn catalyst transfer line section and prepare spool",
     "work_type":"Corrective Maintenance","priority":"High","asset_id":"CTL-205",
     "planned_hrs":6,"actual_hrs":7,"estimated_cost":40000,"actual_cost":45000,
     "status":"Completed","delay_reason":"Access scaffold adjustment delayed start"},
    {"id":"WO-020","moc_id":"MoC-010","title":"Install reinforced catalyst transfer line section and complete welding",
     "work_type":"Modification","priority":"High","asset_id":"CTL-205",
     "planned_hrs":10,"actual_hrs":11,"estimated_cost":80000,"actual_cost":87000,
     "status":"Completed","delay_reason":"Radiography identified a weld defect requiring repair"},
    {"id":"WO-021","moc_id":"MoC-010","title":"Perform NDT, leak test, and return reinforced line to service",
     "work_type":"Inspection","priority":"High","asset_id":"CTL-205",
     "planned_hrs":7,"actual_hrs":7,"estimated_cost":30000,"actual_cost":33000,
     "status":"Completed","delay_reason":"Extended hold-point checks before handover"},
]


def seed(clear=False):
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as s:
        if clear:
            s.run("MATCH (n) DETACH DELETE n")
            print("Cleared existing data.")

        # Constraints
        for label, prop in [("Plant","id"),("ProcessUnit","id"),("Area","id"),
                             ("Asset","id"),("MoC","id"),("WorkOrder","id"),("Approver","name")]:
            try:
                s.run(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE")
            except Exception:
                pass

        # Plant
        s.run("MERGE (p:Plant {id:$id}) SET p.name=$name", **PLANT)
        # ProcessUnit
        s.run("MERGE (u:ProcessUnit {id:$id}) SET u.name=$name", id=PROCESS_UNIT["id"], name=PROCESS_UNIT["name"])
        s.run("MATCH (u:ProcessUnit {id:$uid}),(p:Plant {id:$pid}) MERGE (u)-[:PART_OF]->(p)",
              uid=PROCESS_UNIT["id"], pid=PLANT["id"])
        # Areas
        for a in AREAS:
            s.run("MERGE (ar:Area {id:$id}) SET ar.name=$name", **a)
            s.run("MATCH (ar:Area {id:$aid}),(u:ProcessUnit {id:$uid}) MERGE (ar)-[:PART_OF]->(u)",
                  aid=a["id"], uid=PROCESS_UNIT["id"])
        # Assets
        for a in ASSETS:
            s.run("""MERGE (ast:Asset {id:$id})
                     SET ast.asset_id=$id, ast.name=$name, ast.equipment_type=$equipment_type,
                         ast.criticality=$criticality, ast.pid_reference=$pid_reference""",
                  id=a["id"], name=a["name"], equipment_type=a["equipment_type"],
                  criticality=a["criticality"], pid_reference=a["pid_reference"])
            s.run("MATCH (ast:Asset {id:$aid}),(ar:Area {id:$arid}) MERGE (ast)-[:BELONGS_TO]->(ar)",
                  aid=a["id"], arid=a["area_id"])
        # Dependencies
        for up, dn in DEPENDENCIES:
            s.run("""MATCH (a:Asset {id:$up}),(b:Asset {id:$dn})
                     MERGE (a)-[:UPSTREAM_OF]->(b)
                     MERGE (b)-[:DOWNSTREAM_OF]->(a)
                     MERGE (b)-[:DEPENDS_ON]->(a)""", up=up, dn=dn)
        # MoCs
        for m in MOCS:
            s.run("""MERGE (mc:MoC {id:$id})
                     SET mc.moc_id=$id, mc.title=$title, mc.description=$description,
                         mc.reason=$reason, mc.change_type=$change_type,
                         mc.risk_level=$risk_level, mc.overall_risk_score=$overall_risk_score,
                         mc.risk_people=$risk_people, mc.risk_asset=$risk_asset,
                         mc.risk_community=$risk_community, mc.risk_env=$risk_env,
                         mc.risk_likelihood=$risk_likelihood,
                         mc.hazop_required=$hazop_required, mc.pssr_required=$pssr_required,
                         mc.estimated_cost=$estimated_cost, mc.actual_cost=$actual_cost,
                         mc.estimated_downtime=$estimated_downtime, mc.actual_downtime=$actual_downtime,
                         mc.estimated_manhours=$estimated_downtime, mc.actual_manhours=$actual_downtime,
                         mc.incident_occurred=$incident_occurred,
                         mc.incident_description=$incident_description,
                         mc.lessons_learned=$lessons_learned,
                         mc.hazard_description=$hazard_description,
                         mc.date_initiated=$date_initiated""",
                  id=m["id"], title=m["title"], description=m["description"],
                  reason=m["reason"], change_type=m["change_type"],
                  risk_level=m["risk_level"], overall_risk_score=m["overall_risk_score"],
                  risk_people=m["risk_people"], risk_asset=m["risk_asset"],
                  risk_community=m["risk_community"], risk_env=m["risk_env"],
                  risk_likelihood=m["risk_likelihood"],
                  hazop_required=m["hazop_required"], pssr_required=m["pssr_required"],
                  estimated_cost=m["estimated_cost"], actual_cost=m["actual_cost"],
                  estimated_downtime=m["estimated_downtime"], actual_downtime=m["actual_downtime"],
                  incident_occurred=m["incident_occurred"],
                  incident_description=m["incident_description"],
                  lessons_learned=m["lessons_learned"],
                  hazard_description=m["hazard_description"],
                  date_initiated=m["date_initiated"])
            # TARGETS relationship
            s.run("MATCH (mc:MoC {id:$mid}),(a:Asset {id:$aid}) MERGE (mc)-[:TARGETS]->(a)",
                  mid=m["id"], aid=m["asset_id"])
            # Hazard node
            s.run("""MERGE (h:Hazard {id:$hid})
                     SET h.description=$desc, h.category='Process',
                         h.severity=$sev""",
                  hid=f"HAZ-{m['id']}", desc=m["hazard_description"],
                  sev=m["risk_level"])
            s.run("MATCH (mc:MoC {id:$mid}),(h:Hazard {id:$hid}) MERGE (mc)-[:IDENTIFIES]->(h)",
                  mid=m["id"], hid=f"HAZ-{m['id']}")
            # Approver node
            s.run("MERGE (ap:Approver {name:$role}) SET ap.role=$role",
                  role=m["approver_role"])
            s.run("MATCH (mc:MoC {id:$mid}),(ap:Approver {name:$role}) MERGE (mc)-[:APPROVED_BY]->(ap)",
                  mid=m["id"], role=m["approver_role"])
        # Work Orders
        for w in WORK_ORDERS:
            s.run("""MERGE (wo:WorkOrder {id:$id})
                     SET wo.wo_id=$id, wo.title=$title, wo.work_type=$work_type,
                         wo.priority=$priority, wo.planned_hrs=$planned_hrs,
                         wo.actual_hrs=$actual_hrs, wo.planned_duration=$planned_hrs,
                         wo.actual_duration=$actual_hrs,
                         wo.estimated_cost=$estimated_cost, wo.actual_cost=$actual_cost,
                         wo.status=$status, wo.delay_reason=$delay_reason""",
                  id=w["id"], title=w["title"], work_type=w["work_type"],
                  priority=w["priority"], planned_hrs=w["planned_hrs"],
                  actual_hrs=w["actual_hrs"], estimated_cost=w["estimated_cost"],
                  actual_cost=w["actual_cost"], status=w["status"],
                  delay_reason=w["delay_reason"])
            s.run("MATCH (wo:WorkOrder {id:$wid}),(mc:MoC {id:$mid}) MERGE (wo)-[:IMPLEMENTS]->(mc) MERGE (mc)-[:GENERATES]->(wo)",
                  wid=w["id"], mid=w["moc_id"])
            s.run("MATCH (wo:WorkOrder {id:$wid}),(a:Asset {id:$aid}) MERGE (wo)-[:EXECUTED_ON]->(a)",
                  wid=w["id"], aid=w["asset_id"])

    driver.close()
    print(f"Seeded: {len(ASSETS)} assets, {len(MOCS)} MoCs, {len(WORK_ORDERS)} work orders.")


if __name__ == "__main__":
    import sys
    clear = "--clear" in sys.argv
    seed(clear=clear)
