#!/usr/bin/env python3
"""
Utilitaire pour extraire les cookies d'un fichier HAR
Usage: python extract_cookies.py fichier.har
"""

import json
import sys

def extract_cookies_from_har(har_file: str) -> dict:
    """Extrait les cookies d'un fichier HAR"""
    with open(har_file, 'r', encoding='utf-8') as f:
        har = json.load(f)
    
    cookies = {}
    
    for entry in har['log']['entries']:
        # Cookies des requêtes
        for cookie in entry['request'].get('cookies', []):
            name = cookie.get('name')
            value = cookie.get('value')
            if name and value:
                cookies[name] = value
        
        # Cookies des réponses (Set-Cookie)
        for cookie in entry['response'].get('cookies', []):
            name = cookie.get('name')
            value = cookie.get('value')
            if name and value:
                cookies[name] = value
        
        # Headers Cookie
        for header in entry['request'].get('headers', []):
            if header['name'].lower() == 'cookie':
                for part in header['value'].split(';'):
                    if '=' in part:
                        name, value = part.strip().split('=', 1)
                        cookies[name] = value
    
    return cookies

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_cookies.py <fichier.har>")
        print("\nCe script extrait les cookies d'un fichier HAR exporté depuis Chrome DevTools")
        print("\nPour exporter un HAR avec cookies:")
        print("1. Chrome DevTools (F12) → Network")
        print("2. Navigue sur le site authentifié")
        print("3. Clic droit → Save all as HAR with content")
        sys.exit(1)
    
    har_file = sys.argv[1]
    
    try:
        cookies = extract_cookies_from_har(har_file)
        
        if cookies:
            print("🍪 Cookies trouvés:")
            print("-" * 50)
            for name, value in cookies.items():
                print(f"  {name}: {value[:50]}{'...' if len(value) > 50 else ''}")
            
            print("\n" + "=" * 50)
            print("📋 Format pour Streamlit (copie cette ligne):")
            print("=" * 50)
            cookie_string = "; ".join([f"{k}={v}" for k, v in cookies.items()])
            print(cookie_string)
            
            if 'PHPSESSID' in cookies:
                print(f"\n🔑 PHPSESSID: {cookies['PHPSESSID']}")
        else:
            print("⚠️ Aucun cookie trouvé dans le fichier HAR")
            print("\nAssurez-vous d'exporter le HAR APRÈS vous être connecté au site")
            print("et d'inclure les cookies lors de l'export.")
    
    except FileNotFoundError:
        print(f"❌ Fichier non trouvé: {har_file}")
    except json.JSONDecodeError:
        print(f"❌ Fichier HAR invalide: {har_file}")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    main()
