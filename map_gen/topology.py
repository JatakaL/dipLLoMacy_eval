"""
Topology Module

This module implements the Face-Edge-Vertex topological data structure for maps.
It converts cell-centric Voronoi diagrams into explicit topological relationships.

Data Structures:
- Vertices: Unique geometric points (x, y coordinates)
- Edges: Connections between two vertices with left_face and right_face references
- Faces: Territories/cells that reference their boundary edges
"""

import numpy as np
from typing import Dict, List, Tuple, Optional


class Vertex:
    """Represents a unique geometric point in the topology."""
    
    def __init__(self, vertex_id: int, coords: Tuple[float, float]):
        """
        Initialize a vertex.
        
        Args:
            vertex_id: Unique identifier for this vertex
            coords: (x, y) coordinates
        """
        self.id = vertex_id
        self.coords = coords
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "coords": list(self.coords)
        }


class Edge:
    """Represents a connection between two vertices with face adjacency info."""
    
    def __init__(self, edge_id: str, v1: int, v2: int):
        """
        Initialize an edge.
        
        Args:
            edge_id: Unique identifier for this edge (e.g., "E_0_1")
            v1: ID of first vertex
            v2: ID of second vertex
        """
        self.id = edge_id
        self.v1 = v1
        self.v2 = v2
        self.left_face: Optional[str] = None
        self.right_face: Optional[str] = None
        self.type: Optional[str] = None  # "land", "coast", "map-edge"
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        result = {
            "v1": self.v1,
            "v2": self.v2,
        }
        if self.left_face is not None:
            result["left_face"] = self.left_face
        if self.right_face is not None:
            result["right_face"] = self.right_face
        if self.type is not None:
            result["type"] = self.type
        return result


class Border:
    """
    Represents an ordered list of edges that form a boundary between two faces.
    
    A border is a logical grouping of edges that:
    - All share the same left_face and right_face
    - Are connected end-to-end (share vertices)
    - Can be traversed in order from start_vertex to end_vertex
    
    Before edge subdivision, a border consists of a single edge.
    After subdivision, a border contains multiple edges that together
    represent the original boundary with added detail.
    """
    
    def __init__(self, border_id: str, left_face: Optional[str] = None, 
                 right_face: Optional[str] = None, edge_type: Optional[str] = None):
        """
        Initialize a border.
        
        Args:
            border_id: Unique identifier for this border
            left_face: ID of the face on the left side
            right_face: ID of the face on the right side
            edge_type: Type of border ("land", "coast", "sea", "map-edge")
        """
        self.id = border_id
        self.left_face = left_face
        self.right_face = right_face
        self.type = edge_type
        self.edges: List[str] = []  # Ordered list of edge IDs in this border
        self.start_vertex: Optional[int] = None  # First vertex of the border
        self.end_vertex: Optional[int] = None  # Last vertex of the border
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        result = {
            "edges": self.edges,
        }
        if self.left_face is not None:
            result["left_face"] = self.left_face
        if self.right_face is not None:
            result["right_face"] = self.right_face
        if self.type is not None:
            result["type"] = self.type
        if self.start_vertex is not None:
            result["start_vertex"] = self.start_vertex
        if self.end_vertex is not None:
            result["end_vertex"] = self.end_vertex
        return result


class Face:
    """Represents a territory/cell defined by its boundary borders.
    
    A face references an ordered list of borders, where each border
    contains one or more edges. This design ensures:
    - No redundancy: edges are only listed in borders, not directly in faces
    - Clear hierarchy: face -> borders -> edges
    - Borders group edges that share the same adjacent faces
    """
    
    def __init__(self, face_id: str, face_type: str):
        """
        Initialize a face.
        
        Args:
            face_id: Unique identifier for this face
            face_type: Type of face ("land" or "sea")
        """
        self.id = face_id
        self.type = face_type
        self.borders: List[str] = []  # Ordered list of border IDs forming the perimeter
        self.center: Optional[Tuple[float, float]] = None
        self.coastal: bool = False  # Whether this land face is coastal
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        result = {
            "type": self.type,
            "borders": self.borders,
        }
        if self.center is not None:
            result["center"] = list(self.center)
        # Include coastal property for land faces
        if self.coastal:
            result["coastal"] = self.coastal
        return result


