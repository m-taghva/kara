from pywikibot import family

class Family(family.Family):  # noqa: D101

    name = 'kateb'
    langs = {
        'fa': 'user:pass@kateb-URL',  # uesr:pass of web server@kateb_domain  Attention!! do not type '#' in user or pass here, replace it with Ascii code "%23"
    }

    def scriptpath(self, code):
        return {
            'fa': '/w',
        }[code]

    def protocol(self, code):
        return {
            'fa': 'https',
        }[code]
