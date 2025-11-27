"""
Jaggedness Configuration for Edge Displacement

This module provides configuration settings for fractal edge subdivision.
The jaggedness settings control how rough/smooth different types of borders appear.

Each edge type has three parameters:
- initial_displacement: Starting displacement magnitude (fraction of edge length)
- roughness: How quickly displacement decreases each level (0.0 - 1.0)
- max_depth: Maximum recursion depth

Higher values = more jagged borders
Lower values = smoother borders
"""

# Default jaggedness settings for each edge type
# Format: (initial_displacement, roughness, max_depth)

JAGGEDNESS_CONFIG = {
    # Coastlines (land-sea boundaries): Heavy displacement for jagged, natural-looking shores
    # Doubled from original (0.08, 0.65, 4)
    "coast": (0.16, 0.65, 4),
    
    # Land borders (political lines/rivers): Moderate displacement for organic-looking borders
    # This is the original coastline value - provides good internal land border jaggedness
    "land": (0.08, 0.65, 4),
    
    # Sea borders (water-water boundaries): Gentle displacement
    "sea": (0.02, 0.5, 2),
    
    # Impassable terrain borders (land-impassable or impassable-other boundaries):
    # Same as land borders for consistent appearance
    "impassable": (0.08, 0.65, 4),
    
    # Map edges (boundary of the map): No displacement - remain straight
    "map-edge": (0.0, 0.5, 0),
}

# Default parameters for unknown edge types
DEFAULT_PARAMS = (0.02, 0.5, 2)


def get_edge_displacement_params(edge_type: str) -> tuple:
    """
    Get displacement parameters for a given edge type.
    
    Args:
        edge_type: Type of edge ("coast", "land", "sea", "impassable", "map-edge")
        
    Returns:
        Tuple of (initial_displacement, roughness, max_depth)
    """
    return JAGGEDNESS_CONFIG.get(edge_type, DEFAULT_PARAMS)
