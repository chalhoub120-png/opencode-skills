#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build verified Beirut supermarket CSV from official sources only.
Columns: Name, District, Address, Phone, Hours, Source, Facebook, Instagram, Notes
"""
import csv
import os
import sys

# ------------------------------------------------------------------
# Verified rows (official websites, fetched 2026-11-04)
# ------------------------------------------------------------------

verified = [
    # Spinneys - Beirut branches only (spinneyssupermarket.com)
    {
        "Name": "Spinneys Ashrafieh Alexandre",
        "District": "Ashrafieh, Beirut",
        "Address": "Facing Hotel Alexandre, Adib Eshaq Street, Beirut",
        "Phone": "76 347 247",
        "Hours": "8 AM – 10 PM",
        "Source": "https://spinneyssupermarket.com/",
        "Facebook": "https://www.facebook.com/spinneyslebanon",
        "Instagram": "https://www.instagram.com/spinneyslebanon",
        "Notes": "Verified via official Store Locator",
    },
    {
        "Name": "Spinneys Ashrafieh Mar Mitr",
        "District": "Ashrafieh, Beirut",
        "Address": "La Sagesse school, Beirut",
        "Phone": "01 210 110",
        "Hours": "8 AM – 10 PM",
        "Source": "https://spinneyssupermarket.com/",
        "Facebook": "https://www.facebook.com/spinneyslebanon",
        "Instagram": "https://www.instagram.com/spinneyslebanon",
        "Notes": "Verified via official Store Locator",
    },
    {
        "Name": "Spinneys Ashrafieh Tilal Beirut",
        "District": "Ashrafieh, Beirut",
        "Address": "Rue Ashrafieh, Tilal Beirut Building, Beirut",
        "Phone": "01 216 442",
        "Hours": "8 AM – 10 PM",
        "Source": "https://spinneyssupermarket.com/",
        "Facebook": "https://www.facebook.com/spinneyslebanon",
        "Instagram": "https://www.instagram.com/spinneyslebanon",
        "Notes": "Verified via official Store Locator",
    },
    {
        "Name": "Spinneys Ain El Tineh",
        "District": "Ain El Tineh, Beirut",
        "Address": "Sakiet El Janzeer, Beirut",
        "Phone": "01 793 276",
        "Hours": "8 AM – 10 PM",
        "Source": "https://spinneyssupermarket.com/",
        "Facebook": "https://www.facebook.com/spinneyslebanon",
        "Instagram": "https://www.instagram.com/spinneyslebanon",
        "Notes": "Verified via official Store Locator",
    },
    {
        "Name": "Spinneys Hamra",
        "District": "Hamra, Beirut",
        "Address": "Sourati Road, Idriss Building, Hamra, Beirut",
        "Phone": "01 743 770",
        "Hours": "7:30 AM – 10 PM",
        "Source": "https://spinneyssupermarket.com/",
        "Facebook": "https://www.facebook.com/spinneyslebanon",
        "Instagram": "https://www.instagram.com/spinneyslebanon",
        "Notes": "Verified via official Store Locator",
    },
    {
        "Name": "Spinneys Hazmieh (Beirut outskirts)",
        "District": "Hazmieh (Beirut area)",
        "Address": "Between Chevrolet and Assayad Roundabout, Beirut",
        "Phone": "05 950 530",
        "Hours": "8:30 AM – 10 PM",
        "Source": "https://spinneyssupermarket.com/",
        "Facebook": "https://www.facebook.com/spinneyslebanon",
        "Instagram": "https://www.instagram.com/spinneyslebanon",
        "Notes": "Hazmieh listed in official locator",
    },
    {
        "Name": "Spinneys Jnah",
        "District": "Jnah, Beirut",
        "Address": "Wata El Msaytbeh, Beirut",
        "Phone": "01 837 837",
        "Hours": "8 AM – 10 PM",
        "Source": "https://spinneyssupermarket.com/",
        "Facebook": "https://www.facebook.com/spinneyslebanon",
        "Instagram": "https://www.instagram.com/spinneyslebanon",
        "Notes": "Verified via official Store Locator",
    },
    {
        "Name": "Spinneys Signature (Beirut Souks)",
        "District": "Downtown, Beirut",
        "Address": "Beirut Souks, Downtown, Beirut",
        "Phone": "01 990 845",
        "Hours": "8 AM – 10 PM",
        "Source": "https://spinneyssupermarket.com/",
        "Facebook": "https://www.facebook.com/spinneyslebanon",
        "Instagram": "https://www.instagram.com/spinneyslebanon",
        "Notes": "Signature premium format",
    },

    # Le Charcutier - Beirut-area branches (lecharcutierlebanon.com)
    {
        "Name": "Le Charcutier Achrafieh",
        "District": "Ashrafieh (Achrafieh), Beirut",
        "Address": "Rue Debbas, Beirut",
        "Phone": "01 328 304",
        "Hours": "8 AM – 10 PM",
        "Source": "https://lecharcutierlebanon.com/",
        "Facebook": "https://www.facebook.com/lecharcutier",
        "Instagram": "https://www.instagram.com/le_charcutier/",
        "Notes": "Official branch list; 19 branches across Lebanon",
    },
    {
        "Name": "Le Charcutier Dekwaneh",
        "District": "Dekwaneh (Greater Beirut)",
        "Address": "Rue Camil Chamoun, Dekwaneh",
        "Phone": "01 693 722",
        "Hours": "8 AM – 10 PM",
        "Source": "https://lecharcutierlebanon.com/",
        "Facebook": "https://www.facebook.com/lecharcutier",
        "Instagram": "https://www.instagram.com/le_charcutier/",
        "Notes": "Greater Beirut branch listed on official site",
    },
    {
        "Name": "Le Charcutier Fanar",
        "District": "Fanar (Greater Beirut)",
        "Address": "Rue Fanar, Fanar",
        "Phone": "01 891 609",
        "Hours": "8 AM – 10 PM",
        "Source": "https://lecharcutierlebanon.com/",
        "Facebook": "https://www.facebook.com/lecharcutier",
        "Instagram": "https://www.instagram.com/le_charcutier/",
        "Notes": "Greater Beirut branch listed on official site",
    },
    {
        "Name": "Le Charcutier Saloumi",
        "District": "Saloumi (Greater Beirut)",
        "Address": "Mirna Chalouhi, Saloumi",
        "Phone": "01 501 522",
        "Hours": "8 AM – 10 PM",
        "Source": "https://lecharcutierlebanon.com/",
        "Facebook": "https://www.facebook.com/lecharcutier",
        "Instagram": "https://www.instagram.com/le_charcutier/",
        "Notes": "Greater Beirut branch listed on official site",
    },

    # Metro Market - relevant branch (metrolebanon.com)
    {
        "Name": "Metro Market Hazmieh",
        "District": "Hazmieh (Beirut area)",
        "Address": "Hazmieh Main Road",
        "Phone": "09 851 301",
        "Hours": "Mon-Sat 8 AM-10 PM, Sun 9 AM-9 PM",
        "Source": "https://www.metrolebanon.com/",
        "Facebook": "https://www.facebook.com/metromalllb/",
        "Instagram": "https://www.instagram.com/explore/locations/466758303338839/lebanon/ghazir-mont-liban-lebanon/metro-market-partenaire-intermarche/",
        "Notes": "Official site lists 2 branches (Ghazir + Hazmieh)",
    },

    # Tawfeer - Ouzai (Greater Beirut)
    {
        "Name": "Tawfeer Ouzai",
        "District": "Ouzai, Baabda (Greater Beirut)",
        "Address": "Baabda Ouzai Main Street, next to Chamsine, near Adnan Helbawi School",
        "Phone": "70 675 151",
        "Hours": "8 AM – 7 PM",
        "Source": "https://tawfeerlebanon.com/",
        "Facebook": "https://m.facebook.com/TawfeerDiscountStore/",
        "Instagram": "https://www.instagram.com/tawfeerdiscountstore/",
        "Notes": "Only Greater-Beirut branch in official list; others outside Beirut",
    },
]

# ------------------------------------------------------------------
# Google Maps / Yelleb observations (NOT official store pages)
# - Extracted via real browser with JS (2026-11-04)
# - Hamra: 3 stores verified with phone numbers rendered by Google Maps
# - Ras Beirut / Ashrafieh: browser kept showing blank WeatherWidget
# - Yelleb: 1,046 Food Retailers in Beirut (hundreds of small dukkans)
# These are useful leads but still need a phone call to confirm current status.
# ------------------------------------------------------------------
google_maps_leads = [
    {
        "Name": "Al Fakhani Hamra (Google Maps lead)",
        "District": "Hamra, Beirut",
        "Address": "VFVJ+HVJ, Hamra (Google Maps plus code)",
        "Phone": "01 745 701",
        "Hours": "Open until 12 AM (Maps)",
        "Source": "https://www.google.com/maps/search/Hamra+Beirut+minimarket",
        "Facebook": "",
        "Instagram": "",
        "Notes": "Lead only - from Google Maps card (4.4 stars); confirm by phone",
    },
    {
        "Name": "Petit Marche Hamra",
        "District": "Hamra, Beirut",
        "Address": "VFVH+WM5, Hamra",
        "Phone": "01 355 155",
        "Hours": "Open until 5 AM Thu (Maps)",
        "Source": "https://www.google.com/maps/search/Hamra+Beirut+minimarket",
        "Facebook": "",
        "Instagram": "",
        "Notes": "Lead only - Google Maps card (4.5 stars)",
    },
    {
        "Name": "A to Z Mart Hamra",
        "District": "Hamra, Beirut",
        "Address": "VFXH+6VM, Hamra",
        "Phone": "01 750 789",
        "Hours": "24/7 (Maps)",
        "Source": "https://www.google.com/maps/search/Hamra+Beirut+minimarket",
        "Facebook": "",
        "Instagram": "",
        "Notes": "Lead only - Google Maps card (4.9 stars)",
    },
    # Yelleb examples (names + phones + street-level address, but no socials)
    {
        "Name": "Alexandre Minimarket (Yelleb)",
        "District": "Ashrafieh, Beirut",
        "Address": "A. Ishac Street, Ashrafieh",
        "Phone": "+961 70 111 191",
        "Hours": "",
        "Source": "https://www.yelleb.com/category/food_retailers/29/city:Beirut",
        "Facebook": "",
        "Instagram": "",
        "Notes": "Yelleb directory lead (1,046 Beirut food retailers); socials not verified",
    },
    {
        "Name": "Blacklist Hamra (Yelleb)",
        "District": "Hamra, Beirut",
        "Address": "Hamra Street, Hamra",
        "Phone": "+961 3 850 876",
        "Hours": "",
        "Source": "https://www.yelleb.com/category/food_retailers/29/city:Beirut",
        "Facebook": "",
        "Instagram": "",
        "Notes": "Yelleb directory lead; confirm by phone",
    },
    {
        "Name": "Beik Pâtisserie Ras Beirut (Yelleb)",
        "District": "Ras Beirut, Beirut",
        "Address": "Sadat Street, Ras Beirut",
        "Phone": "+961 1 805 952",
        "Hours": "",
        "Source": "https://www.yelleb.com/category/food_retailers/29/city:Beirut",
        "Facebook": "",
        "Instagram": "",
        "Notes": "Yelleb directory lead",
    },
    {
        "Name": "Azar Boulangerie Ashrafieh (Yelleb)",
        "District": "Ashrafieh, Beirut",
        "Address": "Fassouh, Ashrafieh",
        "Phone": "+961 3 355 814",
        "Hours": "",
        "Source": "https://www.yelleb.com/category/food_retailers/29/city:Beirut",
        "Facebook": "",
        "Instagram": "",
        "Notes": "Yelleb directory lead",
    },
    {
        "Name": "Afrah Ras el Nabeh (Yelleb)",
        "District": "Ras el Nabeh, Beirut",
        "Address": "Noueyri Street, Ras el Nabeh",
        "Phone": "+961 3 332 228",
        "Hours": "",
        "Source": "https://www.yelleb.com/category/food_retailers/29/city:Beirut",
        "Facebook": "",
        "Instagram": "",
        "Notes": "Yelleb directory lead",
    },
    {
        "Name": "Aqua el Siman Ras el Nabeh (Yelleb)",
        "District": "Ras el Nabeh, Beirut",
        "Address": "O. Ben Khattab Street, Ras el Nabeh",
        "Phone": "+961 3 453 144",
        "Hours": "",
        "Source": "https://www.yelleb.com/category/food_retailers/29/city:Beirut",
        "Facebook": "",
        "Instagram": "",
        "Notes": "Yelleb directory lead",
    },
]


all_rows = verified + google_maps_leads

os.makedirs("content", exist_ok=True)
with open("content/beirut_supermarkets_verified.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=["Name", "District", "Address", "Phone", "Hours", "Source", "Facebook", "Instagram", "Notes"])
    writer.writeheader()
    writer.writerows(all_rows)

print(f"Wrote content/beirut_supermarkets_verified.csv with {len(all_rows)} rows ({len(verified)} verified + {len(google_maps_leads)} leads)")
