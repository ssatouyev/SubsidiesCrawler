import scrapy


class SubsidiesSpiderSpider(scrapy.Spider):
    name = "subsidies_spider"
    allowed_domains = ["example.com"]
    start_urls = ["https://example.com"]

    def parse(self, response):
        pass
