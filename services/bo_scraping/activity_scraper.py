import logging
import re
import time
from typing import List, Tuple, Optional
from bs4 import BeautifulSoup
from .base_scraper import BOServiceBase
from common.models import (
    Activity, ActivityDetail, ActivityDescriptions, ActivityCharacteristics,
    ActivityLocation, ActivityPricing
)

logger = logging.getLogger("BOActivityScraper")

class BOActivityScraper(BOServiceBase):
    """Scraper pour les activités (Prestations) en BO"""
    
    def search_activities(self, filters: dict = None, page: int = 1) -> Tuple[List[Activity], int, int]:
        """
        Recherche exhaustive des activités via filtres.
        
        Args:
            filters: Dictionnaire complet des filtres (ex: {'universe': 'GASTRONOMY', 'country': 'FR', 'qualityLabels': ['STAR']})
            page: Numéro de page
        """
        self._log_separator(f"RECHERCHE ACTIVITÉS - Page {page}")
        
        # Base URL
        url_parts = [f"{self.BASE_URL}/search/activity"]
        
        # Default filters if not provided
        if not filters: filters = {}
        
        # Build URL parts from filters
        filter_parts = self._build_filter_url_parts(filters)
        url_parts.extend(filter_parts)
                
        # Pagination & Defaults
        url_parts.extend([
            "boxedShops_nullable/0",
            "in_boxedChecks_check_commissionFree/0",
            "notIn_boxedChecks_check_commissionFree/0",
            f"page/{page}"
        ])
        
        full_url = "/".join(url_parts)
        
        # Handle query params if needed (rare in this routing but possible for arrays)
        # For now assume path segments work for most
        
        html = self._fetch_page(full_url, f"Activités page {page}")
        if not html:
            return [], 0, 0
        
        
        return self._parse_activities_results(html)
    
    def _parse_activities_results(self, html: str) -> Tuple[List[Activity], int, int]:
        """Parse les résultats de recherche activités"""
        soup = BeautifulSoup(html, 'html.parser')
        activities = []
        # Total
        total_results = 0
        match = re.search(r'Nombre de résultats\s*.*?\s*(\d+)', html, re.DOTALL)
        if match:
            total_results = int(match.group(1))

        if total_results == 0:
            summary = soup.find('div', class_='result-summary') or soup.find('span', class_='nb-items')
            if summary:
                # Often "Nombre de résultats : 123"
                text = summary.get_text(strip=True)
                # Find the digits
                match_text = re.search(r'(\d+)', text)
                if match_text:
                    total_results = int(match_text.group(1))
        
        total_pages = (total_results + 9) // 10 if total_results > 0 else 1
        
        table = soup.find('table', class_='data-result')
        if not table:
            return [], total_results, total_pages
        
        tbody = table.find('tbody')
        if not tbody:
            return [], total_results, total_pages
        
        rows = tbody.find_all('tr', class_=re.compile(r'bg-(light|dark)'))
        
        for row in rows:
            activity = self._parse_activity_row(row)
            if activity:
                activities.append(activity)
        
        return activities, total_results, total_pages
    
    def _parse_activity_row(self, row) -> Optional[Activity]:
        """Parse une ligne activité"""
        cells = row.find_all('td')
        if len(cells) < 7:
            return None

        activity = Activity()

        # Status class
        row_classes = row.get('class', [])
        for cls in row_classes:
            if cls not in ['bg-light', 'bg-dark']:
                activity.status = cls
                if 'active' in cls.lower() and 'publish' in cls.lower():
                    activity.web_status = 'ACTIVE'
                elif 'archived' in cls.lower():
                    activity.web_status = 'ARCHIVED'
                elif 'pending' in cls.lower():
                    activity.status = 'pending'
                break

        # Code & ID
        if len(cells) > 2:
            code_link = cells[2].find('a', href=re.compile(r'/activity/index/id/'))
            if code_link:
                activity.code = code_link.get_text(strip=True)
                href = code_link.get('href', '')
                match = re.search(r'/id/(\d+)', href)
                if match:
                    activity.id = int(match.group(1))
                    activity.detail_url = f"{self.BASE_URL}/activity/index/id/{activity.id}"

        # Status Text
        if len(cells) > 3:
            status_text = cells[3].get_text(strip=True)
            if status_text and status_text not in ['-', '']:
                if not activity.status:
                    activity.status = status_text

        # Web Status
        if len(cells) > 4:
            web_status_text = cells[4].get_text(strip=True)
            if web_status_text and web_status_text not in ['-', '']:
                activity.web_status = web_status_text

        # Name, Type, Target
        if len(cells) > 5:
            name_link = cells[5].find('a', href=re.compile(r'/activity/index/id/'))
            if name_link:
                activity.name = name_link.get_text(strip=True)

            parts = cells[5].get_text(separator='|', strip=True).split('|')
            if len(parts) >= 2: activity.activity_type = parts[1].strip()
            if len(parts) >= 3: activity.activity_subtype = parts[2].strip() if parts[2].strip() not in ['-', ''] else ""
            if len(parts) >= 4: activity.target = parts[3].strip()

        # Location
        if len(cells) > 6:
            loc_link = cells[6].find('a', href=re.compile(r'/location/index/id/'))
            if loc_link:
                activity.location_name = loc_link.get_text(strip=True)
                match = re.search(r'/id/(\d+)', loc_link.get('href', ''))
                if match: activity.location_id = int(match.group(1))

            parts = cells[6].get_text(separator='|', strip=True).split('|')
            if len(parts) >= 2: activity.location_address = parts[1].strip()
            if len(parts) >= 3: activity.location_zipcode = parts[2].strip()
            if len(parts) >= 4: activity.location_city = parts[3].strip()
            if len(parts) >= 5: activity.location_country = parts[4].strip()
            if len(parts) >= 6:
                extra = parts[5].strip()
                if re.match(r'^[A-Z]{2}\d+', extra):
                    activity.location_code = extra
                else:
                    activity.location_region = extra

        # Partner
        for cell in cells:
            if '/partner/index/id/' in str(cell):
                link = cell.find('a', href=re.compile(r'/partner/index/id/'))
                if link: activity.partner_name = link.get_text(strip=True)
                break

        # Duration / Persons
        for cell in cells:
            text = cell.get_text(strip=True).lower()
            if not activity.duration:
                match = re.search(r'(\d+)\s*(h|min|jour|day|nuit|night)', text)
                if match: activity.duration = match.group(0)
            if not activity.nb_persons:
                match = re.search(r'(\d+)\s*(pers|person|pax)', text)
                if match: activity.nb_persons = match.group(1)

        # Price
        if len(cells) > 7:
            text = cells[7].get_text(strip=True)
            match = re.search(r'([\d\s,\.]+)\s*€', text)
            if match:
                try: activity.price = float(match.group(1).replace(' ', '').replace(',', '.'))
                except ValueError:
                        pass
            
            match = re.search(r'\(([^)]+)\)', text)
            if match: activity.price_countries = match.group(1).strip()

        # Partner Price / Margin
        for cell in cells[-3:]:
            text = cell.get_text(strip=True)
            if ('partenaire' in str(cell).lower() or 'partner' in str(cell).lower()) and '€' in text:
                match = re.search(r'([\d\s,\.]+)\s*€', text)
                if match:
                    try: activity.partner_price = float(match.group(1).replace(' ', '').replace(',', '.'))
                    except ValueError:
                        pass
            
            if '%' in text:
                match = re.search(r'([\d,\.]+)\s*%', text)
                if match:
                    try: activity.margin_rate = float(match.group(1).replace(',', '.'))
                    except ValueError:
                        pass

        # Publisher
        for cell in cells:
            text = cell.get_text(strip=True).upper()
            if text in ['FRANCE', 'BELGIUM', 'SPAIN', 'ITALY', 'PORTUGAL', 'NETHERLANDS']:
                activity.publisher = text
                break

        if not activity.code and not activity.name:
            return None

        return activity

    def get_activity_detail(self, activity_id: int, fetch_all_tabs: bool = True) -> Optional[ActivityDetail]:
        """Récupère les détails complets d'une activité"""
        self._log_separator(f"DÉTAILS ACTIVITÉ ID={activity_id}")
        
        url1 = f"{self.BASE_URL}/activity/index/id/{activity_id}/locale/fr"
        html1 = self._fetch_page(url1, "Onglet Présentation activité")
        
        if not html1:
            return None
        
        detail = self._parse_activity_presentation(html1, activity_id)
        if not detail:
            return None
        
        if fetch_all_tabs:
            time.sleep(0.1)
            url2 = f"{self.BASE_URL}/activity/characteristic/id/{activity_id}/locale/fr"
            html2 = self._fetch_page(url2, "Onglet Caractéristiques activité")
            if html2:
                self._parse_activity_characteristics(html2, detail)
        
        return detail

    def _parse_activity_presentation(self, html: str, activity_id: int) -> Optional[ActivityDetail]:
        """Parse l'onglet Présentation"""
        soup = BeautifulSoup(html, 'html.parser')
        detail = ActivityDetail(id=activity_id)
        detail.detail_url = f"{self.BASE_URL}/activity/index/id/{activity_id}"

        # Name
        h1 = soup.find('h1')
        if h1:
            raw_name = h1.get_text(strip=True)
            detail.name = re.sub(r'^[^\w]*', '', raw_name)

        # Code
        for a in soup.find_all('a', href=re.compile(r'/activity/index/id/')):
            text = a.get_text(strip=True)
            if re.match(r'^[A-Z0-9]{5,}$', text):
                detail.code = text
                break

        if not detail.code:
            match = re.search(r'>([A-Z][A-Z0-9]{5,})</a>', html)
            if match: detail.code = match.group(1)

        # Statuses
        for select in soup.find_all('select'):
            name = select.get('name', select.get('id', '')).lower()
            selected = select.find('option', selected=True)
            if selected:
                val = selected.get_text(strip=True)
                if val and val not in ['--', '', 'Aucun']:
                    if 'webstatus' in name or 'web_status' in name: detail.web_status = val
                    elif 'status' in name: detail.status = val
                    elif 'publisher' in name: detail.publisher = val
                    elif 'target' in name and 'type' not in name: detail.target = val

        # Location
        loc_link = soup.find('a', href=re.compile(r'/location/index/id/'))
        if loc_link:
            detail.location.name = loc_link.get_text(strip=True)
            match = re.search(r'/id/(\d+)', loc_link.get('href', ''))
            if match: detail.location.id = int(match.group(1))

        # Location Fields
        for inp in soup.find_all('input'):
            name = inp.get('name', '').lower()
            value = inp.get('value', '')
            if not value: continue
            
            if 'address' in name: detail.location.address = value
            elif 'zipcode' in name: detail.location.zipcode = value
            elif 'city' in name: detail.location.city = value
            elif 'country' in name: detail.location.country = value
            elif 'phone' in name: detail.location.phone = value
            elif 'email' in name: detail.location.email = value
            elif 'website' in name: detail.location.website = value
            elif 'lat' in name: detail.location.latitude = value
            elif 'lon' in name: detail.location.longitude = value

        # Descriptions
        for ta in soup.find_all('textarea'):
            ta_id = ta.get('id', ta.get('name', ''))
            content = ta.get_text(strip=True)
            if not content: continue
            
            # Simple Fr fallback
            clean = re.sub(r'<[^>]+>', ' ', content).strip()
            if 'name' in ta_id.lower(): detail.descriptions.name['fr'] = clean
            elif 'short' in ta_id.lower(): detail.descriptions.short_description['fr'] = clean
            elif 'description' in ta_id.lower(): detail.descriptions.description['fr'] = clean
            elif 'condition' in ta_id.lower(): detail.descriptions.conditions['fr'] = clean
            elif 'practical' in ta_id.lower(): detail.descriptions.practical_info['fr'] = clean
            elif 'included' in ta_id.lower(): detail.descriptions.included['fr'] = clean
            elif 'not' in ta_id.lower() and ('included' in ta_id.lower() or 'compris' in ta_id.lower()): detail.descriptions.not_included['fr'] = clean

        # Images
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src and 'placeholder' not in src and src.startswith('http'):
                if src not in detail.images: detail.images.append(src)

        return detail

    def _parse_activity_characteristics(self, html: str, detail: ActivityDetail):
        """Parse Caractéristiques"""
        soup = BeautifulSoup(html, 'html.parser')

        # Selects
        for select in soup.find_all('select'):
            name = select.get('name', select.get('id', '')).lower()
            selected = select.find('option', selected=True)
            if selected:
                val = selected.get_text(strip=True)
                if val and val not in ['--', '', 'Aucun', 'Sélectionner']:
                    if 'duration' in name: detail.characteristics.duration = val
                    elif 'roomtype' in name: detail.characteristics.room_type = val
                    elif 'activitytype' in name: detail.characteristics.activity_type = val
                    elif 'subtype' in name: detail.characteristics.activity_subtype = val
                    elif 'nb' in name or 'person' in name: detail.characteristics.nb_persons = val

        # Pricing Inputs
        for inp in soup.find_all('input'):
            name = inp.get('name', '').lower()
            val = inp.get('value', '')
            if not val: continue
            
            try:
                fval = float(val.replace(',', '.').replace(' ', ''))
                if 'saler' in name: detail.pricing.salers = val
                elif 'value' in name and 'price' not in name: detail.pricing.value = fval
                elif 'partner' in name and 'price' in name: detail.pricing.partner_price = fval
                elif 'public' in name and 'price' in name: detail.pricing.public_price = fval
            except ValueError:
                        pass
