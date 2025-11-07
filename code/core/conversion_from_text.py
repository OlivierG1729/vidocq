
# -*- coding: utf-8 -*-

############################
# Conversion from text     #
#                          #
# Last update : 2025/07/22 #
############################

from datetime import datetime, time
import re

def parse_horaires_to_time(horaires):
    time_objects = {}
    for h in horaires:
        h_clean = h.replace("≈", "").strip()
        match = re.match(r"^([0-2]?\d)h([0-5]?\d)?$", h_clean)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                time_objects[h] = time(hour, minute)
    return time_objects

def combine_date_and_time(dates, times):
    """
    Combine les dates au format 'YYYY-MM-DD' et les horaires ('9h15', '≈ 20h') 
    pour générer des objets datetime complets.
    Renvoie un dictionnaire { (date_str, heure_str) ➜ datetime_object }
    """
    result = {}
    time_objects = parse_horaires_to_time(times)

    for date_str in dates:
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        for time_label, time_obj in time_objects.items():
            result[(date_str, time_label)] = datetime.combine(date_obj, time_obj)

    return result


# horaires = ['9h', '18h05', '≈ 20h', '≈ 6h', '14h30', '≈ 00h']
# result = parse_horaires_to_time(horaires)

# for label, time_obj in result.items():
#     print(f"{label} ➔ {time_obj}")

# dates = ["2023-06-21", "2023-06-22"]
# times = ["9h15", "≈ 20h", "14h"]

# combo = combine_date_and_time(dates, times)

# for key, dt in combo.items():
#     print(f"{key} ➜ {dt}")











































































