# File: src/rendering/renderer.py
"""
Abstract renderer interface.
"""
from abc import ABC, abstractmethod


class Renderer(ABC):
    @abstractmethod
    def attach(self, world, pixel_manager, simulation=None):
        pass

    @abstractmethod
    def run(self):
        pass




