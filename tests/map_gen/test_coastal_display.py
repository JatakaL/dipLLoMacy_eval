#!/usr/bin/env python3
"""
Test that coastal provinces are correctly preserved and displayed.

This test verifies the fix for the issue where coastal provinces were not
displaying properly in the map viewer.
"""

import sys
import json
import tempfile
import os
from pathlib import Path

# Add map_gen to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'map_gen'))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'map_gen' / 'phases'))

from topology import convert_cells_to_topology, reconstruct_cells_from_topology
from phase3_provinces import identify_coastlines


def test_coastal_property_in_topology():
    """Test that coastal property is preserved in topology."""
    
    # Create sample cells with coastal designation
    cells = {
        'C1': {
            'id': 'C1',
            'type': 'land',
            'center': [0.5, 0.5],
            'vertices': [[0.3, 0.3], [0.7, 0.3], [0.7, 0.7], [0.3, 0.7]],
            'neighbors': ['C2', 'C3'],
            'coastal': True
        },
        'C2': {
            'id': 'C2',
            'type': 'sea',
            'center': [0.5, 0.8],
            'vertices': [[0.3, 0.7], [0.7, 0.7], [0.7, 0.9], [0.3, 0.9]],
            'neighbors': ['C1', 'C3'],
            'coastal': False
        },
        'C3': {
            'id': 'C3',
            'type': 'land',
            'center': [0.5, 0.2],
            'vertices': [[0.3, 0.1], [0.7, 0.1], [0.7, 0.3], [0.3, 0.3]],
            'neighbors': ['C1', 'C2'],
            'coastal': False
        }
    }
    
    # Convert to topology
    topology = convert_cells_to_topology(cells)
    
    # Check that coastal property is in topology faces
    assert 'faces' in topology
    assert 'C1' in topology['faces']
    assert 'coastal' in topology['faces']['C1'], "Coastal property not found in topology face C1"
    assert topology['faces']['C1']['coastal'] is True, "C1 should be coastal"
    assert 'C3' in topology['faces']
    # C3 should not have coastal=True in the output (only included if True)
    assert topology['faces']['C3'].get('coastal', False) is False, "C3 should not be coastal"
    
    print("✓ Coastal property preserved in topology")


def test_coastal_property_in_reconstruction():
    """Test that coastal property is preserved when reconstructing cells from topology."""
    
    # Create topology with coastal property
    topology = {
        'vertices': [
            {'id': 0, 'coords': [0.3, 0.3]},
            {'id': 1, 'coords': [0.7, 0.3]},
            {'id': 2, 'coords': [0.7, 0.7]},
            {'id': 3, 'coords': [0.3, 0.7]},
            {'id': 4, 'coords': [0.3, 0.9]},
            {'id': 5, 'coords': [0.7, 0.9]},
        ],
        'edges': {
            'E_0_1': {'v1': 0, 'v2': 1, 'left_face': 'C1', 'type': 'land'},
            'E_1_2': {'v1': 1, 'v2': 2, 'left_face': 'C1', 'right_face': 'C2', 'type': 'coast'},
            'E_2_3': {'v1': 2, 'v2': 3, 'left_face': 'C1', 'type': 'land'},
            'E_0_3': {'v1': 0, 'v2': 3, 'left_face': 'C1', 'type': 'land'},
            'E_3_4': {'v1': 3, 'v2': 4, 'left_face': 'C2', 'type': 'sea'},
            'E_4_5': {'v1': 4, 'v2': 5, 'left_face': 'C2', 'type': 'sea'},
            'E_2_5': {'v1': 2, 'v2': 5, 'left_face': 'C2', 'type': 'sea'},
        },
        'faces': {
            'C1': {
                'type': 'land',
                'center': [0.5, 0.5],
                'edges': ['E_0_1', 'E_1_2', 'E_2_3', 'E_0_3'],
                'coastal': True
            },
            'C2': {
                'type': 'sea',
                'center': [0.5, 0.8],
                'edges': ['E_1_2', 'E_3_4', 'E_4_5', 'E_2_5'],
                'coastal': False
            }
        }
    }
    
    # Reconstruct cells
    cells = reconstruct_cells_from_topology(topology)
    
    # Check that coastal property is preserved
    assert 'C1' in cells
    assert 'coastal' in cells['C1'], "Coastal property not found in reconstructed cell C1"
    assert cells['C1']['coastal'] is True, "C1 should be coastal after reconstruction"
    assert cells['C2']['coastal'] is False, "C2 should not be coastal"
    
    print("✓ Coastal property preserved in reconstruction")


