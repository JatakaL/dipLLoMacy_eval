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


class Face:
    """Represents a territory/cell defined by its boundary edges."""
    
    def __init__(self, face_id: str, face_type: str):
        """
        Initialize a face.
        
        Args:
            face_id: Unique identifier for this face
            face_type: Type of face ("land" or "sea")
        """
        self.id = face_id
        self.type = face_type
        self.edges: List[str] = []  # Ordered list of edge IDs forming the perimeter
        self.center: Optional[Tuple[float, float]] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        result = {
            "type": self.type,
            "edges": self.edges,
        }
        if self.center is not None:
            result["center"] = list(self.center)
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
            
            # Store the ordered edges for this face
            face.edges = edge_ids
            self.faces[cell_id] = face
        
        print(f"Created {len(self.vertices)} vertices, {len(self.edges)} edges, {len(self.faces)} faces")
        
        # Classify edge types
        self._classify_edge_types()
        
        return self._to_dicts()
    
    def _classify_edge_types(self):
        """
        Classify edges based on their adjacent faces.
        
        Edge types:
        - "map-edge": Only one face (boundary of the map)
        - "coast": Adjacent faces have different types (land-sea boundary)
        - "land": Both adjacent faces are land
        - "sea": Both adjacent faces are sea (though we might not distinguish this)
        """
        for edge_id, edge in self.edges.items():
            if edge.right_face is None:
                # Only one face - this is a map boundary
                edge.type = "map-edge"
            else:
                # Two faces - check if they're the same type
                left_face = self.faces.get(edge.left_face)
                right_face = self.faces.get(edge.right_face)
                
                if left_face and right_face:
                    if left_face.type != right_face.type:
                        edge.type = "coast"
                    else:
                        edge.type = left_face.type  # "land" or "sea"
                else:
                    print(f"WARNING: Edge {edge_id} references non-existent face")
    
    def _to_dicts(self) -> Tuple[Dict, Dict, Dict]:
        """
        Convert internal objects to dictionary representations.
        
        Returns:
            Tuple of (vertices_dict, edges_dict, faces_dict)
        """
        vertices_dict = [v.to_dict() for v in self.vertices.values()]
        edges_dict = {e_id: e.to_dict() for e_id, e in self.edges.items()}
        faces_dict = {f_id: f.to_dict() for f_id, f in self.faces.items()}
        
        return vertices_dict, edges_dict, faces_dict
    
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
        Dictionary with "vertices", "edges", and "faces" keys
    """
    converter = TopologyConverter()
    vertices, edges, faces = converter.convert_cells_to_topology(cells)
    
    return {
        "vertices": vertices,
        "edges": edges,
        "faces": faces
    }


def get_adjacency_from_topology(edges: Dict[str, dict]) -> Dict[str, List[str]]:
    """
    Derive face adjacency from edges.
    
    Args:
        edges: Dictionary of edge data with left_face and right_face
        
    Returns:
        Dictionary mapping face_id to list of neighbor face_ids
    """
    adjacency = {}
    
    for edge_data in edges.values():
        left_face = edge_data.get("left_face")
        right_face = edge_data.get("right_face")
        
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


def reconstruct_cells_from_topology(topology: dict) -> Dict[str, dict]:
    """
    Reconstruct a cell-centric structure from topology for internal processing.
    
    This is used by phases that need to work with cell-like data structures
    temporarily during processing (e.g., for terrain assignment or connectivity checks).
    
    Args:
        topology: Topology dictionary with vertices, edges, and faces
        
    Returns:
        Dictionary of cells with id, type, center, vertices, and neighbors
    """
    # Create vertex lookup
    vertex_coords = {v['id']: v['coords'] for v in topology['vertices']}
    adjacency = get_adjacency_from_topology(topology['edges'])
    
    cells = {}
    for face_id, face_data in topology['faces'].items():
        # Reconstruct polygon vertices from edges
        edge_ids = face_data.get('edges', [])
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
