#!/usr/bin/env python3
"""
Serveur MCP pour le scraper Rowbx/Wonderbox
==========================================
Permet à Claude d'interroger le back-office Rowbx via le chat.

Lancement:
    python mcp_server.py

Prérequis:
    - VPN actif vers rowbx2.wonderbox.vpn
    - Cookie PHPSESSID valide (variable d'environnement ROWBX_COOKIE)
"""

import os
import json
import logging
from typing import Any
from dataclasses import asdict

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from scraper import WonderboxScraper
from models import Product, ProductDetail, Activity, ActivityDetail

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RowbxMCP")

# Instance du serveur MCP
server = Server("rowbx-scraper")

# Instance du scraper (initialisée au premier appel)
_scraper: WonderboxScraper = None


def get_scraper() -> WonderboxScraper:
    """Récupère ou initialise le scraper avec le cookie d'environnement."""
    global _scraper
    if _scraper is None:
        cookie = os.environ.get("ROWBX_COOKIE")
        if not cookie:
            raise ValueError(
                "Variable d'environnement ROWBX_COOKIE non définie. "
                "Exporte ton cookie PHPSESSID: export ROWBX_COOKIE='ton_cookie'"
            )
        _scraper = WonderboxScraper(cookies={"PHPSESSID": cookie})
        logger.info("Scraper initialisé avec cookie")
    return _scraper


def to_json(obj: Any) -> str:
    """Convertit un objet en JSON lisible."""
    if hasattr(obj, '__dataclass_fields__'):
        return json.dumps(asdict(obj), indent=2, ensure_ascii=False, default=str)
    elif isinstance(obj, list):
        return json.dumps(
            [asdict(item) if hasattr(item, '__dataclass_fields__') else item for item in obj],
            indent=2, ensure_ascii=False, default=str
        )
    elif isinstance(obj, dict):
        return json.dumps(obj, indent=2, ensure_ascii=False, default=str)
    return str(obj)


