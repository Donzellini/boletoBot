from dataclasses import dataclass
from typing import Optional
import re

@dataclass
class Boleto:
    """
    Representação padronizada de um boleto dentro do sistema.
    Responsável por garantir que os dados básicos estejam limpos.
    """
    origem: str
    titulo: str
    valor: Optional[str] = None
    linha_digitavel: Optional[str] = None
    pix: Optional[str] = None
    arquivo_path: Optional[str] = None
    link_externo: Optional[str] = None

    def __post_init__(self):
        """
        Executado automaticamente após a criação do objeto.
        Limpa a linha digitável para manter apenas números.
        """
        if self.linha_digitavel:
            # Remove qualquer caractere que não seja número (pontos, espaços, barras)
            self.linha_digitavel = re.sub(r'\D', '', self.linha_digitavel)