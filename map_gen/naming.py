"""
Naming Module

This module handles the generation of names for regions.
"""

import random

class RegionNamer:
    """Handles the generation of names for regions."""
    
    def __init__(self):
        """Initialize with name components."""
        self.land_prefixes = ["Ar", "Bel", "Cor", "Dun", "El", "Fal", "Gal", "Hy", "Il", "Jor", 
                            "Kyl", "Lun", "Mor", "Nor", "Os", "Pyr", "Qar", "Ryn", "Sul", "Tyr"]
        
        self.land_suffixes = ["ania", "borg", "crest", "dor", "ell", "ford", "gate", "heim", "isle", 
                            "keep", "land", "moor", "nia", "oria", "peak", "quar", "ria", "shire", 
                            "ton", "vale", "wood"]
        
        self.sea_names = [
            "North Sea", "South Sea", "Eastern Sea", "Western Sea",
            "Great Bay", "Golden Bay", "Storm Bay", "Crystal Bay",
            "Narrow Strait", "Wide Strait", "Iron Strait", "Silver Strait",
            "Inner Sea", "Outer Sea", "Deep Waters", "Shallow Waters",
            "Merchant Sea", "Warrior Sea", "Royal Sea", "Ancient Sea",
            "Misty Waters", "Clear Waters", "Dark Sea", "Bright Sea",
            "Frozen Sea", "Warm Sea", "Peaceful Sea", "Wild Sea"
        ]
        
        self.used_names = set()
    
    def name_regions(self, regions):
        """Generate names for all regions."""
        # Process land regions first
        land_regions = [r for r in regions if regions[r]["type"] == "land"]
        sea_regions = [r for r in regions if regions[r]["type"] == "sea"]
        
        # Name land regions
        for region_id in land_regions:
            regions[region_id]["name"] = self._generate_land_name()
        
        # Name sea regions
        sea_name_index = 0
        for region_id in sea_regions:
            if sea_name_index < len(self.sea_names):
                regions[region_id]["name"] = self.sea_names[sea_name_index]
                self.used_names.add(self.sea_names[sea_name_index])
                sea_name_index += 1
            else:
                regions[region_id]["name"] = self._generate_sea_name()
    
    def _generate_land_name(self):
        """Generate a name for a land region."""
        num_attempts = 0
        while True:
            name = random.choice(self.land_prefixes) + random.choice(self.land_suffixes)
            if name not in self.used_names:
                break
            num_attempts += 1
            if num_attempts > 100:  # Prevent infinite loop
                name = f"{random.choice(self.land_prefixes)}{random.choice(self.land_suffixes)}{num_attempts}"
                break
        
        self.used_names.add(name)
        return name
    
    def _generate_sea_name(self):
        """Generate a name for a sea region when predefined names are exhausted."""
        num_attempts = 0
        while True:
            feature = random.choice(["Sea", "Bay", "Strait", "Waters", "Channel", "Currents"])
            if num_attempts < 20:
                direction = random.choice(["North", "South", "East", "West", "Central", "Narrow", "Deep", "Great"])
                name = f"{direction} {feature}"
            else:
                main_name = random.choice(self.land_prefixes) + random.choice(self.land_prefixes).lower()
                name = f"{main_name} {feature}"
            
            if name not in self.used_names:
                break
                
            num_attempts += 1
            if num_attempts > 100:  # Prevent infinite loop
                name = f"{feature} {num_attempts}"
                break
        
        self.used_names.add(name)
        return name
