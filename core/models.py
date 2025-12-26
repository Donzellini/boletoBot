from dataclasses import dataclass
from typing import Optional
import re

@dataclass
class Boleto:
    origem: str
    titulo: str
    linha_digitavel: Optional[str] = None
    pix: Optional[str] = None
    arquivo_path: Optional[str] = None
    link_externo: Optional[str] = None

    def __post_init__(self):
        """Limpa automaticamente a linha digitável ao criar o objeto."""
        if self.linha_digitavel:
            self.linha_digitavel = re.sub(r'\D', '', self.linha_digitavel)
