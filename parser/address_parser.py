import re

from parser.address import Address
from parser.normalizer import AddressNormalizer
from parser import patterns


class AddressParser:

    def __init__(self):
        self.normalizer = AddressNormalizer()
    
    def parse(self, raw_address: str) -> Address:
        text = self.normalizer.normalize(raw_address)

        address = Address()

        address.zip_code = self._extract_zip_code(text)
        address.state = self._extract_state(text)
        address.number = self._extract_number(text)
        address.street_type = self._extract_street_type(text)
        address.street_name = self._extract_street_name(text, address.street_type, address.number)
        # address.city = self._extract_city(text)
        # address.neighborhood = self._extract_neighborhood(text)

        return address
    
    def _extract_zip_code(self, text: str) -> str:
        match_ = re.search(r'\b\d{5}-?\d{3}\b', text)
        if match_:
            return match_.group()
        
        return ""

    def _extract_state(self, text: str) -> str:
        text = text.split()

        for token in reversed(text):
            if token in patterns.UFS:
                return token
        
        return ""

    def _extract_number(self, text: str) -> str:
        text = re.sub(r'\b\d{5}-?\d{3}\b', '', text)
        match_ = re.search(r'\b\d+\b', text)
        if match_:
            return match_.group()
        
        return ""

    def _extract_street_type(self, text: str) -> str:
        for street_type in patterns.STREET_TYPES:
            if text.startswith(street_type):
                return street_type
        
        return ""
    
    def _extract_street_name(self, text: str, street_type: str, number: str) -> str:
        if street_type:
            text = text.replace(street_type, '', 1)

        if number:
            text = text.replace(number, '', 1)
        
        return text.strip(" ,")
