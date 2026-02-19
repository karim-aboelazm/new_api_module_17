# -*- coding: utf-8 -*-
"""
Odoo RESTful API
================

A secure and extensible REST API framework for Odoo.

Features
--------
- JWT-based authentication
- Generic CRUD endpoints for Odoo models
- JSON ↔ ORM serialization engine
- Attachment handling
- Centralized error management
- Designed for external integrations and mobile apps

Target Version: Odoo 16
License: LGPL-3
"""

{
    # ---------------------------------------------------------
    # Basic Information
    # ---------------------------------------------------------
    'name': "Odoo RESTful API",
    'summary': "Secure REST API framework for Odoo with JWT authentication",
    'description': """
Odoo RESTful API Framework

This module provides a secure and extensible REST API layer
for Odoo, enabling external systems and applications to
interact with Odoo models via JSON endpoints.

Main Capabilities:
- JWT authentication
- Generic model CRUD operations
- Dynamic method execution
- ORM serialization/deserialization
- Structured API error handling

Intended Use:
- Mobile applications
- Third-party integrations
- Microservices architecture
- Headless Odoo deployments
""",

    # ---------------------------------------------------------
    # Classification
    # ---------------------------------------------------------
    'category': 'Tools',
    'version': '0.1',
    'license': 'LGPL-3',
    'author': 'Karim Aboelazm',

    # ---------------------------------------------------------
    # Dependencies
    # ---------------------------------------------------------
    'depends': [
        'base',
    ],

    # ---------------------------------------------------------
    # Data Files
    # ---------------------------------------------------------
    'data': [
        'security/ir.model.access.csv',
    ],

    # ---------------------------------------------------------
    # Installation
    # ---------------------------------------------------------
    'application': False,
    'auto_install': False,
    'installable': True,
}
