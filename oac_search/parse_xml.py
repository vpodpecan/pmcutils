from bs4 import BeautifulSoup as bs


def extract_text(xmldata, skipTags=['xref', 'table', 'graphic', 'ext-link',
                                    'media', 'inline-formula', 'disp-formula', 'references',
                                    'ref-list', 'ack']):
    root = bs(xmldata, 'xml')
    for tag in skipTags:
        _ = [x.extract() for x in root.find_all(tag)]
        # unwanted = root.find_all(tag)
        # unwanted.extract()
    text = root.get_text()
    return text
