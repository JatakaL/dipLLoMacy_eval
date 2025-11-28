#!/usr/bin/env python3
"""
Noise Utilities for Map Generation

This module provides shared noise generation functions used across different phases
of map generation, including Perlin noise for domain warping and terrain generation.
"""

import numpy as np


def generate_perlin_noise_2d(shape, res, seed=None):
    """
    Generate 2D Perlin noise.
    
    Args:
        shape: Shape of the output array (height, width)
        res: Resolution/frequency of the noise tuple (res_y, res_x)
        seed: Random seed
        
    Returns:
        2D numpy array of noise values in approximately [-1, 1]
    """
    if seed is not None:
        np.random.seed(seed)
    
    def smoothstep(t):
        return t * t * (3.0 - 2.0 * t)
    
    # Create coordinate grids
    noise_height, noise_width = shape
    y = np.linspace(0, res[0], noise_height, endpoint=False)
    x = np.linspace(0, res[1], noise_width, endpoint=False)
    x_grid, y_grid = np.meshgrid(x, y)
    
    # Integer parts
    x0 = np.floor(x_grid).astype(int)
    y0 = np.floor(y_grid).astype(int)
    
    # Fractional parts
    fx = x_grid - x0
    fy = y_grid - y0
    
    # Wrap around
    x0 = x0 % res[1]
    y0 = y0 % res[0]
    x1 = (x0 + 1) % res[1]
    y1 = (y0 + 1) % res[0]
    
    # Generate random gradients for grid points
    grad_size = (res[0] + 1, res[1] + 1)
    angles = 2 * np.pi * np.random.rand(*grad_size)
    grad_x = np.cos(angles)
    grad_y = np.sin(angles)
    
    # Get gradients at corners
    g00_x = grad_x[y0, x0]
    g00_y = grad_y[y0, x0]
    g10_x = grad_x[y0, x1]
    g10_y = grad_y[y0, x1]
    g01_x = grad_x[y1, x0]
    g01_y = grad_y[y1, x0]
    g11_x = grad_x[y1, x1]
    g11_y = grad_y[y1, x1]
    
    # Dot products with distance vectors
    n00 = g00_x * fx + g00_y * fy
    n10 = g10_x * (fx - 1) + g10_y * fy
    n01 = g01_x * fx + g01_y * (fy - 1)
    n11 = g11_x * (fx - 1) + g11_y * (fy - 1)
    
    # Interpolate
    sx = smoothstep(fx)
    sy = smoothstep(fy)
    
    n0 = n00 * (1 - sx) + n10 * sx
    n1 = n01 * (1 - sx) + n11 * sx
    
    return n0 * (1 - sy) + n1 * sy
