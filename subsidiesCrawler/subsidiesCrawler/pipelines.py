# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter


class SubsidiesCrawlerPipeline:
    def process_item(self, item, spider):
        # Si vous avez besoin de traiter l'item, faites-le ici
        return item
