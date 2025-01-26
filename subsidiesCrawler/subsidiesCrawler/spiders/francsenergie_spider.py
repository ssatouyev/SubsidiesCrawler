import scrapy
import json
import os

class MySpider(scrapy.Spider):
    name = "francsenergie_spider"

    def start_requests(self):
        # Charger le fichier JSON contenant les communes
        with open('/Users/saddamsatouyev/SubsidiesCrawler/subsidiesCrawler/vaud_communes.json', 'r', encoding='utf-8') as f:
            communes = json.load(f)
        
        # Construire les URLs dynamiques avec le code postal et le nom de la commune
        for commune in communes:
            postal_code = commune['postalCode']
            commune_name = commune['name'].replace(" ", "-")  # Remplacer les espaces par des tirets
            url = f"https://www.francsenergie.ch/fr/{postal_code}-{commune_name}/building/personal"
            yield scrapy.Request(url=url, callback=self.parse, meta={'commune_name': commune['name'], 'postal_code': postal_code})

    def parse(self, response):
        commune_name = response.meta['commune_name']
        postal_code = response.meta['postal_code']

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
            if filtered_fields:
                subsidies = filtered_fields[0]['subsidies']
            else:
                subsidies = []
            filtered_partners_subsidies = [filtered_field for filtered_field in subsidies if filtered_field['contributor']['url'] != 'https://pronovo.ch/fr/']
            
            # Mettre à jour les champs avec les champs filtrés
            json_data['town']['fields'] = filtered_partners_subsidies
            
            # Chemin du fichier de sortie
            output_file = os.path.join('/Users/saddamsatouyev/SubsidiesCrawler/subsidiesCrawler/subsidies_data', f"{commune_name}_{postal_code}.json")
            
            # Sauvegarde du JSON dans un fichier
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            
            self.log(f"JSON sauvegardé dans {output_file}")
        else:
            self.log("Aucun JSON trouvé dans le div spécifié.")