def test_map_viewer_cli_reconstruction():
    """Test that map viewer CLI correctly reconstructs cells with coastal property."""
    import matplotlib
    matplotlib.use('Agg')
    
    # Import after setting backend
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from map_viewer_cli import MapData
    
    # Create a temporary JSON file with topology
    test_data = {
        'config': {'num_cells': 2},
        'topology': {
            'vertices': [
                {'id': 0, 'coords': [0.3, 0.3]},
                {'id': 1, 'coords': [0.7, 0.3]},
                {'id': 2, 'coords': [0.7, 0.7]},
                {'id': 3, 'coords': [0.3, 0.7]},
            ],
            'edges': {
                'E_0_1': {'v1': 0, 'v2': 1, 'left_face': 'C1'},
                'E_1_2': {'v1': 1, 'v2': 2, 'left_face': 'C1', 'right_face': 'C2'},
                'E_2_3': {'v1': 2, 'v2': 3, 'left_face': 'C1'},
                'E_0_3': {'v1': 0, 'v2': 3, 'left_face': 'C1'},
            },
            'faces': {
                'C1': {
                    'type': 'land',
                    'center': [0.5, 0.5],
                    'edges': ['E_0_1', 'E_1_2', 'E_2_3', 'E_0_3'],
                    'coastal': True
                },
                'C2': {
                    'type': 'sea',
                    'center': [0.5, 0.8],
                    'edges': ['E_1_2'],
                    'coastal': False
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_data, f)
        temp_file = f.name
    
    try:
        # Load with MapData
        map_data = MapData(temp_file)
        
        # Check reconstruction
        assert len(map_data.cells) > 0, "Cells should be reconstructed"
        assert 'C1' in map_data.cells, "C1 should be in reconstructed cells"
        assert map_data.cells['C1']['coastal'] is True, "C1 should be coastal in MapData"
        
        print("✓ Map viewer CLI reconstruction preserves coastal property")
    finally:
        os.unlink(temp_file)


def test_phase3_integration():
    """Test full phase 3 pipeline preserves coastal property."""
    from phase1_mesh import run_phase1
    from phase2_terrain import run_phase2
    from phase3_provinces import run_phase3
    
    # Create minimal config
    config = {
        'width': 1.0,
        'height': 1.0,
        'num_cells': 20,
        'land_ratio': 0.6,
        'seed': 42
    }
    
    # Run phases
    phase1_output = run_phase1(config)
    phase2_output = run_phase2(phase1_output, config)
    phase3_output = run_phase3(phase2_output, {'num_impassable_zones': 0, 'seed': 42})
    
    # Check that topology has coastal information
    topology = phase3_output['topology']
    faces = topology['faces']
    
    # Count coastal faces
    coastal_faces = [fid for fid, fdata in faces.items() 
                     if fdata.get('type') == 'land' and fdata.get('coastal', False)]
    land_faces = [fid for fid, fdata in faces.items() if fdata.get('type') == 'land']
    
    assert len(coastal_faces) > 0, "Should have some coastal faces"
    assert len(coastal_faces) < len(land_faces), "Not all land faces should be coastal"
    
    print(f"✓ Phase 3 integration: {len(coastal_faces)} coastal faces out of {len(land_faces)} land faces")


if __name__ == '__main__':
    print("Testing coastal property preservation...")
    print()
    
    test_coastal_property_in_topology()
    test_coastal_property_in_reconstruction()
    test_map_viewer_cli_reconstruction()
    test_phase3_integration()
    
    print()
    print("=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
