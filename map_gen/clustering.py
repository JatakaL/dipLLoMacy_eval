"""
Clustering Module

This module provides various clustering algorithms for grouping cells into regions.
"""

import numpy as np
import networkx as nx
import random

def robust_cluster_cells(cells, target_count, cell_adjacency, cells_data):
    """Robust clustering that ensures all cells are assigned."""
    if len(cells) <= target_count:
        return [[cell] for cell in cells]
    
    print(f"Clustering {len(cells)} cells into {target_count} regions")
    
    # Try multiple clustering approaches in order of preference
    
    # Approach 1: NetworkX-based spatial clustering
    try:
        clusters = networkx_spatial_clustering(cells, target_count, cell_adjacency, cells_data)
        if _validate_clustering(clusters, cells):
            print("  Success with NetworkX spatial clustering")
            return clusters
    except Exception as e:
        print(f"  NetworkX clustering failed: {e}")
    
    # Approach 2: Simple geographic clustering
    try:
        clusters = geographic_clustering(cells, target_count, cells_data)
        if _validate_clustering(clusters, cells):
            print("  Success with geographic clustering")
            return clusters
    except Exception as e:
        print(f"  Geographic clustering failed: {e}")
    
    # Approach 3: Connected component partitioning
    try:
        clusters = connected_partitioning(cells, target_count, cell_adjacency)
        if _validate_clustering(clusters, cells):
            print("  Success with connected partitioning")
            return clusters
    except Exception as e:
        print(f"  Connected partitioning failed: {e}")
    
    # Fallback: Simple sequential partitioning (guaranteed to work)
    print("  Using fallback sequential partitioning")
    return sequential_partitioning(cells, target_count)

def networkx_spatial_clustering(cells, target_count, cell_adjacency, cells_data):
    """Use NetworkX and spatial proximity for clustering."""
    # Create subgraph
    subgraph = cell_adjacency.subgraph(cells)
    
    if not nx.is_connected(subgraph):
        # Handle each component separately
        components = list(nx.connected_components(subgraph))
        all_clusters = []
        
        for component in components:
            comp_cells = list(component)
            comp_target = max(1, len(comp_cells) * target_count // len(cells))
            comp_clusters = robust_cluster_cells(comp_cells, comp_target, cell_adjacency, cells_data)
            all_clusters.extend(comp_clusters)
        
        return all_clusters
    
    # Try sklearn clustering with connectivity
    positions = np.array([cells_data[cell]["center"] for cell in cells])
    
    # Build connectivity matrix
    cell_to_idx = {cell: i for i, cell in enumerate(cells)}
    n = len(cells)
    connectivity = np.zeros((n, n))
    
    for cell1, cell2 in subgraph.edges():
        i, j = cell_to_idx[cell1], cell_to_idx[cell2]
        connectivity[i, j] = 1
        connectivity[j, i] = 1
    
    from sklearn.cluster import AgglomerativeClustering
    clustering = AgglomerativeClustering(
        n_clusters=target_count,
        connectivity=connectivity,
        linkage='ward'
    )
    
    labels = clustering.fit_predict(positions)
    
    # Group cells by cluster
    clusters = {}
    for i, cell in enumerate(cells):
        label = labels[i]
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(cell)
    
    return list(clusters.values())

def geographic_clustering(cells, target_count, cells_data):
    """Simple geographic clustering using KMeans."""
    positions = np.array([cells_data[cell]["center"] for cell in cells])
    
    from sklearn.cluster import KMeans
    kmeans = KMeans(n_clusters=target_count, random_state=42)
    labels = kmeans.fit_predict(positions)
    
    # Group cells by cluster
    clusters = {}
    for i, cell in enumerate(cells):
        label = labels[i]
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(cell)
    
    return list(clusters.values())

def connected_partitioning(cells, target_count, cell_adjacency):
    """Partition based on graph connectivity."""
    subgraph = cell_adjacency.subgraph(cells)
    
    # Use NetworkX community detection
    import networkx.algorithms.community as nx_comm
    
    # Try different community detection methods
    try:
        communities = list(nx_comm.greedy_modularity_communities(subgraph))
    except:
        # Fallback to simple partitioning
        return sequential_partitioning(cells, target_count)
    
    # If we have too many communities, merge the smallest ones
    while len(communities) > target_count:
        # Find two smallest communities to merge
        sizes = [(len(comm), i) for i, comm in enumerate(communities)]
        sizes.sort()
        
        # Merge the two smallest
        _, idx1 = sizes[0]
        _, idx2 = sizes[1]
        
        merged = communities[idx1] | communities[idx2]
        communities = [comm for i, comm in enumerate(communities) if i not in [idx1, idx2]]
        communities.append(merged)
    
    # If we have too few communities, split the largest ones
    while len(communities) < target_count:
        # Find largest community to split
        largest_idx = max(range(len(communities)), key=lambda i: len(communities[i]))
        largest = list(communities[largest_idx])
        
        if len(largest) <= 1:
            break  # Can't split further
        
        # Split roughly in half
        mid = len(largest) // 2
        part1 = largest[:mid]
        part2 = largest[mid:]
        
        communities[largest_idx] = set(part1)
        communities.append(set(part2))
    
    return [list(comm) for comm in communities]

def sequential_partitioning(cells, target_count):
    """Simple sequential partitioning - guaranteed to work."""
    cells_per_cluster = len(cells) // target_count
    remainder = len(cells) % target_count
    
    clusters = []
    start_idx = 0
    
    for i in range(target_count):
        # Some clusters get one extra cell to handle remainder
        cluster_size = cells_per_cluster + (1 if i < remainder else 0)
        cluster = cells[start_idx:start_idx + cluster_size]
        
        if cluster:  # Only add non-empty clusters
            clusters.append(cluster)
        
        start_idx += cluster_size
    
    return clusters

def _validate_clustering(clusters, original_cells):
    """Validate that clustering assigned all cells exactly once."""
    assigned_cells = set()
    
    for i, cluster in enumerate(clusters):
        if not cluster:  # Empty cluster
            print(f"    Empty cluster {i} found!")
            return False
        for cell in cluster:
            if cell in assigned_cells:  # Duplicate assignment
                print(f"    Duplicate assignment: cell {cell} in multiple clusters")
                return False
            assigned_cells.add(cell)
    
    missing_cells = set(original_cells) - assigned_cells
    extra_cells = assigned_cells - set(original_cells)
    
    if missing_cells:
        print(f"    Missing cells: {len(missing_cells)} cells not assigned to any cluster")
        print(f"    Sample missing: {list(missing_cells)[:5]}")
        return False
        
    if extra_cells:
        print(f"    Extra cells: {len(extra_cells)} unknown cells assigned")
        return False
    
    print(f"    Validation passed: {len(assigned_cells)} cells properly assigned to {len(clusters)} clusters")
    return True
