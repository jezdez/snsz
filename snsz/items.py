import scrapy


class School(scrapy.Item):
    id = scrapy.Field()
    name = scrapy.Field()
    publiced_at = scrapy.Field()
    address = scrapy.Field()
    status = scrapy.Field()
    valid_from = scrapy.Field()
    valid_to = scrapy.Field()
    url = scrapy.Field()

    def __repr__(self):
        """only print out title after exiting the Pipeline"""
        return repr({"name": self["name"]})
