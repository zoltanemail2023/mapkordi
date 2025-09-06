\
from defusedxml import ElementTree as ET

def extract_positions_from_xml(xml_path: str):
    with open(xml_path, "r", encoding="utf-8", errors="ignore") as f:
        xml_text = f.read()
    positions = []
    root = ET.fromstring(xml_text)

    def try_add(elem):
        attrs = elem.attrib
        if all(k in attrs for k in ("x","y","z")):
            try:
                positions.append((float(attrs["x"]), float(attrs["y"]), float(attrs["z"]))); return
            except: pass
        def gf(name):
            c = elem.find(name)
            if c is not None and c.text: return float(c.text.strip())
            return None
        try:
            x,y,z = gf("x"), gf("y"), gf("z")
            if x is not None and y is not None and z is not None:
                positions.append((x,y,z)); return
        except: pass

    for ent in root.iter():
        tag = ent.tag.lower().split("}")[-1]
        if tag in ("position","pos","v3"):
            try_add(ent)

    for ent in root.iter():
        tag = ent.tag.lower().split("}")[-1]
        if tag in ("centitydef","ientitydef","entity","item"):
            for child in list(ent):
                ctag = child.tag.lower().split("}")[-1]
                if ctag in ("position","pos","v3"):
                    try_add(child); break

    # dedup
    seen=set(); out=[]
    for x,y,z in positions:
        key=(round(x,6),round(y,6),round(z,6))
        if key not in seen:
            seen.add(key); out.append((x,y,z))
    return out

def summarize(coords):
    if not coords: return "No coordinates found."
    if len(coords)==1:
        x,y,z = coords[0]
        return f"x={x:.4f}, y={y:.4f}, z={z:.4f}"
    n=len(coords)
    cx=sum(p[0] for p in coords)/n
    cy=sum(p[1] for p in coords)/n
    cz=sum(p[2] for p in coords)/n
    xs=[p[0] for p in coords]; ys=[p[1] for p in coords]; zs=[p[2] for p in coords]
    bbox=(min(xs),max(xs),min(ys),max(ys),min(zs),max(zs))
    return (f"Talált entitások: {n}\n"
            f"Középpont: x={cx:.4f}, y={cy:.4f}, z={cz:.4f}\n"
            f"Tartomány: x:[{bbox[0]:.2f},{bbox[1]:.2f}]  y:[{bbox[2]:.2f},{bbox[3]:.2f}]  z:[{bbox[4]:.2f},{bbox[5]:.2f}]")