class TopologyConverter:
    """Converts Voronoi cell data to Face-Edge-Vertex topology."""
    
    def __init__(self):
        """
        Initialize the topology converter.
        
        Note: Currently uses fixed precision (9 decimals) for deduplication.
        # TODO: If a tolerance-based deduplication is needed, add a tolerance parameter here.
        """
        self.vertices: Dict[int, Vertex] = {}
        self.edges: Dict[str, Edge] = {}
        self.faces: Dict[str, Face] = {}
        self.borders: Dict[str, Border] = {}
        self.vertex_lookup: Dict[Tuple[float, float], int] = {}
        self.next_vertex_id = 0
    
    def _round_coords(self, coords: Tuple[float, float]) -> Tuple[float, float]:
        """
        Round coordinates to avoid floating point precision issues.
        
        Args:
            coords: (x, y) coordinates
            
        Returns:
            Rounded coordinates as tuple
        """
        # Round to a reasonable precision (9 decimal places)
        return (round(coords[0], 9), round(coords[1], 9))
    
    def _get_or_create_vertex(self, coords: Tuple[float, float]) -> int:
        """
        Get existing vertex ID or create a new vertex.
        
        This implements vertex deduplication - if a vertex with the same
        coordinates already exists, return its ID. Otherwise create a new one.
        
        Args:
            coords: (x, y) coordinates
            
        Returns:
            Vertex ID
        """
        # Round coordinates for lookup
        rounded_coords = self._round_coords(coords)
        
        # Check if vertex already exists
        if rounded_coords in self.vertex_lookup:
            return self.vertex_lookup[rounded_coords]
        
        # Create new vertex
        vertex_id = self.next_vertex_id
        self.next_vertex_id += 1
        
        vertex = Vertex(vertex_id, rounded_coords)
        self.vertices[vertex_id] = vertex
        self.vertex_lookup[rounded_coords] = vertex_id
        
        return vertex_id
    
    def _create_edge_id(self, v1: int, v2: int) -> str:
        """
        Create a canonical edge ID from two vertex IDs.
        
        The edge ID is always formatted as E_{min}_{max} to ensure
        that edge A->B has the same ID as edge B->A.
        
        Args:
            v1: First vertex ID
            v2: Second vertex ID
            
        Returns:
            Edge ID string
        """
        min_v = min(v1, v2)
        max_v = max(v1, v2)
        return f"E_{min_v}_{max_v}"
    
    def _get_or_create_edge(self, v1: int, v2: int, face_id: str) -> str:
        """
        Get existing edge or create a new edge.
        
        If the edge already exists, update its face references.
        Otherwise, create a new edge and set its left_face.
        
        Args:
            v1: First vertex ID
            v2: Second vertex ID
            face_id: ID of the face this edge belongs to
            
        Returns:
            Edge ID
        """
        edge_id = self._create_edge_id(v1, v2)
        
        if edge_id in self.edges:
            # Edge already exists - set the other face
            edge = self.edges[edge_id]
            if edge.left_face is None:
                edge.left_face = face_id
            elif edge.right_face is None:
                edge.right_face = face_id
            else:
                # Edge already has both faces - this shouldn't happen in a proper Voronoi diagram
                # This indicates a topology error that should be investigated
                print(f"WARNING: Edge {edge_id} already has both faces: {edge.left_face}, {edge.right_face}")
                print(f"  Attempted to add face {face_id}, but edge already complete.")
                print(f"  This may indicate duplicate edges or a malformed Voronoi diagram.")
        else:
            # Create new edge
            edge = Edge(edge_id, min(v1, v2), max(v1, v2))
            edge.left_face = face_id
            self.edges[edge_id] = edge
        
        return edge_id
    
    def _create_border_for_edge(self, edge_id: str) -> str:
        """
        Create a border containing a single edge.
        
        Initially, each edge gets its own border. Borders may later
        contain multiple edges after subdivision.
        
        Args:
            edge_id: ID of the edge
            
        Returns:
            Border ID
        """
        edge = self.edges.get(edge_id)
        if not edge:
            return ""
        
        # Create border ID based on the edge (B_ prefix instead of E_)
        border_id = f"B_{edge.v1}_{edge.v2}"
        
        if border_id in self.borders:
            return border_id
        
        # Create new border with the edge's properties
        border = Border(
            border_id,
            left_face=edge.left_face,
            right_face=edge.right_face,
            edge_type=edge.type
        )
        border.edges = [edge_id]
        border.start_vertex = edge.v1
        border.end_vertex = edge.v2
        
        self.borders[border_id] = border
        return border_id
    
    def convert_cells_to_topology(self, cells: Dict[str, dict]) -> Tuple[Dict, Dict, Dict]:
        """
        Convert cell-centric Voronoi data to Face-Edge-Vertex topology.
        
        This is the main conversion function that processes all cells and creates
        the topological representation.
        
        Args:
            cells: Dictionary of cell data with "vertices" and other properties
            
        Returns:
            Tuple of (vertices_dict, edges_dict, faces_dict)
        """
        print(f"Converting {len(cells)} cells to topological representation...")
        
        # Process each cell
        for cell_id, cell_data in cells.items():
            # Create face for this cell
            face = Face(cell_id, cell_data.get("type", "land"))
            face.center = tuple(cell_data["center"]) if "center" in cell_data else None
            face.coastal = cell_data.get("coastal", False)
            
            # Get vertices of this cell's polygon
            vertices = cell_data["vertices"]
            if isinstance(vertices, np.ndarray):
                vertices = vertices.tolist()
            
            # Process each edge of the polygon
            edge_ids = []
            num_vertices = len(vertices)
            
            for i in range(num_vertices):
                # Get current and next vertex (wrapping around)
                current_vertex = vertices[i]
                next_vertex = vertices[(i + 1) % num_vertices]
                
                # Skip if vertices are the same (within tolerance)
                # Use rounded comparison to match vertex deduplication logic
                if self._round_coords(tuple(current_vertex)) == self._round_coords(tuple(next_vertex)):
                    continue
                
                # Convert to tuples if they're lists
                if isinstance(current_vertex, list):
                    current_vertex = tuple(current_vertex)
                if isinstance(next_vertex, list):
                    next_vertex = tuple(next_vertex)
                
                # Get or create vertex IDs
                v1_id = self._get_or_create_vertex(current_vertex)
                v2_id = self._get_or_create_vertex(next_vertex)
                
                # Get or create edge
                edge_id = self._get_or_create_edge(v1_id, v2_id, cell_id)
                edge_ids.append(edge_id)
            
            # Store edge_ids temporarily for border creation
            face._temp_edge_ids = edge_ids
            self.faces[cell_id] = face
        
        print(f"Created {len(self.vertices)} vertices, {len(self.edges)} edges, {len(self.faces)} faces")
        
        # Classify edge types
        self._classify_edge_types()
        
        # Create borders for each edge (initially one edge per border)
        self._create_borders()
        
        print(f"Created {len(self.borders)} borders")
        
        return self._to_dicts()
    
    def _create_borders(self):
        """
        Create borders for all edges after edge types have been classified.
        
        Each edge initially gets its own border. Faces are updated to
        reference borders (not edges directly).
        """
        for edge_id, edge in self.edges.items():
            border_id = self._create_border_for_edge(edge_id)
            # Update border properties from the classified edge
            if border_id in self.borders:
                self.borders[border_id].type = edge.type
                self.borders[border_id].left_face = edge.left_face
                self.borders[border_id].right_face = edge.right_face
        
        # Update faces to reference their borders (not edges)
        for face_id, face in self.faces.items():
            face.borders = []
            temp_edge_ids = getattr(face, '_temp_edge_ids', [])
            for edge_id in temp_edge_ids:
                edge = self.edges.get(edge_id)
                if edge:
                    border_id = f"B_{edge.v1}_{edge.v2}"
                    if border_id in self.borders and border_id not in face.borders:
                        face.borders.append(border_id)
            # Clean up temporary attribute
            if hasattr(face, '_temp_edge_ids'):
                delattr(face, '_temp_edge_ids')
    
    def _classify_edge_types(self):
        """
        Classify edges based on their adjacent faces.
        
        Edge types:
        - "map-edge": Only one face (boundary of the map)
        - "coast": Adjacent faces are land and sea (land-sea boundary)
        - "impassable": Adjacent faces involve impassable terrain (land-impassable or sea-impassable)
        - "land": Both adjacent faces are land
        - "sea": Both adjacent faces are sea
        """
        for edge_id, edge in self.edges.items():
            if edge.right_face is None:
                # Only one face - this is a map boundary
                edge.type = "map-edge"
            else:
                # Two faces - check their types
                left_face = self.faces.get(edge.left_face)
                right_face = self.faces.get(edge.right_face)
                
                if left_face and right_face:
                    left_type = left_face.type
                    right_type = right_face.type
                    
                    if left_type == right_type:
                        # Same type - use that type (land, sea, or impassable)
                        edge.type = left_type
                    elif "impassable" in (left_type, right_type):
                        # One side is impassable - this is an impassable border
                        edge.type = "impassable"
                    elif set([left_type, right_type]) == {"land", "sea"}:
                        # Land-sea boundary - this is a coastline
                        edge.type = "coast"
                    else:
                        # Fallback for any other combination
                        edge.type = "land"
                else:
                    print(f"WARNING: Edge {edge_id} references non-existent face")
    
    def _to_dicts(self) -> Tuple[Dict, Dict, Dict]:
        """
        Convert internal objects to dictionary representations.
        
        Returns:
            Tuple of (vertices_dict, edges_dict, faces_dict)
            Note: borders_dict is accessed via self.borders for full topology output
        """
        vertices_dict = [v.to_dict() for v in self.vertices.values()]
        edges_dict = {e_id: e.to_dict() for e_id, e in self.edges.items()}
        faces_dict = {f_id: f.to_dict() for f_id, f in self.faces.items()}
        
        return vertices_dict, edges_dict, faces_dict
    
    def get_borders_dict(self) -> Dict[str, dict]:
        """
        Get borders as a dictionary.
        
        Returns:
            Dictionary mapping border_id to border data
        """
        return {b_id: b.to_dict() for b_id, b in self.borders.items()}
    
    def get_adjacency_from_topology(self) -> Dict[str, List[str]]:
        """
        Derive adjacency relationships from edge topology.
        
        Two faces are neighbors if they share an edge.
        
        Returns:
            Dictionary mapping face_id to list of neighbor face_ids
        """
        adjacency = {face_id: [] for face_id in self.faces}
        
        for edge in self.edges.values():
            if edge.left_face and edge.right_face:
                # Both faces exist - they're neighbors
                adjacency[edge.left_face].append(edge.right_face)
                adjacency[edge.right_face].append(edge.left_face)
        
        return adjacency


