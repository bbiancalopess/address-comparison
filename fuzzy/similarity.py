from rapidfuzz import fuzz

from parser.address import Address
from fuzzy.models import SimilarityFeatures


class AddressSimilarityExtractor:

    @staticmethod
    def text_similarity(a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        
        return fuzz.token_sort_ratio(a, b) / 100
    
    @staticmethod
    def number_similarity(n1: str, n2: str) -> float:
        try:
            n1 = int(n1)
            n2 = int(n2)

            diff = abs(n1 - n2)

            return max(0.0, 1 - diff / 20)
    
        except:
            return 0.0
    
    def extract(self, a: Address, b: Address) -> SimilarityFeatures:
        street_name_sim = self.text_similarity(a.street_name, b.street_name)
        street_type_sim = self.text_similarity(a.street_type, b.street_type)
        number_sim = self.number_similarity(a.number, b.number)
        neighborhood_sim = self.text_similarity(a.neighborhood, b.neighborhood)
        city_sim = self.text_similarity(a.city, b.city)
        state_sim = self.text_similarity(a.state, b.state)
        zip_code_sim = self.text_similarity(a.zip_code, b.zip_code)

        return SimilarityFeatures(
            street_name=street_name_sim,
            street_type=street_type_sim,
            number=number_sim,
            neighborhood=neighborhood_sim,
            city=city_sim,
            state=state_sim,
            zip_code=zip_code_sim
        )