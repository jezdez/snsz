import dateparser
import scrapy

NAME_SPLIT_STR = " vom "
VALIDITY_SPLIT_STR = "bis"
AMBIGUITY_SPLIT_STR = "bzw. "
NEW_SPLIT_STR = "NEU: "


class SchoolsSpider(scrapy.Spider):
    name = "schools"
    allowed_domains = [
        "https://www.coronavirus.sachsen.de/amtliche-bekanntmachungen.html"
    ]
    start_urls = [
        "http://https://www.coronavirus.sachsen.de/amtliche-bekanntmachungen.html/"
    ]

    def start_requests(self):
        urls = [
            "https://www.coronavirus.sachsen.de/amtliche-bekanntmachungen.html",
        ]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        # get all table rows in the "Allgemeinverfügungen" box
        rows = response.xpath(
            "//a[contains(text(), 'Allgemeinverfügungen')]//..//..//..//table//tr"
        )
        for row in rows:
            # if there is not table data jump ahead
            if not row.xpath("td"):
                continue
            # first get the name of the school
            name = row.xpath("td[1]//text()").extract_first()
            # and then split it to get name and date
            if NAME_SPLIT_STR not in name:
                print("Split string not in name! Name:", name)
                continue
            name, published_at = name.split(NAME_SPLIT_STR)
            # remove trailing " -" in name
            name = name.rstrip(" -")

            # record if the school is new
            new = name.lower().startswith(NEW_SPLIT_STR.lower())
            if new:
                _, name = name.split(NEW_SPLIT_STR, 1)

            # also parse the date as German text
            parsed_published_at = dateparser.parse(published_at, languages=["de"])

            # get the link to the ruling
            url = row.xpath("td[1]//a//@href").extract_first()

            # next extract the validity of the bulletin
            # which may or may not be multiple dates, because you know, whatever
            validity = row.xpath("td[3]//text()").extract_first()
            if VALIDITY_SPLIT_STR in validity:
                valid_from, valid_to = validity.split(VALIDITY_SPLIT_STR)
                if AMBIGUITY_SPLIT_STR in valid_to:
                    valid_to = valid_to.split(AMBIGUITY_SPLIT_STR)
                else:
                    valid_to = [valid_to]
                try:
                    parsed_valid_from = dateparser.parse(valid_from)
                    parsed_valid_to = [dateparser.parse(val) for val in valid_to]
                except ValueError:
                    # here be dragons
                    continue
            else:
                # in case the validity is just one item or something
                # just treat it as one (?)
                try:
                    parsed_valid_from = parsed_valid_to = dateparser.parse(validity)
                except ValueError:
                    continue

            # finally, the "status" of the current bulletin
            status = row.xpath("td[2]//text()").extract_first()

            yield {
                "name": name,
                "published_at": parsed_published_at,
                "status": status,
                "url": url,
                "validity": validity,
                "valid_from": parsed_valid_from,
                "valid_to": parsed_valid_to,
                "new": new,
            }