def convert_cells_to_topology(cells: Dict[str, dict]) -> dict:
    """
    Convenience function to convert cells to topology.
    
    Args:
        cells: Dictionary of cell data
        
    Returns:
        Dictionary with "vertices", "edges", "faces", and "borders" keys
    """
    converter = TopologyConverter()
    vertices, edges, faces = converter.convert_cells_to_topology(cells)
    borders = converter.get_borders_dict()
    
    return {
        "vertices": vertices,
        "edges": edges,
        "faces": faces,
        "borders": borders
    }


def get_face_edges(face_data: dict, borders: Dict[str, dict]) -> List[str]:
    """
    Get the list of edge IDs for a face by looking up its borders.
    
    Since faces now only contain borders (not edges directly), this helper
    function retrieves the edges by iterating through the face's borders.
    
    Args:
        face_data: Face dictionary with 'borders' list
        borders: Dictionary of border data with 'edges' list
        
    Returns:
        List of edge IDs forming the face perimeter
    """
    edge_ids = []
    for border_id in face_data.get('borders', []):
        if border_id in borders:
            border = borders[border_id]
            edge_ids.extend(border.get('edges', []))
    return edge_ids


def _derive_adjacency_from_data(data: Dict[str, dict]) -> Dict[str, List[str]]:
    """
    Internal helper to derive adjacency from data with left_face/right_face fields.
    
    Works with both edges and borders since they share the same structure.
    
    Args:
        data: Dictionary of edge or border data with left_face and right_face
        
    Returns:
        Dictionary mapping face_id to list of neighbor face_ids
    """
    adjacency = {}
    
    for item_data in data.values():
        left_face = item_data.get("left_face")
        right_face = item_data.get("right_face")
        
        if left_face and right_face:
            # Initialize lists if needed
            if left_face not in adjacency:
                adjacency[left_face] = []
            if right_face not in adjacency:
                adjacency[right_face] = []
            
            # Add mutual adjacency
            if right_face not in adjacency[left_face]:
                adjacency[left_face].append(right_face)
            if left_face not in adjacency[right_face]:
                adjacency[right_face].append(left_face)
    
    return adjacency


