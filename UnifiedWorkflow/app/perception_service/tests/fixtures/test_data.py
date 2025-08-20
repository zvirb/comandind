"""Test data fixtures and validation scenarios for perception service.

Provides comprehensive test data including images, prompts, and expected
outputs for thorough testing of image processing capabilities.
"""

import base64
import io
from typing import Dict, List, Any, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pytest


class ImageTestDataGenerator:
    """Generator for test images with various characteristics."""
    
    @staticmethod
    def create_geometric_patterns(width: int = 512, height: int = 512) -> bytes:
        """Create image with geometric patterns."""
        image = Image.new("RGB", (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # Draw various geometric shapes
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255)]
        
        # Rectangles
        for i in range(5):
            x1 = i * (width // 5)
            y1 = i * 20
            x2 = x1 + (width // 6)
            y2 = y1 + 40
            draw.rectangle([x1, y1, x2, y2], fill=colors[i % len(colors)])
        
        # Circles
        for i in range(3):
            center_x = width // 4 + i * (width // 4)
            center_y = height // 2
            radius = 30 + i * 20
            x1, y1 = center_x - radius, center_y - radius
            x2, y2 = center_x + radius, center_y + radius
            draw.ellipse([x1, y1, x2, y2], fill=colors[(i + 2) % len(colors)])
        
        # Lines
        for i in range(10):
            y = height // 3 + i * 10
            draw.line([0, y, width, y], fill=(0, 0, 0), width=2)
        
        return ImageTestDataGenerator._image_to_bytes(image)
    
    @staticmethod
    def create_color_gradient(width: int = 512, height: int = 512) -> bytes:
        """Create image with color gradients."""
        image = Image.new("RGB", (width, height))
        pixels = image.load()
        
        for x in range(width):
            for y in range(height):
                # Create gradient effect
                r = int(255 * (x / width))
                g = int(255 * (y / height))
                b = int(255 * ((x + y) / (width + height)))
                pixels[x, y] = (r, g, b)
        
        return ImageTestDataGenerator._image_to_bytes(image)
    
    @staticmethod
    def create_text_like_patterns(width: int = 512, height: int = 512) -> bytes:
        """Create image with text-like patterns."""
        image = Image.new("RGB", (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # Simulate text blocks
        y_pos = 50
        for line in range(15):
            # Draw horizontal lines simulating text
            for word in range(8):
                x_start = 50 + word * 60
                x_end = x_start + np.random.randint(30, 50)
                draw.rectangle([x_start, y_pos, x_end, y_pos + 8], fill=(0, 0, 0))
            y_pos += 25
        
        # Add some punctuation-like dots
        for i in range(20):
            x = np.random.randint(50, width - 50)
            y = np.random.randint(50, height - 50)
            draw.ellipse([x, y, x + 3, y + 3], fill=(0, 0, 0))
        
        return ImageTestDataGenerator._image_to_bytes(image)
    
    @staticmethod
    def create_complex_scene(width: int = 512, height: int = 512) -> bytes:
        """Create complex scene with multiple elements."""
        image = Image.new("RGB", (width, height), (135, 206, 235))  # Sky blue background
        draw = ImageDraw.Draw(image)
        
        # Draw ground
        draw.rectangle([0, height * 2//3, width, height], fill=(34, 139, 34))  # Forest green
        
        # Draw sun
        sun_center = (width * 3//4, height // 4)
        sun_radius = 30
        draw.ellipse([sun_center[0] - sun_radius, sun_center[1] - sun_radius,
                     sun_center[0] + sun_radius, sun_center[1] + sun_radius], 
                     fill=(255, 255, 0))
        
        # Draw clouds
        for i in range(3):
            cloud_x = i * (width // 4) + 50
            cloud_y = height // 6
            for j in range(4):
                circle_x = cloud_x + j * 15
                draw.ellipse([circle_x - 20, cloud_y - 10, circle_x + 20, cloud_y + 10], 
                           fill=(255, 255, 255))
        
        # Draw trees
        for i in range(5):
            tree_x = i * (width // 6) + 30
            tree_base = height * 2//3
            # Tree trunk
            draw.rectangle([tree_x - 5, tree_base - 40, tree_x + 5, tree_base], fill=(139, 69, 19))
            # Tree crown
            draw.ellipse([tree_x - 25, tree_base - 80, tree_x + 25, tree_base - 30], 
                        fill=(0, 100, 0))
        
        return ImageTestDataGenerator._image_to_bytes(image)
    
    @staticmethod
    def create_noise_pattern(width: int = 512, height: int = 512) -> bytes:
        """Create image with random noise pattern."""
        # Generate random noise
        noise = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
        image = Image.fromarray(noise, "RGB")
        
        return ImageTestDataGenerator._image_to_bytes(image)
    
    @staticmethod
    def create_minimal_content(width: int = 64, height: int = 64) -> bytes:
        """Create minimal content image for edge case testing."""
        image = Image.new("RGB", (width, height), (128, 128, 128))
        draw = ImageDraw.Draw(image)
        
        # Just a simple cross
        mid_x, mid_y = width // 2, height // 2
        draw.line([0, mid_y, width, mid_y], fill=(255, 255, 255), width=2)
        draw.line([mid_x, 0, mid_x, height], fill=(255, 255, 255), width=2)
        
        return ImageTestDataGenerator._image_to_bytes(image)
    
    @staticmethod
    def _image_to_bytes(image: Image.Image, format: str = "JPEG", quality: int = 95) -> bytes:
        """Convert PIL Image to bytes."""
        buffer = io.BytesIO()
        image.save(buffer, format=format, quality=quality)
        return buffer.getvalue()


class TestPrompts:
    """Collection of test prompts for various scenarios."""
    
    # Basic prompts
    BASIC_DESCRIPTION = "Describe what you see in this image"
    BASIC_ANALYSIS = "Analyze the visual content of this image"
    
    # Specific analysis prompts
    GEOMETRIC_ANALYSIS = "Identify and describe the geometric shapes and patterns in this image"
    COLOR_ANALYSIS = "Analyze the colors, gradients, and color relationships in this image"
    COMPOSITION_ANALYSIS = "Describe the composition, layout, and spatial relationships in this image"
    
    # Detailed prompts
    COMPREHENSIVE_ANALYSIS = "Provide a comprehensive analysis of this image including objects, colors, composition, style, and any notable features"
    ARTISTIC_ANALYSIS = "Analyze this image from an artistic perspective, including composition, color theory, visual balance, and aesthetic elements"
    TECHNICAL_ANALYSIS = "Provide a technical analysis of this image including resolution, quality, format characteristics, and visual properties"
    
    # Task-specific prompts
    OBJECT_DETECTION = "List all the objects and elements you can identify in this image"
    SCENE_DESCRIPTION = "Describe the scene depicted in this image, including setting, atmosphere, and context"
    PATTERN_RECOGNITION = "Identify and describe any patterns, textures, or repetitive elements in this image"
    
    # Edge case prompts
    EMPTY_PROMPT = ""
    VERY_LONG_PROMPT = "This is an extremely detailed prompt that goes on for a very long time to test how the system handles verbose instructions and whether it can maintain focus on the core task of image analysis despite the length and complexity of the request which includes multiple clauses and extensive elaboration on various aspects of visual analysis including color theory, composition principles, artistic techniques, and technical considerations."
    SPECIAL_CHARACTERS = "Analyze this image with émphasis on spëcial characters and ñumbers like 123 & symbols @#$%"
    
    @classmethod
    def get_all_prompts(cls) -> List[str]:
        """Get all test prompts."""
        return [
            cls.BASIC_DESCRIPTION,
            cls.BASIC_ANALYSIS,
            cls.GEOMETRIC_ANALYSIS,
            cls.COLOR_ANALYSIS,
            cls.COMPOSITION_ANALYSIS,
            cls.COMPREHENSIVE_ANALYSIS,
            cls.ARTISTIC_ANALYSIS,
            cls.TECHNICAL_ANALYSIS,
            cls.OBJECT_DETECTION,
            cls.SCENE_DESCRIPTION,
            cls.PATTERN_RECOGNITION,
            cls.EMPTY_PROMPT,
            cls.VERY_LONG_PROMPT,
            cls.SPECIAL_CHARACTERS
        ]


class ValidationHelpers:
    """Helper functions for validating test results."""
    
    @staticmethod
    def validate_vector_properties(vector: List[float], expected_dimensions: int = 1536) -> Dict[str, bool]:
        """Validate vector properties."""
        return {
            "correct_dimensions": len(vector) == expected_dimensions,
            "numeric_values": all(isinstance(v, (int, float)) for v in vector),
            "reasonable_range": all(-10 <= v <= 10 for v in vector),  # Reasonable range
            "not_all_zeros": not all(v == 0 for v in vector),
            "not_all_same": len(set(vector)) > 1
        }
    
    @staticmethod
    def validate_processing_time(processing_time_ms: float, max_time_ms: float = 2000) -> bool:
        """Validate processing time meets requirements."""
        return 0 < processing_time_ms <= max_time_ms
    
    @staticmethod
    def calculate_vector_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between vectors."""
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        
        return float(dot_product / (norm_v1 * norm_v2))


# Pytest fixtures for easy access

@pytest.fixture
def image_generator():
    """Fixture for image test data generator."""
    return ImageTestDataGenerator()

@pytest.fixture
def test_prompts():
    """Fixture for test prompts."""
    return TestPrompts()

@pytest.fixture
def validation_helpers():
    """Fixture for validation helper functions."""
    return ValidationHelpers()