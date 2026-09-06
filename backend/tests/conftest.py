"""
Configuração e fixtures globais para a suíte de testes do CogniMove.

Garante que a suíte unitária execute com rapidez e sem dependência de pacotes
pesados de deep learning (como PyTorch e Ultralytics), fornecendo mocks
automáticos caso não estejam instalados no ambiente de execução.
"""
import sys
from unittest.mock import MagicMock

# Mock de ultralytics se não estiver instalado no ambiente (ex.: CI mínimo)
if "ultralytics" not in sys.modules:
    try:
        import ultralytics  # noqa: F401
    except ImportError:
        mock_ultralytics = MagicMock()
        sys.modules["ultralytics"] = mock_ultralytics
