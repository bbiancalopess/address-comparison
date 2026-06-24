import re
import unicodedata


class NormalizadorDeEndereco:

    ABREVIACOES = {
        "AV.": "AVENIDA",
        "AV": "AVENIDA",
        "R.": "RUA",
        "R": "RUA",
        "TV": "TRAVESSA",
        "TRAV.": "TRAVESSA"
    }

    def normalize(self, text: str) -> str:
        text = text.upper()

        text = self._remove_accents(text)
        
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    @staticmethod
    def _remove_accents(text: str) -> str:
        return ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )