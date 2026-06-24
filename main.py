import pandas as pd
from tqdm import tqdm

from parser.address_parser import AddressParser
from fuzzy.similarity import AddressSimilarityExtractor
from fuzzy.fuzzy_matcher import FuzzyAddressMatcher


class AddressMatchingPipeline:

    def __init__(self):
        self.parser = AddressParser()
        self.similarity_extractor = AddressSimilarityExtractor()
        self.matcher = FuzzyAddressMatcher()
    
    def process_row(self, original_address: str, modified_address: str):
        original = self.parser.parse(original_address)

        modified = self.parser.parse(modified_address)

        features = self.similarity_extractor.extract(original, modified)

        score = self.matcher.match_addresses(original, modified)

        classification = self.matcher.classify(score)

        return {
            "score": score,
            "classification": classification,
            "street_similarity": features.street_name,
            "number_similarity": features.number,
            "neighborhood_similarity": features.neighborhood,
            "city_similarity": features.city,
            "state_similarity": features.state,
            "zip_code_similarity": features.zip_code
        }
    
    def run(self, input_csv: str, output_csv: str):
        df = pd.read_csv(input_csv)

        results = []
        for _, row in tqdm(df.iterrows(), total=len(df)):

            try:
                result = self.process_row(row["endereco_original"], row["endereco_modificado"])

                result["endereco_original"] = row["endereco_original"]
                result["endereco_modificado"] = row["endereco_modificado"]
                result["tipo_erro"] = row["tipo_erro"]
                result["label"] = row["label"]

                results.append(result)
        
            except Exception as e:
                print(f"Erro ao processar linha {_}: {e}")

        pd.DataFrame(
            results
        ).to_csv(
            output_csv,
            index=False
        )

        print(
            f"Resultado salvo em "
            f"{output_csv}"
        )

def main():
    pipeline = AddressMatchingPipeline()
    pipeline.run("data/modified_addresses.csv", "data/results.csv")

if __name__ == "__main__":
    main()