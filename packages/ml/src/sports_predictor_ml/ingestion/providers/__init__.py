"""Adaptadores de proveedor de datos (Ports & Adapters).

El dominio depende únicamente del puerto `SportsDataProvider` (base.py). Cada
proveedor real (football-data.org, nflverse, etc.) o de prueba (mock) implementa
ese puerto, de modo que cambiar de proveedor no requiere tocar el resto del sistema.
"""