def get_adjacency_from_borders(borders: Dict[str, dict]) -> Dict[str, List[str]]:
    """
    Derive face adjacency from borders.
    
    Borders are the proper abstraction layer between faces and edges.
    Each border represents the boundary between two faces and contains
    the left_face and right_face references. This is the preferred way
    to derive adjacency as it works correctly whether edges have been
    subdivided or not.
    
    Args:
        borders: Dictionary of border data with left_face and right_face
        
    Returns:
        Dictionary mapping face_id to list of neighbor face_ids
    """
    return _derive_adjacency_from_data(borders)


def get_adjacency_from_topology(edges: Dict[str, dict], borders: Optional[Dict[str, dict]] = None) -> Dict[str, List[str]]:
    """
    Derive face adjacency from topology data.
    
    This function prefers borders when available (the proper abstraction layer),
    but falls back to edges for backward compatibility with older topology data.
    
    Args:
        edges: Dictionary of edge data with left_face and right_face
        borders: Optional dictionary of border data (preferred when available)
        
    Returns:
        Dictionary mapping face_id to list of neighbor face_ids
    """
    # Prefer borders when available - they are the proper abstraction layer
    if borders:
        return _derive_adjacency_from_data(borders)
    
    # Fall back to edges for backward compatibility
    return _derive_adjacency_from_data(edges)


