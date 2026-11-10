#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build a clean secretary-ready reference CSV from the two source CSVs in this folder.
- No invented addresses/phones/social links.
- Deduplicates by normalized Name + Phone.
- Separates confidence levels: Verified official / Google Maps lead / Directory lead.
- Output: final_secretary_reference.csv
"""
import csv
import os
import re
import unicodedata
from pathlib import Path

BASE = Path(__file__).resolve().parent
SRC_A = BASE / "beirut_supermarkets_verified.csv"
SRC_B = BASE / "google_maps_pois_Hamra_RasBeirut_Ashrafieh.csv"
OUT = BASE / "final_secretary_reference.csv"

def norm(s: str) -> str:
    s = (s or "").strip()
    s = unicodedata.normalize("NFKC", s).lower()
    s = re.sub(r"\s+", " ", s)
    # remove Arabic diacritics lightly (not needed for key, keep simple)
    s = re.sub(r"[^a-z0-9\u0600-\u06FF]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def phone_key(p: str) -> str:
    d = re.sub(r"\D+", "", p or "")
    # normalize +961 / 961 prefix
    if d.startswith("961"):
        d = d[3:].lstrip("0")
    if d.startswith("0"):
        d = d[1:]
    return d

def read_csv(path):
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

rows_a = read_csv(SRC_A)
rows_b = read_csv(SRC_B)

merged = {}  # key -> row
order = []

def add(row, category_hint):
    name = row.get("Name", "") or row.get("Google_Maps_Result", "")
    phone = row.get("Phone", "") or ""
    key = f"{norm(name)}|{phone_key(phone)}"
    # If no phone, fallback to name alone
    if not phone_key(phone):
        key = f"{norm(name)}|NOPHONE"
    if key not in merged:
        merged[key] = row
        order.append(key)
    else:
        # merge: keep first, append note about duplicate source
        prev = merged[key]
        # keep longer address if present
        a1 = (prev.get("Address") or prev.get("Address_Or_PlusCode") or "").strip()
        a2 = (row.get("Address") or row.get("Address_Or_PlusCode") or "").strip()
        if len(a2) > len(a1):
            prev["Address"] = a2
            prev["Address_Or_PlusCode"] = a2
        # append source if different
        s2 = row.get("Source") or row.get("Source_URL") or ""
        s1 = prev.get("Source") or prev.get("Source_URL") or ""
        if s2 and s2 not in s1:
            prev["Source"] = (s1 + " | " + s2).strip(" |")
            prev["Source_URL"] = (prev.get("Source_URL", "") + " | " + s2).strip(" |")
    return key

# 1) Add official/verified rows first (they have priority)
for r in rows_a:
    add(r, "official")

# 2) Add Google Maps POIs (deduped)
for r in rows_b:
    add(r, "googlemaps")

# Build final rows
def get(row, *keys):
    for k in keys:
        v = row.get(k)
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return ""

final = []
for idx, key in enumerate(order, 1):
    r = merged[key]
    name = get(r, "Name")
    district = get(r, "District", "Area")
    address = get(r, "Address", "Address_Or_PlusCode")
    phone = get(r, "Phone")
    hours = get(r, "Hours", "Hours_As_Shown")
    source = get(r, "Source", "Source_URL")
    facebook = get(r, "Facebook")
    instagram = get(r, "Instagram")
    verification = get(r, "Verification")
    notes = get(r, "Notes")
    rating = get(r, "Rating")
    plus = get(r, "Plus_Code")

    # Derive status
    if verification and "Verified official" in verification:
        status = "A — Verified official"
        action = "Ready to publish"
    elif verification and "Google Maps lead" in verification:
        status = "B — Google Maps lead (confirm by phone)"
        action = "Call to confirm open + street address"
    elif verification and "Directory lead" in verification:
        status = "C — Directory lead (confirm by phone)"
        action = "Call to confirm open + social links"
    else:
        status = "B — Google Maps lead (confirm by phone)"
        action = "Call to confirm open + street address"

    # If official, Facebook/Instagram as listed on official site only (already in source)
    # If lead, keep blank unless official brand explicitly linked in source (none)
    maps_url = get(r, "Source_URL", "Source")
    # Keep only the Maps URL if present
    if "google.com/maps/search" in source:
        # extract first google maps url
        m = re.search(r"https://www\.google\.com/maps/search[^\s|]+", source)
        maps_url = m.group(0) if m else source

    final.append({
        "ID": idx,
        "Name": name,
        "District": district,
        "Address_As_Listed": address,
        "Phone": phone,
        "Hours": hours,
        "Facebook": facebook,
        "Instagram": instagram,
        "Verification_Status": status,
        "Source": source,
        "Google_Maps_Search_URL": maps_url,
        "Plus_Code": plus,
        "Rating": rating,
        "Action_Needed": action,
        "Notes": notes,
        "Last_Verified_Date": "2026-11-04",
    })

fields = ["ID","Name","District","Address_As_Listed","Phone","Hours","Facebook","Instagram",
          "Verification_Status","Source","Google_Maps_Search_URL","Plus_Code","Rating",
          "Action_Needed","Notes","Last_Verified_Date"]

with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(final)

from collections import Counter
c = Counter(r["Verification_Status"] for r in final)
print(f"Wrote {OUT} with {len(final)} rows")
for k, v in sorted(c.items()):
    print(f"  {k}: {v}")
# sanity: print first 5 names
for r in final[:5]:
    print(f"  {r['ID']}. {r['Name']} | {r['Verification_Status']}")

# Also write a short summary md
summary = BASE / "final_secretary_summary.md"
with open(summary, "w", encoding="utf-8") as f:
    f.write("# Secretary summary — final_secretary_reference.csv\n\n")
    f.write(f"Generated: 2026-11-04 from {SRC_A.name} + {SRC_B.name}\n\n")
    f.write("## Counts\n")
    for k, v in sorted(c.items()):
        f.write(f"- {k}: {v}\n")
    f.write(f"- **Total unique rows: {len(final)}**\n\n")
    f.write("## How to use\n")
    f.write("- **A — Verified official**: from official chain websites only (Spinneys, Le Charcutier, Metro, Tawfeer). Facebook/Instagram are the official chain accounts linked on those sites — use them directly.\n")
    f.write("- **B — Google Maps lead**: name + phone from Google Maps cards. Address is often a Plus Code — open the detail card to get street address. Call before publishing.\n")
    f.write("- **C — Directory lead**: from Yelleb directory. No socials verified yet. Call + search socials manually.\n\n")
    f.write("## Safety\n")
    f.write("- No phone/social was invented. Blank Facebook/Instagram means none verified in source.\n")
    f.write("- No API key was used. All data was retrieved via browser/fetch and official sites.\n")
    f.write("- Re-verify by phone before treating B/C as active.\n")
print(f"Wrote {summary}")
