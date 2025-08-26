import os
from configparser import ConfigParser

conf = ConfigParser()
conf.read("config.txt")

class TaikoGimmick:
    def __init__(self, filepath=None):
        self.filePath = filepath
        self.content = None
        self.hitObjects = {}
        self.timingPoints = {}

        if filepath and os.path.exists(filepath) and filepath.endswith(".osu"):
            with open(filepath, "r", encoding="utf-8") as file:
                self.content = file.read()
                self.hitObjects = self.parse_hitObjects(self.split_section("HitObjects"))
                self.timingPoints = self.parse_timingPoints(self.split_section("TimingPoints"))

    def timestamp_ms(self, timestamp):
        return sum(int(x) * m for x, m in zip(timestamp.split(':'), [60000, 1000, 1]))

    def interpret_selection(self, selection):
        try:
            timestamp = self.timestamp_ms(selection.split(" ")[0])
            length = len(selection.split(" ")[1].strip("()- ").split(","))
            keysList = list(self.hitObjects.keys())
            startIdx = keysList.index(timestamp)
            affectedObjs = {keysList[i]: self.hitObjects[keysList[i]][0] for i in range(startIdx, startIdx + length)}
            print(f"\nAffecting \033[32;1m{len(affectedObjs)} objects\033[0m in \033[3m{self.filePath}\033[0m")
            return affectedObjs
        except Exception as e:
            print(f"\nError interpreting selection: {str(e)}")
            return None

    def split_section(self, name):
        return self.content.split(f"[{name}]\n")[1].split("\n\n")[0].splitlines()
    
    def parse_timingPoints(self, objects):
        timingPoints = {}
        for line in objects:
            splitLine = line.split(",")
            timingPoints[float(splitLine[0])] = {
                "beat_length": float(splitLine[1]),
                "meter": int(splitLine[2]),
                "sample_set": int(splitLine[3]),
                "sample_index": int(splitLine[4]),
                "volume": int(splitLine[5]),
                "uninherited": bool(int(splitLine[6])),
                "effects": int(splitLine[7]) if len(splitLine) > 7 else 0
            }
        return timingPoints
    
    def parse_hitObjects(self, objects):
        objectsDict = {}
        for line in objects:
            splitLine = line.split(",")
            try:
                time = int(splitLine[2])
                hitsound = int(splitLine[4])
                hitObject = {
                    "is_kat": hitsound in (2,6,8,10,12,14),
                    "is_large": hitsound in (4,6,12,14)
                }
                if time not in objectsDict:
                    objectsDict[time] = []
                objectsDict[time].append(hitObject)
            except (ValueError, IndexError):
                continue
        return objectsDict

    def _get_green_lines(self):
        green_lines = {}
        for timestamp, tp in self.timingPoints.items():
            if not tp['uninherited']:
                green_lines[timestamp] = tp['beat_length'] / -100.0
        return green_lines

    def _get_default_sv(self, min_time):
        default_sv = 1.0
        latest_green_line = None
        for timestamp, tp in self.timingPoints.items():
            if not tp['uninherited'] and timestamp <= min_time:
                if latest_green_line is None or timestamp > latest_green_line:
                    latest_green_line = timestamp
                    default_sv = tp['beat_length'] / -100.0
        print(f"Default SV: {default_sv} found at offset {latest_green_line}")
        return default_sv

    def _get_scroll_speed(self, timestamp, green_lines, default_sv):
        applicable_times = [t for t in green_lines.keys() if t <= timestamp]
        if applicable_times:
            closest_time = max(applicable_times)
            return green_lines[closest_time]
        return default_sv

    def _get_kiai_state(self, timestamp):
        applicable_times = [t for t in self.timingPoints.items() if t[0] <= timestamp]
        if applicable_times:
            last_point = max(applicable_times, key=lambda x: x[0])
            return bool(last_point[1]['effects'] & 1)  # Check bit 0 for kiai
        return False

    def _add_timing_point(self, time, beat_length, uninherited=True, effects=0):
        kiai_state = self._get_kiai_state(time)
        # Combine kiai state (bit 0) with other effects
        final_effects = effects | (1 if kiai_state else 0)
        return f"{time},{beat_length},2,1,0,100,{1 if uninherited else 0},{final_effects}"

    def _update_timing_section(self, min_time, max_time, new_lines):
        timing_lines = self.split_section("TimingPoints")
        filtered_lines = [line for line in timing_lines 
                         if not (min_time <= float(line.split(",")[0]) <= max_time)]
        
        new_timing_section = "\n".join(filtered_lines + new_lines)
        timing_section_start = self.content.find("[TimingPoints]\n")
        timing_section_end = self.content.find("\n\n", timing_section_start)
        
        return (self.content[:timing_section_start + len("[TimingPoints]\n")] + 
                new_timing_section + self.content[timing_section_end:])


    def barline_gimmick(self, selection, preset=None, bpm=120):
        if preset is None:
            preset = {
                'don': [int(x) for x in conf.get('Barlines', 'don').split(',')],
                'kat': [int(x) for x in conf.get('Barlines', 'kat').split(',')]
            }

        affectedObjs = self.interpret_selection(selection)
        if not affectedObjs:
            raise ValueError("Invalid selection")

        selection_timestamps = list(affectedObjs.keys())
        min_time = min(selection_timestamps)
        max_time = max(selection_timestamps)
    
        green_lines = self._get_green_lines()
        default_sv = self._get_default_sv(min_time)
        base_beat_length = 60000 / bpm

        barlines = []
        for timestamp, hit_obj in affectedObjs.items():
            object_scroll_speed = self._get_scroll_speed(timestamp, green_lines, default_sv)

            # Add timing points for the note
            barlines.append(self._add_timing_point(timestamp, 1, True, 8))
            barlines.append(self._add_timing_point(timestamp, -10.0, False))
            
            offsets = preset['kat'] if hit_obj['is_kat'] else preset['don']
            
            for offset in offsets:
                barline_time = timestamp + offset
                barlines.append(self._add_timing_point(barline_time, base_beat_length))
                if object_scroll_speed != 1.0:
                    barlines.append(self._add_timing_point(barline_time, object_scroll_speed * -100.0, False))

        new_content = self._update_timing_section(min_time, max_time, barlines)
        
        with open(self.filePath, "w", encoding="utf-8") as file:
            file.write(new_content)

        print(f"Added \033[32;1m{len(barlines)} barlines.\033[0m\n")


    def slider_gimmick(self, selection, bpm=120, stack=1, flash_kat=True, shine=False, divisions=6):
        """Add sliders after notes with optional shining effect."""
        affectedObjs = self.interpret_selection(selection)
        if not affectedObjs:
            raise ValueError("Invalid selection")

        selection_timestamps = list(affectedObjs.keys())
        min_time = min(selection_timestamps)
        max_time = max(selection_timestamps)

        green_lines = self._get_green_lines()
        default_sv = self._get_default_sv(min_time)

        # Calculate shine timing if enabled
        if shine:
            slow_bpm = bpm / 2  # BPM is halved
            beat_length = 60000 / slow_bpm
            division_length = beat_length / divisions
            base_beat_length = beat_length
        else:
            base_beat_length = 60000 / bpm

        new_lines = []
        sliders = []

        for timestamp, hit_obj in affectedObjs.items():
            is_kat = hit_obj['is_kat']
            should_flash = (is_kat and flash_kat) or (not is_kat and not flash_kat)
            
            if stack > 1 and not should_flash:
                continue

            object_scroll_speed = self._get_scroll_speed(timestamp, green_lines, default_sv)
            slider_time = timestamp + 1

            # Double the SV for shine effect
            final_sv = object_scroll_speed * (0.5 if shine else 1)

            # Add timing points for the note
            new_lines.append(self._add_timing_point(timestamp, 1, True, 8))
            new_lines.append(self._add_timing_point(timestamp, final_sv * -100.0, False))

            # Add timing points for the slider
            new_lines.append(self._add_timing_point(slider_time, base_beat_length, True, 8))
            new_lines.append(self._add_timing_point(slider_time, final_sv * -100.0, False))

            # Create slider(s)
            hitsound = "0"
            slider = f"256,192,{slider_time},2,{hitsound},L|256:192,1,2"
            if should_flash:
                sliders.extend([slider] * stack)
                
                # Add shine effect timing points with consistent doubled SV
                if shine:
                    for i in range(divisions):
                        division_time = timestamp + (i * division_length) + 1
                        new_lines.append(self._add_timing_point(division_time, beat_length, True, 8))
                        new_lines.append(self._add_timing_point(division_time, final_sv * -100.0, False))
            else:
                sliders.append(slider)

        # Update timing points section
        new_content = self._update_timing_section(min_time, max_time, new_lines)
        
        # Update hit objects section
        hitobjects_start = new_content.find("[HitObjects]\n")
        hitobjects_section = new_content[hitobjects_start:]
        new_hitobjects = (hitobjects_section.split("\n", 1)[0] + "\n" + 
                         "\n".join(sliders) + "\n" + 
                         hitobjects_section.split("\n", 1)[1])
        
        final_content = new_content[:hitobjects_start] + new_hitobjects
        
        with open(self.filePath, "w", encoding="utf-8") as file:
            file.write(final_content)

        print(f"Added \033[32;1m{len(sliders)} sliders.\033[0m\n")