def get_coastal_faces_from_borders(borders: Dict[str, dict]) -> set:
    """
    Determine which faces are coastal by checking border types.
    
    A face is coastal if it has at least one border of type "coast".
    This is the preferred method as it uses borders (the proper abstraction
    layer) rather than iterating over individual edges.
    
    Args:
        borders: Dictionary of border data from topology
        
    Returns:
        Set of face IDs that are coastal
    """
    coastal_faces = set()
    for border_data in borders.values():
        if border_data.get("type") == "coast":
            left_face = border_data.get("left_face")
            right_face = border_data.get("right_face")
            if left_face:
                coastal_faces.add(left_face)
            if right_face:
                coastal_faces.add(right_face)
    return coastal_faces


def reconstruct_cells_from_topology(topology: dict) -> Dict[str, dict]:
    """
    Reconstruct a cell-centric structure from topology for internal processing.
    
    This is used by phases that need to work with cell-like data structures
    temporarily during processing (e.g., for terrain assignment or connectivity checks).
    
    Args:
        topology: Topology dictionary with vertices, edges, borders, and faces
        
    Returns:
        Dictionary of cells with id, type, center, vertices, and neighbors
    """
    # Create vertex lookup
    vertex_coords = {v['id']: v['coords'] for v in topology['vertices']}
    borders = topology.get('borders', {})
    # Use borders for adjacency (proper abstraction layer), with edge fallback
    adjacency = get_adjacency_from_topology(topology['edges'], borders)
    
    cells = {}
    for face_id, face_data in topology['faces'].items():
        # Get edge IDs through borders
        edge_ids = get_face_edges(face_data, borders)
        vertices = []
        
        # Build vertex graph from edges
        vertex_graph = {}
        for edge_id in edge_ids:
            if edge_id in topology['edges']:
                edge = topology['edges'][edge_id]
                v1, v2 = edge['v1'], edge['v2']
                if v1 not in vertex_graph:
                    vertex_graph[v1] = []
                if v2 not in vertex_graph:
                    vertex_graph[v2] = []
                vertex_graph[v1].append(v2)
                vertex_graph[v2].append(v1)
        
        # Trace polygon boundary
        if vertex_graph:
            start_vertex = next(iter(vertex_graph.keys()))
            current = start_vertex
            visited = set()
            
            for _ in range(len(vertex_graph) + 1):
                if current in visited and current == start_vertex and len(visited) > 0:
                    break
                if current in visited:
                    break
                visited.add(current)
                if current in vertex_coords:
                    vertices.append(vertex_coords[current])
                
                # Find next vertex
                neighbors = vertex_graph.get(current, [])
                next_vertex = None
                for neighbor in neighbors:
                    if neighbor not in visited or (neighbor == start_vertex and len(visited) == len(vertex_graph)):
                        next_vertex = neighbor
                        break
                if next_vertex is None:
                    break
                current = next_vertex
        
        cells[face_id] = {
            'id': face_id,
            'type': face_data.get('type', 'land'),
            'center': face_data.get('center', [0.5, 0.5]),
            'vertices': vertices,
            'neighbors': adjacency.get(face_id, []),
            'coastal': face_data.get('coastal', False)
        }
    
    return cells