# =============================================================================
# OUTILS MCP
# =============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """Liste des outils disponibles."""
    return [
        Tool(
            name="rowbx_test_connection",
            description="Teste la connexion au back-office Rowbx. Vérifie que le VPN est actif et le cookie valide.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="rowbx_get_product",
            description="Récupère les détails complets d'un produit/coffret par son ID. Retourne: code, nom, descriptions, images, matérialisations, EAN, merchandising, SEO.",
            inputSchema={
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "integer",
                        "description": "ID du produit (ex: 32953)"
                    },
                    "fetch_all_tabs": {
                        "type": "boolean",
                        "description": "Charger tous les onglets (descriptions, caractéristiques, web). Défaut: true",
                        "default": True
                    }
                },
                "required": ["product_id"]
            }
        ),
        Tool(
            name="rowbx_get_activity",
            description="Récupère les détails complets d'une activité/prestation par son ID. Retourne: code, lieu, caractéristiques, prix, partenaire.",
            inputSchema={
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "integer",
                        "description": "ID de l'activité (ex: 529215)"
                    },
                    "fetch_all_tabs": {
                        "type": "boolean",
                        "description": "Charger tous les onglets. Défaut: true",
                        "default": True
                    }
                },
                "required": ["activity_id"]
            }
        ),
        Tool(
            name="rowbx_search_products",
            description="Recherche des produits/coffrets avec filtres. Retourne une liste paginée.",
            inputSchema={
                "type": "object",
                "properties": {
                    "publisher": {
                        "type": "string",
                        "description": "Éditeur: FRANCE, BELGIUM, SPAIN, ITALY",
                        "enum": ["FRANCE", "BELGIUM", "SPAIN", "ITALY"],
                        "default": "FRANCE"
                    },
                    "web_status": {
                        "type": "string",
                        "description": "Statut web: ACTIVE, ARCHIVED, PUBLISHABLE",
                        "enum": ["ACTIVE", "ARCHIVED", "PUBLISHABLE"],
                        "default": "ACTIVE"
                    },
                    "page": {
                        "type": "integer",
                        "description": "Numéro de page (10 résultats par page)",
                        "default": 1
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="rowbx_list_products",
            description="Liste tous les produits avec filtres (plusieurs pages). Peut inclure les détails complets.",
            inputSchema={
                "type": "object",
                "properties": {
                    "publisher": {
                        "type": "string",
                        "description": "Éditeur: FRANCE, BELGIUM, SPAIN, ITALY",
                        "enum": ["FRANCE", "BELGIUM", "SPAIN", "ITALY"],
                        "default": "FRANCE"
                    },
                    "web_status": {
                        "type": "string",
                        "description": "Statut web: ACTIVE, ARCHIVED, PUBLISHABLE",
                        "enum": ["ACTIVE", "ARCHIVED", "PUBLISHABLE"],
                        "default": "ACTIVE"
                    },
                    "max_pages": {
                        "type": "integer",
                        "description": "Nombre max de pages à récupérer (10 produits/page). Défaut: 3",
                        "default": 3
                    },
                    "include_details": {
                        "type": "boolean",
                        "description": "Inclure les détails complets de chaque produit (plus lent)",
                        "default": False
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="rowbx_search_activities",
            description="Recherche les activités/prestations d'un coffret par son code.",
            inputSchema={
                "type": "object",
                "properties": {
                    "box_code": {
                        "type": "string",
                        "description": "Code du coffret (ex: FRWOPCSE94)"
                    },
                    "publisher": {
                        "type": "string",
                        "description": "Éditeur: FRANCE, BELGIUM, SPAIN, ITALY",
                        "enum": ["FRANCE", "BELGIUM", "SPAIN", "ITALY"],
                        "default": "FRANCE"
                    },
                    "web_status": {
                        "type": "string",
                        "description": "Statut web: ACTIVE, ARCHIVED, PUBLISHABLE",
                        "enum": ["ACTIVE", "ARCHIVED", "PUBLISHABLE"],
                        "default": "ACTIVE"
                    },
                    "page": {
                        "type": "integer",
                        "description": "Numéro de page",
                        "default": 1
                    }
                },
                "required": ["box_code"]
            }
        ),
        Tool(
            name="rowbx_list_activities_for_product",
            description="Liste toutes les activités d'un coffret (toutes les pages).",
            inputSchema={
                "type": "object",
                "properties": {
                    "box_code": {
                        "type": "string",
                        "description": "Code du coffret (ex: FRWOPCSE94)"
                    },
                    "publisher": {
                        "type": "string",
                        "description": "Éditeur",
                        "enum": ["FRANCE", "BELGIUM", "SPAIN", "ITALY"],
                        "default": "FRANCE"
                    },
                    "web_status": {
                        "type": "string",
                        "description": "Statut web",
                        "enum": ["ACTIVE", "ARCHIVED", "PUBLISHABLE"],
                        "default": "ACTIVE"
                    }
                },
                "required": ["box_code"]
            }
        ),
        Tool(
            name="rowbx_search_by_country",
            description="Recherche des produits ou activités par pays.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "description": "Type d'entité à rechercher",
                        "enum": ["products", "activities"]
                    },
                    "country": {
                        "type": "string",
                        "description": "Code pays: FR, BE, ES, IT, PT, NL, CH, LU",
                        "enum": ["FR", "BE", "ES", "IT", "PT", "NL", "CH", "LU", "MC", "AD"]
                    },
                    "publisher": {
                        "type": "string",
                        "description": "Éditeur",
                        "enum": ["FRANCE", "BELGIUM", "SPAIN", "ITALY"],
                        "default": "FRANCE"
                    },
                    "max_pages": {
                        "type": "integer",
                        "description": "Nombre max de pages",
                        "default": 3
                    }
                },
                "required": ["entity_type", "country"]
            }
        ),
        Tool(
            name="rowbx_get_statistics",
            description="Calcule des statistiques sur une liste de produits récupérés.",
            inputSchema={
                "type": "object",
                "properties": {
                    "publisher": {
                        "type": "string",
                        "description": "Éditeur",
                        "enum": ["FRANCE", "BELGIUM", "SPAIN", "ITALY"],
                        "default": "FRANCE"
                    },
                    "web_status": {
                        "type": "string",
                        "description": "Statut web",
                        "enum": ["ACTIVE", "ARCHIVED", "PUBLISHABLE"],
                        "default": "ACTIVE"
                    },
                    "max_pages": {
                        "type": "integer",
                        "description": "Nombre de pages à analyser",
                        "default": 5
                    }
                },
                "required": []
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Exécute un outil."""
    try:
        scraper = get_scraper()

        if name == "rowbx_test_connection":
            success, message = scraper.test_connection()
            return [TextContent(
                type="text",
                text=f"{'✅' if success else '❌'} {message}"
            )]

        elif name == "rowbx_get_product":
            product_id = arguments["product_id"]
            fetch_all = arguments.get("fetch_all_tabs", True)
            detail = scraper.get_product_detail(product_id, fetch_all_tabs=fetch_all)
            if detail:
                return [TextContent(type="text", text=to_json(detail))]
            return [TextContent(type="text", text=f"❌ Produit ID {product_id} non trouvé")]

        elif name == "rowbx_get_activity":
            activity_id = arguments["activity_id"]
            fetch_all = arguments.get("fetch_all_tabs", True)
            detail = scraper.get_activity_detail(activity_id, fetch_all_tabs=fetch_all)
            if detail:
                return [TextContent(type="text", text=to_json(detail))]
            return [TextContent(type="text", text=f"❌ Activité ID {activity_id} non trouvée")]

        elif name == "rowbx_search_products":
            publisher = arguments.get("publisher", "FRANCE")
            web_status = arguments.get("web_status", "ACTIVE")
            page = arguments.get("page", 1)
            products, total, total_pages = scraper.search_products(publisher, web_status, page)
            result = {
                "total": total,
                "total_pages": total_pages,
                "page": page,
                "count": len(products),
                "products": [asdict(p) for p in products]
            }
            return [TextContent(type="text", text=to_json(result))]

        elif name == "rowbx_list_products":
            publisher = arguments.get("publisher", "FRANCE")
            web_status = arguments.get("web_status", "ACTIVE")
            max_pages = arguments.get("max_pages", 3)
            include_details = arguments.get("include_details", False)

            if include_details:
                products = scraper.get_all_products_with_details(
                    publisher, web_status, max_pages=max_pages
                )
            else:
                products = scraper.get_all_products(
                    publisher, web_status, max_pages=max_pages
                )

            result = {
                "count": len(products),
                "products": [asdict(p) for p in products]
            }
            return [TextContent(type="text", text=to_json(result))]

        elif name == "rowbx_search_activities":
            box_code = arguments["box_code"]
            publisher = arguments.get("publisher", "FRANCE")
            web_status = arguments.get("web_status", "ACTIVE")
            page = arguments.get("page", 1)
            activities, total, total_pages = scraper.search_activities(
                box_code, publisher, web_status, page
            )
            result = {
                "box_code": box_code,
                "total": total,
                "total_pages": total_pages,
                "page": page,
                "count": len(activities),
                "activities": [asdict(a) for a in activities]
            }
            return [TextContent(type="text", text=to_json(result))]

        elif name == "rowbx_list_activities_for_product":
            box_code = arguments["box_code"]
            publisher = arguments.get("publisher", "FRANCE")
            web_status = arguments.get("web_status", "ACTIVE")
            activities = scraper.get_all_activities_for_product(
                box_code, publisher, web_status
            )
            result = {
                "box_code": box_code,
                "count": len(activities),
                "activities": [asdict(a) for a in activities]
            }
            return [TextContent(type="text", text=to_json(result))]

        elif name == "rowbx_search_by_country":
            entity_type = arguments["entity_type"]
            country = arguments["country"]
            publisher = arguments.get("publisher", "FRANCE")
            max_pages = arguments.get("max_pages", 3)

            if entity_type == "products":
                items = scraper.get_all_products_by_country(
                    country, publisher, max_pages=max_pages
                )
                result = {
                    "entity_type": "products",
                    "country": country,
                    "count": len(items),
                    "products": [asdict(p) for p in items]
                }
            else:
                items = scraper.get_all_activities_by_country(
                    country, publisher, max_pages=max_pages
                )
                result = {
                    "entity_type": "activities",
                    "country": country,
                    "count": len(items),
                    "activities": [asdict(a) for a in items]
                }
            return [TextContent(type="text", text=to_json(result))]

        elif name == "rowbx_get_statistics":
            publisher = arguments.get("publisher", "FRANCE")
            web_status = arguments.get("web_status", "ACTIVE")
            max_pages = arguments.get("max_pages", 5)

            products = scraper.get_all_products(publisher, web_status, max_pages=max_pages)
            stats = scraper.get_statistics(products)
            return [TextContent(type="text", text=to_json(stats))]

        else:
            return [TextContent(type="text", text=f"❌ Outil inconnu: {name}")]

    except ValueError as e:
        return [TextContent(type="text", text=f"❌ Erreur config: {str(e)}")]
    except Exception as e:
        logger.exception(f"Erreur lors de l'exécution de {name}")
        return [TextContent(type="text", text=f"❌ Erreur: {str(e)}")]


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Point d'entrée du serveur MCP."""
    logger.info("Démarrage du serveur MCP Rowbx...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
