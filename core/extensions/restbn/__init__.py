from .md import MarketDataXT
from .td import TraderXT
from extensions import EXTENSION_REGISTRY_MD, EXTENSION_REGISTRY_TD
EXTENSION_REGISTRY_MD.register_extension('restbn', MarketDataXT)
EXTENSION_REGISTRY_TD.register_extension('restbn', TraderXT)
