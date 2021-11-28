import dateparser
import pytz
import scrapy

NAME_SPLIT_STR = " vom "
VALIDITY_SPLIT_STR = "bis"
AMBIGUITY_SPLIT_STR = "bzw. "
NEW_SPLIT_STR = "NEU: "


def parse_german_datetime(datetime, *args, **kwargs):
    return dateparser.parse(datetime, languages=["de"], *args, **kwargs)


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
            recently_added = name.lower().startswith(NEW_SPLIT_STR.lower())
            if recently_added:
                _, name = name.split(NEW_SPLIT_STR, 1)

            # also parse the date as German text
            parsed_published_at = parse_german_datetime(published_at)

            # get the link to the ruling
            url = row.xpath("td[1]//a//@href").extract_first()

            # next extract the validity of the bulletin
            # which may or may not be multiple dates, because you know, whatever
            # we ignore the earlier date
            validity = row.xpath("td[3]//text()").extract_first()
            if VALIDITY_SPLIT_STR in validity:
                valid_from, valid_to = validity.split(VALIDITY_SPLIT_STR)
                if AMBIGUITY_SPLIT_STR in valid_to:
                    _, valid_to = valid_to.split(AMBIGUITY_SPLIT_STR)
                try:
                    parsed_valid_from = parse_german_datetime(valid_from)
                    parsed_valid_to = parse_german_datetime(valid_to)
                except ValueError:
                    # here be dragons
                    continue
            else:
                # in case the validity is just one item or something
                # just treat it as one (?)
                try:
                    parsed_valid_from = parsed_valid_to = parse_german_datetime(validity)
                except ValueError:
                    continue

            if parsed_valid_to:
                epoch_valid_to = int(
                    pytz.utc.localize(parsed_valid_to).timestamp()
                )
            else:
                epoch_valid_from = None
            if parsed_valid_from:
                epoch_valid_from = int(
                    pytz.utc.localize(parsed_valid_from).timestamp()
                )
            else:
                epoch_valid_to = None

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
                "epoch_valid_from": epoch_valid_from,
                "epoch_valid_to": epoch_valid_to,
                "recently_added": recently_added,
            }
