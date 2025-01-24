import scrapy
import re
from together import Together

class MySpider(scrapy.Spider):
    name = "francsenergie_spider"
    start_urls = ["https://www.francsenergie.ch/fr/2000-Neuchatel/building/personal"]  # Remplace par l'URL cible

    def parse(self, response):
        # Liste des mots-clés à rechercher
        keywords = ["photovoltaïques", "photovoltaiques", "installations solaires"]
        
        # Recherche des mots-clés dans le texte de la page
        for keyword in keywords:
            if keyword in response.text:
                self.log(f"Texte trouvé: {keyword}")
                
                # Extraction du texte à partir du mot-clé trouvé jusqu'à 200 caractères suivants
                pattern = re.escape(keyword) + r'.{0,200}'
                match = re.search(pattern, response.text)
                if match:
                    extracted_text = match.group(0)
                    self.log(f"Texte extrait: {extracted_text}")
                    
                    # Envoi du texte extrait à l'IA LLaMA
                    self.query_llama(extracted_text)
            else:
                self.log(f"Texte NON trouvé: {keyword}")

        # Extraction des paragraphes (exemple)
        for paragraph in response.css('p::text').getall():
            yield {"paragraphe": paragraph}

    def query_llama(self, text):
        # Initialisation du client Together
        client = Together()
        
        # Préparation du message pour l'IA
        message = f"Y a-t-il des informations sur les subventions pour l'installation photovoltaïque dans ce texte : {text} ?"
        
        # Création du flux de complétion
        stream = client.chat.completions.create(
            model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
            messages=[{"role": "user", "content": message}],
            stream=True,
        )

        # Impression de la réponse de l'IA
        for chunk in stream:
            print(chunk.choices[0].delta.content or "", end="", flush=True)