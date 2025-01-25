import scrapy
import json
import os

class MySpider(scrapy.Spider):
    name = "francsenergie_spider"
    start_urls = ["https://www.francsenergie.ch/fr/2000-Neuchatel/building/personal"]

    def parse(self, response):
        # Extraction des paragraphes (exemple)
        for paragraph in response.css('p::text').getall():
            yield {"paragraphe": paragraph}

        # Sélection du div contenant le JSON
        div = response.css('div[data-svelte-component="subsidies"]::attr(data-svelte-props)').get()
        
        if div:
            # Chargement du JSON
            json_data = json.loads(div)
            
            # Filtrer les champs pour ne garder que ceux avec 'name' == 'Production d'électricité'
            filtered_fields = [field for field in json_data['town']['fields'] if field['name'] == 'Production d’électricité']
            print(filtered_fields)
            print("🔥🔥🔥🔥🔥")
            # Mettre à jour les champs avec les champs filtrés
            json_data['town']['fields'] = filtered_fields
            
            # Chemin du fichier de sortie
            output_file = os.path.join(self.settings.get('FILES_STORE', ''), 'subsidies_data.json')
            
            # Sauvegarde du JSON dans un fichier
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            
            self.log(f"JSON sauvegardé dans {output_file}")
        else:
            self.log("Aucun JSON trouvé dans le div spécifié.")