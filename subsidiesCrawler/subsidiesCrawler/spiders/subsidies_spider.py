import scrapy
import json
import os
from urllib.parse import urlparse
import re

class SubsidiesSpiderSpider(scrapy.Spider):
    name = "subsidies_spider"
    
    # Configuration des mots-clés mise à jour
    title_keywords = {
        "photovoltaïque": 1,
        "photovoltaïques": 1,
        "photovoltaic": 1,
        "subvention": 1,
        "subventions": 1,
        "commune": 1,
        "communes": 1,
        "communal": 1
    }
    content_keywords = [
        "photovoltaïque", "photovoltaïques", "photovoltaic",
        "subvention", "subventions",
        "commune", "communes", "communal"
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.output_dir = kwargs.get("output_dir", "output_subsidies")
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.communes_list = []        # Liste des communes du JSON
        self.communes_no_info = []     # Communes sans pages pertinentes
        self.visited_urls = set()      # Pour éviter de revisiter la même URL
        self.results = {}              # Pour stocker les résultats

    def start_requests(self):
        # Charger les données JSON
        json_path = self.settings.get("VAUD_COMMUNES_FILE", "") or \
                    "/Users/saddamsatouyev/SubsidiesCrawler/subsidiesCrawler/subsidiesInfoJSON/InclompleteInfoSubsidies.json"

        with open(json_path, 'r', encoding='utf-8') as file:
            communes = json.load(file)

        for commune in communes:
            commune_name = commune.get('name')
            url = commune.get('sourceUrl')
            ofs = commune.get('ofs')  # Récupérer l'identifiant OFS
            postal_code = commune.get('postalCode')  # Récupérer le code postal
            
            if commune_name and url:
                # Garde le nom de la commune pour le suivi
                self.communes_list.append(commune_name)
                
                # Définir allowed_domains dynamiquement pour inclure la variante avec et sans "www"
                domain = urlparse(url).netloc.lower().split(':')[0]
                if domain:
                    if domain.startswith("www."):
                        domain_naked = domain[4:]
                        variants = [domain, domain_naked]
                    else:
                        domain_with_www = "www." + domain
                        variants = [domain, domain_with_www]

                    if not hasattr(self, 'allowed_domains'):
                        self.allowed_domains = []
                    for d in variants:
                        if d not in self.allowed_domains:
                            self.allowed_domains.append(d)
                
                yield scrapy.Request(
                    url=url,
                    callback=self.parse,
                    meta={"commune_name": commune_name, "depth": 0, "ofs": ofs, "postal_code": postal_code},
                    errback=self.errback
                )

    def parse(self, response):
        commune_name = response.meta["commune_name"]
        current_depth = response.meta["depth"]
        ofs = response.meta["ofs"]
        postal_code = response.meta["postal_code"]

        # Évite de revisiter la même URL
        if response.url in self.visited_urls:
            return
        self.visited_urls.add(response.url)

        # Si le contenu n'est pas textuel (ex. PDF), on ignore le traitement de la page
        content_type = response.headers.get('Content-Type', b'').decode('utf-8')
        if "text" not in content_type:
            self.logger.debug(f"Contenu non-textuel détecté dans parse, ignorer le traitement pour: {response.url} (Content-Type: {content_type})")
            return

        # Vérification de la présence des mots-clés
        relevant_text = self.find_keywords(response)
        if relevant_text:
            self.logger.info(f"[{commune_name}] Page pertinente : {response.url}")
            
            result = {
                "url": response.url,
                "content": relevant_text,
                "ofs": ofs,  # Ajouter l'identifiant OFS
                "postal_code": postal_code  # Ajouter le code postal
            }
            
            # Stocker tous les résultats
            self.results.setdefault(commune_name, []).append(result)

            # Écrire immédiatement dans le fichier JSON
            file_name = f"{commune_name}.json"
            file_path = os.path.join(self.output_dir, file_name)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.results[commune_name], f, ensure_ascii=False, indent=2)
            self.logger.info(f"[{commune_name}] => {file_name} mis à jour ({len(self.results[commune_name])} pages pertinentes).")
        else:
            self.logger.debug(f"[{commune_name}] Page NON pertinente : {response.url}")

        # Limite la profondeur à 3 (modifiable selon les besoins)
        if current_depth < 2:
            # Suivre les liens internes
            for href in response.css('a::attr(href)').getall():
                next_page = response.urljoin(href)
                # Filtre pour rester sur le même domaine
                if urlparse(next_page).netloc == urlparse(response.url).netloc:
                    yield scrapy.Request(
                        next_page,
                        callback=self.parse,
                        meta={"commune_name": commune_name, "depth": current_depth + 1, "ofs": ofs, "postal_code": postal_code},
                        errback=self.errback
                    )

    def find_keywords(self, response):
        """
        Vérifie la présence des catégories de mots-clés dans les titres et le contenu.
        Retourne True si toutes les catégories de mots-clés sont trouvées, sinon False.
        """
        # Mots-clés dans les titres
        titles_text = " ".join(response.css('h1::text, h2::text, h3::text, h4::text, h5::text, h6::text').getall()).lower()

        # Mots-clés dans le texte global
        text_elements = response.css('::text').getall()
        text_content = " ".join(text_elements).lower()

        # Vérifier la présence de chaque catégorie de mots-clés
        photovoltaic_keywords = ["photovoltaïque", "photovoltaïques", "photovoltaic"]
        communal_keywords = ["commune", "communes", "communal"]
        subsidy_keywords = ["subvention", "subventions"]

        photovoltaic_found = any(keyword in titles_text or keyword in text_content for keyword in photovoltaic_keywords)
        communal_found = any(keyword in titles_text or keyword in text_content for keyword in communal_keywords)
        subsidy_found = any(keyword in titles_text or keyword in text_content for keyword in subsidy_keywords)

        # Si tous les mots-clés sont trouvés, extraire le texte pertinent
        if photovoltaic_found and communal_found and subsidy_found:
            relevant_text = self.extract_relevant_text(text_content, photovoltaic_keywords + communal_keywords + subsidy_keywords)
            return relevant_text

        return None

    def extract_relevant_text(self, text, keywords, max_length=15000):
        """
        Extrait un segment de texte autour de chaque mot-clé trouvé, avec 3 000 caractères avant et 12 000 caractères après.
        Évite les doublons en vérifiant le chevauchement des segments.
        """
        segments = []
        last_end = 0  # Pour suivre la fin du dernier segment ajouté

        for keyword in keywords:
            start = 0
            while start < len(text):
                index = text.find(keyword, start)
                if index == -1:
                    break
                # Définir les limites du segment
                segment_start = max(0, index - 3000)
                segment_end = min(len(text), index + 12000)

                # Ajouter le segment seulement s'il ne chevauche pas le dernier segment ajouté
                if segment_start >= last_end:
                    segments.append(text[segment_start:segment_end])
                    last_end = segment_end  # Mettre à jour la fin du dernier segment ajouté

                start = index + len(keyword)

        # Combiner les segments
        combined_text = " ".join(segments)

        # Nettoyer le texte pour supprimer les espaces blancs, tabulations et nouvelles lignes excessives
        cleaned_text = re.sub(r'\s+', ' ', combined_text).strip()

        return cleaned_text[:max_length]

    def errback(self, failure):
        """
        Gestion des erreurs HTTP, DNS, Timeout, etc.
        """
        self.logger.error(f"Erreur lors de la requête: {failure.value}")
    
    def closed(self, reason):
        not_found_path = os.path.join(self.output_dir, "communes_not_found.txt")
        
        with open(not_found_path, 'w', encoding='utf-8') as nf:
            for commune_name in self.communes_list:
                # Récupérer les pages pertinentes
                pages_pertinentes = self.results.get(commune_name, [])
                
                if pages_pertinentes:
                    # Écrit le JSON de la commune avec les résultats
                    file_name = f"{commune_name}.json"
                    file_path = os.path.join(self.output_dir, file_name)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(pages_pertinentes, f, ensure_ascii=False, indent=2)
                    self.logger.info(f"[{commune_name}] => {file_name} créé ({len(pages_pertinentes)} pages pertinentes).")
                else:
                    # Liste les communes sans info
                    nf.write(f"{commune_name}\n")
                    self.logger.warning(f"[{commune_name}] Aucune page pertinente trouvée.")
        
        self.logger.info(f"Spider terminé. Raison: {reason}")