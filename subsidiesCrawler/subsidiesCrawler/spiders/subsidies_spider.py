import scrapy
import json
import os
from urllib.parse import urlparse

class SubsidiesSpiderSpider(scrapy.Spider):
    name = "subsidies_spider"
    
    # Configuration des mots-clés et de leurs poids
    url_keywords = ["energie", "developpement-durable", "subventions"]
    title_keywords = {
        "subventions": 5,
        "photovoltaïque": 5
    }
    content_keywords = [
        "installation", "photovoltaïque",
        "consommation", "subvention", "chf", "pronovo"
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
                    "/Users/saddamsatouyev/SubsidiesCrawler/subsidiesCrawler/test.json"

        with open(json_path, 'r', encoding='utf-8') as file:
            communes = json.load(file)

        for commune in communes:
            commune_name = commune.get('name')
            url = commune.get('websiteUrl')
            
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
                meta={"commune_name": commune_name, "depth": 0},
                errback=self.errback
            )

    def parse(self, response):
        commune_name = response.meta["commune_name"]
        current_depth = response.meta["depth"]

        # Évite de revisiter la même URL
        if response.url in self.visited_urls:
            return
        self.visited_urls.add(response.url)

        # Si le contenu n'est pas textuel (ex. PDF), on ignore le traitement de la page
        content_type = response.headers.get('Content-Type', b'').decode('utf-8')
        if "text" not in content_type:
            self.logger.debug(f"Contenu non-textuel détecté dans parse, ignorer le traitement pour: {response.url} (Content-Type: {content_type})")
            return

        # Calcul du score pour la page
        score, keywords_found = self.calculate_score(response)
        if score > 0:
            self.logger.info(f"[{commune_name}] Page pertinente (score {score}) : {response.url}")
            
            # Extraire le contenu des balises de texte
            text_elements = response.css('p::text, h1::text, h2::text, h3::text, h4::text, h5::text, h6::text, li::text, span::text, div::text').getall()
            # Nettoyer le contenu pour supprimer les espaces blancs et les lignes vides
            content = "\n".join(line.strip() for line in text_elements if line.strip())

            result = {
                "url": response.url,
                "score": score,
                "keywords_found": keywords_found,
                "content": content
            }
            
            # Stocker temporairement les résultats
            self.results.setdefault(commune_name, []).append(result)

            # Trier et garder les trois meilleurs résultats
            self.results[commune_name].sort(key=lambda x: x['score'], reverse=True)
            top_pages = self.results[commune_name][:3]

            # Écrire immédiatement dans le fichier JSON
            file_name = f"{commune_name}.json"
            file_path = os.path.join(self.output_dir, file_name)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(top_pages, f, ensure_ascii=False, indent=2)
            self.logger.info(f"[{commune_name}] => {file_name} mis à jour ({len(top_pages)} pages pertinentes).")
        else:
            self.logger.debug(f"[{commune_name}] Page NON pertinente (score 0) : {response.url}")

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
                        meta={"commune_name": commune_name, "depth": current_depth + 1},
                        errback=self.errback
                    )

    def calculate_score(self, response):
        """
        Calcule un score en fonction de la présence de certains mots-clés
        dans l'URL, les titres et le contenu.
        Retourne (score, liste_des_mots_clés_trouvés).
        """
        # Vérifie que le contenu de la réponse est textuel
        content_type = response.headers.get('Content-Type', b'').decode('utf-8')
        if "text" not in content_type:
            self.logger.debug(f"Contenu non-textuel détecté, ignorer le traitement pour: {response.url} (Content-Type: {content_type})")
            return 0, []

        score = 0
        keywords_found = []

        # 1) Mots-clés dans l'URL
        url_lower = response.url.lower()
        for keyword in self.url_keywords:
            if keyword in url_lower:
                score += 5
                keywords_found.append(f"URL:{keyword}")

        # 2) Mots-clés dans les titres
        titles_text = " ".join(response.css('h1::text, h2::text, h3::text, h4::text, h5::text, h6::text').getall()).lower()
        for keyword, weight in self.title_keywords.items():
            if keyword in titles_text:
                score += weight
                keywords_found.append(f"TITLE:{keyword}")

        # 3) Mots-clés dans le texte global
        text_elements = response.css('::text').getall()
        text_content = " ".join(text_elements).lower()
        for keyword in self.content_keywords:
            if keyword in text_content:
                score += 0.5
                keywords_found.append(f"CONTENT:{keyword}")

        return score, keywords_found

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
                    # Trier les pages par score décroissant
                    pages_pertinentes.sort(key=lambda x: x['score'], reverse=True)
                    # Garder seulement les trois premiers
                    top_pages = pages_pertinentes[:3]
                    
                    # Écrit le JSON de la commune avec les trois meilleurs scores
                    file_name = f"{commune_name}.json"
                    file_path = os.path.join(self.output_dir, file_name)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(top_pages, f, ensure_ascii=False, indent=2)
                    self.logger.info(f"[{commune_name}] => {file_name} créé ({len(top_pages)} pages pertinentes).")
                else:
                    # Liste les communes sans info
                    nf.write(f"{commune_name}\n")
                    self.logger.warning(f"[{commune_name}] Aucune page pertinente trouvée.")
        
        self.logger.info(f"Spider terminé. Raison: {reason}")