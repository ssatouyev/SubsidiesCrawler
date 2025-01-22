import scrapy

class MySpider(scrapy.Spider):
    name = "francsenergie_spider"
    start_urls = ["https://www.francsenergie.ch/fr/2000-Neuchatel/building/personal"]  # Remplace par l'URL cible

    def parse(self, response):
        # Recherche d'un texte spécifique dans la page
        search_text = "photovoltaïques"
        if search_text in response.text:
            self.log(f"Texte trouvé: {search_text}")
        else:
            self.log(f"Texte NON trouvé: {search_text}")

        # Extraction des paragraphes (exemple)
        for paragraph in response.css('p::text').getall():
            yield {"paragraphe": paragraph}