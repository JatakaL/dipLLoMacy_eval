"""
Tests for the label_positions module.

Tests the label position calculation functionality including:
- Basic position calculation
- Handling of supply centers
- Fallback behavior when Shapely is not available
- Integration with topology data
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from map_gen.label_positions import (
    calculate_label_positions,
    calculate_all_label_positions,
    _calculate_centroid,
    _fallback_positions,
    SHAPELY_AVAILABLE,
    DEFAULT_ELEMENT_SPACING
)


class TestLabelPositionCalculation:
    """Tests for basic label position calculation."""
    
    def test_simple_square_polygon(self):
        """Test position calculation for a simple square polygon."""
        # Simple unit square
        vertices = [[0, 0], [1, 0], [1, 1], [0, 1]]
        
        positions = calculate_label_positions(vertices, has_supply_center=False)
        
        # Should have name_position and unit_position
        assert 'name_position' in positions
        assert 'unit_position' in positions
        assert 'sc_position' not in positions
        
        # Positions should be within the polygon bounds
        for key, pos in positions.items():
            assert 0 <= pos[0] <= 1, f"{key} x coord out of bounds"
            assert 0 <= pos[1] <= 1, f"{key} y coord out of bounds"
    
    def test_square_polygon_with_sc(self):
        """Test position calculation for a polygon with supply center."""
        # Simple unit square
        vertices = [[0, 0], [1, 0], [1, 1], [0, 1]]
        
        positions = calculate_label_positions(vertices, has_supply_center=True)
        
        # Should have all three positions
        assert 'name_position' in positions
        assert 'sc_position' in positions
        assert 'unit_position' in positions
        
        # All positions should be within bounds
        for key, pos in positions.items():
            assert 0 <= pos[0] <= 1, f"{key} x coord out of bounds"
            assert 0 <= pos[1] <= 1, f"{key} y coord out of bounds"
    
    def test_positions_are_different(self):
        """Test that positions for different elements are not identical."""
        vertices = [[0, 0], [1, 0], [1, 1], [0, 1]]
        
        positions = calculate_label_positions(vertices, has_supply_center=True)
        
        # Positions should be distinct
        name_pos = tuple(positions['name_position'])
        sc_pos = tuple(positions['sc_position'])
        unit_pos = tuple(positions['unit_position'])
        
        # Positions should be distinct from each other in a normally-sized polygon
        # The positions are stacked vertically, so at minimum the y-coordinates differ
        all_same = (name_pos == sc_pos == unit_pos)
        assert not all_same, "All three positions should not be identical in a normal polygon"
    
    def test_empty_polygon(self):
        """Test handling of empty polygon."""
        positions = calculate_label_positions([], has_supply_center=False)
        
        # Should return fallback positions at default center
        assert 'name_position' in positions
        assert 'unit_position' in positions
    
    def test_too_few_vertices(self):
        """Test handling of polygon with too few vertices."""
        positions = calculate_label_positions([[0, 0], [1, 1]], has_supply_center=False)
        
        # Should return fallback positions
        assert 'name_position' in positions
        assert 'unit_position' in positions
    
    def test_irregular_polygon(self):
        """Test position calculation for an irregular polygon."""
        # L-shaped polygon
        vertices = [
            [0, 0], [0.5, 0], [0.5, 0.5], 
            [1, 0.5], [1, 1], [0, 1]
        ]
        
        positions = calculate_label_positions(vertices, has_supply_center=True)
        
        # Should have all positions
        assert 'name_position' in positions
        assert 'sc_position' in positions
        assert 'unit_position' in positions
    
    def test_unit_position_always_present(self):
        """Test that unit_position is always created regardless of SC status."""
        vertices = [[0.3, 0.3], [0.4, 0.3], [0.4, 0.4], [0.3, 0.4]]
        
        # With SC
        positions_with_sc = calculate_label_positions(vertices, has_supply_center=True)
        assert 'unit_position' in positions_with_sc, "unit_position should exist with SC"
        
        # Without SC
        positions_no_sc = calculate_label_positions(vertices, has_supply_center=False)
        assert 'unit_position' in positions_no_sc, "unit_position should exist without SC"
    
    def test_vertical_ordering_with_sc(self):
        """Test that name is at top, SC in middle, unit at bottom (higher Y = north)."""
        vertices = [[0.2, 0.2], [0.5, 0.2], [0.5, 0.5], [0.2, 0.5]]
        
        positions = calculate_label_positions(vertices, has_supply_center=True)
        
        name_y = positions['name_position'][1]
        sc_y = positions['sc_position'][1]
        unit_y = positions['unit_position'][1]
        
        # Name should be highest (northern), unit lowest (southern)
        assert name_y >= sc_y, "Name should be at or above SC (northern position)"
        assert sc_y >= unit_y, "SC should be at or above unit"
    
    def test_sufficient_spacing(self):
        """Test that there is sufficient spacing between elements."""
        vertices = [[0.2, 0.2], [0.5, 0.2], [0.5, 0.5], [0.2, 0.5]]
        
        positions = calculate_label_positions(vertices, has_supply_center=True)
        
        sc_y = positions['sc_position'][1]
        unit_y = positions['unit_position'][1]
        
        # Spacing between SC and unit should be at least 80% of default element spacing
        min_expected_spacing = DEFAULT_ELEMENT_SPACING * 0.8
        spacing = abs(sc_y - unit_y)
        assert spacing >= min_expected_spacing, f"SC-Unit spacing ({spacing}) should be at least {min_expected_spacing}"


class TestCentroidCalculation:
    """Tests for centroid calculation."""
    
    def test_square_centroid(self):
        """Test centroid of a unit square."""
        vertices = [[0, 0], [1, 0], [1, 1], [0, 1]]
        centroid = _calculate_centroid(vertices)
        
        assert abs(centroid[0] - 0.5) < 0.001
        assert abs(centroid[1] - 0.5) < 0.001
    
    def test_triangle_centroid(self):
        """Test centroid of a triangle."""
        vertices = [[0, 0], [1, 0], [0.5, 1]]
        centroid = _calculate_centroid(vertices)
        
        assert abs(centroid[0] - 0.5) < 0.001
        assert abs(centroid[1] - 1/3) < 0.001
    
    def test_empty_vertices(self):
        """Test centroid with empty vertices."""
        centroid = _calculate_centroid([])
        assert centroid == [0.5, 0.5]  # Default fallback


class TestFallbackPositions:
    """Tests for fallback position calculation."""
    
    def test_fallback_no_sc(self):
        """Test fallback positions without supply center."""
        center = [0.5, 0.5]
        positions = _fallback_positions(center, has_supply_center=False, element_spacing=0.015)
        
        assert 'name_position' in positions
        assert 'unit_position' in positions
        assert 'sc_position' not in positions
        
        # Name should be above unit
        assert positions['name_position'][1] > positions['unit_position'][1]
    
    def test_fallback_with_sc(self):
        """Test fallback positions with supply center."""
        center = [0.5, 0.5]
        positions = _fallback_positions(center, has_supply_center=True, element_spacing=0.015)
        
        assert 'name_position' in positions
        assert 'sc_position' in positions
        assert 'unit_position' in positions
        
        # Name should be above SC, SC above unit
        assert positions['name_position'][1] > positions['sc_position'][1]
        assert positions['sc_position'][1] > positions['unit_position'][1]


class TestCalculateAllLabelPositions:
    """Tests for calculating positions for all faces."""
    
    @staticmethod
    def _create_simple_topology():
        """Create a simple topology for testing."""
        return {
            'vertices': [
                {'id': 0, 'coords': [0, 0]},
                {'id': 1, 'coords': [1, 0]},
                {'id': 2, 'coords': [1, 1]},
                {'id': 3, 'coords': [0, 1]},
            ],
            'edges': {
                'E_0_1': {'v1': 0, 'v2': 1},
                'E_1_2': {'v1': 1, 'v2': 2},
                'E_2_3': {'v1': 2, 'v2': 3},
                'E_0_3': {'v1': 0, 'v2': 3},
            },
            'borders': {
                'B_0_1': {'edges': ['E_0_1']},
                'B_1_2': {'edges': ['E_1_2']},
                'B_2_3': {'edges': ['E_2_3']},
                'B_0_3': {'edges': ['E_0_3']},
            },
            'faces': {
                'C1': {
                    'type': 'land',
                    'center': [0.5, 0.5],
                    'borders': ['B_0_1', 'B_1_2', 'B_2_3', 'B_0_3'],
                    'is_supply_center': True,
                },
            }
        }
    
    def test_calculate_all_positions(self):
        """Test calculating positions for all faces in topology."""
        topology = self._create_simple_topology()
        faces = topology['faces']
        
        updated_faces = calculate_all_label_positions(faces, topology)
        
        # All faces should have label_positions
        for face_id, face_data in updated_faces.items():
            assert 'label_positions' in face_data, f"Face {face_id} missing label_positions"
            
            positions = face_data['label_positions']
            assert 'name_position' in positions
            assert 'unit_position' in positions
            
            # Since C1 has supply center
            if face_data.get('is_supply_center', False):
                assert 'sc_position' in positions


class TestShapelyDependency:
    """Tests for Shapely dependency handling."""
    
    def test_shapely_availability(self):
        """Test that Shapely availability is correctly detected."""
        # This test just verifies the flag exists and is boolean
        assert isinstance(SHAPELY_AVAILABLE, bool)
    
    def test_works_without_shapely(self):
        """Test that calculation works even if Shapely is unavailable."""
        # We can't easily disable Shapely, but we can test the fallback path
        vertices = [[0, 0], [1, 0], [1, 1], [0, 1]]
        
        # This should work regardless of Shapely availability
        positions = calculate_label_positions(vertices, has_supply_center=False)
        
        assert 'name_position' in positions
        assert 'unit_position' in positions


def run_tests():
    """Run all tests and report results."""
    test_classes = [
        TestLabelPositionCalculation,
        TestCentroidCalculation,
        TestFallbackPositions,
        TestCalculateAllLabelPositions,
        TestShapelyDependency,
    ]
    
    total = 0
    passed = 0
    failed = 0
    
    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        instance = test_class()
        
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                total += 1
                try:
                    getattr(instance, method_name)()
                    print(f"  ✓ {method_name}")
                    passed += 1
                except Exception as e:
                    print(f"  ✗ {method_name}: {e}")
                    failed += 1
    
    print(f"\n{'='*50}")
    print(f"Results: {passed}/{total} passed, {failed} failed")
    
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
