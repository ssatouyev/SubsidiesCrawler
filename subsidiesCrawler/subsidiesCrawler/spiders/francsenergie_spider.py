import scrapy
import json
import os

class MySpider(scrapy.Spider):
    name = "francsenergie_spider"
    start_urls = ["https://www.francsenergie.ch/fr/1261-Le-Vaud/building/personal"]

    def parse(self, response):
        # Extraction des paragraphes (exemple)
        for paragraph in response.css('p::text').getall():
            yield {"paragraphe": paragraph}

        # Sélection du div contenant le JSON
        div = response.css('div[data-svelte-component="subsidies"]::attr(data-svelte-props)').get()
        
        if div:
            # Chargement du JSON
            json_data = json.loads(div)
            
            # Chemin du fichier de sortie
            output_file = os.path.join(self.settings.get('FILES_STORE', ''), 'subsidies_data.json')
            
            # Sauvegarde du JSON dans un fichier
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            
            self.log(f"JSON sauvegardé dans {output_file}")
        else:
            self.log("Aucun JSON trouvé dans le div spécifié.")