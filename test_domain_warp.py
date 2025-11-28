#!/usr/bin/env python3
"""
Tests for domain warping (distortion fields) functionality in Phase 1.

These tests verify the domain warping algorithm that creates stretched,
organic continent shapes by distorting space before Voronoi generation.
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'map_gen', 'phases'))
from phase1_mesh import (
    generate_perlin_noise_2d,
    sample_noise_at_point,
    apply_domain_warp,
    run_phase1
)


def test_perlin_noise_generation():
    """Test that Perlin noise is generated with expected properties."""
    noise = generate_perlin_noise_2d((100, 100), (4, 4), seed=42)
    
    # Check shape
    assert noise.shape == (100, 100), f"Expected shape (100, 100), got {noise.shape}"
    
    # Check range - Perlin noise should be roughly in [-1, 1]
    assert noise.min() >= -1.5, f"Noise min {noise.min()} too low"
    assert noise.max() <= 1.5, f"Noise max {noise.max()} too high"
    
    # Check reproducibility with same seed
    noise2 = generate_perlin_noise_2d((100, 100), (4, 4), seed=42)
    assert np.allclose(noise, noise2), "Noise should be reproducible with same seed"
    
    # Check different seeds produce different results
    noise3 = generate_perlin_noise_2d((100, 100), (4, 4), seed=123)
    assert not np.allclose(noise, noise3), "Different seeds should produce different noise"
    
    print("✓ Perlin noise generation test passed")


def test_noise_sampling():
    """Test that noise sampling at points works correctly."""
    noise = generate_perlin_noise_2d((50, 50), (2, 2), seed=42)
    
    # Sample at corners
    v00 = sample_noise_at_point(noise, 0.0, 0.0, 1.0, 1.0)
    v11 = sample_noise_at_point(noise, 1.0, 1.0, 1.0, 1.0)
    
    # Verify values are within expected range
    assert -1.5 <= v00 <= 1.5, f"Sample at (0,0) = {v00} out of range"
    assert -1.5 <= v11 <= 1.5, f"Sample at (1,1) = {v11} out of range"
    
    # Sample at center
    v_center = sample_noise_at_point(noise, 0.5, 0.5, 1.0, 1.0)
    assert -1.5 <= v_center <= 1.5, f"Sample at center = {v_center} out of range"
    
    print("✓ Noise sampling test passed")


def test_domain_warp_basic():
    """Test basic domain warping functionality."""
    points = np.array([
        [0.5, 0.5],
        [0.3, 0.7],
        [0.7, 0.3],
        [0.2, 0.2],
        [0.8, 0.8]
    ])
    
    # Apply domain warping
    warped = apply_domain_warp(points, 1.0, 1.0, warp_strength=0.1, warp_frequency=2, seed=42)
    
    # Check shape preserved
    assert warped.shape == points.shape, "Warped points should have same shape"
    
    # Check points moved
    displacement = np.linalg.norm(warped - points, axis=1)
    assert np.any(displacement > 0), "Warping should move at least some points"
    
    # Check displacement is reasonable (not too large)
    max_expected_displacement = 0.1 * np.sqrt(2)  # strength * max diagonal
    assert np.all(displacement <= max_expected_displacement * 2), \
        f"Displacement too large: max={displacement.max()}"
    
    print("✓ Basic domain warp test passed")


def test_domain_warp_bounds():
    """Test that warped points stay within valid bounds."""
    # Create points near edges
    points = np.array([
        [0.05, 0.05],
        [0.95, 0.95],
        [0.05, 0.95],
        [0.95, 0.05],
        [0.5, 0.5]
    ])
    
    # Apply strong warping
    warped = apply_domain_warp(points, 1.0, 1.0, warp_strength=0.3, warp_frequency=2, seed=42)
    
    # Check all points are still within bounds (with buffer)
    buffer = 0.05
    assert np.all(warped[:, 0] >= buffer), "X coordinates should be >= buffer"
    assert np.all(warped[:, 0] <= 1.0 - buffer), "X coordinates should be <= 1-buffer"
    assert np.all(warped[:, 1] >= buffer), "Y coordinates should be >= buffer"
    assert np.all(warped[:, 1] <= 1.0 - buffer), "Y coordinates should be <= 1-buffer"
    
    print("✓ Domain warp bounds test passed")


def test_domain_warp_zero_strength():
    """Test that zero warp strength returns unchanged points."""
    points = np.array([
        [0.5, 0.5],
        [0.3, 0.7],
        [0.7, 0.3]
    ])
    
    # Apply zero warping
    warped = apply_domain_warp(points, 1.0, 1.0, warp_strength=0.0, warp_frequency=2, seed=42)
    
    # Points should be unchanged (just copied)
    assert np.allclose(warped, points), "Zero strength should not move points"
    
    print("✓ Zero warp strength test passed")


def test_domain_warp_reproducibility():
    """Test that warping is reproducible with the same seed."""
    points = np.array([
        [0.5, 0.5],
        [0.3, 0.7],
        [0.7, 0.3],
        [0.2, 0.2],
        [0.8, 0.8]
    ])
    
    warped1 = apply_domain_warp(points, 1.0, 1.0, warp_strength=0.1, warp_frequency=2, seed=42)
    warped2 = apply_domain_warp(points, 1.0, 1.0, warp_strength=0.1, warp_frequency=2, seed=42)
    
    assert np.allclose(warped1, warped2), "Same seed should produce same warp"
    
    # Different seeds should produce different results
    warped3 = apply_domain_warp(points, 1.0, 1.0, warp_strength=0.1, warp_frequency=2, seed=123)
    assert not np.allclose(warped1, warped3), "Different seeds should produce different warps"
    
    print("✓ Domain warp reproducibility test passed")


def test_phase1_with_warping():
    """Test that Phase 1 runs correctly with domain warping enabled."""
    config = {
        "num_cells": 20,
        "width": 1.0,
        "height": 1.0,
        "min_distance": 0.1,
        "lloyd_iterations": 0,
        "seed": 42,
        "warp_enabled": True,
        "warp_strength": 0.1,
        "warp_frequency": 2
    }
    
    result = run_phase1(config)
    
    # Check basic output structure
    assert "topology" in result, "Result should contain topology"
    assert "config" in result, "Result should contain config"
    assert "statistics" in result, "Result should contain statistics"
    
    # Check config preserved
    assert result["config"]["warp_enabled"] == True
    assert result["config"]["warp_strength"] == 0.1
    assert result["config"]["warp_frequency"] == 2
    
    # Check topology is valid
    topology = result["topology"]
    assert len(topology["faces"]) > 0, "Should have generated faces"
    assert len(topology["edges"]) > 0, "Should have generated edges"
    assert len(topology["vertices"]) > 0, "Should have generated vertices"
    
    print("✓ Phase 1 with warping test passed")


def test_phase1_without_warping():
    """Test that Phase 1 runs correctly with domain warping disabled."""
    config = {
        "num_cells": 20,
        "width": 1.0,
        "height": 1.0,
        "min_distance": 0.1,
        "lloyd_iterations": 0,
        "seed": 42,
        "warp_enabled": False
    }
    
    result = run_phase1(config)
    
    # Check basic output structure
    assert "topology" in result, "Result should contain topology"
    assert result["config"]["warp_enabled"] == False
    
    # Check topology is valid
    topology = result["topology"]
    assert len(topology["faces"]) > 0, "Should have generated faces"
    
    print("✓ Phase 1 without warping test passed")


def test_phase1_default_warp_disabled():
    """Test that Phase 1 defaults to warping disabled for backwards compatibility."""
    config = {
        "num_cells": 20,
        "width": 1.0,
        "height": 1.0,
        "min_distance": 0.1,
        "lloyd_iterations": 0,
        "seed": 42
        # warp_enabled not specified - should default to False
    }
    
    result = run_phase1(config)
    
    # Check that warping is disabled by default
    assert result["config"].get("warp_enabled", False) == False, \
        "Warping should be disabled by default"
    
    print("✓ Phase 1 default warp disabled test passed")


def test_warp_strength_effect():
    """Test that warp strength affects displacement magnitude."""
    points = np.array([
        [0.5, 0.5],
        [0.3, 0.7],
        [0.7, 0.3]
    ])
    
    # Low strength warp
    warped_low = apply_domain_warp(points, 1.0, 1.0, warp_strength=0.05, warp_frequency=2, seed=42)
    displacement_low = np.linalg.norm(warped_low - points, axis=1).mean()
    
    # High strength warp
    warped_high = apply_domain_warp(points, 1.0, 1.0, warp_strength=0.2, warp_frequency=2, seed=42)
    displacement_high = np.linalg.norm(warped_high - points, axis=1).mean()
    
    # Higher strength should generally cause larger displacement
    assert displacement_high > displacement_low, \
        f"Higher strength should cause larger displacement ({displacement_high} vs {displacement_low})"
    
    print("✓ Warp strength effect test passed")


if __name__ == "__main__":
    # Run all tests
    test_perlin_noise_generation()
    test_noise_sampling()
    test_domain_warp_basic()
    test_domain_warp_bounds()
    test_domain_warp_zero_strength()
    test_domain_warp_reproducibility()
    test_phase1_with_warping()
    test_phase1_without_warping()
    test_phase1_default_warp_disabled()
    test_warp_strength_effect()
    
    print("\n" + "=" * 60)
    print("All domain warp tests passed!")
    print("=" * 60)
